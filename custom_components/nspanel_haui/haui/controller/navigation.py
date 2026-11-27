from __future__ import annotations

import contextlib
import math
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ..device_config import resolve_snapshot_max_age as _resolve_snapshot

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPCommand, ESPEvent, PopupPanelKey
from ..mapping.panel import PAGE_MAPPING
from ..utils.page import get_page_class_for_panel, get_page_id_for_panel

# Overflow recovery backoff: base delay, doubling, then a pause until quiet
# for the reset period.
OVERFLOW_RECOVERY_DELAY = 0.5  # seconds, debounce before first recovery
OVERFLOW_RECOVERY_MAX_ATTEMPTS = 5  # consecutive recoveries before pausing
OVERFLOW_RECOVERY_RESET = 30.0  # seconds without overflows to reset backoff

# seconds to wait for the page ack before resending goto_page.
PAGE_ACK_TIMEOUT = 10.0

# A panel outside navigation with the kwargs it was opened with.
StackEntry = tuple[HAUIPanel, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class NavigationSnapshot:
    """The navigation state an idle page covered, restored when it is left."""

    panel: HAUIPanel | None
    panel_kwargs: dict[str, Any]
    current_nav: HAUIPanel | None
    current_nav_kwargs: dict[str, Any]
    stack: list[StackEntry]
    created_at: float = field(default_factory=time.monotonic)

    @property
    def age(self) -> float:
        """Seconds since the snapshot was taken."""
        return time.monotonic() - self.created_at


class HAUINavigationController(HAUIBase):
    """Navigation Controller

    Provides the whole navigation functionality. Implemented as a controller
    so full app access is possible when navigating.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for navigation controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Navigation Controller with config: {config}", level="DEBUG")
        self.page: HAUIPage | None = None
        self.panel: HAUIPanel | None = None  # current panel config
        self.panel_kwargs: dict[str, Any] = {}  # current panel kwargs
        self._current_nav: HAUIPanel | None = None  # current nav panel config
        self._current_nav_kwargs: dict[str, Any] = {}  # current nav panel kwargs
        self._ids: list[UUID] = []  # ids of nav panels
        self._id_to_idx: dict[UUID, int] = {}  # O(1) index lookup for nav panels
        self._home_panel: HAUIPanel | None = None  # home panel config
        # idle page: automatic page-switch target, never display-off.
        self._idle_panel: HAUIPanel | None = None  # current idle page
        self._idle_panels: list[HAUIPanel] = []  # carousel, cycles on each entry
        self._idle_panel_idx = 0  # next carousel index
        # True while the idle page is displayed; a stacked overlay can suspend
        # the session.
        self._idle_panel_active = False
        # An overlay opened from the idle page suspends its session until the
        # overlay stack returns to that page.
        self._idle_panel_suspended = False
        self._page_timeout: str | None = None  # Timer for switching pages
        # request time of the pending page change; a touch after it means
        # goto_page was lost.
        self._page_change_ts: float = 0.0
        self._buffer_overflow_timer: str | None = None  # Debounced re-render after overflow
        self._overflow_recoveries = 0  # consecutive overflow recoveries (backoff)
        self._last_overflow_ts: float = 0.0  # monotonic time of last overflow event
        self._page_settle_timer: str | None = None  # Delayed re-render after page event settle
        self._close_timeout: str | None = None  # Timer for panel auto close
        # activity clock shared by auto-home and the idle page; checked every
        # second.
        self._activity_ts: float = time.monotonic()
        # True from a connect until the restored page has been displayed: the
        # inactivity check must not run while that navigation is in flight.
        self._resume_pending = True
        self._idle_check_timer: str | None = None  # 1 s level-triggered inactivity check
        self._stack: list[StackEntry] = []  # stack for non-nav panels
        self._snapshot: NavigationSnapshot | None = None  # state the idle page covered
        self._navigating = False  # re-entrance guard for navigation operations
        self._pending_reload = False  # reload was queued while navigating

    # part

    def _resolve_special_panels(self, *, log: bool = False) -> list:
        """Resolve nav-panel ids and the home/idle-page special panels."""
        nav_panels = self.app.device_config.get_panels(filter_nav_panel=True)
        self._ids = [panel.id for panel in nav_panels]
        self._id_to_idx = {panel_id: idx for idx, panel_id in enumerate(self._ids)}
        panel_key = self.app.device.get("home_panel")
        self._home_panel = self.app.device_config.get_panel(panel_key) if panel_key else None
        if log and panel_key:
            self.log(
                f"Home panel using panel {self._home_panel.id}"
                if self._home_panel
                else f"Home panel key '{panel_key}' not found"
            )
        if self._home_panel is None and len(self._ids) > 0:
            if log:
                self.log(f"Using first panel {self._ids[0]} as home panel")
            self._home_panel = nav_panels[0]
        # idle pages: one key or a carousel cycled on each automatic switch.
        self._resolve_idle_panels(log=log)
        return nav_panels

    def _resolve_idle_panels(self, *, log: bool = False) -> None:
        """Resolve the idle page carousel from config.

        Resetting the carousel cursor when the configured list changes makes
        repeated reloads resume at the first entry instead of mid-list.
        """
        idle_keys = self.app.device.get("idle_panel")
        use_auto_page = self.app.device.get("use_auto_page")
        extra = self.app.device.get("idle_panel_extra")
        candidates: list[str] = []
        if isinstance(idle_keys, list):
            candidates = [k for k in idle_keys if k]
        elif isinstance(idle_keys, str) and idle_keys:
            candidates = [idle_keys]
        if isinstance(extra, str):
            candidates += [k.strip() for k in extra.split(",") if k.strip()]
        new_panels: list[HAUIPanel] = []
        seen: set[str] = set()
        for key in candidates:
            if key in seen:
                continue
            seen.add(key)
            panel = self.app.device_config.get_panel(key)
            if panel is None:
                if use_auto_page is True:
                    self.log(f"Idle panel key '{key}' not found", level="WARNING")
                continue
            new_panels.append(panel)
        keys = [p.get("key") for p in new_panels]
        current = 0
        if keys != [p.get("key") for p in self._idle_panels]:
            self._idle_panel_idx = 0
        elif self._idle_panel is not None:
            # Same carousel, rebuilt panels (a save): keep the entry that is
            # the idle panel, which may be on screen right now.
            current = keys.index(self._idle_panel.get("key"))
        self._idle_panels = new_panels
        self._idle_panel = self._idle_panels[current] if self._idle_panels else None
        if log and self._idle_panels:
            self.log(
                "Idle panel carousel: "
                + ", ".join(panel.get("key", str(panel.id)) for panel in self._idle_panels)
            )

    def start_part(self) -> None:
        """Starts the part."""
        self._activity_ts = time.monotonic()
        self._resolve_special_panels(log=True)
        self.log(f"Panels used for navigation: {', '.join([str(x) for x in self._ids])}")
        # One per-second check for the idle page and auto-home; started once,
        # never cancelled on reconnect.
        self._idle_check_timer = self.app.run_every(self._check_inactivity, "now+1", 1)

    def stop_part(self) -> None:
        """Stops the part.

        Cleans up the active page so entity state listeners are properly
        unregistered before the app is destroyed (e.g., on config entry reload).
        """
        self._cancel_timer("_idle_check_timer")
        self.cancel_timeouts()
        self.unset_page()
        self._stack.clear()

    # events

    def _fire_page_event(self, action: str, panel: HAUIPanel | None) -> None:
        """Publish a ``nspanel_haui.page_changed`` HA event for automations.

        Fired whenever a panel is opened (through the full render pipeline)
        or closed.  The payload identifies the device and the panel by key,
        type, title and the underlying Nextion page name.
        """
        if panel is None:
            return
        page_id = get_page_id_for_panel(panel.get_type())
        self.app.fire_event(
            "nspanel_haui.page_changed",
            {
                "device": self.app.device.get_name(),
                "action": action,
                "panel": panel.get("key", ""),
                "type": panel.get_type(),
                "title": panel.get_title(),
                "page": (
                    PAGE_MAPPING.get(page_id, panel.get_type()) if page_id else panel.get_type()
                ),
            },
        )

    # public methods

    @contextlib.contextmanager
    def _guard(self, what: str) -> Iterator[bool]:
        """Re-entrance guard for navigation mutations.

        Yields ``True`` if the lock was acquired (caller should proceed), or
        ``False`` if a navigation operation is already in progress (caller
        should skip). Replaces the four hand-rolled ``_navigating`` try/finally
        blocks that accreted across rewrites.
        """
        if self._navigating:
            self.log(f"Navigation in progress, skipping {what}")
            yield False
            return
        self._navigating = True
        try:
            yield True
        finally:
            self._navigating = False
        # A reload requested mid-navigation (e.g. a panel save) must not be
        # lost, otherwise navigation keeps panel objects/UUIDs from before it.
        if self._pending_reload:
            self._pending_reload = False
            self.reload_panels()

    def reload_panels(self) -> None:
        """Re-resolves panel references from updated config.

        Called after panels are rebuilt in the config (e.g., UI save).
        Does NOT re-send ESPHome commands or re-register callbacks.
        """
        if self._navigating:
            self._pending_reload = True
            self.log("Navigation in progress, queuing reload_panels")
            return
        self._pending_reload = False
        with self._guard("reload_panels"):
            self._reload_panels_impl()

    def _reload_panels_impl(self) -> None:
        self._resolve_special_panels()
        # re-resolve current nav
        if self._current_nav is not None:
            current_key = self._current_nav.get("key", "")
            self._current_nav = (
                self.app.device_config.get_panel(current_key) if current_key else None
            )
        # re-resolve currently displayed panel (otherwise stale reference)
        if self.panel is not None:
            current_key = self.panel.get("key", "")
            new_panel = self.app.device_config.get_panel(current_key) if current_key else None
            if new_panel is not None:
                self.panel = new_panel
        # clear stack (stale panel references)
        self._stack.clear()
        self.log("Navigation panel references reloaded")

        # Re-render the displayed panel so config changes take effect; load the
        # page again when its type changed or it reads different load data.
        if self.panel is not None:
            new_page_id = get_page_id_for_panel(self.panel.get_type())
            if (
                self.page is not None
                and new_page_id is not None
                and self.page.page_id == new_page_id
                and self.page.is_loaded_for(self.panel)
            ):
                self.display_panel(self.panel)
            else:
                self._open_panel_impl(self.panel.id, **self.panel_kwargs, force=True)

    def goto_page(self, page_id: int, force: bool = False) -> None:
        """Goto page method.

        Args:
            page_id (str): Page name or id
            force (bool): Force re-send, bypass ESPHome dedup
        """
        self.log(f"Goto page: {PAGE_MAPPING.get(page_id)}")
        self.send_esphome(ESPCommand.GOTO_PAGE, str(page_id), force=force)

    def unset_page(self) -> None:
        """Unsets the currently set page."""
        if self.page is not None:
            if self.page.is_started():
                self.page.stop()
            self.page = None

    def get_current_panel(self) -> HAUIPanel | None:
        """Returns the current panel.

        Returns:
            HAUIPanel|None
        """
        return self.panel

    def get_current_nav_panel(self) -> HAUIPanel | None:
        """Returns the current nav panel.

        Returns:
            HAUIPanel|None
        """
        return self._current_nav

    @property
    def home_panel(self) -> HAUIPanel | None:
        """The panel Home opens: ``home_panel``, else the first navigation panel."""
        return self._home_panel

    @property
    def idle_panel_active(self) -> bool:
        """Whether the idle page (automatic page switching) is shown.

        This is the only hub-side "idle session" flag.  It is independent of
        the display brightness state, which the firmware owns: the display can
        be off (``use_auto_display_off``) without any page switch, and the idle
        page can be shown while the display is still on.
        """
        return self._idle_panel_active

    # main methods

    def reload_panel(self) -> None:
        """Reloads the current panel."""
        if self.panel is None:
            return
        self.log(f"Reloading panel: {self.panel.id}")
        if len(self._stack) > 0:
            self._stack.pop()
        self._open_panel_impl(self.panel.id, **self.panel_kwargs)

    def refresh_panel(self) -> None:
        """Refreshes the current panel."""
        if self.panel is None or self.page is None:
            return
        self.log(f"Refreshing panel: {self.panel.id}")
        self.page.refresh_panel()

    def display_panel(self, panel: HAUIPanel) -> None:
        """Displays the given panel.

        Args:
            panel (HAUIPanel): Panel to display.
        """
        page_id = get_page_id_for_panel(panel.get_type())
        if self.page is not None and self.page.page_id == page_id:
            self.log(f"Setting new panel: {panel.get_type()}")
            # Clear the prev_cmd cache so this render is not deduped against
            # the previous page's.
            if "esphome" in self.app.controller:
                self.app.controller["esphome"].reset_prev_cmd()
            # only start the page if it was not started before
            if not self.page.is_started():
                self.page.start()
            self.page.set_panel(panel)
            # The new page may hold different auto switches; the inactivity
            # check may run again.
            self._resume_pending = False

    def open_panel(self, panel_id: UUID | str, **kwargs: Any) -> None:
        """Opens the panel with the given id.

        Args:
            panel_id (str): Id of panel
            kwargs (dict): Additional arguments for panel
        """
        with self._guard(f"open_panel({panel_id})") as acquired:
            if acquired:
                self._open_panel_impl(panel_id, **kwargs)

    def _open_panel_impl(self, panel_id: UUID | str, **kwargs: Any) -> None:
        self.log(f"Opening panel: {panel_id}-{kwargs}")

        # lock current panel before setting new
        # only if the panel had a locked state
        if self.panel is not None and self.panel.get_state("locked") is not None:
            self.panel.set_state("locked", True)

        # create and check page of new panel
        panel = self.app.device_config.get_panel(panel_id)
        self.log(
            f"Resolved panel: id={panel_id}, type={panel.get_type() if panel else 'NOT FOUND'!r}, "
            f"key={panel.get('key', '') if panel else 'NOT FOUND'!r}, "
            f"show_in_nav={panel.show_in_navigation() if panel else 'NOT FOUND'}, "
            f"kwargs={kwargs}",
            level="DEBUG",
        )
        if panel is None:
            self.log(f"Panel {panel_id} not found")
            if self._home_panel is not None and panel_id == self._home_panel.id:
                self.log("Home panel not found, cannot fall back to itself")
                return
            self._open_home_fallback()
            return

        self._track_idle_session(panel)
        page_id = get_page_id_for_panel(panel.get_type())
        page_class = get_page_class_for_panel(panel.get_type())
        if page_id is None or page_class is None:
            self.log(
                f"Panel {panel_id} has unknown type '{panel.get_type()}', falling back to home",
                level="WARNING",
            )
            if self._home_panel is not None and panel.id == self._home_panel.id:
                self.log("Home panel has no page defined, cannot fall back to itself")
                return
            self._open_home_fallback()
            return

        # reset panel config to defaults and overlay navigation kwargs
        panel.apply_kwargs(kwargs)
        self._track_history(panel, kwargs)

        # set new panel as current panel
        self.panel = panel
        self.panel_kwargs = kwargs
        self._fire_page_event("opened", panel)

        # if new panel has an unlock code set and panel is locked,
        # open unlock panel instead
        if panel.get("unlock_code", "") != "" and panel.get_state("locked", True):
            self.log(f"Unlock code set, locking panel {panel.id}")
            # lock new panel
            panel.set_state("locked", True)
            # open the unlock panel with the panel to unlock as a param
            self._open_panel_impl(PopupPanelKey.POPUP_UNLOCK, unlock_panel=panel, autostart=True)
            return

        # extract optional force flag before passing to goto_page
        force = kwargs.pop("force", False)

        # check current page before setting new panel
        curr_page_id = None
        if self.page is not None:
            curr_page_id = self.page.page_id
            self.page.stop()
            self.page = None

        # set new current page and panel
        self.log(
            f"Switching to page {PAGE_MAPPING.get(page_id)}"
            f" from {PAGE_MAPPING.get(curr_page_id) if curr_page_id is not None else None}"
        )
        self.page = page_class(self.app, {"page_id": page_id})

        # the theme colours and whatever else the page reads while it loads
        self.page.prepare_page_load(panel)

        # set new page for panel
        self.goto_page(page_id, force=force)

        # Render only after the page ack (0x66), or widget commands hit a page
        # still initialising and are rejected. The page timeout is the fallback.
        self.log("Waiting for page event before rendering")
        self._cancel_timer("_page_timeout")
        self._page_timeout = self.app.run_in(self._page_timeout_callback, PAGE_ACK_TIMEOUT)
        self._page_change_ts = time.monotonic()

        # The previous panel's close timer must never fire for this panel,
        # whether or not the new panel has a timeout of its own.
        self._cancel_timer("_close_timeout")
        # check for close timeout in panel config (contains also kwargs)
        timeout = panel.get("close_timeout", 0)
        if timeout > 0:
            self._close_timeout = self.app.run_in(self._close_timeout_callback, timeout)

    def _track_idle_session(self, panel: HAUIPanel) -> None:
        """Follow the idle session as ``panel`` opens.

        An overlay opened from idle suspends the session so touches on the
        overlay do not wake through it; closing back to idle resumes it, and
        a navigation panel ends it.
        """
        is_idle_panel = self._idle_panel is not None and panel.id == self._idle_panel.id
        if self._idle_panel_suspended and is_idle_panel:
            self._idle_panel_suspended = False
            self._idle_panel_active = True
            self.app.device.on_idle_page_opened()
        elif self._idle_panel_active and self._idle_panel and not is_idle_panel:
            self._idle_panel_suspended = not panel.show_in_navigation()
            self._idle_panel_active = False
        elif self._idle_panel_suspended and panel.show_in_navigation():
            self._idle_panel_suspended = False

    def _track_history(self, panel: HAUIPanel, kwargs: dict[str, Any]) -> None:
        """Record where ``panel`` was opened from.

        A navigation panel becomes the current nav panel and drops the stack;
        any other panel is pushed onto the stack, unless it is already on top
        (a reconnect or page-timeout retry opens it again).
        """
        if panel.show_in_navigation():
            self._current_nav = panel
            self._current_nav_kwargs = kwargs
            self._stack = []
        elif not self._stack or self._stack[-1][0].id != panel.id:
            self._stack.append((panel, kwargs))

    def _open_home_fallback(self) -> None:
        """Open the home panel from inside an already guarded navigation.

        ``open_home_panel`` goes through the guarded ``open_panel``, which would
        skip itself here because the guard is held by the caller.
        """
        if self._home_panel is None:
            self.log("No home panel available")
            return
        self._open_panel_impl(self._home_panel.id)

    def _page_timeout_callback(self, _kwargs: dict[str, Any]) -> None:
        """Last-resort fallback: page event never arrived within timeout."""
        # The touch recovery calls this directly: the pending timer must not
        # fire on top of it.
        self._cancel_timer("_page_timeout")
        # An upload owns the display: it stops acking a page change, and both
        # the re-send and the render would be dropped by the command guard.
        if self._display_busy():
            self.log(
                "Page ack timeout during a TFT install; the page is drawn once it ends",
                level="DEBUG",
            )
            return
        # re-send goto_page and render without pushing a duplicate onto the stack.
        if self.page is not None and self.panel is not None:
            page_id = self.page.page_id
            self.log(
                f"Page event not received within timeout, "
                f"force re-sending goto_page for {PAGE_MAPPING.get(page_id)}"
            )
            self.goto_page(page_id, force=True)
            self.display_panel(self.panel)

    def _close_timeout_callback(self, kwargs: dict[str, Any]) -> None:
        """Scheduler callback for panel auto-close."""
        self._close_timeout = None
        self.close_panel()

    def cancel_timeouts(self) -> None:
        """Cancel all active navigation timeouts.

        Called on connect/disconnect to prevent stale timeouts from firing
        after a connection state change.
        """
        self._cancel_timer("_page_timeout")
        self._cancel_timer("_page_settle_timer")
        self._cancel_timer("_buffer_overflow_timer")
        self._cancel_timer("_close_timeout")

    # inactivity: one level-triggered check for auto-navigate-home and the idle page

    def prepare_resume(self) -> None:
        """Start the inactivity clock again after a (re)connect.

        A reconnect is no interaction: the restored page is displayed first
        (the check stays off until ``display_panel`` runs), then the page
        timeout starts again from the reconnect.
        """
        self._activity_ts = time.monotonic()
        self._resume_pending = True
        self.log("Inactivity clock restarted on connect", level="DEBUG")

    def reset_activity(self) -> None:
        """Record a user interaction for the inactivity checks."""
        self._activity_ts = time.monotonic()
        self.log("Interaction recorded, inactivity clock reset", level="DEBUG")

    def _check_inactivity(self, _kwargs: dict[str, Any]) -> None:
        """Level-triggered idle-page and auto-navigate-home check (every second).

        Re-evaluate deadlines instead of arming timers that a page hold or
        config reload would have to reschedule.
        """
        if not self.app.device.connected:
            return
        if self._resume_pending:
            return
        if self.panel is None or self.page is None:
            return
        age = time.monotonic() - self._activity_ts
        self._check_nav_home(age)
        self._maybe_open_idle(age)

    def _maybe_open_idle(self, age: float) -> None:
        """Open the idle page when every condition holds, else do nothing."""
        if self._navigating:
            return
        if self._page_timeout is not None:
            return
        if self._idle_panel_active or self._idle_panel_suspended:
            return
        timeout_page = self._idle_timeout()
        if timeout_page is None or age < timeout_page:
            return
        if self.page is not None and self.page.suspends_auto_page():
            return
        self.log("Idle page due, opening the idle panel", level="INFO")
        self.open_idle_panel(autostart=True)

    def _idle_timeout(self) -> float | None:
        """The idle-page timeout, or ``None`` while the idle page is off."""
        if not self._idle_panels:
            return None
        use_auto_page = self.app.device.get("use_auto_page")
        timeout_page = self.app.device.get("timeout_page")
        if (
            not isinstance(use_auto_page, bool)
            or type(timeout_page) not in (int, float)
            or not math.isfinite(timeout_page)
            or timeout_page < 0
        ):
            self.log(
                "Idle page check skipped: invalid use_auto_page or timeout_page value",
                level="WARNING",
            )
            return None
        if not use_auto_page or timeout_page <= 0:
            return None
        return float(timeout_page)

    def idle_status(self) -> dict[str, Any]:
        """Where the idle page stands, for the editor's diagnostics.

        ``state`` is ``active`` (the idle page is shown), ``suspended`` (an
        overlay was opened from it), ``offline`` (the device is disconnected,
        so the check waits for it), ``held`` (the current page holds it off),
        ``pending`` (it opens after ``idle_in`` more seconds without an
        interaction) or ``off`` (no idle page, or automatic switching is off).
        """
        if self._idle_panel_active:
            return {"state": "active", "idle_in": None}
        if self._idle_panel_suspended:
            return {"state": "suspended", "idle_in": None}
        if not self.app.device.connected:
            return {"state": "offline", "idle_in": None}
        timeout_page = self._idle_timeout()
        if timeout_page is None:
            return {"state": "off", "idle_in": None}
        if self.page is not None and self.page.suspends_auto_page():
            return {"state": "held", "idle_in": None}
        age = time.monotonic() - self._activity_ts
        return {"state": "pending", "idle_in": max(0, round(timeout_page - age))}

    def _check_nav_home(self, age: float) -> None:
        """Auto-navigate-home, from the same activity clock as the idle page."""
        if self._navigating or self._page_timeout is not None:
            return
        timeout = self.app.device.get("auto_navigate_home_timeout")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
            self.log(
                "Auto-navigate-home check skipped: invalid auto_navigate_home_timeout value",
                level="WARNING",
            )
            return
        if timeout == 0 or age < timeout:
            return
        if self._idle_panel_active:
            # The idle page is on screen: leaving it goes home instead of
            # restoring the panel it covered.
            self.unset_snapshot()
            return
        if self._home_panel is None:
            return
        if self.panel is None or self.panel.id == self._home_panel.id:
            return
        self.log("Auto-navigate-home timeout reached, navigating to home panel")
        self.open_home_panel()

    def close_panel(self) -> None:
        """Closes the current panel."""
        with self._guard("close_panel") as acquired:
            if acquired:
                self._close_panel_impl()

    def _close_panel_impl(self) -> None:
        self._fire_page_event("closed", self.panel)
        # Leaving the idle page ends the idle session, including via the close
        # button or service.
        if (
            self._idle_panel_active
            and self.panel is not None
            and self._idle_panel
            and self.panel.id == self._idle_panel.id
        ):
            self._idle_panel_active = False
        # check for active timer
        self._cancel_timer("_close_timeout")
        prev_panel: HAUIPanel | None = None
        prev_kwargs: dict[str, Any] = {}
        unlock_panel: HAUIPanel | None = None
        # check stack
        if len(self._stack) > 0:
            # remove last stacked panel
            curr_panel, curr_kwargs = self._stack.pop()
            unlock_panel = curr_kwargs.get("unlock_panel", None)
            self.log(f"Closing panel: {curr_panel.id}")
            # get previous panel
            while len(self._stack) > 0:
                panel, kwargs = self._stack.pop()
                # if a unlock panel is set, check if it should be skipped (if not unlocked)
                if (
                    unlock_panel
                    and panel.id == unlock_panel.id
                    and panel.get_state("locked", False)
                ):
                    continue
                prev_panel, prev_kwargs = panel, kwargs
                break
        # no stack, use current nav panel
        if prev_panel is None and self._current_nav:
            prev_panel, prev_kwargs = self._current_nav, self._current_nav_kwargs
        # fallback panel home panel
        if prev_panel is None:
            prev_panel, prev_kwargs = self._home_panel, {}
        # Closing the unlock popup of a locked navigation panel must not return
        # to that panel: it would only open the popup again. Leave it for home.
        if (
            unlock_panel is not None
            and prev_panel is not None
            and prev_panel.id == unlock_panel.id
            and unlock_panel.get_state("locked", False)
        ):
            prev_panel, prev_kwargs = self._home_panel, {}

        # open new panel
        if prev_panel is not None:
            self.log(f"Open previous panel: {prev_panel.id}")
            self._open_panel_impl(prev_panel.id, **prev_kwargs)

    # additional methods

    def open_next_panel(self) -> None:
        """Opens the next panel."""
        self.log("Open next panel")
        if self._current_nav is None:
            return
        idx = self._id_to_idx.get(self._current_nav.id)
        if idx is None:
            return
        panel_id = self._ids[idx + 1] if idx < len(self._ids) - 1 else self._ids[0]
        self.open_panel(panel_id)

    def open_prev_panel(self) -> None:
        """Opens the previous panel."""
        self.log("Open prev panel")
        if self._current_nav is None:
            return
        idx = self._id_to_idx.get(self._current_nav.id)
        if idx is None:
            self.log(f"current nav not in ids {self._current_nav} - {self._ids}")
            return
        panel_id = self._ids[idx - 1] if idx > 0 else self._ids[-1]
        self.open_panel(panel_id)

    def go_back(self) -> None:
        """Return to the panel the current one was opened from, else to the home panel.

        A panel outside navigation sits on the stack, so closing it returns to
        where it was opened from. A navigation panel has no history (it was
        reached by swiping or as home), so it goes to the home panel.
        """
        if self._stack and self.panel is not None and self._stack[-1][0].id == self.panel.id:
            self.close_panel()
        elif self._home_panel is not None and (
            self.panel is None or self.panel.id != self._home_panel.id
        ):
            self.open_home_panel()
        else:
            self.log("Go back: already on the home panel")

    def open_home_panel(self, autostart: bool = False) -> None:
        """Opens the home panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
        """
        if self._home_panel is None:
            self.close_panel()
            self.log("No home panel available")
            return
        self.open_panel(self._home_panel.id, autostart=autostart)

    def open_idle_panel(self, autostart: bool = False, key: str | None = None) -> None:
        """Open the configured idle page (automatic page switching).

        This is a pure page switch: it never turns the display off (that is
        the firmware's ``use_auto_display_off`` display-idle machine) and never
        starts a hardware sleep.  A snapshot of the pre-idle navigation state
        is created only when an idle session actually starts, so repeated
        entries (page timeout, idle button, ``idle`` service) cannot
        overwrite it with the idle page itself.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
            key (str, optional): Open this panel of the carousel instead of the
                next one; the carousel continues after it.

        Raises:
            ValueError: If ``key`` is not one of the idle panels.
        """
        if key is not None:
            keys = [panel.get("key") for panel in self._idle_panels]
            if key not in keys:
                raise ValueError(f"Not an idle panel: {key!r}")
            self._idle_panel_idx = keys.index(key)
        if not self._idle_panels:
            self._idle_panel = None
            self.log("No idle panel configured; staying on the current panel")
            return
        if not self._idle_panel_active:
            self.create_snapshot()
        # Carousel: each entry advances to the next panel in the list.
        panel = self._idle_panels[self._idle_panel_idx % len(self._idle_panels)]
        self._idle_panel_idx += 1
        self._idle_panel = panel
        self._idle_panel_active = True
        # The device owns the wake guard: a dark display needs a wake touch; a
        # visible one needs one touch.
        self.app.device.on_idle_page_opened()
        self.open_panel(panel.id, autostart=autostart)

    def mark_awake(self) -> None:
        """Clear the idle-page session.

        Called whenever the device leaves the idle page (wake input, service,
        navigation cleanup).  It is not the mechanism that wakes the display:
        the firmware restores brightness itself when its interaction timer is
        reset.
        """
        self._idle_panel_active = False
        self._idle_panel_suspended = False

    def exit_idle_to_prev_or_home(self, config: dict | None) -> None:
        """Exit the idle page: restore the prior panel or open home.

        Restores the snapshot when ``snapshot_max_age_seconds`` allows it,
        otherwise opens the home panel.  A no-op when no idle session is
        active, so callers (touch, wakeup service, wakeup events) never
        navigate away from normal operation on a device that is only dark.
        """
        if not self._idle_panel_active:
            return
        self._leave_idle_restoring_or_home(config)

    def _leave_idle_restoring_or_home(self, config: dict | None) -> None:
        """Restore the pre-idle navigation snapshot or fall back to home.

        Unlike ``exit_idle_to_prev_or_home`` this runs regardless of the idle
        session flag; it is used when navigation context must be rebuilt after
        a hardware sleep (no-hub path) that dropped the active page.
        """
        snap_max_age = _resolve_snapshot(config or {})
        restored = snap_max_age != 0 and self.restore_snapshot(
            snap_max_age if snap_max_age > 0 else 0
        )
        if not restored:
            self.mark_awake()
            self.open_home_panel()

    # snapshot methods

    def create_snapshot(self) -> None:
        """Creates a snapshot of the current navigation state."""
        self._snapshot = NavigationSnapshot(
            panel=self.panel,
            panel_kwargs=self.panel_kwargs.copy(),
            current_nav=self._current_nav,
            current_nav_kwargs=self._current_nav_kwargs.copy(),
            stack=self._stack.copy(),
        )
        self.log("Navigation snapshot created")

    def unset_snapshot(self) -> None:
        """Unsets the current navigation snapshot."""
        self._snapshot = None

    def restore_snapshot(self, max_seconds_ago: int = 0) -> bool:
        """Restores a previously created navigation snapshot.

        Args:
            max_seconds_ago (int, optional): If > 0, only restore when the snapshot
                is at most this many seconds old. Defaults to 0 (no age limit).

        Returns:
            bool: True if successfully restored, False if not
        """
        snapshot = self._snapshot
        if snapshot is None:
            return False
        if max_seconds_ago > 0 and snapshot.age > max_seconds_ago:
            self.log(
                f"Navigation snapshot too old ({snapshot.age:.1f}s > {max_seconds_ago}s), "
                "not restoring"
            )
            return False
        with self._guard("restore_snapshot") as acquired:
            if not acquired:
                return False
            return self._restore_snapshot_impl(snapshot)

    def _resolve_live_panel(self, panel: HAUIPanel) -> HAUIPanel | None:
        """Find the live panel object matching a possibly stale one.

        Panel UUIDs are per instance and change on every reload, so the stable
        key is used. Panels without a key can only be matched by id.
        """
        key = panel.get("key", "")
        return self.app.device_config.get_panel(key if key else panel.id)

    def _restore_snapshot_impl(self, snapshot: NavigationSnapshot) -> bool:
        # Re-resolve snapshot references: reload_panels() replaces HAUIPanel
        # objects.
        prev_panel = snapshot.panel
        if prev_panel is not None:
            resolved = self._resolve_live_panel(prev_panel)
            if resolved is None:
                self.log(
                    f"Snapshot panel {prev_panel.id} no longer in config, falling back to home"
                )
                self.unset_snapshot()
                self.mark_awake()
                self._open_home_fallback()
                return False
            prev_panel = resolved
        prev_current_nav = snapshot.current_nav
        if prev_current_nav is snapshot.panel:
            prev_current_nav = prev_panel
        elif prev_current_nav is not None:
            prev_current_nav = self._resolve_live_panel(prev_current_nav)
        live_stack: list[StackEntry] = []
        for stacked, stacked_kwargs in snapshot.stack:
            live = self._resolve_live_panel(stacked)
            if live is not None:
                live_stack.append((live, stacked_kwargs))

        self.panel = prev_panel
        self.panel_kwargs = snapshot.panel_kwargs
        self._current_nav = prev_current_nav
        self._current_nav_kwargs = snapshot.current_nav_kwargs
        self._stack = live_stack

        # Consume the snapshot and clear idle-session state so check_wakeup() and
        # process_event() don't re-trigger the same restore on the next event.
        self.unset_snapshot()
        self.mark_awake()

        # Cancel any pending timeouts before restoring the panel to prevent
        # stale _page_timeout_callbacks from firing mid-restore.
        self.cancel_timeouts()

        # Clear the prev_cmd cache so a repeated goto_page is not deduped.
        if "esphome" in self.app.controller:
            self.app.controller["esphome"].reset_prev_cmd()
        # Force goto_page so it always reaches the display after snapshot restore.
        self.panel_kwargs["force"] = True

        self.reload_panel()

        # Refresh after a short delay so commands lost during the page transition
        # are replayed. If the initial render succeeded, this is harmless.
        self.app.run_in(self._refresh_after_snapshot_restore, 1.0)

        self.log("Navigation snapshot restored")
        return True

    # event

    def _refresh_after_snapshot_restore(self, _kwargs: dict[str, Any]) -> None:
        """Re-send the restored panel after the display has processed the transition."""
        if self.panel is not None:
            self.log("Refreshing panel after snapshot restore")
            self.refresh_panel()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Dispatch a device event to the matching handler, then forward it
        to the active page.

        The per-event handlers are mutually exclusive on ``event.name``; the
        interaction-timer reset runs first because it applies across several
        event types (touch/button/gesture).
        """
        self.log(
            f"Navigation process_event: {event.name} value={str(event.value)[:100]}",
            level="DEBUG",
        )
        self._record_activity(event)

        # A touch while a page change is pending means goto_page was lost;
        # resend after the 1 s grace for a normal render.
        if event.name == ESPEvent.TOUCH_START and self._page_timeout is not None:
            now = time.monotonic()
            if now - self._page_change_ts > 1.0:
                self.log(
                    "Touch while page change pending — forcing page recovery",
                    level="WARNING",
                )
                self._page_timeout_callback({})

        handlers: dict[str, Any] = {
            ESPEvent.PAGE: self._handle_page_event,
            ESPEvent.DISPLAY_ON: self._handle_display_on_event,
            ESPEvent.DISPLAY_OFF: self._handle_display_off_event,
            ESPEvent.BUFFER_OVERFLOW: self._handle_buffer_overflow_event,
            ESPEvent.RES_DRAW: self._handle_res_draw_event,
        }
        handler = handlers.get(event.name)
        if handler is not None:
            handler(event)

        # allow page to process events (the display-off handler may have cleared it)
        if self.page is not None:
            self.page.process_event(event)

    def _record_activity(self, event: HAUIEvent) -> None:
        """Reset the hub's activity clock on a user interaction.

        Touch events, component taps and gestures always count; hardware
        buttons only when ``reset_interaction_on_button`` is enabled. Redraws,
        settings saves and popups opening are not interactions.
        """
        if event.name not in (
            ESPEvent.TOUCH_START,
            ESPEvent.TOUCH_END,
            ESPEvent.COMPONENT,
            ESPEvent.GESTURE,
            ESPEvent.BUTTON_LEFT,
            ESPEvent.BUTTON_RIGHT,
        ):
            return
        is_button = event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT)
        if is_button and not self.app.device.get("reset_interaction_on_button"):
            return
        self.reset_activity()

    def _handle_page_event(self, event: HAUIEvent) -> None:
        """A page-change ack arrived from the device."""
        # cancel page timeout if any
        self._cancel_timer("_page_timeout")
        self._page_change_ts = 0.0
        if self.page is None:
            return
        # mismatch - likely a stale echo of a previous goto.
        # Don't reload; _page_timeout handles real failures.
        if self.page.page_id != event.as_int():
            self.log(
                f"Stale page event {PAGE_MAPPING.get(event.as_int())} "
                f"received while {PAGE_MAPPING.get(self.page.page_id)} is active, ignoring",
                level="DEBUG",
            )
            return
        # wait for the settle delay so the Nextion finishes initialising the page.
        if not self.page.is_started() and self.panel is not None:
            delay = self.app.device.get("page_settle_delay")
            self._cancel_timer("_page_settle_timer")
            self._page_settle_timer = self.app.run_in(self._page_settle_callback, delay)

    def _page_settle_callback(self, _kwargs: dict[str, Any]) -> None:
        """Timer callback: render the panel after the page settle delay."""
        self._page_settle_timer = None
        if self.panel is not None:
            self.display_panel(self.panel)

    def _handle_display_on_event(self, _event: HAUIEvent) -> None:
        """esphome.display_on (post-hardware-sleep wake, no-hub path).

        Hardware sleep only ever engages without a hub connection.  With the
        hub connected the touch itself drives both the display wake and the
        exit from the idle page (``Device.check_wakeup``); this handler only
        restores navigation state so a device that slept in hardware is not
        left on a dark screen.  ``exit_idle_to_prev_or_home`` is a no-op when
        no idle session is active.
        """
        if self._idle_panel_active:
            self.log("Wakeup event while idle page active; awaiting touch to exit")
            return
        self.log("Wakeup event from hardware sleep, restoring previous page or home")
        self._leave_idle_restoring_or_home(self.app.device.config)

    def _handle_display_off_event(self, event: HAUIEvent) -> None:
        """esphome.display_off -> drop the active page.

        Hardware sleep (no-hub path): no page survives the Nextion's sleep
        state, so drop the hub-side page to keep listeners and commands in
        sync with what the display actually shows.
        """
        if self.page:
            self.unset_page()

    def _handle_res_draw_event(self, event: HAUIEvent) -> None:
        """esphome.res_draw — a draw program ended, with its drained time.

        The firmware measures from the first run it queued to the readback that
        can only answer after the last one was sent, so this is the figure to
        tune the pacing from (``runs * command_spacing``) instead of a guess.
        """
        payload = event.as_json()
        self.log(
            f"Draw program finished: {payload.get('runs', 0)} runs, "
            f"ok={payload.get('ok', False)}, {payload.get('elapsed_ms', 0)} ms"
        )

    def _handle_buffer_overflow_event(self, _event: HAUIEvent) -> None:
        """esphome.buffer_overflow — Nextion RX buffer overflowed, commands lost.

        The Nextion reports 0x24 when its internal serial buffer overflows.
        All instructions that were in-flight at that moment are permanently
        lost — the display shows a mix of stale and updated widgets.

        We schedule a debounced re-render of the current panel so the display
        recovers automatically.  The delay lets the ESPHome queue drain any
        remaining commands before we re-send the panel state.

        Recovery must not be able to loop: if the re-render batch itself
        overflows the buffer, re-sending it forever just repeats the overflow.
        Consecutive recoveries therefore back off exponentially and recovery
        pauses entirely after OVERFLOW_RECOVERY_MAX_ATTEMPTS, until the
        display has been overflow-free for OVERFLOW_RECOVERY_RESET seconds.
        """
        now = time.monotonic()
        if now - self._last_overflow_ts > OVERFLOW_RECOVERY_RESET:
            self._overflow_recoveries = 0
        self._last_overflow_ts = now
        if self._overflow_recoveries >= OVERFLOW_RECOVERY_MAX_ATTEMPTS:
            # Recovery is paused; stay quiet until a reset period passes.
            self.log(
                "Nextion buffer overflow while recovery is paused — ignoring",
                level="DEBUG",
            )
            return
        delay = OVERFLOW_RECOVERY_DELAY * (2**self._overflow_recoveries)
        self.log(
            f"Nextion buffer overflow detected — scheduling panel re-render in {delay:.1f}s",
            level="WARNING",
        )
        self._cancel_timer("_buffer_overflow_timer")
        self._buffer_overflow_timer = self.app.run_in(self._buffer_overflow_recover, delay)

    def _buffer_overflow_recover(self, _kwargs: dict[str, Any]) -> None:
        """Re-render the current panel after a buffer overflow.

        Uses refresh_panel (render only) instead of a full set_panel so the
        recovery batch is smaller than the batch that overflowed and cannot
        re-trigger the overflow by itself.
        """
        self._buffer_overflow_timer = None
        if self.panel is None or self.page is None:
            return
        self._overflow_recoveries += 1
        self.log(
            "Re-rendering panel after buffer overflow "
            f"(attempt {self._overflow_recoveries}/{OVERFLOW_RECOVERY_MAX_ATTEMPTS})"
        )
        if self._overflow_recoveries >= OVERFLOW_RECOVERY_MAX_ATTEMPTS:
            self.log(
                "Buffer overflow keeps recurring — pausing recovery until "
                f"{OVERFLOW_RECOVERY_RESET:.0f}s without overflows",
                level="ERROR",
            )
        self.refresh_panel()

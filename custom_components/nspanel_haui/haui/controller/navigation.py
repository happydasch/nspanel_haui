from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ..device_config import resolve_snapshot_max_age as _resolve_snapshot

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPCommand, ESPEvent, SysPanelKey
from ..mapping.page import PAGE_MAPPING
from ..utils.page import get_page_class_for_panel, get_page_id_for_panel


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
        self.debug_log(f"Creating Navigation Controller with config: {config}")
        self.page: HAUIPage | None = None
        self.panel: HAUIPanel | None = None  # current panel config
        self.panel_kwargs: dict[str, Any] = {}  # current panel kwargs
        self._current_nav: HAUIPanel | None = None  # current nav panel config
        self._current_nav_kwargs: dict[str, Any] = {}  # current nav panel kwargs
        self._ids: list = []  # ids of nav panels
        self._id_to_idx: dict = {}  # O(1) index lookup for nav panels
        self._home_panel: HAUIPanel | None = None  # home panel config
        self._sleep_panel: HAUIPanel | None = None  # sleep panel config
        self._sleep_panel_active = False  # sleep panel state
        self._wakeup_panel: HAUIPanel | None = None  # wakeup panel config
        self._page_timeout: str | None = None  # Timer for switching pages
        self._buffer_overflow_timer: str | None = None  # Debounced re-render after overflow
        self._page_settle_timer: str | None = None  # Delayed re-render after page event settle
        self._close_timeout: str | None = None  # Timer for panel auto close
        self._idle_timer: str | None = None  # Timer for hub-side idle timeout
        self._nav_home_timer: str | None = None  # Timer for auto-navigate-home
        self._last_interaction: float = 0.0  # monotonic time of last user interaction
        self._stack: list[tuple[HAUIPanel, dict[str, Any]]] = []  # stack for non-nav panels
        self._snapshot: (
            tuple[
                HAUIPanel | None,
                dict[str, Any],
                HAUIPanel | None,
                dict[str, Any],
                list[tuple[HAUIPanel, dict[str, Any]]],
            ]
            | None
        ) = None  # snapshot for navigation
        self._snapshot_time: float | None = None  # monotonic time when snapshot was created
        self._navigating = False  # re-entrance guard for navigation operations
        self._pending_reload = False  # reload was queued while navigating

    # part

    def _resolve_special_panels(self, *, log: bool = False) -> list:
        """Resolve nav-panel ids and the home/sleep/wakeup special panels.

        Reads the panel keys from device config, populates ``_ids`` /
        ``_id_to_idx`` and ``_home_panel`` / ``_sleep_panel`` / ``_wakeup_panel``,
        and falls back to the first nav panel as home. Shared by ``start_part``
        (``log=True``) and ``_reload_panels_impl`` (silent), which previously
        carried near-identical copies. Returns the nav-panel list.
        """
        nav_panels = self.app.device_config.get_panels(filter_nav_panel=True)
        self._ids = [panel.id for panel in nav_panels]
        self._id_to_idx = {panel_id: idx for idx, panel_id in enumerate(self._ids)}
        for attr, cfg_key, label in (
            ("_home_panel", "home_panel", "Home panel"),
            ("_sleep_panel", "sleep_panel", "Sleep panel"),
            ("_wakeup_panel", "wakeup_panel", "Wakeup panel"),
        ):
            panel_key = self.app.device.get(cfg_key)
            panel = self.app.device_config.get_panel(panel_key) if panel_key else None
            setattr(self, attr, panel)
            if log and panel_key:
                self.log(
                    f"{label} using panel {panel.id}"
                    if panel
                    else f"{label} key '{panel_key}' not found"
                )
        if self._home_panel is None and len(self._ids) > 0:
            if log:
                self.log(f"Using first panel {self._ids[0]} as home panel")
            self._home_panel = nav_panels[0]
        return nav_panels

    def start_part(self) -> None:
        """Starts the part."""
        self._resolve_special_panels(log=True)
        self.log(f"Panels used for navigation: {', '.join([str(x) for x in self._ids])}")

    def stop_part(self) -> None:
        """Stops the part.

        Cleans up the active page so entity state listeners are properly
        unregistered before the app is destroyed (e.g., on config entry reload).
        """
        self.cancel_timeouts()
        self.unset_page()
        self._stack.clear()

    # public methods

    @contextlib.contextmanager
    def _guard(self, what: str):
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
        # If a reload was queued while we were busy, apply it now
        if self._pending_reload:
            self._pending_reload = False
            self.reload_panels()

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

        # Re-render currently displayed panel so config changes take effect.
        # If page type unchanged, set_panel reapplies new config in place.
        # If type changed (or page missing), do a full open_panel.
        if self.panel is not None:
            new_page_id = get_page_id_for_panel(self.panel.get_type())
            if (
                self.page is not None
                and new_page_id is not None
                and self.page.page_id == new_page_id
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

    def has_prev_panel(self) -> bool:
        """Returns if a previous panel is available.

        Returns:
            bool: True if current panel has a previous panel
        """
        if self._current_nav is None:
            return False
        idx = self._id_to_idx.get(self._current_nav.id)
        return idx is not None and idx != 0

    def has_next_panel(self) -> bool:
        """Returns if a next panel is available.

        Returns:
            bool: True if current panel has a next panel
        """
        if self._current_nav is None:
            return False
        idx = self._id_to_idx.get(self._current_nav.id)
        return idx is not None and len(self._ids) > 1 and idx != len(self._ids) - 1

    def has_up_panel(self) -> bool:
        """Returns if a up panel is available.

        Returns:
            bool: True if current panel has a up panel
        """
        return len(self._stack) == 0

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
            # Reset the ESPHome controller's prev_cmd cache so the batch
            # from this panel's render is never suppressed as a duplicate of
            # the previous page's batch (which can happen when two panels
            # share the same Nextion page and render similar commands).
            if "esphome" in self.app.controller:
                self.app.controller["esphome"].reset_prev_cmd()
            # only start the page if it was not started before
            if not self.page.is_started():
                self.page.start()
            self.page.set_panel(panel)
            # Start hub-side idle timer when a panel is displayed
            self._start_idle_timer()
            # Start auto-navigate-home timer when a panel is displayed
            self._start_nav_home_timer()

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
            f"key={panel.get('key') if panel else 'NOT FOUND'!r}, "
            f"show_in_nav={panel.show_in_navigation() if panel else 'NOT FOUND'}, "
            f"kwargs={kwargs}",
            level="DEBUG",
        )
        if panel is None:
            self.log(f"Panel {panel_id} not found")
            if self._home_panel is not None and panel_id == self._home_panel.id:
                self.log("Home panel not found, cannot fall back to itself")
                return
            self.open_home_panel()
            return
        page_id = get_page_id_for_panel(panel.get_type())
        page_class = get_page_class_for_panel(panel.get_type())
        if page_id is None or page_class is None:
            if page_id is None:
                self.log(f"Panel {panel_id} ({panel.get_type()}) has no page defined")
            if page_class is None:
                self.log(f"Panel {panel_id} ({panel.get_type()}) has no page class defined")
            if self._home_panel is not None and panel_id == self._home_panel.id:
                self.log("Home panel has no page defined, cannot fall back to itself")
                return
            self.open_home_panel()
            return

        # reset panel config to defaults and overlay navigation kwargs
        panel.apply_kwargs(kwargs)

        # debug: trace post-apply_kwargs config for popup/override debugging
        self.log(
            f"After apply_kwargs: item_id={panel.get('item_id', None)!r} "
            f"sonos_favorites={panel.get('sonos_favorites', None)!r} "
            f"media_favorites={panel.get('media_favorites', None)!r} "
            f"sonos_favorites_in_source={panel.get('sonos_favorites_in_source', None)!r}",
            level="DEBUG",
        )

        # new panel is a navigatable panel
        if panel.show_in_navigation():
            self._current_nav = panel
            self._current_nav_kwargs = kwargs
            # new panel is a nav panel, clear stack
            if len(self._stack) > 0:
                self._stack = []
        # new panel is not a navigatable panel
        else:
            # add to the navigation stack
            # Guard against duplicates: don't push if this panel is already at
            # the top of the stack (e.g. reconnect retry, page-timeout retry).
            if not self._stack or self._stack[-1][0].id != panel.id:
                self._stack.append((panel, kwargs))

        # set new panel as current panel
        self.panel = panel
        self.panel_kwargs = kwargs

        # if new panel has an unlock code set and panel is locked,
        # open unlock panel instead
        if panel.get("unlock_code", "") != "" and panel.get_state("locked", True):
            self.log(f"Unlock code set, locking panel {panel.id}")
            # lock new panel
            panel.set_state("locked", True)
            # open the unlock panel with the panel to unlock as a param
            self._open_panel_impl(SysPanelKey.POPUP_UNLOCK, unlock_panel=panel, autostart=True)
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

        # notify about panel creation early in process
        self.page.create_panel(panel)

        # set new page for panel
        self.goto_page(page_id, force=force)

        # Wait for the esphome.page event confirming the page changed before
        # rendering.  The Nextion sends a 0x66 postulate after every page
        # command — even when the target page is the same as the current one
        # (page N causes a full page refresh).  Rendering before the 0x66
        # arrives means widget commands hit a page that hasn't finished
        # initialising and are rejected as "Invalid variable name" (0x1A).
        # _handle_page_event calls display_panel() when the ack arrives.
        # If the ack never comes, the page_timeout fires as a last-resort
        # fallback.
        self.log("Waiting for page event before rendering")
        timeout = self.get("page_timeout", 10.0)
        if self._page_timeout is not None:
            self.app.cancel_timer(self._page_timeout)
            self._page_timeout = None
        self._page_timeout = self.app.run_in(self._page_timeout_callback, timeout)

        # check for close timeout in panel config (contains also kwargs)
        timeout = panel.get("close_timeout", 0)
        if timeout > 0:
            if self._close_timeout is not None:
                self.app.cancel_timer(self._close_timeout)
            self._close_timeout = self.app.run_in(self._close_timeout_callback, timeout)

    def _page_timeout_callback(self, _kwargs: dict[str, Any]) -> None:
        """Last-resort fallback: page event never arrived within timeout."""
        self._page_timeout = None
        # Force re-send goto_page and render the current panel. This avoids
        # pushing a duplicate onto the navigation stack when the ESPHome page
        # ack doesn't arrive in time.
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
        if self._page_timeout is not None:
            self.app.cancel_timer(self._page_timeout)
            self._page_timeout = None
        if self._page_settle_timer is not None:
            self.app.cancel_timer(self._page_settle_timer)
            self._page_settle_timer = None
        if self._buffer_overflow_timer is not None:
            self.app.cancel_timer(self._buffer_overflow_timer)
            self._buffer_overflow_timer = None
        if self._close_timeout is not None:
            self.app.cancel_timer(self._close_timeout)
            self._close_timeout = None
        self._cancel_idle_timer()
        self._cancel_nav_home_timer()

    # idle timer (hub-side fallback for device inactivity timeout)

    def _start_idle_timer(self) -> None:
        """Start or restart the hub-side idle timer.

        Cancels any existing idle timer and starts a new one-shot timer
        that will trigger sleep after ``hub_idle_timeout`` seconds of
        inactivity.  Does nothing when ``hub_idle_timeout`` is 0 (disabled)
        or the sleep panel is already active.
        """
        timeout = self.app.device.get("hub_idle_timeout", 0)
        if timeout <= 0:
            return
        if self._sleep_panel_active:
            return
        self._cancel_idle_timer()
        self._last_interaction = time.monotonic()
        self._idle_timer = self.app.run_in(self._idle_timer_callback, timeout)

    def _cancel_idle_timer(self) -> None:
        """Cancel the hub-side idle timer if active."""
        if self._idle_timer is not None:
            self.app.cancel_timer(self._idle_timer)
            self._idle_timer = None

    def _idle_timer_callback(self, kwargs: dict[str, Any]) -> None:
        """Called when the hub-side idle timer fires.

        Opens the sleep panel if the user has been idle longer than
        ``hub_idle_timeout`` and the device-side timeout hasn't already
        triggered sleep.
        """
        self._idle_timer = None
        if self._sleep_panel_active:
            return  # device-side timeout already triggered sleep
        if not self.app.device.connected:
            return
        if self._sleep_panel and self.panel and self._sleep_panel.id != self.panel.id:
            self.log("Hub idle timeout reached, opening sleep panel (no esphome.timeout received)")
            self._sleep_panel_active = True
            self.open_sleep_panel(autostart=True)

    # auto-navigate-home timer

    def _start_nav_home_timer(self) -> None:
        """Start or restart the auto-navigate-home timer.

        Cancels any existing nav-home timer and starts a new one-shot timer
        that will navigate back to the home panel after
        ``auto_navigate_home_timeout`` seconds of inactivity.  Does nothing
        when ``auto_navigate_home_timeout`` is 0 (disabled) or the sleep
        panel is already active.
        """
        timeout = self.app.device.get("auto_navigate_home_timeout", 0)
        if timeout <= 0:
            return
        if self._sleep_panel_active:
            return
        self._cancel_nav_home_timer()
        self._nav_home_timer = self.app.run_in(self._nav_home_timer_callback, timeout)

    def _cancel_nav_home_timer(self) -> None:
        """Cancel the auto-navigate-home timer if active."""
        if self._nav_home_timer is not None:
            self.app.cancel_timer(self._nav_home_timer)
            self._nav_home_timer = None

    def _nav_home_timer_callback(self, kwargs: dict[str, Any]) -> None:
        """Called when the auto-navigate-home timer fires.

        Navigates to the home panel if the current panel differs from the
        home panel and the device is still connected.  Does nothing if the
        sleep panel is active (the user would be woken by an unwanted
        navigation).
        """
        self._nav_home_timer = None
        if self._sleep_panel_active:
            return
        if not self.app.device.connected:
            return
        if self._home_panel is None:
            return
        if self.panel and self._home_panel.id != self.panel.id:
            self.log("Auto-navigate-home timeout reached, navigating to home panel")
            self.open_home_panel()

    def close_panel(self) -> None:
        """Closes the current panel."""
        with self._guard("close_panel") as acquired:
            if acquired:
                self._close_panel_impl()

    def _close_panel_impl(self) -> None:
        # check for active timer
        if self._close_timeout is not None:
            self.app.cancel_timer(self._close_timeout)
            self._close_timeout = None
        prev_panel: HAUIPanel | None = None
        prev_kwargs: dict[str, Any] = {}
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
        # check for locked panel before opening
        if prev_panel is not None:
            unlock_panel = prev_panel.get("unlock_panel", None)
            if (
                unlock_panel is not None
                and prev_panel.id == unlock_panel.id
                and prev_panel.get_state("locked", False)
            ):
                prev_panel, prev_kwargs = None, {}

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

    def open_sleep_panel(self, autostart: bool = False, create_snapshot: bool = True) -> None:
        """Opens the sleep panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
            create_snapshot (bool, optional): Should a navigation snapshot be created.
                Defaults to True.
        """
        if create_snapshot:
            self.create_snapshot()
        if self._sleep_panel is None:
            self.close_panel()
            self.log("No sleep panel available")
            return
        self._sleep_panel_active = True
        self.app.device.sleeping = True
        self._cancel_idle_timer()
        # Swallow the touch that triggered the navigation so check_wakeup
        # doesn't immediately exit back to home when the sleep panel is also
        # the wakeup panel.
        self.app.device.woke_up = True
        self.open_panel(self._sleep_panel.id, autostart=autostart)

    def open_wakeup_panel(self, autostart: bool = False) -> None:
        """Opens the wakeup panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
        """
        if self._wakeup_panel is None:
            self.close_panel()
            self.log("No wakeup panel available")
            return
        # Clear sleep state — when a wakeup panel opens, sleep is exited.
        # check_wakeup() determines has_wakeup_panel from device config
        # independent of _sleep_panel_active, so touch-gate behaviour is kept.
        self._sleep_panel_active = False
        self.app.device.sleeping = False
        self.open_panel(self._wakeup_panel.id, autostart=autostart)

    def exit_sleep_to_prev_or_home(self, config: dict | None) -> None:
        """Exit sleep: restore the prior panel if the snapshot is fresh enough,
        otherwise open the home panel.

        Sleep state is cleared in both paths — ``restore_snapshot`` clears it on
        success, the home fallback clears it explicitly. Shared by
        ``Device.check_wakeup`` and the WAKEUP-without-wakeup-panel handler,
        which previously carried two copies of this snapshot-or-home dance.
        """
        snap_max_age = _resolve_snapshot(config or {})
        restored = snap_max_age != 0 and self.restore_snapshot(
            snap_max_age if snap_max_age > 0 else 0
        )
        if not restored:
            self._sleep_panel_active = False
            self.app.device.sleeping = False
            self.open_home_panel()

    # snapshot methods

    def create_snapshot(self) -> None:
        """Creates a snapshot of the current navigation state."""
        panel = self.panel
        panel_kwargs = self.panel_kwargs.copy()
        current_nav = self._current_nav
        current_nav_kwargs = self._current_nav_kwargs.copy()
        stack = self._stack.copy()
        snapshot = (panel, panel_kwargs, current_nav, current_nav_kwargs, stack)
        self._snapshot = snapshot
        self._snapshot_time = time.monotonic()
        self.log("Navigation snapshot created")

    def unset_snapshot(self) -> None:
        """Unsets the current navigation snapshot."""
        self._snapshot = None
        self._snapshot_time = None

    def restore_snapshot(self, max_seconds_ago: int = 0) -> bool:
        """Restores a previously created navigation snapshot.

        Args:
            max_seconds_ago (int, optional): If > 0, only restore when the snapshot
                is at most this many seconds old. Defaults to 0 (no age limit).

        Returns:
            bool: True if successfully restored, False if not
        """
        if self._snapshot is None:
            return False
        if max_seconds_ago > 0 and self._snapshot_time is not None:
            age = time.monotonic() - self._snapshot_time
            if age > max_seconds_ago:
                self.log(
                    f"Navigation snapshot too old ({age:.1f}s > {max_seconds_ago}s), not restoring"
                )
                return False
        with self._guard("restore_snapshot") as acquired:
            if not acquired:
                return False
            return self._restore_snapshot_impl(max_seconds_ago)

    def _restore_snapshot_impl(self, max_seconds_ago: int = 0) -> bool:
        prev_panel: HAUIPanel | None
        panel_kwargs: dict[str, Any]
        prev_current_nav: HAUIPanel | None
        current_nav_kwargs: dict[str, Any]
        stack: list[tuple[HAUIPanel, dict[str, Any]]]
        assert self._snapshot is not None  # checked above
        (
            prev_panel,
            panel_kwargs,
            prev_current_nav,
            current_nav_kwargs,
            stack,
        ) = self._snapshot

        # Re-resolve snapshot references against live config.
        # reload_panels() creates new HAUIPanel objects with new UUIDs, so
        # the snapshot may hold stale references.  Failing to re-resolve causes
        # the restored panel to be dead, which triggers a fallback to home on
        # the next interaction - producing the ping-pong navigation bug.
        if prev_panel is not None:
            resolved = self.app.device_config.get_panel(prev_panel.id)
            if resolved is not None:
                prev_panel = resolved
            else:
                self.log(
                    f"Snapshot panel {prev_panel.id} no longer in config, falling back to home"
                )
                self.unset_snapshot()
                self._sleep_panel_active = False
                self.app.device.sleeping = False
                self.open_home_panel()
                return False
        if prev_current_nav is not None and prev_current_nav is not prev_panel:
            resolved_nav = self.app.device_config.get_panel(prev_current_nav.id)
            if resolved_nav is not None:
                prev_current_nav = resolved_nav
            else:
                prev_current_nav = None

        self.panel = prev_panel
        self.panel_kwargs = panel_kwargs
        self._current_nav = prev_current_nav
        self._current_nav_kwargs = current_nav_kwargs
        self._stack = stack

        # Consume the snapshot and clear sleep state so check_wakeup() and
        # process_event() don't re-trigger the same restore on the next event.
        self.unset_snapshot()
        self._sleep_panel_active = False
        self.app.device.sleeping = False

        # Cancel any pending timeouts before restoring the panel to prevent
        # stale _page_timeout_callbacks from firing mid-restore.
        self.cancel_timeouts()

        self.reload_panel()
        self.log("Navigation snapshot restored")
        return True

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Dispatch a device event to the matching handler, then forward it
        to the active page.

        The per-event handlers are mutually exclusive on ``event.name``; the
        interaction-timer reset runs first because it applies across several
        event types (touch/button/gesture).
        """
        self.debug_log(f"Navigation process_event: {event.name} value={str(event.value)[:100]}")
        self._reset_hub_timers_on_interaction(event)

        handlers: dict[str, Any] = {
            ESPEvent.PAGE: self._handle_page_event,
            ESPEvent.TIMEOUT: self._handle_timeout_event,
            ESPEvent.DISPLAY_STATE: self._handle_display_state_event,
            ESPEvent.WAKEUP: self._handle_wakeup_event,
            ESPEvent.SLEEP: self._handle_sleep_event,
            ESPEvent.BUFFER_OVERFLOW: self._handle_buffer_overflow_event,
        }
        handler = handlers.get(event.name)
        if handler is not None:
            handler(event)

        # allow page to process events (the SLEEP handler may have cleared it)
        if self.page is not None:
            self.page.process_event(event)

    def _reset_hub_timers_on_interaction(self, event: HAUIEvent) -> None:
        """Reset the hub-side idle / nav-home timers on user interaction.

        Fallback for when the device doesn't publish esphome.timeout events
        (e.g. use_auto_sleeping OFF). Button presses only count when
        ``reset_interaction_on_button`` is enabled.
        """
        if event.name not in (
            ESPEvent.TOUCH_START,
            ESPEvent.BUTTON_LEFT,
            ESPEvent.BUTTON_RIGHT,
            ESPEvent.GESTURE,
        ):
            return
        is_button = event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT)
        if is_button and not self.app.device.get("reset_interaction_on_button", True):
            return
        self._start_idle_timer()
        self._start_nav_home_timer()

    def _handle_page_event(self, event: HAUIEvent) -> None:
        """A page-change ack arrived from the device."""
        # cancel page timeout if any
        if self._page_timeout is not None:
            self.app.cancel_timer(self._page_timeout)
            self._page_timeout = None
        if self.page is None:
            return
        # mismatch - likely a stale echo of a previous goto.
        # Don't reload; _page_timeout handles real failures.
        if self.page.page_id != event.as_int():
            self.debug_log(
                f"Stale page event {PAGE_MAPPING.get(event.as_int())} "
                f"received while {PAGE_MAPPING.get(self.page.page_id)} is active, ignoring",
            )
            return
        if self.page.page_id_recv is None:
            self.page.page_id_recv = event.as_int()
        # page not started yet - schedule display_panel after settle delay
        # to let the Nextion finish initialising all page components before
        # render commands arrive.
        if not self.page.is_started() and self.panel is not None:
            delay = self.app.device.get("page_settle_delay", 0.05)
            if self._page_settle_timer is not None:
                self.app.cancel_timer(self._page_settle_timer)
            self._page_settle_timer = self.app.run_in(self._page_settle_callback, delay)

    def _page_settle_callback(self, _kwargs: dict[str, Any]) -> None:
        """Timer callback: render the panel after the page settle delay."""
        self._page_settle_timer = None
        if self.panel is not None:
            self.display_panel(self.panel)

    def _handle_timeout_event(self, event: HAUIEvent) -> None:
        """esphome.timeout (sleep/page) -> open the sleep panel."""
        if event.value not in ("sleep", "page"):
            return
        if self._sleep_panel and self.panel and self._sleep_panel.id != self.panel.id:
            self._sleep_panel_active = True
            self.open_sleep_panel(autostart=True)

    def _handle_display_state_event(self, event: HAUIEvent) -> None:
        """display_state on/dim/off transitions (hub-connected wake path)."""
        device = self.app.device
        # During reconnection the device publishes display_state="on" before
        # the handshake completes; _sleep_panel_active may still be True and
        # device.connected False. Skip panel openings - set_connected handles
        # it. Returning early still lets the page forwarding in process_event
        # run for this event.
        if not device.connected:
            return
        # Woke from off with a wakeup panel configured -> show it. The
        # sleep-screen *exit* decision is made on the touch itself
        # (Device.check_wakeup), never here, so the order of the touch and
        # display_state events can't cause a double / premature exit.
        prev_state = device.device_info.get("display_state")
        if prev_state == "off" and not self._sleep_panel_active:
            if not self.app.device.sleeping:
                return  # check_wakeup already exited sleep
            self.log(f"Display state changed from sleep to {event.as_str()}")
            self.open_wakeup_panel()

    def _handle_wakeup_event(self, event: HAUIEvent) -> None:
        """esphome.wakeup (non-hub / post-hardware-sleep wake)."""
        if self._wakeup_panel is not None:
            self.log(f"Wakeup panel: {self._wakeup_panel.id}")
            self.open_wakeup_panel()
            # open_wakeup_panel() clears _sleep_panel_active; check_wakeup()
            # still gates touch via the wakeup_panel key (independent of the
            # flag). device.sleeping is cleared by Device.process_event.
        else:
            # No wakeup panel: restore the prior panel unless config forces home.
            self.log("No wakeup panel available, restoring snapshot or home")
            self.exit_sleep_to_prev_or_home(self.app.device.config)

    def _handle_sleep_event(self, event: HAUIEvent) -> None:
        """esphome.sleep -> drop the active page."""
        if self.page:
            self.unset_page()

    def _handle_buffer_overflow_event(self, _event: HAUIEvent) -> None:
        """esphome.buffer_overflow — Nextion RX buffer overflowed, commands lost.

        The Nextion reports 0x24 when its internal serial buffer overflows.
        All instructions that were in-flight at that moment are permanently
        lost — the display shows a mix of stale and updated widgets.

        We schedule a debounced re-render of the current panel so the display
        recovers automatically.  The 500ms delay lets the ESPHome queue drain
        any remaining commands before we re-send the full panel state.
        """
        self.log(
            "Nextion buffer overflow detected — scheduling panel re-render",
            level="WARNING",
        )
        if self._buffer_overflow_timer is not None:
            self.app.cancel_timer(self._buffer_overflow_timer)
        self._buffer_overflow_timer = self.app.run_in(self._buffer_overflow_recover, 0.5)

    def _buffer_overflow_recover(self, _kwargs: dict[str, Any]) -> None:
        """Re-render the current panel after a buffer overflow."""
        self._buffer_overflow_timer = None
        if self.panel is not None and self.page is not None:
            self.log("Re-rendering panel after buffer overflow")
            self.display_panel(self.panel)

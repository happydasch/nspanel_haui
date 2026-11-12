from __future__ import annotations

import time
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from .abstract.haui_base import HAUIBase
from .abstract.haui_event import HAUIEvent
from .controller.notification import Notification
from .device_config import is_portrait_model
from .mapping.const import AUTO_SWITCHES, ESPAction, ESPEvent, NotifEvent
from .mapping.panel import PANEL_MAPPING, POPUP_PANEL_MAPPING, SYS_PANEL_MAPPING
from .schedule import ScheduleEntry, active_entry, next_boundary

if TYPE_CHECKING:
    from ..hub.app import NSPanelHAUI
from .mapping.const import SysPanelKey

# How long after a touch-initiated idle-page open the residual touch events
# of the triggering interaction are ignored.  The ESP32 publishes touch_start
# twice per press — instantly from the Nextion on_touch callback and again once
# its 200 ms touch poller catches up (serial read lag can push that ~1 s behind
# a render burst).  A quick tap on the idle button can therefore leave a
# duplicate touch_start behind *after* open_idle_panel() already ran; the
# display is still "on" in that flow (open_idle_panel never reported "off"),
# so the duplicate would take the one-touch wakeup path and dismiss the
# idle page the button had just opened.  1.5 s covers the poller lag while
# staying far shorter than a deliberate second tap to wake the display.
IDLE_TOUCH_GRACE_WINDOW: float = 1.5

# The native Nextion callback ("1") and the 200 ms coordinate poller ("")
# publish a touch_start for the same physical press.  The native event is the
# authoritative wake decision; the poller event is ignored while a native event
# for the same press is recent.  If the native event is lost (serial/API lag),
# the poller event is used as a fallback so the touch is never ignored.
TOUCH_DUPLICATE_WINDOW: float = 1.5

# A freshly booted device reports an uptime of a few seconds in its
# connection request; a Wi-Fi drop-and-reconnect keeps the (much longer)
# uptime.  The startup sound plays only while uptime stays under this
# threshold.  A missing uptime key (older firmware) plays anyway, preserving
# the previous every-connect behavior.
STARTUP_SOUND_MAX_UPTIME_SECONDS = 120


class HAUIDevice(HAUIBase):
    """
    Represents a NSPanel device.

    - Interaction with device (swipes are the gesture controller's)
    - Device wide callbacks from entities / homeassistant
    - Physical buttons state
    """

    def __init__(self, app: NSPanelHAUI, config: dict | None = None) -> None:
        """Initializes the device.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config of device. Defaults to None.
        """
        super().__init__(app, config)
        self.device_info: dict = {}
        # First-touch guard of the idle page: while the display is **off** the
        # first touch only wakes it (see check_wakeup).  Set when the idle page
        # opens (in case the display is off) and whenever the display reports
        # "off"; cleared when a touch exits the idle page or is consumed as the
        # wake touch.  A visible display ("on" or "dim") needs only one touch,
        # so the guard is not armed there.
        self._first_touch_consumed = False
        # Monotonic timestamp of the last visible ("on" or "dim") display_state
        # event.  A touch that woke the display may reach the hub after the
        # display-on event; the guard is consumed as the wake touch only within
        # TOUCH_DUPLICATE_WINDOW of this timestamp.  Older = stale guard.
        self._display_on_ts: float = 0.0
        # Monotonic deadline until which TOUCH_START events are treated as
        # leftovers of the touch that opened the idle page (see
        # arm_idle_touch_grace).  0.0 = no grace active.
        self._idle_touch_grace_until = 0.0
        # Monotonic timestamp of the last native touch_start ("1") event.
        # The poller's empty-value duplicate is ignored within
        # TOUCH_DUPLICATE_WINDOW of this timestamp, but used as a fallback
        # when the native event was lost (serial/API lag).
        self._last_native_touch_ts: float = 0.0
        self._initial_connect_done = False
        self._btn_left_info: dict[str, Any] = {
            "item_id": None,
        }
        self._btn_right_info: dict[str, Any] = {
            "item_id": None,
        }
        self._persistent_sound_handle: str | None = None
        self._schedule_timer: str | None = None

    # prepare and update

    def _check_config(self) -> None:
        """Checks if the configuration is valid.

        Raises:
            ValueError: Missing values in config
        """
        config = self.app.device_config
        # check if all sys_panels are valid
        chk_sys_panels = [x.get("key") for x in config.get("sys_panels", [])]
        for panel_key in SYS_PANEL_MAPPING | POPUP_PANEL_MAPPING:
            if panel_key not in chk_sys_panels:
                raise ValueError(f"Missing sys_panel {panel_key} in config")
        for panel in config.get_panels():
            if panel.get_type() not in PANEL_MAPPING:
                raise ValueError(f"Panel type {panel.get_type()} not supported")
        self.log(f"Loaded {len(config.get_panels())} panels")

    def _register_callbacks(self) -> None:
        """Resolves the relay entity each physical button toggles."""
        for side in ("left", "right"):
            button = getattr(self, f"_btn_{side}_info")
            entity_id = self.get(f"button_{side}_entity", None)
            if not entity_id:
                name = f"Relay {side.title()}"
                entity_id = self._resolve_esp_entity("switch", name)
            button["item_id"] = entity_id

    def _cancel_callbacks(self) -> None:
        """Forgets the resolved button entities."""
        for i in ["left", "right"]:
            getattr(self, f"_btn_{i}_info")["item_id"] = None

    def _resolve_esp_entity(self, domain: str, name: str) -> str | None:
        """Resolve a built-in ESPHome entity on this device by its authored name."""
        return self.find_esphome_entity_id(domain, name)

    def _sync_config_switch(
        self,
        hub_key: str,
        switch_entity_id: str | None,
        hub_value: bool | None = None,
        reason: str = "",
    ) -> None:
        """Apply a deliberate config value to its corresponding ESPHome switch."""
        if not switch_entity_id or not self.app.item_exists(switch_entity_id):
            return
        if hub_value is None:
            hub_value = self.get(hub_key, True)
        item = self.app.get_item(switch_entity_id)
        state = item.get_state()
        if state not in ("on", "off"):
            return
        if hub_value and state == "off":
            self.log(f"Syncing {switch_entity_id} ON ({reason or f'hub config {hub_key}=True'})")
            item.turn_on()
        elif not hub_value and state == "on":
            self.log(f"Syncing {switch_entity_id} OFF ({reason or f'hub config {hub_key}=False'})")
            item.turn_off()

    def _sync_changed_auto_switch_settings(self, changed_settings: set[str]) -> None:
        """Apply only automatic-switch settings that changed in the Settings editor."""
        for setting in changed_settings:
            switch_key = setting.removeprefix("use_")
            if switch_key in AUTO_SWITCHES:
                self._sync_config_switch(
                    setting,
                    self._resolve_esp_entity("switch", AUTO_SWITCHES[switch_key]),
                    reason="Settings changed",
                )

    def _sun_time(self, event: str, day: date) -> datetime | None:
        """Local time of a sun event; None where the sun does not rise or set that day."""
        point = self.app.get_sun_time(event, day)
        if point is None:
            self.log(
                f"No {event} on {day} at this location; schedule entries using it are inactive",
                level="WARNING",
            )
        return point

    def _schedule_entries(self) -> list[ScheduleEntry]:
        return [ScheduleEntry.from_config(entry) for entry in self.get("schedule", [])]

    def _active_schedule_entry(self) -> ScheduleEntry | None:
        """The schedule entry whose window contains now, if any."""
        entries = self._schedule_entries()
        if not entries:
            return None
        return active_entry(entries, self.app.now(), self._sun_time)

    def _sync_number(self, value: float | int | None, entity_name: str) -> None:
        """Write a value to one of the device's ESPHome numbers when it differs."""
        entity_id = self._resolve_esp_entity("number", entity_name)
        if value is None or not entity_id or not self.app.item_exists(entity_id):
            return
        item = self.app.get_item(entity_id)
        current = item.get_state()
        if (
            current is not None
            and current not in ("unavailable", "unknown")
            and float(current) != value
        ):
            self.log(f"Syncing {entity_id} to {value}")
            item.set_state(state=value)

    def _sync_button_interaction(self) -> None:
        """Keep ``reset_interaction_on_button`` aligned with ESPHome.

        The device handles the timer reset on the physical button press;
        mirroring this switch keeps that behavior consistent with hub config.
        """
        self._sync_config_switch(
            "reset_interaction_on_button",
            self._resolve_esp_entity("switch", "Use Button Interaction"),
        )

    def _sync_relay_config(self) -> None:
        """Sync hub config ``use_relay_left``/``use_relay_right`` with ESPHome switches.

        Prevents the double-toggle / no-toggle scenario where the hub expects
        one behaviour but the ESPHome firmware (with its own
        ``use_relay_left``/``use_relay_right`` switches using
        ``RESTORE_DEFAULT_ON``) acts differently.
        """
        self._sync_config_switch(
            "use_relay_left",
            self._resolve_esp_entity("switch", "Use Relay Left"),
        )
        self._sync_config_switch(
            "use_relay_right",
            self._resolve_esp_entity("switch", "Use Relay Right"),
        )

    # part
    def _sync_behavior_config(self) -> None:
        """Sync display timeouts and brightness: the active schedule entry's, else the settings.

        Without a schedule the Auto display off switch belongs to its live
        ESPHome state.  A schedule turns the display-off on and off per entry,
        so the hub then owns the switch and writes it on every sync.
        """
        entry = self._active_schedule_entry()

        def value(key: str) -> float | int | None:
            """The active entry's value for ``key``, else the device setting."""
            if entry is not None:
                entry_value = getattr(entry, key)
                if entry_value is not None:
                    return entry_value
            return self.get(key, None)

        self._sync_number(value("timeout_dimming"), "Timeout Dimming")
        self._sync_number(value("timeout_display_off"), "Timeout Display-Off")
        self._sync_number(value("brightness"), "Brightness Full")
        self._sync_number(value("brightness_dim"), "Brightness Dimmed")
        self._sync_number(value("duration_dimming"), "Duration Dimming")
        if self.get("schedule", []):
            self._sync_config_switch(
                "use_auto_display_off",
                self._resolve_esp_entity("switch", AUTO_SWITCHES["auto_display_off"]),
                hub_value=entry.display_off if entry else None,
                reason="Schedule",
            )
        self._sync_display_model()

    def _sync_display_model(self) -> None:
        """Sync the hub's display model with the firmware's gesture size.

        The gesture script derives its touch dimensions from the model
        (``display_model`` number: 0 = landscape, 1 = portrait). The ESPHome
        number entity is resolved by its authored name on this linked device.
        """
        number_entity_id = self._resolve_esp_entity("number", "Display Model")
        if not number_entity_id or not self.app.item_exists(number_entity_id):
            return
        value = 1 if self.is_portrait else 0
        item = self.app.get_item(number_entity_id)
        current = item.get_state()
        if current is not None and current != "unavailable" and float(current) != value:
            self.log(
                f"Syncing {number_entity_id} to {value} "
                f"(hub config display_model={self.display_model!r})"
            )
            item.set_state(state=value)

    @property
    def display_model(self) -> str:
        """The configured display model (``eu`` or ``us``), lower-cased."""
        return str(self.get("display_model", "eu")).lower()

    @property
    def is_portrait(self) -> bool:
        """Whether this device runs the rotated portrait TFT layout."""
        return is_portrait_model(self.display_model)

    # part

    def sync_config_to_device(self, changed_auto_settings: set[str] | None = None) -> None:
        """Apply non-automatic-switch config and explicitly changed switch settings.

        Automatic switches are otherwise owned by the live ESPHome state, which
        lets Home Assistant automations control them without lifecycle or page
        changes writing a stale config value back.
        """
        self._sync_button_interaction()
        self._sync_relay_config()
        self._sync_changed_auto_switch_settings(changed_auto_settings or set())
        self._sync_behavior_config()
        self._arm_schedule_timer()

    def start_part(self) -> None:
        """Starts the part."""
        self.log("Device is starting")
        self._check_config()
        self._register_callbacks()
        self.sync_config_to_device()

    def stop_part(self) -> None:
        """Stops the part."""
        self.log("Device is stopping")
        self._cancel_callbacks()
        self._cancel_timer("_schedule_timer")
        self._stop_persistent_sound()

    # public

    def set_device_info(self, device_info: dict, append: bool = True) -> None:
        """Sets devices related vars from a dict.

        Args:
            device_info (dict): dict with device info vars
            append (bool, optional): Append or replace values. Defaults to True (append).
        """
        if append:
            self.device_info = {**self.device_info, **device_info}
        else:
            self.device_info = device_info

    # ------------------------------------------------------------------
    # Sleep / display-state predicates — the single source of truth
    # ------------------------------------------------------------------

    @property
    def display_state(self) -> str:
        """Display brightness state reported by the firmware: "on", "dim" or "off"."""
        return str(self.device_info.get("display_state", "off"))

    @property
    def display_visible(self) -> bool:
        """Whether the display is visible to the user ("on" or "dim")."""
        return self.display_state in ("on", "dim")

    @property
    def display_dark(self) -> bool:
        """Whether the display is dark ("off")."""
        return self.display_state == "off"

    @property
    def sleeping(self) -> bool:
        """Whether the device is sleeping: the idle page is shown.

        "Sleep" is the hub-side idle page and is independent of display
        brightness: the display may be dark without an idle page, and the
        idle page may be shown while the display is visible.  This is the
        single place that answers "is the device sleeping?"; consumers should
        not read ``navigation.idle_panel_active`` directly.
        """
        navigation = self.app.controller.get("navigation")
        return bool(navigation is not None and navigation.idle_panel_active)

    @property
    def needs_wake_touch(self) -> bool:
        """Whether the next touch only wakes a dark display instead of exiting sleep.

        True while the device sleeps with the display "off".  A visible
        display ("on" or "dim") leaves the idle page on the first touch.
        """
        return self.sleeping and not self.display_visible

    def on_idle_page_opened(self) -> None:
        """Arm the first-touch guard when the idle page opens.

        Called by the navigation controller whenever the idle page is shown.
        Only a dark display needs a wake touch before the idle page can be
        exited; a visible display ("on" or "dim") leaves on the first touch.
        Touch-initiated entry while the display is visible is protected
        separately by the idle-touch grace window.
        """
        self._first_touch_consumed = not self.display_visible

    # ------------------------------------------------------------------
    # Connection state — delegates to connection controller
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Return ``True`` iff the device connection is fully established.

        Delegates to the connection controller so there is a single source
        of truth for connection state.
        """
        conn = self.app.controller.get("connection")
        return conn.is_connected if conn else False

    def on_connection_changed(self, connected: bool) -> None:
        """Handle connection state change from the connection controller.

        On first connect: opens sys_system panel.
        On reconnect: restores the navigation panel (or falls back to home).
        On disconnect: resets idle-session state so stale flags do not
        trigger navigation or wake handling during reconnection.

        The ``_initial_connect_done`` guard distinguishes first-connect from
        reconnect. Without this guard, every reconnect (~30s ESPHome heartbeat
        timeout) would trigger sys_system → home → clock, disrupting the user.

        Args:
            connected (bool): Connection state
        """
        self.log(f"Device connected: {connected}")
        navigation = self.app.controller.get("navigation")
        if navigation is None:
            return
        # Cancel any stale navigation timeouts before changing state.
        # Timeouts set before a disconnect can fire after reconnect and
        # interfere with the new panel navigation (stale goto_page,
        # premature close_panel).
        navigation.cancel_timeouts()
        if connected:
            navigation.prepare_resume()
            self.sync_config_to_device()
            if self.get("sound_on_startup"):
                uptime = self.device_info.get("uptime")
                if uptime is None or uptime < STARTUP_SOUND_MAX_UPTIME_SECONDS:
                    self.play_sound("startup")
            # Only open sys_system on initial connection, not on reconnects.
            # Without this guard, every reconnect (~30s ESPHome heartbeat timeout)
            # triggers sys_system → home → clock, disrupting the user.
            if not self._initial_connect_done:
                navigation.open_panel(SysPanelKey.SYS_SYSTEM)
                self._initial_connect_done = True
            else:
                # Reconnect: restore the correct panel on the display.
                # The ESP32 firmware navigates to the system page on disconnect,
                # so we must re-navigate back to the user's panel here.
                # If the current panel is a popup (non-nav), skip it - popups
                # don't survive disconnects. Fall back to the current nav panel.
                # Use run_in to schedule the panel opening asynchronously.
                # open_panel involves blocking ESPHome native API service calls
                # (publish → async_call(blocking=True) → .result(timeout=10)).
                # Running it synchronously would prevent heartbeat events from
                # being processed on this executor thread, causing the connection
                # timeout to fire.
                panel = navigation.get_current_panel()
                nav_panel = navigation.get_current_nav_panel()
                if panel is not None and nav_panel is not None and panel.id == nav_panel.id:
                    # Current panel is the nav panel - re-open it directly
                    self.app.run_in(
                        lambda _: navigation.open_panel(panel.id, force=True),
                        0,
                    )
                elif nav_panel is not None:
                    self.app.run_in(
                        lambda _: navigation.open_panel(nav_panel.id, force=True),
                        0,
                    )
                else:
                    navigation.open_home_panel()
        else:
            # Reset idle-session state on disconnect so stale flags do not
            # trigger navigation or wake handling during reconnection.  Touch
            # guards are reset too - the next interaction starts on a clean
            # slate.
            navigation.mark_awake()
            self._first_touch_consumed = False
            self._idle_touch_grace_until = 0.0

    def _sounds_muted(self) -> bool:
        """Whether the active schedule entry mutes sounds.

        A muted window suppresses every sound and keeps a notification from
        waking the display.
        """
        entry = self._active_schedule_entry()
        return entry is not None and not entry.sound

    def _arm_schedule_timer(self) -> None:
        """Arm a timer for the next moment a schedule entry starts or ends."""
        self._cancel_timer("_schedule_timer")
        entries = self._schedule_entries()
        if not entries:
            return
        now = self.app.now()
        boundary = next_boundary(entries, now, self._sun_time)
        if boundary is None:
            return
        delay = (boundary - now).total_seconds()
        self._schedule_timer = self.app.run_in(self._schedule_boundary_callback, max(delay, 1))

    def _schedule_boundary_callback(self, _kwargs: Any) -> None:
        """A schedule boundary passed: apply the now-active settings and re-arm."""
        self._schedule_timer = None
        self._sync_behavior_config()
        self._arm_schedule_timer()

    # public

    def wake_for_notification(self) -> None:
        """Wake the display for a notification popup that opened on its own.

        A schedule entry with sound off keeps the display dark: the popup stays
        open, so it is what the user sees on the next touch.  The display then
        dims and turns off on its normal timers.
        """
        if self._sounds_muted():
            self.log("Schedule mutes sounds — not waking the display", level="DEBUG")
            return
        self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")

    def get_locale(self) -> str:
        """Returns the device locale.

        Returns:
            str: Locale
        """
        return self.get("locale")

    def get_time_format(self) -> str:
        """Return the device's strftime time format, falling back to the hub default.

        An empty per-device value means "inherit the hub-level default"
        (``DEFAULT_CONFIG["time_format"]``), so a device can stay in sync
        with the integration default or override it per panel.

        Returns:
            str: strftime format, e.g. "%H:%M" or "%I:%M %p"
        """
        value = self.get("time_format", "")
        if value:
            return value
        return self.app.device_config.get("time_format", "%H:%M")

    def get_date_format(self) -> str:
        """Return the device's strftime date format, falling back to the hub default.

        Returns:
            str: strftime format, e.g. "%m/%d/%Y"
        """
        value = self.get("date_format", "")
        if value:
            return value
        return self.app.device_config.get("date_format", "%A, %d. %B %Y")

    def get_date_format_locale(self) -> str:
        """Return the device's locale date pattern name, falling back to the hub default.

        The pattern name (e.g. "full", "long", "medium", "short", "E", "EEEE")
        selects a locale-aware date layout.  An empty string disables locale
        patterns so ``get_date_format()`` (strftime) is used instead.

        Returns:
            str: Babel-style pattern name, e.g. "full"
        """
        value = self.get("date_format_locale", "")
        if value:
            return value
        return self.app.device_config.get("date_format_locale", "full")

    def get_slug(self) -> str:
        """Returns the device name slugified the way Home Assistant builds entity ids.

        Returns:
            str: Slug, e.g. ``nspanel_living`` for ``NSPanel-Living``
        """
        return self.app.device_slug

    def get_name(self) -> str:
        """Returns the device name.

        Returns:
            str: Device name
        """
        # self.get("name") returns the hub-level name from the device
        # sub-dict config. The actual per-device name is resolved at app
        # level in NSPanelHAUI.initialize() and stored in _runtime_device_name.
        return self.app._runtime_device_name or self.get("name")

    def toggle_left_button_state(self) -> None:
        """Toggles the left button relay entity."""
        self._toggle_button_state("left")

    def toggle_right_button_state(self) -> None:
        """Toggles the right button relay entity."""
        self._toggle_button_state("right")

    def play_sound(self, name: str) -> None:
        """Plays a sound.

        A schedule entry with sound off suppresses all sounds — the call is a
        no-op then, so callers do not need individual checks.

        Args:
            name (str): Name of the sound
        """
        if self._sounds_muted():
            self.log(f"Schedule mutes sounds — suppressing sound '{name}'", level="DEBUG")
            return
        self.app.controller["esphome"].esphome.publish(ESPAction.PLAY_SOUND, name)

    # callback

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process event.

        Args:
            event (HAUIEvent): Event
        """
        # update device vars values. Store under the unprefixed key so the
        # handshake-populated keys ("display_state", "page", ...) stay in sync
        # with live events; all readers use the unprefixed names.
        key = event.name.removeprefix("esphome.")
        self.device_info[key] = event.value
        # a touch is the sole driver of the idle-page exit decision
        if event.name == ESPEvent.TOUCH_START:
            if self._idle_touch_grace_active():
                self.log("Ignoring residual touch_start after idle-page open")
                return
            # The native Nextion callback ("1") is the authoritative wake
            # decision per physical press; the ESPHome coordinate poller
            # reports the same press with an empty value up to ~1 s later.
            # Suppress the poller duplicate, but use it as a fallback when the
            # native event was lost (serial/API lag) — otherwise a lost "1"
            # makes the touch do nothing at all.
            now = time.monotonic()
            if event.value == "1":
                self._last_native_touch_ts = now
                self.check_wakeup()
            elif now - self._last_native_touch_ts > TOUCH_DUPLICATE_WINDOW:
                self.check_wakeup()
        # The display went dark again (e.g. while the idle page stays open),
        # so the next touch must only wake it: re-arm the two-touch guard when
        # the display turns "off".  "on" and "dim" are both visible states
        # where a single touch leaves the idle page.  A touch that caused a
        # dark→visible transition can reach the hub after the display-state
        # event, so both visible states record the transition time:
        # check_wakeup() consumes that wake touch within TOUCH_DUPLICATE_WINDOW
        # and treats an older guard as stale.
        elif event.name == ESPEvent.DISPLAY_STATE:
            if event.value == "off":
                self._first_touch_consumed = True
            elif event.value in ("on", "dim"):
                self._display_on_ts = time.monotonic()
        elif event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT):
            side = "left" if event.name == ESPEvent.BUTTON_LEFT else "right"
            if event.value == "1":  # pressed
                # ESPHome records the press as interaction; the hub handles
                # the idle-page exit. The entity toggle stays on release so a
                # held button does not spam toggles.
                if self.get("reset_interaction_on_button", True):
                    self.check_wakeup()
            elif event.value == "0":  # released
                self._on_button_release(side)
        # process notification events
        elif event.name == NotifEvent.NOTIF_ADD:
            if not isinstance(event.value, Notification):
                raise TypeError(f"Notification event value must be a Notification: {event.value!r}")
            if self.get("sound_on_notification"):
                if event.value.persistent:
                    # Started even while the schedule mutes sounds: the loop
                    # stays silent there and sounds once that entry ends,
                    # until dismissed.
                    self._start_persistent_sound()
                elif event.value.sound:
                    if self._sounds_muted():
                        self.log(
                            "Schedule mutes sounds — suppressing notification sound",
                            level="DEBUG",
                        )
                    else:
                        self.play_sound(event.value.sound)
        elif event.name in (NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR):
            # Stop as soon as no audible persistent notification remains; a
            # silent persistent entry must not keep the loop alive.
            if not self._persistent_sound():
                self._stop_persistent_sound()

    def arm_idle_touch_grace(self) -> None:
        """Ignore the residual touch events of the touch that opened the idle page.

        Called by the touch producer (e.g. the header idle button) right
        before the idle page opens.  Expires after
        ``IDLE_TOUCH_GRACE_WINDOW`` seconds; hardware-button presses and
        touches after the window behave normally.
        """
        self._idle_touch_grace_until = time.monotonic() + IDLE_TOUCH_GRACE_WINDOW

    def _idle_touch_grace_active(self) -> bool:
        """Whether an incoming TOUCH_START is inside the armed grace window.

        Only while the idle page is actually open: once the idle session was
        exited the window must not swallow the fresh interaction.
        """
        if not self.sleeping:
            return False
        return time.monotonic() < self._idle_touch_grace_until

    def reset_interaction_timer(self) -> None:
        """Reset the firmware's interaction timer without changing the current page."""
        self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")

    def check_wakeup(self) -> None:
        """Exit the idle page on any touch or hardware-button press.

        When the display is **on** or **dim** the user can see the screen, so a
        single touch immediately leaves the idle page (one-touch).  When the
        display is **off** the first touch only wakes the display; the second
        touch performs the action (two-touch).

        A hardware button calls this on both press and release, so a single
        physical press wakes and exits (documented in docs/user/device.md).

        The wake operation itself is panel-independent: with no idle page
        open there is nothing to exit and the firmware's own display-idle
        machine handles brightness when its interaction timer is reset by the
        touch.
        """
        navigation = self.app.controller.get("navigation")
        if navigation is None or not self.sleeping:
            return
        if not navigation.panel:
            return

        if self.display_visible:
            # A visible display needs only one touch to leave the idle page.
            # A dark→visible transition caused by a touch can reach the hub
            # after the display-state event.  Consume that wake touch when it
            # arrives within TOUCH_DUPLICATE_WINDOW of the transition; an older
            # armed guard is stale (the display was woken remotely) and a
            # single touch leaves the idle page.
            if (
                self._first_touch_consumed
                and time.monotonic() - self._display_on_ts <= TOUCH_DUPLICATE_WINDOW
            ):
                self._first_touch_consumed = False
                self.log("Not exiting idle page, just woke up")
                return
            self._first_touch_consumed = False
            navigation.exit_idle_to_prev_or_home(self.config)
            return

        # Display is "off" (or not yet known): the first touch only wakes the
        # display; the second touch exits.
        if self._first_touch_consumed:
            self._first_touch_consumed = False
            self.log("Not exiting idle page, just woke up")
            return
        navigation.exit_idle_to_prev_or_home(self.config)

    def _on_button_release(self, side: str) -> None:
        """Handle a hardware button release (``side`` = "left" / "right").

        With ``reset_interaction_on_button`` enabled, the firmware records the
        press as the interaction and this handler completes the idle-page wake.
        The toggle runs before ``check_wakeup`` so it isn't delayed by the
        blocking goto_page navigation inside it.
        """
        reset = self.get("reset_interaction_on_button", True)
        getattr(self, f"toggle_{side}_button_state")()
        if reset:
            self.check_wakeup()

    def _toggle_button_state(self, side: str) -> None:
        button = getattr(self, f"_btn_{side}_info")
        entity_id = button["item_id"]
        if not entity_id or not self.app.item_exists(entity_id):
            if self.get(f"button_{side}_entity", None):
                return
            entity_id = self._resolve_esp_entity("switch", f"Relay {side.title()}")
            button["item_id"] = entity_id
        if not entity_id or not self.app.item_exists(entity_id):
            return
        if not self.get(f"use_relay_{side}", True):
            self.app.get_item(entity_id).call_service("toggle")

    def _persistent_sound(self) -> str:
        """The loop sound: the first queued audible persistent notification's sound.

        Silent persistent notifications neither mute the loop nor block a
        later audible one; when the current one leaves the queue, the next
        audible sound takes over.
        """
        notifications = self.app.controller["notification"].get_notifications()
        return next((n.sound for n in notifications if n.persistent and n.sound), "")

    def _play_persistent_sound(self) -> None:
        """Play one round of the persistent alert, unless the schedule mutes sounds."""
        if self._sounds_muted():
            return
        sound = self._persistent_sound()
        if sound:
            self.play_sound(sound)

    def _persistent_sound_callback(self, kwargs: Any) -> None:
        if self._persistent_sound():
            self._play_persistent_sound()
        else:
            self._stop_persistent_sound()

    def _start_persistent_sound(self) -> None:
        if self._persistent_sound_handle is not None:
            return
        if not self._persistent_sound():
            return
        interval = self.get("persistent_sound_interval")
        self._play_persistent_sound()
        self._persistent_sound_handle = self.app.run_every(
            self._persistent_sound_callback, f"now+{interval}", interval
        )

    def _stop_persistent_sound(self) -> None:
        self._cancel_timer("_persistent_sound_handle")

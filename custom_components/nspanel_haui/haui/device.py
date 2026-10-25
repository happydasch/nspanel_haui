from __future__ import annotations

import time
from datetime import datetime, timedelta
from datetime import time as dt_time
from typing import TYPE_CHECKING, Any

from .abstract.haui_base import HAUIBase
from .abstract.haui_event import HAUIEvent
from .controller.notification import Notification
from .device_config import is_portrait_model
from .mapping.const import ESPAction, ESPEvent, NotifEvent, NotifType
from .mapping.panel import PANEL_MAPPING, SYS_PANEL_MAPPING

if TYPE_CHECKING:
    from ..nspanel_haui import NSPanelHAUI
from .mapping.const import SysPanelKey


def _notification_sound(notif_type: str) -> str:
    """Name of the ESPHome sound played for a notification of this type."""
    return "alert" if notif_type == NotifType.CRITICAL else "notification"


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

# A freshly booted device reports an uptime of a few seconds in its
# connection request; a Wi-Fi drop-and-reconnect keeps the (much longer)
# uptime.  The startup sound plays only while uptime stays under this
# threshold.  A missing uptime key (older firmware) plays anyway, preserving
# the previous every-connect behavior.
STARTUP_SOUND_MAX_UPTIME_SECONDS = 120


def _time_in_window(now_time: dt_time, start_time: dt_time, end_time: dt_time) -> bool:
    """Whether *now_time* falls inside the ``[start, end]`` wall-clock window.

    A window where ``start <= end`` is a same-day window; a window where
    ``start > end`` spans midnight (e.g. 22:00-06:00).  Boundaries are
    inclusive.  Both quiet hours and the sleep schedule use this comparison.
    """
    if start_time <= end_time:
        return start_time <= now_time <= end_time
    # overnight range
    return now_time >= start_time or now_time <= end_time


class HAUIDevice(HAUIBase):
    """
    Represents a NSPanel device.

    - Gestures and interaction with device
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
        # First-touch guard of the idle page: while the display is
        # dimmed/off the first touch only wakes it (see check_wakeup).  Set
        # when the idle page opens (in case the display is not on) and
        # whenever the display reports dim/off; cleared when a touch exits the
        # idle page or is consumed as the wake touch.
        self._first_touch_consumed = False
        # Monotonic deadline until which TOUCH_START events are treated as
        # leftovers of the touch that opened the idle page (see
        # arm_idle_touch_grace).  0.0 = no grace active.
        self._idle_touch_grace_until = 0.0
        self._initial_connect_done = False
        self._synced_display_model: str | None = None
        self._btn_left_info: dict[str, Any] = {
            "item_id": None,
        }
        self._btn_right_info: dict[str, Any] = {
            "item_id": None,
        }
        self._persistent_sound_handle: str | None = None
        # run_in handle of the sleep-schedule boundary timer (None = not armed).
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
        for panel_key in SYS_PANEL_MAPPING.keys():
            if panel_key not in chk_sys_panels:
                raise ValueError(f"Missing sys_panel {panel_key} in config")
        for panel in config.get_panels():
            if panel.get_type() not in PANEL_MAPPING:
                raise ValueError(f"Panel type {panel.get_type()} not supported")
        self.log(f"Loaded {len(config.get_panels())} panels")

    def _register_callbacks(self) -> None:
        """Resolves the relay entity each physical button toggles."""
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")  # button info dict
            entity_id = self.get(f"button_{i}_entity")  # the entity to control
            # no entity id set, use relay
            if not entity_id:
                # default button entity - hardware relay
                slug = self.get_slug()
                entity_id = f"switch.{slug}_relay_{i}"
            button["item_id"] = entity_id

    def _cancel_callbacks(self) -> None:
        """Forgets the resolved button entities."""
        for i in ["left", "right"]:
            getattr(self, f"_btn_{i}_info")["item_id"] = None

    def _resolve_esp_entity(self, domain: str, fallback_id: str, name: str) -> str:
        """Resolve an ESPHome entity id, preferring the entity registry.

        Home Assistant's entity-id naming (area/device prefixed ids) and
        device renames produce ids that do not match the ``{slug}_{name}``
        pattern, so every config-sync target is resolved through the registry
        by its ESPHome-authored *name* first and only falls back to the
        classic ``{domain}.{slug}_{name}`` id when the registry is
        unavailable or nothing matches.

        Args:
            domain: Entity domain (``"switch"``, ``"number"``, ...).
            fallback_id: The classic ``{domain}.{slug}_{name}`` entity id.
            name: The name the ESPHome YAML authored (e.g. ``"Display Model"``).

        Returns:
            str: The resolved entity id, or the fallback id.
        """
        resolver = getattr(self.app, "find_entity_id", None)
        if resolver is not None:
            resolved = resolver(domain, name)
            if resolved:
                return resolved
        return fallback_id

    def _sync_config_switch(
        self,
        hub_key: str,
        switch_entity_id: str,
        hub_value: bool | None = None,
        reason: str = "",
    ) -> None:
        """Sync a hub config boolean with the device's corresponding ESPHome switch.

        Ensures the hub config and ESPHome firmware switch are in agreement.
        Sync is bidirectional: re-enabling the config after it was disabled turns
        the firmware switch back on, otherwise ``RESTORE_DEFAULT_ON`` switches
        would stay stuck in their restored state across reconnects.

        Args:
            hub_key: Config key holding the desired value.
            switch_entity_id: ESPHome switch entity id.
            hub_value: Optional override to push instead of ``self.get(hub_key)``
                (used for the clock-driven sleep schedule).
            reason: Optional log reason replacing the "hub config" explanation.
        """
        if not self.app.item_exists(switch_entity_id):
            return
        if hub_value is None:
            hub_value = self.get(hub_key, True)
        item = self.app.get_item(switch_entity_id)
        is_on = item.get_state() == "on"
        if hub_value and not is_on:
            self.log(
                f"Syncing {switch_entity_id} ON "
                f"({reason or f'hub config {hub_key}=True'})"
            )
            item.turn_on()
        elif not hub_value and is_on:
            self.log(
                f"Syncing {switch_entity_id} OFF "
                f"({reason or f'hub config {hub_key}=False'})"
            )
            item.turn_off()

    def _sync_config_number(self, hub_key: str, number_entity_id: str) -> None:
        """Sync a hub config number with the device's ESPHome number entity."""
        if not self.app.item_exists(number_entity_id):
            return
        hub_value = self.get(hub_key, 0)
        item = self.app.get_item(number_entity_id)
        current = item.get_state()
        if current is not None and current != "unavailable" and float(current) != hub_value:
            self.log(f"Syncing {number_entity_id} to {hub_value} (hub config {hub_key})")
            item.set_state(state=hub_value)

    def _sync_button_interaction(self) -> None:
        """Sync the hub's ``reset_interaction_on_button`` with the device's switch.

        ``reset_interaction_on_button`` controls whether button presses reset the
        idle timer.  The device-side ``use_button_interaction`` switch must mirror
        it so the ESPHome firmware (which gates its own ``update_last_interaction``
        on that switch) stays in step.  Sync is bidirectional: re-enabling the
        config after it was disabled turns the firmware switch back on, otherwise
        the switch (``RESTORE_DEFAULT_ON``) would stay stuck off across reconnects.
        """
        self._sync_config_switch(
            "reset_interaction_on_button",
            self._resolve_esp_entity(
                "switch",
                f"switch.{self.get_slug()}_use_button_interaction",
                "Use Button Interaction",
            ),
        )

    def _sync_relay_config(self) -> None:
        """Sync hub config ``use_relay_left``/``use_relay_right`` with ESPHome switches.

        Prevents the double-toggle / no-toggle scenario where the hub expects
        one behaviour but the ESPHome firmware (with its own
        ``use_relay_left``/``use_relay_right`` switches using
        ``RESTORE_DEFAULT_ON``) acts differently.
        """
        slug = self.get_slug()
        self._sync_config_switch(
            "use_relay_left",
            self._resolve_esp_entity("switch", f"switch.{slug}_use_relay_left", "Use Relay Left"),
        )
        self._sync_config_switch(
            "use_relay_right",
            self._resolve_esp_entity("switch", f"switch.{slug}_use_relay_right", "Use Relay Right"),
        )

    # part
    def _sync_behavior_config(self) -> None:
        """Sync hub config auto-* and timeout fields with ESPHome switches/numbers."""
        slug = self.get_slug()
        self._sync_config_switch(
            "use_auto_dimming",
            self._resolve_esp_entity(
                "switch", f"switch.{slug}_use_auto_dimming", "Use Auto-Dimming"
            ),
        )
        self._sync_config_switch(
            "use_auto_page",
            self._resolve_esp_entity("switch", f"switch.{slug}_use_auto_page", "Use Auto-Page"),
        )
        # use_auto_display_off can be overridden by the display-off schedule: inside
        # the configured window the display may turn off, outside it never may.  A
        # schedule that is disabled/incomplete/malformed leaves the static
        # toggle in charge (_display_off_schedule_active returns None).
        display_off = self.get("use_auto_display_off", True)
        schedule_active = self._display_off_schedule_active()
        if schedule_active is not None:
            display_off = schedule_active
        self._sync_config_switch(
            "use_auto_display_off",
            self._resolve_esp_entity(
                "switch", f"switch.{slug}_use_auto_display_off", "Use Auto Display-Off"
            ),
            hub_value=display_off,
            reason=(
                f"sleep schedule {'active' if schedule_active else 'inactive'}"
                if schedule_active is not None
                else ""
            ),
        )
        self._sync_config_number(
            "timeout_dimming",
            self._resolve_esp_entity("number", f"number.{slug}_timeout_dimming", "Timeout Dimming"),
        )
        self._sync_config_number(
            "timeout_page",
            self._resolve_esp_entity("number", f"number.{slug}_timeout_page", "Timeout Page"),
        )
        self._sync_config_number(
            "timeout_display_off",
            self._resolve_esp_entity(
                "number", f"number.{slug}_timeout_display_off", "Timeout Display-Off"
            ),
        )
        self._sync_display_model()

    def _sync_display_model(self) -> None:
        """Sync hub config ``display_model`` with the firmware's gesture size.

        The gesture script derives its touch dimensions from the model
        (``display_model`` number: 0 = landscape, 1 = portrait).  The hub
        config uses names; translate them so the firmware stays in step.

        The number entity is resolved through the entity registry by its
        ESPHome name first — Home Assistant's entity-id naming (area/device
        prefixed ids) and device renames can produce ids that do not match
        ``number.{slug}_display_model`` — and falls back to that classic id.
        """
        number_entity_id = self._resolve_esp_entity(
            "number", f"number.{self.get_slug()}_display_model", "Display Model"
        )
        if not self.app.item_exists(number_entity_id):
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

    def _install_tft_on_model_change(self) -> None:
        """Install the matching TFT when the display model was switched in the settings.

        The display cannot report which layout it runs and the version check
        only compares versions, so a device that already has the current TFT
        would keep the wrong layout after the model changed.
        """
        model = self.display_model
        previous, self._synced_display_model = self._synced_display_model, model
        if previous is None or previous == model:
            return
        self.log(f"Display model changed from {previous!r} to {model!r}; installing its TFT")
        self.app.controller["update"].install_tft()

    @property
    def display_model(self) -> str:
        """The configured display model (``eu`` or ``us``), lower-cased."""
        return str(self.get("display_model", "eu")).lower()

    @property
    def is_portrait(self) -> bool:
        """Whether this device runs the rotated portrait TFT layout."""
        return is_portrait_model(self.display_model)

    # part

    def sync_config_to_device(self) -> None:
        """Push the hub's device settings to the device's ESPHome switches and numbers.

        Runs at start, on every connect (a rebooted device restores its own
        stored values, and at HA startup the entities are often unavailable) and
        after the settings are saved. Only values that differ are written.
        """
        self._sync_button_interaction()
        self._sync_relay_config()
        self._sync_behavior_config()
        self._install_tft_on_model_change()
        # Re-arm the sleep-schedule boundary timer whenever settings are pushed
        # (start, connect, reconnect, setting save via reload_config) so a
        # changed window takes effect without waiting for the next boundary.
        self._arm_display_off_schedule_timer()

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

    def _is_quiet_hours(self) -> bool:
        """Check if the current time falls within quiet hours.

        Quiet hours suppress notification sounds and screen wake.
        Supports overnight ranges (e.g., 22:00-07:00).

        Returns:
            bool: True if quiet hours are active
        """
        if not self.get("use_do_not_disturb"):
            return False
        start = self.get("quiet_hours_start", "")
        end = self.get("quiet_hours_end", "")
        if not start or not end:
            return False
        try:
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
        except (ValueError, TypeError):
            # Not raised: callers decide whether to play a sound, and an exception
            # there would also abort what follows (e.g. the startup navigation).
            self.log(
                f"Ignoring quiet hours: expected HH:MM, got start={start!r} end={end!r}",
                level="WARNING",
            )
            return False
        return _time_in_window(datetime.now().time(), start_time, end_time)

    def _display_off_schedule_active(self, now: datetime | None = None) -> bool | None:
        """Whether the display-off schedule currently allows the display to turn off.

        The schedule drives ``use_auto_display_off`` by the clock: inside the
        window the display may turn off after ``timeout_display_off``, outside it
        never turns off automatically.  Supports overnight ranges.

        Args:
            now: Injectable clock for tests (defaults to ``datetime.now()``).

        Returns:
            bool: True while inside the window, False while outside.
            None: Schedule disabled, window incomplete, or times malformed —
                callers fall back to the configured ``use_auto_display_off``
                value (and the malformed case is logged).
        """
        if not self.get("use_sleep_schedule", False):
            return None
        start = self.get("sleep_schedule_start", "")
        end = self.get("sleep_schedule_end", "")
        if not start or not end:
            return None
        try:
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
        except (ValueError, TypeError):
            self.log(
                f"Ignoring sleep schedule: expected HH:MM, got start={start!r} end={end!r}",
                level="WARNING",
            )
            return None
        return _time_in_window((now or datetime.now()).time(), start_time, end_time)

    def _next_schedule_boundary(self, now: datetime | None = None) -> datetime | None:
        """When the sleep-schedule window next changes state.

        Args:
            now: Injectable clock for tests (defaults to ``datetime.now()``).

        Returns:
            datetime: The next future window boundary (start or end), or None
                when no timer should be armed (schedule inactive/invalid).
        """
        if not self.get("use_sleep_schedule", False):
            return None
        start = self.get("sleep_schedule_start", "")
        end = self.get("sleep_schedule_end", "")
        if not start or not end:
            return None
        try:
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
        except (ValueError, TypeError):
            return None
        now = (now or datetime.now()).replace(second=0, microsecond=0)
        candidates = [
            datetime.combine(now.date(), start_time),
            datetime.combine(now.date(), end_time),
            datetime.combine(now.date() + timedelta(days=1), start_time),
            datetime.combine(now.date() + timedelta(days=1), end_time),
        ]
        future = [candidate for candidate in candidates if candidate > now]
        return min(future) if future else None

    def _arm_display_off_schedule_timer(self) -> None:
        """(Re)schedule the flip of ``use_auto_display_off`` at the next boundary."""
        self._cancel_timer("_schedule_timer")
        boundary = self._next_schedule_boundary()
        if boundary is None:
            return
        delay = (boundary - datetime.now()).total_seconds()
        # run_in fires the callback ``delay`` seconds later; arm it to run just
        # after the boundary so the clock-driven value is already the new one.
        self._schedule_timer = self.app.run_in(self._display_off_schedule_callback, max(delay, 1))

    def _display_off_schedule_callback(self, _kwargs: Any) -> None:
        """A window boundary passed: re-push ``use_auto_display_off``, re-arm.

        ``sync_config_to_device`` is not called here on purpose - the boundary
        flip only needs the behavior sync, and a full sync would also re-run
        ``_install_tft_on_model_change`` bookkeeping.
        """
        self._schedule_timer = None
        if not self.get("use_sleep_schedule", False):
            return
        self._sync_behavior_config()
        self._arm_display_off_schedule_timer()

    # public

    def notify(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        persistent: bool = False,
        notif_type: str = "info",
        force_show: bool = False,
        require_ack: bool = False,
    ) -> None:
        """Send a notification via the notification controller."""
        self.app.controller["notification"].send_notification(
            title, message, icon, persistent, notif_type, force_show, require_ack
        )

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

        Quiet hours suppress all sounds — the call is a no-op when
        quiet hours are active so callers do not need individual checks.

        Args:
            name (str): Name of the sound
        """
        if self._is_quiet_hours():
            self.debug_log(f"Quiet hours active — suppressing sound '{name}'")
            return
        self.app.controller["esphome"].esphome.publish("play_sound", name)

    # callback

    # event

    def process_gesture(self, event: HAUIEvent) -> None:
        """Progress gesture event.

        Args:
            event (HAUIEvent): Event
        """
        self.log(f"Got gesture: {event.as_str()}")
        navigation = self.app.controller["navigation"]
        if not navigation.page or not navigation.page.panel:
            return
        # a slider drag also produces a swipe gesture — ignore it so
        # adjusting a slider doesn't navigate away
        if navigation.page.is_gesture_suppressed():
            self.log("Ignoring gesture during slider interaction")
            return
        # check event
        if event.as_str() == "swipe_left":
            navigation.open_next_panel()
        elif event.as_str() == "swipe_right":
            navigation.open_prev_panel()
        elif event.as_str() == "swipe_up":
            navigation.open_panel(SysPanelKey.SYS_ABOUT)
        elif event.as_str() == "swipe_down":
            navigation.open_panel(SysPanelKey.SYS_SETTINGS)

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
        # process gesture event
        if event.name == ESPEvent.GESTURE:
            self.process_gesture(event)
        # a touch is the sole driver of the idle-page exit decision
        elif event.name == ESPEvent.TOUCH_START:
            if self._idle_touch_grace_active():
                self.log("Ignoring residual touch_start after idle-page open")
                return
            self.check_wakeup()
        # the display went dark again (e.g. while the idle page stays open),
        # so the next touch must only wake it: re-arm the two-touch guard
        elif event.name == ESPEvent.DISPLAY_STATE:
            if event.value in ("dim", "off"):
                self._first_touch_consumed = True
        elif event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT):
            side = "left" if event.name == ESPEvent.BUTTON_LEFT else "right"
            if event.value == "1":  # pressed
                # On press, immediately reset the interaction timer so the
                # display wakes without waiting for release.  The entity toggle
                # stays on release so a held button does not spam toggles.
                if self.get("reset_interaction_on_button", True):
                    self.app.controller["esphome"].esphome.publish(
                        ESPAction.RESET_LAST_INTERACTION, "0"
                    )
                    self.check_wakeup()
            elif event.value == "0":  # released
                self._on_button_release(side)
        # process notification events
        elif event.name == NotifEvent.NOTIF_ADD:
            if not isinstance(event.value, Notification):
                raise TypeError(f"Notification event value must be a Notification: {event.value!r}")
            persistent, notif_type = event.value.persistent, event.value.notif_type
            if self.get("sound_on_notification"):
                if self._is_quiet_hours():
                    self.debug_log("Quiet hours active — suppressing notification sound")
                elif persistent:
                    self._start_persistent_sound()
                else:
                    self.play_sound(_notification_sound(notif_type))
        elif (
            event.name in (NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR)
            and not self.app.controller["notification"].has_persistent_notifications()
        ):
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
        navigation = self.app.controller["navigation"]
        if not navigation.idle_panel_active:
            return False
        return time.monotonic() < self._idle_touch_grace_until

    def check_wakeup(self) -> None:
        """Exit the idle page on any touch or hardware-button press.

        When the display is already **on** the user can see the screen, so a
        single touch immediately leaves the idle page (one-touch).  When the
        display is **off** or **dim** the first touch only wakes the display;
        the second touch performs the action (two-touch).

        A hardware button calls this on both press and release, so a single
        physical press wakes and exits (documented in docs/device.md).

        The wake operation itself is panel-independent: with no idle page
        open there is nothing to exit and the firmware's own display-idle
        machine handles brightness when its interaction timer is reset by the
        touch.
        """
        navigation = self.app.controller["navigation"]
        if not navigation.panel:
            return
        if not navigation.idle_panel_active:
            return

        # Determine the display state to decide one-touch vs two-touch.
        # Values from the device: "on", "dim", "off".
        display_state = self.device_info.get("display_state", "off")

        if display_state == "on":
            # Display is already on — the user can see the screen.
            # Exit the idle page immediately on the first touch (one-touch).
            self._first_touch_consumed = False
            navigation.exit_idle_to_prev_or_home(self.config)
            return

        # Display is off or dim — the user cannot see the screen.
        # First touch wakes the display; second touch exits the idle page.
        if self._first_touch_consumed:
            self._first_touch_consumed = False
            self.log("Not exiting idle page, just woke up")
            return

        self._first_touch_consumed = False
        navigation.exit_idle_to_prev_or_home(self.config)

    def _on_button_release(self, side: str) -> None:
        """Handle a hardware button release (``side`` = "left" / "right").

        With ``reset_interaction_on_button`` enabled the press also wakes the
        display (resets the firmware idle timer — needed even when the ESPHome
        ``use_button_interaction`` switch is OFF) and completes the idle-page
        wake: on a dark
        display the press only wakes, and this release completes the exit. With it
        disabled the press only toggles the relay/entity and never touches the
        display. The toggle runs before ``check_wakeup`` so it isn't delayed by
        the blocking goto_page navigation inside it.
        """
        reset = self.get("reset_interaction_on_button", True)
        if reset:
            self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")
        getattr(self, f"toggle_{side}_button_state")()
        if reset:
            self.check_wakeup()

    def _toggle_button_state(self, side: str) -> None:
        entity_id = getattr(self, f"_btn_{side}_info")["item_id"]
        if not entity_id or not self.app.item_exists(entity_id):
            return
        if not self.get(f"use_relay_{side}", True):
            self.app.get_item(entity_id).call_service("toggle")

    def _persistent_sound(self) -> str:
        """The loop sound: the alert while any persistent notification is critical."""
        notifications = self.app.controller["notification"].get_notifications()
        if any(n.persistent and n.notif_type == NotifType.CRITICAL for n in notifications):
            return _notification_sound(NotifType.CRITICAL)
        return _notification_sound(NotifType.INFO)

    def _persistent_sound_callback(self, kwargs: Any) -> None:
        if self.app.controller["notification"].has_persistent_notifications():
            self.play_sound(self._persistent_sound())
        else:
            self._stop_persistent_sound()

    def _start_persistent_sound(self) -> None:
        if self._persistent_sound_handle is not None:
            return
        interval = self.get("persistent_sound_interval")
        self.play_sound(self._persistent_sound())
        self._persistent_sound_handle = self.app.run_every(
            self._persistent_sound_callback, f"now+{interval}", interval
        )

    def _stop_persistent_sound(self) -> None:
        self._cancel_timer("_persistent_sound_handle")

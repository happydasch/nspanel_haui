from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .abstract.haui_base import HAUIBase
from .abstract.haui_event import HAUIEvent
from .mapping.const import ESPAction, ESPEvent, NotifEvent
from .mapping.panel import PANEL_MAPPING, SYS_PANEL_MAPPING

if TYPE_CHECKING:
    from ..nspanel_haui import NSPanelHAUI
from .mapping.const import SysPanelKey


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
        self.sleeping = False
        self.woke_up = False
        self._initial_connect_done = False
        self._btn_left_info: dict[str, Any] = {
            "state": False,
            "item_id": None,
            "handle": None,
        }
        self._btn_right_info: dict[str, Any] = {
            "state": False,
            "item_id": None,
            "handle": None,
        }
        self._persistent_sound_handle: str | None = None

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
        """Registers all device callbacks."""
        # set button state callbacks
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")  # button info dict
            entity_id = self.get(f"button_{i}_entity")  # the entity to control
            # no entity id set, use relay
            if not entity_id:
                # default button entity - hardware relay
                slug = self.get_name().lower().replace("-", "_").replace(" ", "_")
                entity_id = f"switch.{slug}_relay_{i}"
            # entity exists, add callbacks and set up hardware button entity
            if self.app.item_exists(entity_id):
                handle = self.app.listen_state(self.callback_button_state_entities, entity_id)
                button["item_id"] = entity_id
                button["handle"] = handle
            else:
                button["item_id"] = entity_id
                button["handle"] = None

    def _cancel_callbacks(self) -> None:
        """Cancels all device callbacks."""
        # cancel button state callbacks
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")
            if button["handle"]:
                self.app.cancel_listen_state(button["handle"])
            button["handle"] = None
            button["item_id"] = None

    def _sync_config_switch(self, hub_key: str, switch_entity_id: str) -> None:
        """Sync a hub config boolean with the device's corresponding ESPHome switch.

        Ensures the hub config and ESPHome firmware switch are in agreement.
        Sync is bidirectional: re-enabling the config after it was disabled turns
        the firmware switch back on, otherwise ``RESTORE_DEFAULT_ON`` switches
        would stay stuck in their restored state across reconnects.
        """
        if not self.app.item_exists(switch_entity_id):
            return
        hub_value = self.get(hub_key, True)
        item = self.app.get_item(switch_entity_id)
        is_on = bool(item.get_state())
        if hub_value and not is_on:
            self.log(f"Syncing {switch_entity_id} ON (hub config {hub_key}=True)")
            item.turn_on()
        elif not hub_value and is_on:
            self.log(f"Syncing {switch_entity_id} OFF (hub config {hub_key}=False)")
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
        reset = self.get("reset_interaction_on_button", True)
        name = self.get_name()
        slug = name.lower().replace("-", "_").replace(" ", "_")
        entity_id = f"switch.{slug}_use_button_interaction"
        if not self.app.item_exists(entity_id):
            return
        item = self.app.get_item(entity_id)
        is_on = bool(item.get_state())
        if reset and not is_on:
            item.turn_on()
        elif not reset and is_on:
            item.turn_off()

    def _sync_relay_config(self) -> None:
        """Sync hub config ``use_relay_left``/``use_relay_right`` with ESPHome switches.

        Prevents the double-toggle / no-toggle scenario where the hub expects
        one behaviour but the ESPHome firmware (with its own
        ``use_relay_left``/``use_relay_right`` switches using
        ``RESTORE_DEFAULT_ON``) acts differently.
        """
        slug = self.get_name().lower().replace("-", "_").replace(" ", "_")
        self._sync_config_switch(
            "use_relay_left",
            f"switch.{slug}_use_relay_left",
        )
        self._sync_config_switch(
            "use_relay_right",
            f"switch.{slug}_use_relay_right",
        )

    # part
    def _sync_behavior_config(self) -> None:
        """Sync hub config auto-* and timeout fields with ESPHome switches/numbers."""
        slug = self.get_name().lower().replace("-", "_").replace(" ", "_")
        self._sync_config_switch("use_auto_dimming", f"switch.{slug}_use_auto_dimming")
        self._sync_config_switch("use_auto_page", f"switch.{slug}_use_auto_page")
        self._sync_config_switch("use_auto_sleeping", f"switch.{slug}_use_auto_sleeping")
        self._sync_config_number("timeout_dimming", f"number.{slug}_timeout_dim")
        self._sync_config_number("timeout_page", f"number.{slug}_timeout_page")
        self._sync_config_number("timeout_sleep", f"number.{slug}_timeout_sleep")

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self.log("Device is starting")
        self._check_config()
        self._register_callbacks()
        self._sync_button_interaction()
        self._sync_relay_config()
        self._sync_behavior_config()

    def stop_part(self) -> None:
        """Stops the part."""
        self.log("Device is stopping")
        self._cancel_callbacks()
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
        On disconnect: resets sleep-panel state so stale _sleep_panel_active
        does not trigger open_home_panel from display_state events during
        reconnection.

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
            if self.get("sound_on_startup"):
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
            # Reset sleep panel state on disconnect so stale
            # _sleep_panel_active does not trigger open_home_panel
            # from display_state events during reconnection.
            navigation.mark_awake()

    def _is_quiet_hours(self) -> bool:
        """Check if the current time falls within quiet hours.

        Quiet hours suppress notification sounds and screen wake.
        Supports overnight ranges (e.g., 22:00-07:00).

        Returns:
            bool: True if quiet hours are active
        """
        start = self.get("quiet_hours_start", "")
        end = self.get("quiet_hours_end", "")
        if not start or not end:
            return False
        try:
            from datetime import datetime

            now = datetime.now().time()
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
            if start_time <= end_time:
                return start_time <= now <= end_time
            # overnight range
            return now >= start_time or now <= end_time
        except (ValueError, TypeError):
            return False

    def set_sleeping(self, sleeping: bool) -> None:
        self.sleeping = sleeping

    def notify(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
        notif_type: str = "info",
        force_show: bool = False,
    ) -> None:
        """Send a notification via the notification controller."""
        self.app.controller["notification"].send_notification(
            title, message, icon, timeout, persistent, notif_type, force_show
        )

    def get_locale(self) -> str:
        """Returns the device locale.

        Returns:
            str: Locale
        """
        return self.get("locale")

    def get_name(self) -> str:
        """Returns the device name.

        Returns:
            str: Device name
        """
        # self.get("name") returns the hub-level name from the device
        # sub-dict config. The actual per-device name is resolved at app
        # level in NSPanelHAUI.initialize() and stored in _runtime_device_name.
        return self.app._runtime_device_name or self.get("name")

    def get_active_listeners(self) -> list[dict[str, Any]]:
        """Returns active device-level entity listeners for status reporting.

        Returns:
            list[dict]: List of listener metadata dicts with keys handle, item_id,
                attribute, and callback_name.
        """
        listeners: list[dict[str, Any]] = []
        for side in ["left", "right"]:
            info: dict[str, Any] = getattr(self, f"_btn_{side}_info")
            if info["handle"]:
                listeners.append(
                    {
                        "handle": info["handle"],
                        "item_id": info["item_id"],
                        "attribute": None,
                        "callback_name": "callback_button_state_entities",
                    }
                )
        return listeners

    def get_left_button_state(self) -> bool:
        """Returns the left button state."""
        return self._get_button_state("left")

    def set_left_button_state(self, state: bool) -> None:
        """Sets the left button state."""
        self._set_button_state("left", state)

    def toggle_left_button_state(self) -> None:
        """Toggles the left button relay entity."""
        self._toggle_button_state("left")

    def get_right_button_state(self) -> bool:
        """Returns the right button state."""
        return self._get_button_state("right")

    def set_right_button_state(self, state: bool) -> None:
        """Sets the right button state."""
        self._set_button_state("right", state)

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

    def callback_button_state_entities(
        self, entity: str, attribute: str, old: str, new: str, _unused: Any = None
    ) -> None:
        """Callback method for button state entity state changes.

        Args:
            entity (str): Entity id
            attribute (str): Entity attribute
            old (str): Old state
            new (str): New state
            kwargs (dict): Args
        """
        self.log(f"Got button state entity callback: {entity}.{attribute}:{new}")
        navigation = self.app.controller["navigation"]
        if not navigation.page:
            return
        state = new == "on"
        # Push relay state to the display when it changes — unless the user
        # disabled button interaction (reset_interaction_on_button False), in
        # which case the serial write is skipped so a button toggle cannot wake
        # or alter the display.  Internal state is tracked regardless.
        push = self._may_push_button_state()
        if entity == self._btn_left_info["item_id"]:
            self._btn_left_info["state"] = state
            if push:
                navigation.page.set_button_left_state(state)
        elif entity == self._btn_right_info["item_id"]:
            self._btn_right_info["state"] = state
            if push:
                navigation.page.set_button_right_state(state)

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
        # a touch is the sole driver of the sleep-screen exit decision
        elif event.name == ESPEvent.TOUCH_START:
            self.check_wakeup()
        elif event.name == ESPEvent.SLEEP:
            self.set_sleeping(True)
        elif event.name == ESPEvent.WAKEUP:
            self.set_sleeping(False)
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
                    self.check_wakeup(from_button=True)
            elif event.value == "0":  # released
                self._on_button_release(side)
        elif event.name in (ESPEvent.RELAY_LEFT, ESPEvent.RELAY_RIGHT):
            side = "left" if event.name == ESPEvent.RELAY_LEFT else "right"
            self._on_relay_event(side, event.value == "1")
        # process notification events
        elif event.name == NotifEvent.NOTIF_ADD:
            notification = event.value  # (title, message, icon, timeout, persistent,
            # type, force_show)
            if isinstance(notification, (list, tuple)):
                persistent = notification[4] if len(notification) > 4 else False
            else:
                persistent = False
            if self.get("sound_on_notification"):
                if self._is_quiet_hours():
                    self.debug_log("Quiet hours active — suppressing notification sound")
                elif persistent:
                    self._start_persistent_sound()
                else:
                    self.play_sound("notification")
        elif (
            event.name in (NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR)
            and not self.app.controller["notification"].has_persistent_notifications()
        ):
            self._stop_persistent_sound()

    def check_wakeup(self, from_button: bool = False) -> None:
        """Exit the sleep / wakeup screen on any touch or hardware-button press.

        A single touch-down immediately wakes the display and exits the
        sleep / wake panel, restoring the home or previous panel.

        ``woke_up`` — set when the sleep panel opens — is cleared here so
        the flag does not accumulate, but no longer gates the exit decision.
        """
        navigation = self.app.controller["navigation"]
        if not navigation.panel:
            return

        on_wakeup_panel = (
            self.get("wakeup_panel")
            and navigation.panel.get("key") == self.get("wakeup_panel")
            and navigation.panel.get("key") != self.get("home_panel")
        )
        if not (on_wakeup_panel or navigation._sleep_panel_active):
            return

        # First touch after sleep just wakes the display — do NOT exit yet.
        # The ``woke_up`` flag was set by ``open_sleep_panel()`` to swallow
        # this touch.  Clear it so the *next* touch triggers the exit.
        if self.woke_up:
            self.woke_up = False
            self.log("Not exiting sleep/wakeup screen, just woke up")
            return

        self.woke_up = False
        navigation.exit_sleep_to_prev_or_home(self.config)

    def _on_button_release(self, side: str) -> None:
        """Handle a hardware button release (``side`` = "left" / "right").

        With ``reset_interaction_on_button`` enabled the press also wakes the
        display (resets the firmware idle timer — needed even when the ESPHome
        ``use_button_interaction`` switch is OFF) and exits sleep/wakeup. With it
        disabled the press only toggles the relay/entity and never touches the
        display. The toggle runs before ``check_wakeup`` so it isn't delayed by
        the blocking goto_page navigation inside it.
        """
        reset = self.get("reset_interaction_on_button", True)
        if reset:
            self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")
        getattr(self, f"toggle_{side}_button_state")()
        if reset:
            self.check_wakeup(from_button=True)

    def _on_relay_event(self, side: str, state: bool) -> None:
        """Handle a relay state change reported by the device.

        Tracks the internal button state and reflects it on the display, unless
        ``reset_interaction_on_button`` is disabled — then the relay only toggles
        the device and the display is left untouched (no serial write that could
        wake it).
        """
        getattr(self, f"_btn_{side}_info")["state"] = state
        navigation = self.app.controller["navigation"]
        if self._may_push_button_state() and navigation.page:
            with navigation.page.rec_cmd:
                getattr(navigation.page, f"set_button_{side}_state")(state)

    def _may_push_button_state(self) -> bool:
        """Whether a relay state change may write to the display.

        With ``reset_interaction_on_button`` False the user opted out of any
        button-driven display interaction: a relay change must only toggle the
        device, never wake or alter the display.  In that case the internal
        button state is still tracked, but the Nextion serial write (which can
        activate the display) is skipped.  Default True keeps the previous
        behaviour of reflecting relay changes on the display immediately.
        """
        return self.get("reset_interaction_on_button", True)

    def _get_button_state(self, side: str) -> bool:
        return getattr(self, f"_btn_{side}_info")["state"]

    def _set_button_state(self, side: str, state: bool) -> None:
        entity_id = getattr(self, f"_btn_{side}_info")["item_id"]
        if not entity_id or not self.app.item_exists(entity_id):
            return
        self.app.get_item(entity_id).call_service("turn_on" if state else "turn_off")

    def _toggle_button_state(self, side: str) -> None:
        entity_id = getattr(self, f"_btn_{side}_info")["item_id"]
        if not entity_id or not self.app.item_exists(entity_id):
            return
        if not self.get(f"use_relay_{side}", True):
            self.app.get_item(entity_id).call_service("toggle")

    def _persistent_sound_callback(self, kwargs: Any) -> None:
        if self.app.controller["notification"].has_persistent_notifications():
            self.play_sound("notification")
        else:
            self._stop_persistent_sound()

    def _start_persistent_sound(self) -> None:
        if self._persistent_sound_handle is not None:
            return
        interval = self.get("persistent_sound_interval", 5)
        self.play_sound("notification")
        self._persistent_sound_handle = self.app.run_every(
            self._persistent_sound_callback, f"now+{interval}", interval
        )

    def _stop_persistent_sound(self) -> None:
        if self._persistent_sound_handle is not None:
            self.app.cancel_timer(self._persistent_sound_handle)
            self._persistent_sound_handle = None

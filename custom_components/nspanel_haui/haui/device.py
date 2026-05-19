from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .abstract.haui_base import HAUIBase
from .abstract.haui_event import HAUIEvent
from .mapping.const import ESPEvent, NotifEvent
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
        self.connected = False
        self.sleeping = False
        self.woke_up = False
        self._initial_connect_done = False
        self.first_touch = False
        self.is_on_check = False
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

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self.log("Device is starting")
        self._check_config()
        self._register_callbacks()

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

    def set_connected(self, connected: bool) -> None:
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
        self.connected = connected
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
            navigation._sleep_panel_active = False

    def set_sleeping(self, sleeping: bool) -> None:
        """Sets the device as sleeping.

        Args:
            sleeping (bool): Sleeping state
        """
        self.sleeping = sleeping

    def notify(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
    ) -> None:
        """Send a notification via the notification controller."""
        self.app.controller["notification"].send_notification(
            title, message, icon, timeout, persistent
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

        Args:
            name (str): Name of the sound
        """
        self.app.controller["esphome"].esphome.publish("play_sound", name)

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
        if entity == self._btn_left_info["item_id"]:
            self._btn_left_info["state"] = state
            navigation.page.set_button_left_state(state)
        elif entity == self._btn_right_info["item_id"]:
            self._btn_right_info["state"] = state
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
        # update device vars values
        self.device_info[event.name] = event.value
        # process gesture event
        if event.name == ESPEvent.GESTURE:
            self.process_gesture(event)
        # process sleeping state
        elif event.name == ESPEvent.TOUCH_START:
            self.check_wakeup()
        elif event.name == ESPEvent.SLEEP:
            self.set_sleeping(True)
        elif event.name == ESPEvent.WAKEUP:
            self.set_sleeping(False)
            # set a flag as just woke up
            self.woke_up = True
        elif event.name == ESPEvent.PAGE:
            if self.device_info.get("page", 0) != event.value:
                self.first_touch = True
        elif event.name == ESPEvent.DISPLAY_STATE:
            if event.value == "on":
                self.is_on_check = True
        elif event.name == ESPEvent.BUTTON_LEFT:
            if event.value == "0":
                if self.get("home_on_button_toggle"):
                    self.check_wakeup()
                self.toggle_left_button_state()
        elif event.name == ESPEvent.BUTTON_RIGHT:
            if event.value == "0":
                if self.get("home_on_button_toggle"):
                    self.check_wakeup()
                self.toggle_right_button_state()
        # process notification events
        elif event.name == ESPEvent.RELAY_LEFT:
            state = event.value == "1"
            self._btn_left_info["state"] = state
            if self.app.controller["navigation"].page:
                self.app.controller["navigation"].page.set_button_left_state(state)
        elif event.name == ESPEvent.RELAY_RIGHT:
            state = event.value == "1"
            self._btn_right_info["state"] = state
            if self.app.controller["navigation"].page:
                self.app.controller["navigation"].page.set_button_right_state(state)

        elif event.name == NotifEvent.NOTIF_ADD:
            notification = event.value  # (title, message, icon, timeout, persistent)
            if isinstance(notification, (list, tuple)):
                persistent = notification[4] if len(notification) > 4 else False
            else:
                persistent = False
            if self.get("sound_on_notification"):
                if persistent:
                    self._start_persistent_sound()
                else:
                    self.play_sound("notification")
        elif (
            event.name in (NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR)
            and not self.app.controller["notification"].has_persistent_notifications()
        ):
            self._stop_persistent_sound()

    def check_wakeup(self) -> None:
        """Checks if the display just woke up to switch from wakeup page.

        How to wake up from sleep:
        - touch the display once, the sleep or wakeup panel will be opened
        - touch again, the home panel will be opened

        How exit sleep works by default:
        - when display off:
            - first touch wakes up the display
            - second touch closes the panel
        - when display dimmed/on:
            - first touch closes the panel

        How to modify this behaviour:
        - use hardware buttons to exit panel:
            - home_on_button_toggle: true
        - when display is off:
            - wake up on first touch:
              - home_on_wakeup: true
        - when display is dimmed/on:
            - display will only exit panel if display is not dimmed:
              - home_only_when_on: true
            - exit display on second touch:
              - home_on_first_touch: false
        """
        navigation = self.app.controller["navigation"]
        if not navigation.panel:
            return
        has_wakeup_panel = (
            self.get("wakeup_panel")
            and navigation.panel.get("key") == self.get("wakeup_panel")
            and navigation.panel.get("key") != self.get("home_panel")
        )
        has_sleep_panel = not self.get("wakeup_panel") and navigation._sleep_panel_active
        if has_wakeup_panel or has_sleep_panel:
            exit_sleep = True
            display_state = self.device_info.get("display_state")

            if self.woke_up:
                self.first_touch = True

            if not self.get("home_on_wakeup") and self.woke_up:
                self.log("not exiting sleep/wakeup screen, just woke up")
                self.woke_up = False
                exit_sleep = False

            if not self.get("home_on_first_touch") and self.first_touch:
                self.log("not exiting sleep/wakeup screen, first touch")
                self.first_touch = False
                exit_sleep = False

            if self.get("home_only_when_on") and (display_state != "on" or self.is_on_check):
                self.log(f"not exiting sleep/wakeup screen, display state {display_state}")
                self.is_on_check = False
                exit_sleep = False

            if self.woke_up:
                self.woke_up = False

            if exit_sleep:
                return_to_home_after_seconds = self.get("return_to_home_after_seconds")
                if self.get("always_return_to_home") or not navigation.restore_snapshot(
                    return_to_home_after_seconds
                ):
                    navigation.open_home_panel()

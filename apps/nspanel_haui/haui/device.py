from typing import Optional

from .mapping.page import PANEL_MAPPING, SYS_PANEL_MAPPING
from .mapping.const import ESP_EVENT, NOTIF_EVENT
from .abstract.part import HAUIPart
from .abstract.event import HAUIEvent


class HAUIDevice(HAUIPart):

    """
    Represents a NSPanel device.

    - Gestures and interaction with device
    - Device wide callbacks from entities / homeassistant
    - Physical buttons state
    """

    def __init__(self, app, config: Optional[dict] = None) -> None:
        """Initializes the device.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config of device. Defaults to None.
        """
        super().__init__(app, config)
        self.device_info = {}
        self.connected = False
        self.sleeping = False
        self.woke_up = False
        self.first_touch = False
        self.is_on_check = False
        self._btn_left_info = {"state": False, "entity_id": None, "handle": None}
        self._btn_right_info = {"state": False, "entity_id": None, "handle": None}

    # prepare and update

    def _check_config(self) -> None:
        """Checks if the configuration is valid.

        Raises:
            ValueError: Missing values in config
        """
        config = self.app.config
        # check if all sys_panels are valid
        chk_sys_panels = [x.get("key") for x in config.get("sys_panels", [])]
        for panel_key in SYS_PANEL_MAPPING.keys():
            if panel_key not in chk_sys_panels:
                raise ValueError(f"Missing sys_panel {panel_key} in config")
        for panel in config.get_panels():
            if panel.get_type() not in PANEL_MAPPING:
                raise ValueError(f"Panel type {panel.get_type()} not supported")
        self.log(
            f"Loaded {len(config.get_panels())} panels and {len(config.get_entities())} entities"
        )

    def _register_callbacks(self) -> None:
        """Registers all device callbacks."""
        # set button state callbacks
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")  # button info dict
            entity_id = self.get(f"button_{i}_entity")  # the entity to control
            # no entity id set, use relay
            if not entity_id:
                # default button entity - hardware relay
                entity_id = f"switch.{self.get_name()}_relay_{i}"
            # entity exists, add callbacks and set up hardware button entity
            if self.app.entity_exists(entity_id):
                handle = self.app.listen_state(
                    self.callback_button_state_entities, entity_id
                )
                button["entity_id"] = entity_id
                button["handle"] = handle

    def _cancel_callbacks(self) -> None:
        """Cancels all device callbacks."""
        # cancel button state callbacks
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")
            if button["handle"]:
                self.app.cancel_listen_state(button["handle"])
                button["handle"] = None

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
        """Sets the device as connected.

        Args:
            connected (bool): Connection state
        """
        self.log(f"Device connected: {connected}")
        self.connected = connected
        navigation = self.app.controller["navigation"]
        if connected:
            if self.get("sound_on_startup", True):
                self.play_sound("startup")
            # entry point after connected
            navigation.open_panel("sys_system")

    def set_sleeping(self, sleeping: bool) -> None:
        """Sets the device as sleeping.

        Args:
            sleeping (bool): Sleeping state
        """
        self.sleeping = sleeping

    def get_locale(self) -> str:
        """Returns the device locale.

        Returns:
            str: Locale
        """
        return self.get("locale", "en_US")

    def get_name(self) -> str:
        """Returns the device name.

        Returns:
            str: Device name
        """
        return self.get("name", "nspanel_haui")

    def get_left_button_state(self) -> str:
        """Returns the left button state.

        Returns:
            str: state
        """
        return self._btn_left_info["state"]

    def set_left_button_state(self, state: bool) -> None:
        """Sets the left button state.

        Args:
            state (bool): State
        """
        entity_id = self._btn_left_info["entity_id"]
        if not self.app.entity_exists(entity_id):
            return
        # toggle entity
        entity = self.app.get_entity(entity_id)
        if state:
            entity.call_service("turn_on")
        else:
            entity.call_service("turn_off")

    def toggle_left_button_state(self) -> None:
        """Sets the state of the left button.

        This will change the state of the set entity. By default its the relay.
        """
        entity_id = self._btn_left_info["entity_id"]
        if not self.app.entity_exists(entity_id):
            return
        # toggle entity
        if not self.device_info.get("use_relay_left", True):
            entity = self.app.get_entity(entity_id)
            entity.call_service("toggle")

    def get_right_button_state(self) -> str:
        """Returns the right button state.

        Returns:
            str: state
        """
        return self._btn_right_info["state"]

    def set_right_button_state(self, state: bool) -> None:
        """Sets the right button state.

        Args:
            state (bool): State
        """
        entity_id = self._btn_right_info["entity_id"]
        if not self.app.entity_exists(entity_id):
            return
        # toggle entity
        entity = self.app.get_entity(entity_id)
        if state:
            entity.call_service("turn_on")
        else:
            entity.call_service("turn_off")

    def toggle_right_button_state(self) -> None:
        """Toggles the state of the right button.

        This will change the state of the set entity. By default its the relay.
        """
        entity_id = self._btn_right_info["entity_id"]
        if not self.app.entity_exists(entity_id):
            return
        # toggle entity
        self.log(f"device button right {self.device_info.get('use_relay_right', True)}")
        if not self.device_info.get("use_relay_right", True):
            entity = self.app.get_entity(entity_id)
            entity.call_service("toggle")

    def play_sound(self, name: str) -> None:
        """Plays a sound.

        Args:
            name (str): Name of the sound
        """
        device_name = self.get_name()
        self.app.call_service(f"esphome/{device_name}_play_sound", name=name)

    # callback

    def callback_button_state_entities(self, entity, attribute, old, new, kwargs):
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
        state = True if new == "on" else False
        if entity == self._btn_left_info["entity_id"]:
            self._btn_left_info["state"] = state
            navigation.page.set_button_left_state(state)
        elif entity == self._btn_right_info["entity_id"]:
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
        # check if currently a locked panel is active
        unlock_panel = navigation.page.panel.get("unlock_panel", None)
        # check event
        if event.as_str() == "swipe_left":
            navigation.open_next_panel()
        elif event.as_str() == "swipe_right":
            navigation.open_prev_panel()
        elif event.as_str() == "swipe_up":
            if not navigation.has_up_panel() or unlock_panel:
                navigation.open_popup("sys_about")
            else:
                navigation.close_panel()
        elif event.as_str() == "swipe_down":
            if not navigation.has_up_panel() or unlock_panel:
                navigation.open_popup("sys_settings")
            else:
                navigation.close_panel()

    def process_event(self, event: HAUIEvent) -> None:
        """Process event.

        Args:
            event (HAUIEvent): Event
        """
        # update device vars values
        self.device_info[event.name] = event.value
        # process gesture event
        if event.name == ESP_EVENT["gesture"]:
            self.process_gesture(event)
        # process sleeping state
        elif event.name == ESP_EVENT["touch_start"]:
            self.check_wakeup()
        elif event.name == ESP_EVENT["sleep"]:
            self.set_sleeping(True)
            # clear navigation snapshot when sleeping
            navigation = self.app.controller["navigation"]
            navigation.unset_snapshot()
        elif event.name == ESP_EVENT["wakeup"]:
            self.set_sleeping(False)
            # set a flag as just woke up
            self.woke_up = True
        elif event.name == ESP_EVENT["page"]:
            if self.device_info.get("page", 0) != event.value:
                self.first_touch = True
        elif event.name == ESP_EVENT["display_state"]:
            if event.value == "on":
                self.is_on_check = True
        elif event.name == ESP_EVENT["button_left"]:
            if event.value == "0":
                if self.get("home_on_button_toggle"):
                    self.check_wakeup()
                self.toggle_left_button_state()
        elif event.name == ESP_EVENT["button_right"]:
            if event.value == "0":
                if self.get("home_on_button_toggle"):
                    self.check_wakeup()
                self.toggle_right_button_state()
        # process notification events
        elif event.name == NOTIF_EVENT["notif_add"]:
            if self.get("sound_on_notification", True):
                self.play_sound("notification")

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
        if navigation.panel.is_wakeup_panel() and not navigation.panel.is_home_panel():
            exit_sleep = True
            display_state = self.device_info.get("display_state")

            if self.woke_up:
                self.first_touch = True

            if not self.get("home_on_wakeup"):
                if self.woke_up:
                    self.log("not exiting sleep/wakeup screen, just woke up")
                    self.woke_up = False
                    exit_sleep = False

            if not self.get("home_on_first_touch"):
                if self.first_touch:
                    self.log("not exiting sleep/wakeup screen, first touch")
                    self.first_touch = False
                    exit_sleep = False

            if self.get("home_only_when_on"):
                if display_state != "on" or self.is_on_check:
                    self.log(f"not exiting sleep/wakeup screen, display state {display_state}")
                    self.is_on_check = False
                    exit_sleep = False

            if self.woke_up:
                self.woke_up = False

            if exit_sleep:
                return_to_home_after_seconds = self.get("return_to_home_after_seconds", 0)
                if (
                    self.get("always_return_to_home", False)
                    or not navigation.restore_snapshot(return_to_home_after_seconds)
                ):
                    navigation.open_home_panel()

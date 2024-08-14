from .mapping.page import PANEL_MAPPING, SYS_PANEL_MAPPING
from .mapping.const import ESP_EVENT
from .abstract.part import HAUIPart


class HAUIDevice(HAUIPart):

    """
    Represents a NSPanel device.

    - Gestures and interaction with device
    - Device wide callbacks from entities / homeassistant
    - Physical buttons state
    """

    def __init__(self, app, config=None):
        """Initializes the device.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config of device. Defaults to None.
        """
        super().__init__(app, config)
        self.device_info = {}
        self.connected = False
        self.sleeping = False
        self.wake_up = False
        self._btn_left_info = {"state": False, "entity_id": None, "handle": None}
        self._btn_right_info = {"state": False, "entity_id": None, "handle": None}

    # prepare and update

    def _check_config(self):
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

    def _register_callbacks(self):
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

    def _cancel_callbacks(self):
        """Cancels all device callbacks."""
        # cancel button state callbacks
        for i in ["left", "right"]:
            button = getattr(self, f"_btn_{i}_info")
            if button["handle"]:
                self.app.cancel_listen_state(button["handle"])
                button["handle"] = None

    # part

    def start_part(self):
        """Starts the part."""
        self.log("Device is starting")
        self._check_config()
        self._register_callbacks()

    def stop_part(self):
        """Stops the part."""
        self.log("Device is stopping")
        self._cancel_callbacks()

    # public

    def set_device_info(self, device_info, append=True):
        """Sets devices related vars from a dict.

        Args:
            device_info (dict): dict with device info vars
            append (bool, optional): Append or replace values. Defaults to True (append).
        """
        if append:
            self.device_info = {**self.device_info, **device_info}
        else:
            self.device_info = device_info

    def set_connected(self, connected):
        """Sets the device as connected.

        Args:
            connected (bool): Connection state
        """
        self.log(f"Device connected: {connected}")
        self.connected = connected
        navigation = self.app.controller["navigation"]
        if connected:
            # entry point after connected
            navigation.open_panel("sys_system")

    def set_sleeping(self, sleeping):
        """Sets the device as sleeping.

        Args:
            sleeping (bool): Sleeping state
        """
        self.sleeping = sleeping

    def get_locale(self):
        """Returns the device locale.

        Returns:
            str: Locale
        """
        return self.get("locale", "en_US")

    def get_name(self):
        """Returns the device name.

        Returns:
            str: Device name
        """
        return self.get("name", "nspanel_haui")

    def get_left_button_state(self):
        """Returns the left button state.

        Returns:
            str: state
        """
        return self._btn_left_info["state"]

    def toggle_left_button_state(self):
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

    def get_right_button_state(self):
        """Returns the right button state.

        Returns:
            str: state
        """
        return self._btn_right_info["state"]

    def toggle_right_button_state(self):
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

    def process_gesture(self, event):
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

    def process_event(self, event):
        """Process event.

        Args:
            event (HAUIEvent): Event
        """
        # update device vars values
        self.device_info[event.name] = event.value
        # process gesture event
        if event.name == ESP_EVENT["gesture"]:
            self.process_gesture(event)
        elif event.name == ESP_EVENT["touch_start"]:
            self.check_wake_up()
        # update device sleeping state
        elif event.name == ESP_EVENT["sleep"]:
            self.set_sleeping(True)
        elif event.name == ESP_EVENT["wakeup"]:
            self.set_sleeping(False)
            self.wake_up = True
        elif event.name == ESP_EVENT["button_left"]:
            if event.value == "0":
                self.check_wake_up()
                self.toggle_left_button_state()
        elif event.name == ESP_EVENT["button_right"]:
            if event.value == "0":
                self.check_wake_up()
                self.toggle_right_button_state()

    def check_wake_up(self):
        """Checks if the display just woke up to switch from wakeup page."""
        navigation = self.app.controller["navigation"]
        if not navigation.panel:
            return
        if navigation.panel.is_wakeup_panel() and not navigation.panel.is_home_panel():
            display_state = self.device_info.get("display_state")
            if display_state != "on":
                self.log(f"display state {display_state}")
                return
            if self.wake_up:
                self.wake_up = False
            else:
                navigation.open_home_panel()

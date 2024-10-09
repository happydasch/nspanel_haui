from haui.abstract.config import HAUIConfig
from haui.device import HAUIDevice
from haui.controller import (
    HAUIMQTTController,
    HAUIConnectionController,
    HAUIGestureController,
    HAUINavigationController,
    HAUIUpdateController,
    HAUINotificationController,
)

import appdaemon.plugins.hass.hassapi as hass


class NSPanelHAUI(hass.Hass):

    """
    NSPanel HAUI App

    This class is only used to initialize and provide callbacks
    The main logic is in the haui module.
    """

    def __init__(self, *args, **kwargs):
        """ Initialize NSPanel HAUI """
        super().__init__(*args, **kwargs)
        self.controller = {}
        self.config = None
        self.device = None

    def initialize(self):
        """ Called from AppDaemon when starting. """
        # create config
        self.config = HAUIConfig(self, self.args["config"])
        # create the nspanel device representation
        self.device = HAUIDevice(self, self.config.get("device"))
        # create mqtt controller
        mqtt_controller = HAUIMQTTController(
            self,
            self.config.get("mqtt"),
            self.get_plugin_api("MQTT"),
            self.callback_event,
        )
        self.controller["mqtt"] = mqtt_controller
        # create connection controller
        connection_controller = HAUIConnectionController(
            self, self.config.get("connection"), self.callback_connection
        )
        self.controller["connection"] = connection_controller
        # create navigation controller
        navigation_controller = HAUINavigationController(
            self, self.config.get("navigation")
        )
        self.controller["navigation"] = navigation_controller
        # create notification controller
        notification_controller = HAUINotificationController(
            self, self.config.get("notification")
        )
        self.controller["notification"] = notification_controller
        # create update controller
        update_controller = HAUIUpdateController(self, self.config.get("update"))
        self.controller["update"] = update_controller
        # create gesture controller
        gesture_controller = HAUIGestureController(self, self.config.get("gesture"))
        self.controller["gesture"] = gesture_controller
        # start all parts everything
        self.start()

    def terminate(self):
        """ Called from AppDaemon when stopping. """
        self.stop()

    # part

    def start(self):
        """ Called when starting. """
        for controller in self.controller.values():
            if not isinstance(controller, NSPanelHAUI):
                controller.start()
        self.device.start()

    def stop(self):
        """ Called when stopping. """
        if self.device is not None:
            self.device.stop()
        for controller in self.controller.values():
            if not isinstance(controller, NSPanelHAUI):
                controller.stop()

    # callback

    def callback_event(self, event):
        """ Callback for events.

        Args:
            event (HAUIEvent): Event
        """
        for controller in self.controller.values():
            if not isinstance(controller, NSPanelHAUI):
                controller.process_event(event)
        self.device.process_event(event)

    def callback_connection(self, connected):
        """ Callback for connection events from controller.

        Args:
            connected (bool): Connection status
        """
        self.log(f"Device connection status: {connected}")
        self.device.set_connected(connected)

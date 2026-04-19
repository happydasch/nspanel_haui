from typing import Any, ClassVar, TypedDict, cast

import appdaemon.plugins.hass.hassapi as hass
from haui.abstract.base import HAUIBase
from haui.abstract.config import HAUIConfig
from haui.controller import (
    HAUIConnectionController,
    HAUIGestureController,
    HAUIMQTTController,
    HAUINavigationController,
    HAUINotificationController,
    HAUIUpdateController,
)
from haui.device import HAUIDevice


class ControllerFactory:
    """Factory class for creating controllers with unified approach."""

    # Registry mapping controller names to their constructor parameters
    _controller_registry: ClassVar[dict[str, dict]] = {}

    @classmethod
    def _init_registry(cls):
        """Initialize the controller registry."""
        if not cls._controller_registry:
            cls._controller_registry = {
                "mqtt": {
                    "class": HAUIMQTTController,
                    "params": ["app", "config", "mqtt", "event_callback"],
                },
                "connection": {
                    "class": HAUIConnectionController,
                    "params": ["app", "config", "connection_callback"],
                },
                "navigation": {"class": HAUINavigationController, "params": ["app", "config"]},
                "notification": {"class": HAUINotificationController, "params": ["app", "config"]},
                "update": {"class": HAUIUpdateController, "params": ["app", "config"]},
                "gesture": {"class": HAUIGestureController, "params": ["app", "config"]},
            }

    @classmethod
    def create_controller(cls, controller_name: str, app: Any, config: dict, **kwargs) -> HAUIBase:
        """Create a controller instance with unified approach.

        Args:
            controller_name: Name of the controller to create
            app: The NSPanelHAUI app instance
            config: Configuration for the controller
            **kwargs: Additional parameters needed for specific controllers

        Returns:
            Controller instance
        """
        cls._init_registry()

        if controller_name not in cls._controller_registry:
            raise ValueError(f"Unknown controller type: {controller_name}")

        controller_info = cls._controller_registry[controller_name]
        controller_class = controller_info["class"]

        # Build the parameter dictionary
        params = {"app": app, "config": config}

        # Add special parameters based on controller type
        if controller_name == "mqtt":
            params["mqtt"] = kwargs.get("mqtt_api")
            params["event_callback"] = kwargs.get("event_callback")
        elif controller_name == "connection":
            params["connection_callback"] = kwargs.get("connection_callback")

        # Create the controller instance
        return controller_class(**params)


class ControllerDict(TypedDict, total=True):
    # TypedDict with per-key types so callers get the concrete controller
    # (e.g. controller["navigation"] is HAUINavigationController, not a union).
    mqtt: HAUIMQTTController
    connection: HAUIConnectionController
    navigation: HAUINavigationController
    notification: HAUINotificationController
    update: HAUIUpdateController
    gesture: HAUIGestureController


class NSPanelHAUI(hass.Hass):
    """
    NSPanel HAUI App

    This class is only used to initialize and provide callbacks
    The main logic is in the haui module.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize NSPanel HAUI"""
        super().__init__(*args, **kwargs)
        self.controller: ControllerDict = {}  # type: ignore[typeddict-item]
        # Set in initialize() — AppDaemon guarantees initialize() runs before any
        # code paths that touch these, so we declare them as non-Optional.
        self.device_config: HAUIConfig = None  # type: ignore[assignment]
        self.device: HAUIDevice = None  # type: ignore[assignment]

    def initialize(self) -> None:
        """Called from AppDaemon when starting."""
        # create device config
        self.device_config = HAUIConfig(self, self.args["config"])
        # create the nspanel device representation
        self.device = HAUIDevice(self, self.device_config.get("device"))

        # create all controllers using unified factory approach
        self.controller["mqtt"] = cast(HAUIMQTTController, ControllerFactory.create_controller(
            "mqtt",
            self,
            self.device_config.get("mqtt"),
            mqtt_api=self.get_plugin_api("MQTT"),
            event_callback=self.callback_event,
        ))
        self.controller["connection"] = cast(HAUIConnectionController, ControllerFactory.create_controller(
            "connection",
            self,
            self.device_config.get("connection"),
            connection_callback=self.callback_connection,
        ))
        self.controller["navigation"] = cast(HAUINavigationController, ControllerFactory.create_controller(
            "navigation", self, self.device_config.get("navigation")
        ))
        self.controller["notification"] = cast(HAUINotificationController, ControllerFactory.create_controller(
            "notification", self, self.device_config.get("notification")
        ))
        self.controller["update"] = cast(HAUIUpdateController, ControllerFactory.create_controller(
            "update", self, self.device_config.get("update")
        ))
        self.controller["gesture"] = cast(HAUIGestureController, ControllerFactory.create_controller(
            "gesture", self, self.device_config.get("gesture")
        ))

        # start all parts everything
        self.start()

    def terminate(self) -> None:
        """Called from AppDaemon when stopping."""
        self.stop()

    # part

    def start(self) -> None:
        """Called when starting."""
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.start()
        self.device.start()

    def stop(self) -> None:
        """Called when stopping."""
        if self.device:
            self.device.stop()
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.stop()

    # callback

    def callback_event(self, event: Any) -> None:
        """Callback for events.

        Args:
            event (Any): Event
        """
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.process_event(event)
        self.device.process_event(event)

    def callback_connection(self, connected: bool) -> None:
        """Callback for connection events from controller.

        Args:
            connected (bool): Connection status
        """
        self.log(f"Device connection status: {connected}")
        self.device.set_connected(connected)

from typing import Any, TypedDict

from .ha_adapter import HAAdapter
from .haui.abstract.base import HAUIBase
from .haui.abstract.config import HAUIConfig
from .haui.controller import (
    HAUIConnectionController,
    HAUIGestureController,
    HAUIMQTTController,
    HAUINavigationController,
    HAUINotificationController,
    HAUIUpdateController,
)
from .haui.device import HAUIDevice


class ControllerDict(TypedDict, total=True):
    mqtt: HAUIMQTTController
    connection: HAUIConnectionController
    navigation: HAUINavigationController
    notification: HAUINotificationController
    update: HAUIUpdateController
    gesture: HAUIGestureController


class NSPanelHAUI(HAAdapter):
    """NSPanel HAUI integration entry point.

    Inherits HAAdapter so all haui sub-components receive a compatible API surface via self.app.
    Prepared for future migration to HA config entries.
    """

    def __init__(self, hass: Any, name: str, config_args: dict) -> None:
        super().__init__(hass, name)
        self._config_args = config_args
        self.controller: ControllerDict = {}  # type: ignore[typeddict-item]
        self.device_config: HAUIConfig = None  # type: ignore[assignment]
        self.device: HAUIDevice = None  # type: ignore[assignment]

    def initialize(self) -> None:
        """Called from async_setup via hass.async_add_executor_job."""
        self.device_config = HAUIConfig(self, self._config_args)
        self.device = HAUIDevice(self, self.device_config.get("device"))
        mqtt_api = self.get_plugin_api("MQTT")

        self.controller["mqtt"] = HAUIMQTTController(
            self, self.device_config.get("mqtt"), mqtt_api, self.callback_event
        )
        self.controller["connection"] = HAUIConnectionController(
            self, self.device_config.get("connection"), self.callback_connection
        )
        self.controller["navigation"] = HAUINavigationController(
            self, self.device_config.get("navigation")
        )
        self.controller["notification"] = HAUINotificationController(
            self, self.device_config.get("notification")
        )
        self.controller["update"] = HAUIUpdateController(
            self, self.device_config.get("update")
        )
        self.controller["gesture"] = HAUIGestureController(
            self, self.device_config.get("gesture")
        )

        self.start()

    # lifecycle

    def start(self) -> None:
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.start()
        self.device.start()

    def stop(self) -> None:
        if self.device:
            self.device.stop()
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.stop()

    # callbacks

    def callback_event(self, event: Any) -> None:
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.process_event(event)
        self.device.process_event(event)

    def callback_connection(self, connected: bool) -> None:
        self.log(f"Device connection status: {connected}")
        self.device.set_connected(connected)

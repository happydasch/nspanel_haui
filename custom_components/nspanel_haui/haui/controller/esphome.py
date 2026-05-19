from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...ha_adapter import ESPHomeProxy
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ALL_CMD, ALL_RECV, ESP_NS_EVENT


class HAUIESPHomeController(HAUIBase):
    """ESPHome controller for device communication via ESPHome native API.

    Provides access to ESPHome native API functionality for device communication.
    """

    def __init__(
        self,
        app: NSPanelHAUI,
        config: dict[str, Any],
        esp_api: ESPHomeProxy,
        event_callback: Any,
    ) -> None:
        """Initialize ESPHome controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
            esp_api (ESPHomeProxy): ESPHome native API bridge
            event_callback (method): Callback for events
        """
        super().__init__(app, config)
        self.esphome = esp_api
        self.prev_cmd: str | None = None
        self._event_callback = event_callback
        self._device_names: list[str] = []

        # Build list of configured device names
        devices = self.config.get("devices", [])
        device_name = self.config.get("device_name", "")

        if not device_name and not devices:
            self.log(
                "Neither device_name nor devices configured in ESPHome config",
                level="ERROR",
            )
            raise ValueError("device_name is required when no devices list is configured")

        if devices:
            for device in devices:
                name = device.get("name", "")
                if name:
                    self._device_names.append(name)
        if not self._device_names and device_name:
            self._device_names = [device_name]

    # part

    def start_part(self) -> None:
        """Starts the part."""
        # Listen for the single static event type used by all device events
        self.esphome.listen_event(self.callback_event, ESP_NS_EVENT)
        self.log(f"Listening for ESPHome events (devices: {self._device_names})")

    def stop_part(self) -> None:
        """Stops the part.

        Cancels all ESPHome event bus listeners registered during start_part.
        """
        self.esphome.cancel_listen_events()

    # public

    def send_cmd(self, cmd: str, value: str = "", force: bool = False) -> None:
        """Sends a command to the device(s) via ESPHome native API.

        Commands are broadcast to all discovered ESPHome devices.

        Args:
            cmd (str): Command name (with or without esphome. prefix).
            value (str, optional): Value for command. Defaults to ''.
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        # Strip esphome. prefix for the JSON payload - ESPHomeProxy expects
        # unprefixed names (e.g., "send_command", not "esphome.send_command")
        bare_cmd = cmd.removeprefix("esphome.")

        if f"esphome.{bare_cmd}" not in ALL_CMD:
            self.log(f"Unknown command {cmd} received. content: {value}")

        if value is None:
            value = ""
        elif not isinstance(value, (dict, list)):
            value = str(value)
        cmd_json = json.dumps({"name": bare_cmd, "value": value})
        if not force and self.prev_cmd == cmd_json:
            self.log(f"Dropping identical consecutive message: {cmd_json}")
            return

        self.esphome.publish(bare_cmd, cmd_json)
        self.prev_cmd = cmd_json

    def callback_event(self, event_name: str, data: dict[str, Any], kwargs: dict[str, Any]) -> None:
        """Callback for ESPHome events.

        The ESPHomeProxy passes pre-parsed data with 'name' and 'value' keys.

        Args:
            event_name (str): HA event type (e.g., "esphome.connected").
            data (dict): Event data with 'name' and 'value' keys.
            kwargs (dict): Additional arguments.
        """
        name = data.get("name", event_name)
        value = data.get("value", "")

        self.debug_log(
            f"ESPHome event received - name: {name}, value: {str(value)[:100]}",
        )

        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received. content: {value}")

        event = HAUIEvent(name, value)
        self._event_callback(event)

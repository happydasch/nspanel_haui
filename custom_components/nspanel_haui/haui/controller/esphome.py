from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...hub.adapter import ESPHomeProxy
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ALL_CMD, ALL_RECV, ESP_NS_EVENT, ESPAction


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
        self.prev_cmd: tuple[str, str] | None = None
        # What the shown page was sent since it loaded: target -> last command.
        self._page_commands: dict[str, str] = {}
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

    def send_cmd(self, cmd: str, value: str | dict | list = "", force: bool = False) -> None:
        """Sends a command to the device(s) via ESPHome native API.

        Commands are broadcast to all discovered ESPHome devices.

        Args:
            cmd (str): Command name (with or without esphome. prefix).
            value: Value for command. Passed as-is (str/dict/list).
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        # Strip esphome. prefix for the JSON payload - ESPHomeProxy expects
        # unprefixed names (e.g., "send_command", not "esphome.send_command")
        bare_cmd = cmd.removeprefix("esphome.")

        if f"esphome.{bare_cmd}" not in ALL_CMD:
            self.log(f"Unknown command {cmd} received. content: {value}", level="WARNING")

        if value is None:
            value = ""

        # Dedup only applies to single-command sends. Batch sends
        # (send_commands) are already deduplicated at the _dedup_commands
        # level in haui_base.py; transport-level dedup of batches can drop
        # an entire chunk of a multi-chunk send, causing partial updates.
        dedup_key = (bare_cmd, value if isinstance(value, str) else str(value))
        if bare_cmd != "send_commands" and not force and self.prev_cmd == dedup_key:
            self.log(
                f"Dropping identical consecutive message: {bare_cmd}/{value}",
                level="WARNING",
            )
            return

        self.log(f"Publishing command: {bare_cmd}", level="DEBUG")
        published = self.esphome.publish(bare_cmd, value)
        if bare_cmd == ESPAction.GOTO_PAGE:
            # The display loads the page with its compiled widgets again.
            self._page_commands.clear()
        elif published and bare_cmd == ESPAction.SEND_COMMAND:
            self._record_page_command(str(value))
        elif published and bare_cmd == ESPAction.SEND_COMMANDS:
            for command in value if isinstance(value, list) else [value]:
                self._record_page_command(str(command))
        if published and bare_cmd in (
            ESPAction.SEND_COMMAND,
            ESPAction.SEND_COMMANDS,
            ESPAction.GOTO_PAGE,
        ):
            self.app.publish_preview_output(bare_cmd, value)
        # Only a command the device got may hold back the same one next time.
        if published:
            self.prev_cmd = dedup_key

    def publish_detached(self, cmd: str, value: str | dict | list = "") -> None:
        """Send a command without waiting for it and without touching the worker.

        Same command names as ``send_cmd`` (the ``esphome.`` prefix is
        stripped), but the command is executed fire-and-forget straight on the
        event loop: it neither waits for the device nor queues behind work on
        the app's worker thread. Only for high-frequency liveness traffic —
        the hub→device heartbeat — which must not be delayed by renders or
        update checks.

        Args:
            cmd (str): Command name (with or without esphome. prefix).
            value: Value for command.
        """
        if value is None:
            value = ""
        self.esphome.publish_detached(cmd.removeprefix("esphome."), value)

    def page_commands(self) -> list[str]:
        """The display commands the shown page was sent since it loaded.

        Only the last write to each target is kept (an attribute, a widget's
        ``vis`` or ``tsw``; any other command is its own target), in the order
        of those last writes. Replayed on the freshly loaded page, after the
        page's ``load_commands``, they end on the screen the panel shows: what
        the Live preview gives a viewer that attaches to a shown page.
        """
        return list(self._page_commands.values())

    def _record_page_command(self, command: str) -> None:
        target = _command_target(command)
        self._page_commands.pop(target, None)
        self._page_commands[target] = command

    def reset_prev_cmd(self) -> None:
        """Clear the previous-command cache so the next render is never suppressed.

        Call this when switching pages so the first render batch after a page
        transition always reaches the display, even if it happens to be
        identical to the last batch sent from the previous page.
        """
        self.prev_cmd = None

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

        self.log(
            f"ESPHome event received - name: {name}, value: {str(value)[:100]}",
            level="DEBUG",
        )

        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received. content: {value}")

        event = HAUIEvent(name, value)
        self._event_callback(event)


def _command_target(command: str) -> str:
    """What a display command sets: a later command with the same target replaces it."""
    eq = command.find("=")
    if eq > 0:
        return command[:eq]
    if command.startswith(("vis ", "tsw ")):
        comma = command.rfind(",")
        if comma > 0:
            return command[:comma]
    # Drawing, ref, click: each distinct command is one target.
    return command

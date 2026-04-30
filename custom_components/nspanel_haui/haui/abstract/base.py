import json
import re
import uuid
from contextlib import contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.display_interface import DisplayInterface, MqttTransport
from ..utils.debounce import Debouncer
from ..utils.icon import parse_icon
from ..utils.text import get_state_translation, get_translation
from .event import HAUIEvent


class HAUIBase:
    """Base class for all Home Assistant UI (HAUI) classes."""

    def __init__(
        self, app: "NSPanelHAUI", config: dict[str, Any] | None = None
    ) -> None:
        """Initializes a new instance of the HAUIBase class.

        Args:
            app: The app instance that this HAUI class is associated with.
            config: Optional configuration settings for the HAUI class.
        """
        self.id: uuid.UUID = uuid.uuid4()
        self.app: NSPanelHAUI = app
        self.display = DisplayInterface(MqttTransport(self.app))
        self.debouncer = Debouncer()
        self.config: dict[str, Any] = config or {}
        self.state: dict[str, Any] = {}
        self.started: bool = False
        self._recording: bool = False
        self._rec_cmd: list[str] = []

    def get_id(self) -> uuid.UUID:
        """Returns the id of the config.

        Returns:
            uuid: Id
        """
        return self.id

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a value from the configuration.

        Allows to access nested dicts using a dot notation:

            config = {'a': {'b': {'c': 1}}}
            name = 'a.b.c'
            will return 1

        Args:
            key: The key of the value to get.
            default: Optional default value to return if the value is not found.

        Returns:
            The value.
        """
        value = self.config
        path = key.split(".")
        for p in path:
            if value is not None:
                value = value.get(p, None)
        return value if value is not None else default

    def log(self, msg: str, **kwargs) -> None:
        """Logs a message.

        Args:
            msg: log message.
            args: Optional positional arguments to include in the log message.
            kwargs: Optional keyword arguments to include in the log message.
        """
        ascii_encode = kwargs.get("ascii_encode", False)
        if "ascii_encode" in kwargs:
            kwargs.pop("ascii_encode")
        self.app.log(msg, ascii_encode=ascii_encode, **kwargs)

    def get_locale(self) -> str:
        """Returns the locale of the config.

        Returns:
            str: Locale
        """
        return self.app.device.get_locale()

    def get_config(self) -> dict:
        """Returns a deep copy of the config dict.

        Returns:
            dict: Config (deep copy)
        """
        return deepcopy(self.config)

    def get_state(self, key: str, default: Any = None) -> Any:
        """Returns a value from the runtime state dict.

        Args:
            key: State key.
            default: Default value if key is not present.

        Returns:
            The state value, or default.
        """
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Sets a value in the runtime state dict.

        Args:
            key: State key.
            value: Value to store.
        """
        self.state[key] = value

    def translate(self, text: str) -> str:
        """Returns the translation of the given text.

        Args:
            text (str): Text

        Returns:
            str: Translated text
        """
        return get_translation(text, self.get_locale())

    def translate_state(self, entity_type: str, state: str, attr: str = "state") -> str:
        """Returns the translation of the given state.

        Args:
            entity_type (str): Entity type
            state (str): State

        Returns:
            str: Translated state
        """
        return get_state_translation(entity_type, state, self.get_locale(), attr)

    def process_event(self, event: HAUIEvent) -> None:
        """Callback for events.

        This class should be overwritten.

        Args:
            event: The event.
        """

    # lifecycle

    def is_started(self) -> bool:
        """Returns if the part is started."""
        return self.started

    def start(self) -> None:
        """Starts the object."""
        if self.started:
            return
        self.started = True
        self.start_part()

    def stop(self) -> None:
        """Stops the object."""
        if not self.started:
            return
        self.stop_part()
        self.started = False

    def start_part(self) -> None:
        """Called on start. Override in subclasses."""

    def stop_part(self) -> None:
        """Called on stop. Override in subclasses."""

    # command recording

    @property
    def rec_cmd(self):
        """Context manager for recording and sending commands as a batch.

        Usage:
            with self.rec_cmd:
                self.send_cmd("...")
                self.set_component_text(...)
        """
        return self._rec_cmd_cm()

    @contextmanager
    def _rec_cmd_cm(self):
        self.start_rec_cmd()
        try:
            yield
        finally:
            self.stop_rec_cmd()

    def start_rec_cmd(self) -> None:
        """Starts recording commands."""

        self._recording = True

    def stop_rec_cmd(self, send_commands: bool = True) -> list[str]:
        """Stops the recording of commands.

        Args:
            send_commands (bool, optional): Should commands be sent after
                stopping recording. Defaults to True.

        Returns:
            list: Recorded commands (after per-batch dedup)
        """
        self._recording = False
        commands = self._dedup_commands(self._rec_cmd)
        self._rec_cmd = []
        if send_commands and len(commands) > 0:
            if self.app.device.get("log_commands"):
                commands_str = "\n".join(commands)
                self.log(f"Commands:\n{commands_str}")
            self.send_cmds(commands)
        return commands

    @staticmethod
    def _dedup_commands(commands: list[str]) -> list[str]:
        # Collapse multiple writes to the same target within a batch so the
        # last write wins. Non-assignment commands (vis, ref, click, cirs, ...)
        # are preserved in place to keep their ordering relative to the writes.
        last_seen: dict[str, int] = {}
        for i, cmd in enumerate(commands):
            eq = cmd.find("=")
            if eq <= 0:
                continue
            last_seen[cmd[:eq]] = i
        result: list[str] = []
        for i, cmd in enumerate(commands):
            eq = cmd.find("=")
            if eq <= 0 or last_seen.get(cmd[:eq]) == i:
                result.append(cmd)
        return result

    def send_mqtt(self, name: str, value: str = "", force: bool = False) -> None:
        """Publishes a message to the mqtt cmd topic.

        Args:
            name: The name of the message.
            value: The value of the message.
            force: If True, force sending of message.
        """
        if "mqtt" not in self.app.controller:
            return
        self.app.controller["mqtt"].send_cmd(name, value, force)

    def send_mqtt_json(
        self, name: str, value: dict | None = None, force: bool = False
    ) -> None:
        """Publishes a message to the mqtt cmd topic with a json encoded message.

        Args:
            name: The name of the message.
            value: The value of the message.
            force: If True, force sending of message.
        """
        if value is None:
            value = {}
        self.send_mqtt(name, json.dumps(value), force)

    def send_cmd(self, cmd: str) -> None:
        """Sends a command to the MQTT controller with the name "send_command".

        Args:
            cmd: The command to send.
        """
        if self._recording:
            self._rec_cmd.append(cmd)
            return
        if self.app.device.get("log_commands"):
            self.log(f"Command: {cmd}")
        self.display.send_cmd(cmd)

    def send_cmds(self, cmds: list[str]) -> None:
        """Sends a list of commands to the MQTT controller with the name "send_commands".

        This method will split the commands into chunks and send them in one go.

        Args:
            cmds: The commands to send.
        """
        self.display.send_cmds(cmds)

    def set_component_text(self, component: tuple[int, str], text: str) -> None:
        """Sends a command to set the text of a component.

        Args:
            component: The component to set the text for.
            text: The text to set for the component.
        """
        if not component:
            return
        self.send_cmd(f'{component[1]}.txt="{text!s}"')

    def set_component_value(self, component: tuple[int, str], value: int) -> None:
        """Sends a command to set the value of a component.

        Args:
            component_id: The component to set the value for.
            value: The value to set for the component.
        """
        if not component:
            return
        self.send_cmd(f"{component[1]}.val={int(value)}")

    def render_template(self, template: str, parse_icons: bool = True) -> str:
        """Returns a rendered home assistant template string.

        Args:
            template (str): template to render
            parse_icons (bool, optional): If True, the result will be processed
                by parse_icon. Defaults to True.

        Returns:
            str: rendered template string
        """
        if "template:" in template:
            template = template.replace("template:", "")
            splitted_string = template.replace("template:", "").rpartition("}")
            # ATT: there seems to be an encoding problem if the template is too short
            template_string = f"<!--{splitted_string[0]}{splitted_string[1]}-->"
            template = self.app.render_template(template_string)
            try:
                template = re.sub(r"<!--(.*?)-->", r"\1", template)
                template = f"{template}{splitted_string[2]}"
            except Exception:
                template = ""
        if parse_icons:
            template = parse_icon(template)
        return template

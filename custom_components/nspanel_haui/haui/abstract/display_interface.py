from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class DisplayTransport(Protocol):
    def send(self, command: str, value: str) -> None:
        """Send a raw Nextion command string via the underlying transport."""


class MqttTransport:
    """Transport implementation that forwards commands to the MQTT controller."""

    def __init__(self, app):
        self.app = app

    def send(self, command: str, value: str) -> None:
        if "mqtt" not in self.app.controller:
            return
        self.app.controller["mqtt"].send_cmd(command, value)


@dataclass
class DisplayInterface:
    """High‑level interface for Nextion display commands.

    The interface mirrors the public methods that existed on :class:`haui.base.HAUIBase`
    (``set_component_text``/``set_component_value``/``send_cmd``/``send_cmds``).  It delegates to a
    transport object that implements :class:`DisplayTransport`.
    """

    transport: DisplayTransport

    # ---------------------------------------------------------------------
    # Command helpers
    # ---------------------------------------------------------------------
    def send_cmd(self, cmd: str) -> None:
        self.transport.send("send_command", cmd)

    def send_cmds(self, cmds: list[str], max_len: int = 700) -> None:
        total_len = 0
        batch: list[str] = []
        for cmd in cmds:
            if batch and total_len + len(cmd) > max_len:
                self.transport.send("send_commands", json.dumps({"commands": batch}))
                batch = []
                total_len = 0
            batch.append(cmd)
            total_len += len(cmd)
        if batch:
            self.transport.send("send_commands", json.dumps({"commands": batch}))

    def set_component_text(self, component: str, text: str) -> None:
        if not component:
            return
        self.send_cmd(f'{component[1]}.txt="{str(text)}"')

    def set_component_value(self, component: str, value: int) -> None:
        if not component:
            return
        self.send_cmd(f"{component[1]}.val={int(value)}")

    def render_template(self, template: str, parse_icons: bool = True) -> str:
        # For now simply return the template; parsing can be added later.
        return template

    # ---------------------------------------------------------------------
    # Convenience wrappers used by page classes
    # ---------------------------------------------------------------------
    def set_title(self, component: str, title: str) -> None:
        self.set_component_text(component, title)

    def set_message(self, component: str, message: str) -> None:
        self.set_component_text(component, message)

    def send_mqtt_json(
        self, name: str, value: dict | None = None, force: bool = False
    ) -> None:
        if value is None:
            value = {}
        payload = json.dumps(value)
        self.send_cmd(f"{name}={payload}")

    # Future methods can be added here as needed

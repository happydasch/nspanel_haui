from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..mapping.const import ESPCommand

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI


@runtime_checkable
class DisplayTransport(Protocol):
    def send(self, command: str, value: str) -> None:
        """Send a raw Nextion command string via the underlying transport."""


class ESPHomeTransport:
    """Transport implementation that forwards commands to the ESPHome controller."""

    def __init__(self, app: NSPanelHAUI):
        self.app = app

    def send(self, command: str, value: str) -> None:
        if "esphome" not in self.app.controller:
            return
        self.app.controller["esphome"].send_cmd(command, value)


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
        self.transport.send(ESPCommand.SEND_COMMAND, cmd)

    def send_cmds(self, cmds: list[str], max_len: int = 700) -> None:
        total_len = 0
        batch: list[str] = []
        for cmd in cmds:
            if batch and total_len + len(cmd) > max_len:
                self.transport.send(ESPCommand.SEND_COMMANDS, json.dumps({"commands": batch}))
                batch = []
                total_len = 0
            batch.append(cmd)
            total_len += len(cmd)
        if batch:
            self.transport.send(ESPCommand.SEND_COMMANDS, json.dumps({"commands": batch}))

    def set_component_text(self, component: tuple[int, str], text: str) -> None:
        if not component:
            return
        self.send_cmd(f'{component[1]}.txt="{str(text)}"')

    def set_component_value(self, component: tuple[int, str], value: int) -> None:
        if not component:
            return
        self.send_cmd(f"{component[1]}.val={int(value)}")

    def render_template(self, template: str, parse_icons: bool = True) -> str:
        # For now simply return the template; parsing can be added later.
        return template

    # ---------------------------------------------------------------------
    # Convenience wrappers used by page classes
    # ---------------------------------------------------------------------
    def set_title(self, component: tuple[int, str], title: str) -> None:
        self.set_component_text(component, title)

    def set_message(self, component: tuple[int, str], message: str) -> None:
        self.set_component_text(component, message)

    # Future methods can be added here as needed

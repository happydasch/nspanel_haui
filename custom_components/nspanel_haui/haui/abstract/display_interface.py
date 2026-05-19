from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..abstract.component import Component
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
    """High-level interface for Nextion display commands.

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

    def set_component_text(self, component: Component, text: str) -> None:
        if not component:
            return
        self.send_cmd(f'{component.name}.txt="{str(text)}"')

    def set_component_value(self, component: Component, value: int) -> None:
        if not component:
            return
        self.send_cmd(f"{component.name}.val={int(value)}")

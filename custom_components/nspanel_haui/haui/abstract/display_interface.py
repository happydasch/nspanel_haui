from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..abstract.component import Component
from ..mapping.const import ESPCommand

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)


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
            _LOGGER.warning(
                "ESPHome controller not available — dropping command %s (value: %s)",
                command,
                str(value)[:100],
            )
            return
        _LOGGER.debug("ESPHomeTransport.send: %s", command)
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

    def send_cmds(self, cmds: list[str], max_len: int = 2048) -> None:
        total_len = 0
        batch: list[str] = []
        chunks: list[tuple[int, list[str]]] = []
        for cmd in cmds:
            if batch and total_len + len(cmd) > max_len:
                chunks.append((len(chunks), batch))
                batch = []
                total_len = 0
            batch.append(cmd)
            total_len += len(cmd)
        if batch:
            chunks.append((len(chunks), batch))

        if len(chunks) > 1:
            _LOGGER.debug(
                "send_cmds: %d commands split into %d chunks (max_len=%d)",
                len(cmds),
                len(chunks),
                max_len,
            )

        for idx, chunk in chunks:
            try:
                self.transport.send(ESPCommand.SEND_COMMANDS, json.dumps({"commands": chunk}))
            except Exception:
                _LOGGER.error(
                    "Failed to send chunk %d/%d (%d commands) to display transport",
                    idx + 1,
                    len(chunks),
                    len(chunk),
                    exc_info=True,
                )
                raise

    def set_component_text(self, component: Component, text: str) -> None:
        if not component:
            return
        self.send_cmd(f'{component.name}.txt="{str(text)}"')

    def set_component_value(self, component: Component, value: int) -> None:
        if not component:
            return
        self.send_cmd(f"{component.name}.val={int(value)}")

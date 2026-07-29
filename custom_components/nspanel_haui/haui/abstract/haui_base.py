from __future__ import annotations

import threading
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .component import Component

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..utils.debounce import Debouncer
from .display_interface import DisplayInterface, ESPHomeTransport
from .haui_config_access import HAUIConfigAccess


class HAUIBase(HAUIConfigAccess):
    """Runtime base class for HAUI components that need display transport,
    command batching, debouncing, and lifecycle management.

    Extends :class:"HAUIConfigAccess" which provides config access and logging.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initializes a new instance of the HAUIBase class.

        Args:
            app: The app instance that this HAUI class is associated with.
            config: Optional configuration settings for the HAUI class.
        """
        super().__init__(app, config)
        self.display = DisplayInterface(ESPHomeTransport(self.app))
        # Debouncer with executor dispatch: timer callbacks run on the
        # HA executor thread so page code (send_cmd, state access) is
        # always on the correct thread.
        executor: Callable[[Callable[[], None]], None] | None = None
        loop = getattr(getattr(self.app, "hass", None), "loop", None)
        if loop is not None:
            hass = self.app.hass
            if getattr(hass, "async_add_executor_job", None) is not None:

                def _executor_wrapper(func: Callable[[], None]) -> None:
                    try:
                        loop.call_soon_threadsafe(hass.async_add_executor_job, func)
                    except RuntimeError:
                        pass  # Event loop is closed during HA shutdown

                executor = _executor_wrapper
        self.debouncer = Debouncer(executor=executor)
        self._recording: bool = False
        self._rec_cmd_depth: int = 0
        self._rec_cmd: list[str] = []
        self._rec_cmd_lock = threading.RLock()

    # lifecycle

    def start(self) -> None:
        """Starts the object."""
        if self.started:
            return
        self.started = True
        self.start_part()

    def stop(self) -> None:
        """Stops the object."""
        self.debouncer.clear_all()  # cancel any pending state-flap timers
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
    def rec_cmd(self) -> AbstractContextManager[None]:
        """Context manager for recording and sending commands as a batch.

        Usage:
            with self.rec_cmd:
                self.send_cmd("...")
                self.set_component_text(...)
        """
        return self._rec_cmd_cm()

    @contextmanager
    def _rec_cmd_cm(self) -> Generator[None, None, None]:
        self.start_rec_cmd()
        exc_occurred = False
        try:
            yield
        except Exception:
            exc_occurred = True
            raise
        finally:
            if exc_occurred:
                if self._rec_cmd_depth <= 1:
                    self.log(
                        f"Render aborted with exception; discarding "
                        f"{len(self._rec_cmd)} partial commands",
                        level="ERROR",
                    )
                self.stop_rec_cmd(send_commands=False)
            else:
                self.stop_rec_cmd(send_commands=True)

    def start_rec_cmd(self) -> None:
        """Starts recording commands.

        Re-entrant: nested calls increment a depth counter without resetting
        the buffer.  Only the outermost ``stop_rec_cmd`` sends the batch.
        """
        with self._rec_cmd_lock:
            self._rec_cmd_depth += 1
            self._recording = True

    def stop_rec_cmd(self, send_commands: bool = True) -> list[str]:
        """Stops the recording of commands.

        Re-entrant: decrements the depth counter.  Only when the outermost
        context exits (depth reaches 0) are the recorded commands deduplicated
        and sent.  Inner exits are no-ops.

        The lock is held for the entire method including ``send_cmds`` so that
        a concurrent caller on another executor thread cannot interleave its
        commands between chunks of this batch or corrupt the buffer while it
        is being drained.

        Args:
            send_commands (bool, optional): Should commands be sent after
                stopping recording. Defaults to True.

        Returns:
            list: Recorded commands (after per-batch dedup), empty for inner exits.
        """
        with self._rec_cmd_lock:
            if self._rec_cmd_depth > 0:
                self._rec_cmd_depth -= 1
            if self._rec_cmd_depth > 0:
                return []
            self._recording = False
            commands = self._dedup_commands(self._rec_cmd)
            self._rec_cmd = []
            if send_commands and len(commands) > 0:
                ctx = self._cmd_context()
                prefix = f"[{ctx}] " if ctx else ""
                # Level 1: one-line summary for diagnosing partial updates
                if self.app.device.get("debug_level") >= 1:
                    self.log(
                        f"{prefix}Sending {len(commands)} command(s)",
                        level="DEBUG",
                    )
                # Level 2: full command dump
                if self.app.device.get("debug_level") >= 2:
                    commands_str = "\n".join(commands)
                    self.log(
                        f"{prefix}Commands ({len(commands)}):\n{commands_str}",
                        level="DEBUG",
                    )
                self.send_cmds(commands)
            return commands

    @staticmethod
    def _dedup_commands(commands: list[str]) -> list[str]:
        # Collapse multiple writes to the same target within a batch so the
        # last write wins. Non-assignment commands (vis, ref, click, cirs, ...)
        # are preserved in place to keep their ordering relative to the writes.
        # ``vis`` commands are also deduplicated by component name so that
        # hide-then-show of the same component collapses to just the show.
        last_seen: dict[str, int] = {}
        for i, cmd in enumerate(commands):
            eq = cmd.find("=")
            if eq <= 0:
                if cmd.startswith("vis "):
                    comma = cmd.rfind(",")
                    if comma > 0:
                        last_seen[cmd[:comma]] = i
                continue
            last_seen[cmd[:eq]] = i
        result: list[str] = []
        for i, cmd in enumerate(commands):
            eq = cmd.find("=")
            if eq <= 0:
                if cmd.startswith("vis "):
                    comma = cmd.rfind(",")
                    if comma > 0 and last_seen.get(cmd[:comma]) == i:
                        result.append(cmd)
                else:
                    result.append(cmd)
                continue
            if last_seen.get(cmd[:eq]) == i:
                result.append(cmd)
        return result

    def send_esphome(self, name: str, value: Any = "", force: bool = False) -> None:
        """Publishes a command via the ESPHome controller.

        Args:
            name: The name of the command (prefixes with esphome. as needed).
            value: The value of the command.
            force: If True, force sending of command.
        """
        if "esphome" not in self.app.controller:
            return
        self.app.controller["esphome"].send_cmd(name, value, force)

    def _cmd_context(self) -> str:
        """Build a context string for command logs using navigation state.

        Returns:
            str: Context string like "page=grid panel=abc123"
                 or empty string if no context is available.
        """
        nav = self.app.controller.get("navigation")
        if nav is None:
            return ""
        parts = []
        if nav.page is not None:
            from ..mapping.page import PAGE_MAPPING

            parts.append(f"page={PAGE_MAPPING.get(nav.page.page_id, nav.page.page_id)}")
        if nav.panel is not None:
            panel_key = nav.panel.get("key", "")
            panel_type = nav.panel.get_type()
            parts.append(f"panel={panel_type}/{panel_key}")

        return " ".join(parts)

    def send_cmd(self, cmd: str) -> None:
        """Sends a command to the display via the ESPHome transport.

        Args:
            cmd: The Nextion command to send.
        """
        if not isinstance(cmd, str):
            self.log(f"send_cmd: expected str, got {type(cmd).__name__}", level="ERROR")
            return
        with self._rec_cmd_lock:
            if self._recording:
                self._rec_cmd.append(cmd)
                return
            if self.app.device.get("debug_level") >= 2:
                ctx = self._cmd_context()
                prefix = f"[{ctx}] " if ctx else ""
                self.log(f"{prefix}Command: {cmd}", level="DEBUG")
            self.app._last_panel_update = datetime.now(UTC).isoformat()
            self.display.send_cmd(cmd)

    def send_cmds(self, cmds: list[str]) -> None:
        """Sends a list of commands to the display via the ESPHome transport.

        This method will split the commands into chunks and send them in one go.

        Args:
            cmds: The commands to send.
        """
        if self.app.device.get("debug_level") >= 1:
            self.log(f"send_cmds: {len(cmds)} command(s)", level="DEBUG")
        self.app._last_panel_update = datetime.now(UTC).isoformat()
        self.display.send_cmds(cmds)

    def set_component_text(self, component: Component, text: str) -> None:
        """Sends a command to set the text of a component.

        Args:
            component: The component to set the text for.
            text: The text to set for the component.
        """
        if not component:
            return
        self.send_cmd(f'{component.name}.txt="{text!s}"')

    def set_component_value(self, component: Component, value: int) -> None:
        """Sends a command to set the value of a component.

        Args:
            component_id: The component to set the value for.
            value: The value to set for the component.
        """
        if not component:
            return
        self.send_cmd(f"{component.name}.val={int(value)}")


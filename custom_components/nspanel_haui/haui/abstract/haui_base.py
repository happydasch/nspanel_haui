from __future__ import annotations

import re
import threading
import uuid
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ..mapping.color import COLORS, ColorTheme
from .component import Component

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..utils.debounce import Debouncer
from ..utils.icon import parse_icon
from ..utils.text import get_state_translation, get_translation
from .display_interface import DisplayInterface, ESPHomeTransport
from .haui_event import HAUIEvent

_MISSING = object()


class HAUIBase:
    """Base class for all Home Assistant UI (HAUI) classes."""

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initializes a new instance of the HAUIBase class.

        Args:
            app: The app instance that this HAUI class is associated with.
            config: Optional configuration settings for the HAUI class.
        """
        self.id: uuid.UUID = uuid.uuid4()
        self.app: NSPanelHAUI = app
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
        self.config: dict[str, Any] = config or {}
        self.state: dict[str, Any] = {}
        self.started: bool = False
        self._recording: bool = False
        self._rec_cmd_depth: int = 0
        self._rec_cmd: list[str] = []
        self._rec_cmd_lock = threading.RLock()

    def get_id(self) -> uuid.UUID:
        """Returns the id of the config.

        Returns:
            uuid: Id
        """
        return self.id

    def get(self, key: str, default: Any = _MISSING) -> Any:
        """Gets a value from the configuration.

        Allows to access nested dicts using a dot notation:

            config = {'a': {'b': {'c': 1}}}
            name = 'a.b.c'
            will return 1

        Args:
            key: The key of the value to get.
            default: Optional default value to return if the value is not found.
                If not provided and the key is missing, raises KeyError.

        Returns:
            The value.

        Raises:
            KeyError: If the key is not found and no default is provided.
        """
        value: Any = self.config
        path = key.split(".")
        for p in path:
            if value is None:
                if default is not _MISSING:
                    return default
                raise KeyError(
                    f"Config key '{key}' not found (intermediate value is None at '{p}')"
                )
            if not hasattr(value, "get") or not callable(getattr(value, "get", None)):
                if default is not _MISSING:
                    return default
                raise KeyError(
                    f"Config key '{key}' not found "
                    f"(intermediate value {type(value).__name__} has no .get())"
                )
            value = value.get(p, _MISSING)
            if value is _MISSING:
                if default is not _MISSING:
                    return default
                raise KeyError(f"Config key '{key}' not found (missing '{p}')")
        if value is None:
            if default is not _MISSING:
                return default
            raise KeyError(f"Config key '{key}' is None")
        return value

    def get_int(self, key: str, default: int = 0) -> int:
        """Gets a config value as int, coercing and logging on type mismatch.

        Args:
            key: The key of the value to get.
            default: Default value to return if the key is missing or uncoercible.

        Returns:
            int: The config value coerced to int.
        """
        val = self.get(key, None)
        if isinstance(val, int):
            return val
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            self.log(
                f"Config key '{key}' expected int, got {type(val).__name__}: {val!r}",
                level="WARNING",
            )
            return default

    def get_str(self, key: str, default: str = "") -> str:
        """Gets a config value as str, coercing and logging on type mismatch.

        Args:
            key: The key of the value to get.
            default: Default value to return if the key is missing.

        Returns:
            str: The config value coerced to str.
        """
        val = self.get(key, None)
        if isinstance(val, str):
            return val
        if val is None:
            return default
        self.log(
            f"Config key '{key}' expected str, got {type(val).__name__}: {val!r}",
            level="WARNING",
        )
        return str(val)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Gets a config value as bool, coercing and logging on type mismatch.

        Args:
            key: The key of the value to get.
            default: Default value to return if the key is missing.

        Returns:
            bool: The config value coerced to bool.
        """
        val = self.get(key, None)
        if isinstance(val, bool):
            return val
        if val is None:
            return default
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        if isinstance(val, int):
            return val != 0
        self.log(
            f"Config key '{key}' expected bool, got {type(val).__name__}: {val!r}",
            level="WARNING",
        )
        return bool(val)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Gets a config value as float, coercing and logging on type mismatch.

        Args:
            key: The key of the value to get.
            default: Default value to return if the key is missing or uncoercible.

        Returns:
            float: The config value coerced to float.
        """
        val = self.get(key, None)
        if isinstance(val, float):
            return val
        if isinstance(val, int):
            return float(val)
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            self.log(
                f"Config key '{key}' expected float, got {type(val).__name__}: {val!r}",
                level="WARNING",
            )
            return default

    def log(self, msg: str, **kwargs: Any) -> None:
        """Logs a message.

        Args:
            msg: log message.
            args: Optional positional arguments to include in the log message.
            kwargs: Optional keyword arguments to include in the log message.
        """
        # Gate: drop DEBUG messages when debug_level < 1.
        # Callers should use self.debug_log() instead of self.log(level="DEBUG"),
        # but this backstop prevents accidental bypass of the user's setting.
        if kwargs.get("level", "").upper() == "DEBUG":
            if self.app.device.get("debug_level") < 1:
                return
        ascii_encode = kwargs.get("ascii_encode", False)
        if "ascii_encode" in kwargs:
            kwargs.pop("ascii_encode")
        self.app.log(msg, ascii_encode=ascii_encode, **kwargs)

    def debug_log(self, msg: str, min_level: int = 1, **kwargs: Any) -> None:
        """Log at DEBUG level if the device's debug_level >= min_level.

        Args:
            msg: The log message.
            min_level: Minimum debug_level required to emit this log (default 1).
            **kwargs: Additional keyword arguments passed to self.log().
        """
        if self.app.device.get("debug_level") >= min_level:
            kwargs["level"] = "DEBUG"
            self.log(msg, **kwargs)

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

    def translate_state(self, item_type: str, state: str, attr: str = "state") -> str:
        """Returns the translation of the given state.

        Args:
            item_type (str): Item type
            state (str): State

        Returns:
            str: Translated state
        """
        return get_state_translation(item_type, state, self.get_locale(), attr)

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

    def get_color(self, key: str) -> int:
        """Return an RGB565 color value for the given theme key.

        Respects per-device overrides (set in the device config's
        ``color_overrides`` dict) if configured; falls back to the
        built-in ``COLORS`` defaults otherwise.

        When called from a page instance with ``_use_system_colors``
        set to ``False`` (e.g. picture-background pages like clock,
        clocktwo, weather), user overrides are bypassed so the page
        retains its hardcoded palette.

        Args:
            key: A key from the ``COLORS`` dict (e.g. ``"background"``).

        Returns:
            RGB565 integer color value.
        """
        if not getattr(self, "_use_system_colors", True):
            return COLORS[key]
        theme: ColorTheme | None = getattr(self.app, "_color_theme", None)
        if theme is None:
            return COLORS[key]
        return theme.get(key)

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
            except (re.error, IndexError, TypeError) as exc:
                self.log(f"Template render error: {exc}", level="WARNING")
                template = ""
        if parse_icons:
            template = parse_icon(template)
        return template

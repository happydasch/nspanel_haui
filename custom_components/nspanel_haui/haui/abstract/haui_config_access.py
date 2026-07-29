"""Lightweight config access and logging base class.

Provides config access (``get``, ``get_int``, ``get_str``, etc.), runtime
state, logging, translation, and template rendering — without the display
transport, command batching, or lifecycle machinery from ``HAUIBase``.

Use this class instead of ``HAUIBase`` for data/config wrapper classes
(e.g. ``HAUIItem``, ``HAUIConfig``, ``HAUIPanel``) that only need
config access and logging, not display commands.
"""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..mapping.color import COLORS, ColorTheme
from ..utils.icon import parse_icon
from ..utils.text import get_state_translation, get_translation
from .haui_event import HAUIEvent

_MISSING = object()


class HAUIConfigAccess:
    """Lightweight base providing config access, logging, and translation.

    Intentionally excludes display transport, command batching, debouncer,
    and lifecycle methods — those belong in ``HAUIBase`` for runtime
    components that need them.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initializes a new instance.

        Args:
            app: The app instance that this HAUI class is associated with.
            config: Optional configuration settings for the HAUI class.
        """
        self.id: uuid.UUID = uuid.uuid4()
        self.app: NSPanelHAUI = app
        self.config: dict[str, Any] = config or {}
        self.state: dict[str, Any] = {}
        self.started: bool = False

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
        """Callback for events. Override in subclasses.

        Args:
            event: The event.
        """
        return

    def is_started(self) -> bool:
        """Returns if the part is started."""
        return self.started

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

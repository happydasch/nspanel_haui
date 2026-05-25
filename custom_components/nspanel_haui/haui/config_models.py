"""Optional pydantic v2 config validation for NSPanel HAUI.

Gracefully degrades to a no-op when pydantic is not installed.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

__all__ = ["validate_config", "validate_device_config", "validate_panels"]

# Pydantic's BaseModel metaclass triggers blocking importlib.metadata I/O
# (os.listdir, open, read_text) during class creation.  To avoid that on the
# HA event loop, we defer class creation until the first validate_* call by
# wrapping it in a lazy initializer function.  Callers on the event loop
# (e.g. api.py) already dispatch validation via async_add_executor_job, so
# the lazy init will run on a worker thread.
try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

    _HAVE_PYDANTIC = True
except ImportError:
    _HAVE_PYDANTIC = False

_CONFIG_MODEL: type | None = None
_DEVICE_CONFIG_MODEL: type | None = None


def _ensure_models() -> None:
    """Create Pydantic model classes lazily, outside any import path."""
    global _CONFIG_MODEL, _DEVICE_CONFIG_MODEL  # noqa: PLW0603

    if not _HAVE_PYDANTIC or _CONFIG_MODEL is not None:
        return

    from .mapping.color import COLORS

    class _PanelConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        type: str | None = None
        title: str = ""
        key: str | None = None
        show_in_navigation: bool = True

    class _DeviceConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        locale: str | None = None
        button_left_entity: str | None = None
        button_right_entity: str | None = None
        home_panel: str = ""
        sleep_panel: str = ""
        wakeup_panel: str = ""
        show_home_button: bool = False
        show_sleep_button: bool = False
        show_notifications_button: bool = True
        home_on_wakeup: bool = False
        home_on_first_touch: bool = True
        home_only_when_on: bool = False
        home_on_button_toggle: bool = False
        reset_interaction_on_button: bool = True
        return_to_home_after_seconds: int = 0
        always_return_to_home: bool = False
        sound_on_startup: bool = True
        sound_on_notification: bool = True
        use_relay_left: bool = True
        use_relay_right: bool = True
        debug_level: int = 0
        log_items: bool = False
        hub_idle_timeout: int = 0
        color_overrides: dict[str, int] = Field(default_factory=dict)
        enabled: bool = True

        @field_validator("color_overrides", mode="before")
        @classmethod
        def _validate_color_overrides(cls, v: Any) -> dict[str, int]:
            """Validate color_overrides: warn on unknown keys, clamp to 0-65535."""
            if not isinstance(v, dict):
                return v
            validated: dict[str, int] = {}
            for key, raw in v.items():
                if not isinstance(key, str):
                    _LOGGER.warning("Ignoring non-string key %r in color_overrides", key)
                    continue
                if key not in COLORS:
                    _LOGGER.warning(
                        "Unknown color key %r in color_overrides (valid keys: %s)",
                        key,
                        ", ".join(sorted(COLORS)),
                    )
                try:
                    val = int(raw) if not isinstance(raw, int) else raw
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid color value %r for key %r, ignoring", raw, key)
                    continue
                if val < 0 or val > 65535:
                    _LOGGER.warning(
                        "Color value %r for key %r outside RGB565 range, clamping", val, key
                    )
                    val = max(0, min(val, 65535))
                validated[key] = val
            return validated

    class _DeviceEntry(_DeviceConfig):
        """Device entry as it appears in cfg['devices'] — identity + config."""

        name: str = ""
        esphome_device_id: str = ""
        panels: list[_PanelConfig] = Field(default_factory=list)

    class _ConfigModel(BaseModel):
        model_config = ConfigDict(extra="allow")
        panels: list[_PanelConfig] = Field(default_factory=list)
        sys_panels: list[_PanelConfig] = Field(default_factory=list)
        devices: list[_DeviceEntry] = Field(default_factory=list)

        @model_validator(mode="before")
        @classmethod
        def _coerce_lists(cls, v: Any) -> Any:
            if not isinstance(v, dict):
                return v
            v.setdefault("panels", [])
            v.setdefault("sys_panels", [])
            v.setdefault("devices", [])
            return v

    _CONFIG_MODEL = _ConfigModel
    _DEVICE_CONFIG_MODEL = _DeviceConfig


def _get_model() -> type[BaseModel] | None:
    """Return the ConfigModel class, creating it lazily if needed."""
    _ensure_models()
    return _CONFIG_MODEL  # type: ignore[return-value]


def _get_device_config_model() -> type[BaseModel] | None:
    """Return the DeviceConfig model class, creating it lazily if needed."""
    _ensure_models()
    return _DEVICE_CONFIG_MODEL  # type: ignore[return-value]


def validate_config(raw_cfg: dict) -> BaseModel | None:
    """Validate *raw_cfg* against the config schema.

    Returns the validated model instance, or None when pydantic is unavailable.
    """
    model = _get_model()
    if model is None:
        return None
    return model(**raw_cfg)


def validate_device_config(config: dict) -> BaseModel | None:
    """Validate a single device *config* sub-object against _DeviceConfig.

    Returns the validated model instance, or None when pydantic is unavailable.
    """
    model = _get_device_config_model()
    if model is None:
        return None
    return model(**config)


def validate_panels(panels_data: dict) -> BaseModel | None:
    """Validate panel store data.

    Ensures the panels dict has valid panel definitions and that
    each device's ``config`` sub-object has correct field types.
    """
    all_panels = []
    for dev_data in panels_data.get("devices", {}).values():
        all_panels.extend(dev_data.get("panels", []))
        if "config" in dev_data:
            validate_device_config(dev_data["config"])
    return validate_config({"panels": all_panels})

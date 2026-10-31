"""Pydantic v2 config validation for NSPanel HAUI.

Pydantic is a hard requirement (declared in ``manifest.json``); the model
classes are created lazily because importing pydantic does blocking
importlib I/O that must stay off the HA event loop.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .device_config import LOG_LEVEL_OPTIONS
from .mapping.const import GESTURES

if TYPE_CHECKING:
    from pydantic import BaseModel

_LOGGER = logging.getLogger(__name__)

__all__ = ["validate_config_model", "validate_device_config", "validate_panels"]

# Importing pydantic at module scope does blocking importlib I/O (import_module,
# importlib.metadata reads), and its BaseModel metaclass triggers more blocking
# I/O during class creation.  Both must stay off the HA event loop, so we defer
# the pydantic import AND model creation until the first validate_* call.
# Callers on the event loop (e.g. api.py) already dispatch validation via
# async_add_executor_job, so this lazy init runs on a worker thread.
_CONFIG_MODEL: type | None = None
_DEVICE_CONFIG_MODEL: type | None = None


def _ensure_models() -> None:
    """Import pydantic and create model classes lazily, off the event loop."""
    global _CONFIG_MODEL, _DEVICE_CONFIG_MODEL  # noqa: PLW0603

    if _CONFIG_MODEL is not None:
        return

    from pydantic import (
        BaseModel,
        ConfigDict,
        Field,
        field_validator,
        model_validator,
    )

    from .mapping.color import COLORS

    class _PanelConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        type: str | None = None
        title: str = ""
        key: str | None = None
        show_in_navigation: bool = True

    class _GestureSequence(BaseModel):
        """One entry of the ``gesture_sequences`` device setting."""

        model_config = ConfigDict(extra="forbid")
        sequence: list[str]
        timeframe: int = Field(ge=1, le=60)
        open: str

        @field_validator("sequence")
        @classmethod
        def _known_gestures(cls, v: list[str]) -> list[str]:
            if not v:
                raise ValueError("a gesture sequence needs at least one swipe")
            unknown = [g for g in v if g not in GESTURES]
            if unknown:
                raise ValueError(f"unknown gesture(s) {unknown}; use one of {list(GESTURES)}")
            return v

        @field_validator("open")
        @classmethod
        def _needs_panel(cls, v: str) -> str:
            if not v:
                raise ValueError("a gesture sequence needs a panel to open")
            return v

    class _DeviceConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        locale: str = "en_US"
        display_model: str = "eu"
        time_format: str = ""
        date_format: str = ""
        date_format_locale: str = ""
        button_left_entity: str = ""
        button_right_entity: str = ""
        home_panel: str = ""
        idle_panel: str = ""
        idle_panel_extra: str = ""
        show_home_button: bool = False
        show_idle_button: bool = False
        show_notifications_button: bool = True
        reset_interaction_on_button: bool = True
        snapshot_max_age_seconds: int = Field(-1, ge=-1)
        sound_on_startup: bool = False
        sound_on_notification: bool = False
        persistent_sound_interval: int = Field(5, ge=1, le=600)
        use_do_not_disturb: bool = False
        quiet_hours_start: str = ""
        quiet_hours_end: str = ""
        use_sleep_schedule: bool = False
        sleep_schedule_start: str = ""
        sleep_schedule_end: str = ""
        use_night_mode: bool = False
        night_mode_start: str = ""
        night_mode_end: str = ""
        brightness_full: int = Field(50, ge=0, le=100)
        brightness_dimmed: int = Field(20, ge=0, le=100)
        night_brightness_full: int = Field(5, ge=0, le=100)
        night_brightness_dimmed: int = Field(5, ge=0, le=100)
        use_relay_left: bool = True
        use_relay_right: bool = True
        use_auto_dimming: bool = True
        use_auto_page: bool = True
        use_auto_display_off: bool = True
        # Timeout values are pushed into ESPHome number entities whose own
        # ranges are 0-3600 (dim/page/display-off) resp. 0-86400 (hub-side
        # timers); the REST editor clamps to the same bounds, so enforcement
        # here keeps every entry path (REST, YAML import, stored JSON)
        # consistent.
        timeout_dimming: int = Field(10, ge=0, le=3600)
        timeout_page: int = Field(30, ge=0, le=3600)
        timeout_display_off: int = Field(120, ge=0, le=3600)
        night_timeout_page: int = Field(15, ge=0, le=3600)
        night_timeout_display_off: int = Field(30, ge=0, le=3600)
        log_level: str = "INFO"
        stale_data_seconds: int = Field(0, ge=0, le=86400)
        hub_idle_timeout: int = Field(0, ge=0, le=86400)
        auto_navigate_home_timeout: int = Field(0, ge=0, le=86400)
        color_overrides: dict[str, int] = Field(default_factory=dict)
        gesture_sequences: list[_GestureSequence] = Field(default_factory=list)
        enabled: bool = True

        @field_validator("log_level")
        @classmethod
        def _validate_log_level(cls, v: Any) -> str:
            """Only standard logging levels are accepted; normalize to upper case."""
            if not isinstance(v, str) or v.upper() not in LOG_LEVEL_OPTIONS:
                raise ValueError(
                    f"unsupported log level {v!r}; use one of {LOG_LEVEL_OPTIONS}"
                )
            return v.upper()

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
                    # Only the global COLORS palette is overridable. Domain
                    # colors (weather/alarm/climate) are fixed constants, so any
                    # unknown key is dropped rather than stored.
                    _LOGGER.debug("Dropping non-overridable color key %r from color_overrides", key)
                    continue
                try:
                    val = int(raw) if not isinstance(raw, int) else raw
                except ValueError, TypeError:
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


def _get_model() -> type[BaseModel]:
    """Return the ConfigModel class, creating it lazily if needed."""
    _ensure_models()
    assert _CONFIG_MODEL is not None
    return _CONFIG_MODEL


def _get_device_config_model() -> type[BaseModel]:
    """Return the DeviceConfig model class, creating it lazily if needed."""
    _ensure_models()
    assert _DEVICE_CONFIG_MODEL is not None
    return _DEVICE_CONFIG_MODEL


def validate_config_model(raw_cfg: dict) -> BaseModel:
    """Validate *raw_cfg* against the config schema.

    Returns the validated model instance.
    """
    model = _get_model()
    return model(**raw_cfg)


def validate_device_config(config: dict) -> BaseModel:
    """Validate a single device *config* sub-object against _DeviceConfig.

    Returns the validated model instance.
    """
    model = _get_device_config_model()
    return model(**config)


def validate_panels(panels_data: dict) -> BaseModel:
    """Validate panel store data.

    Ensures the panels dict has valid panel definitions and that
    each device's ``config`` sub-object has correct field types.
    """
    all_panels = []
    for dev_data in panels_data.get("devices", {}).values():
        all_panels.extend(dev_data.get("panels", []))
        if "config" in dev_data:
            validate_device_config(dev_data["config"])
    return validate_config_model({"panels": all_panels})

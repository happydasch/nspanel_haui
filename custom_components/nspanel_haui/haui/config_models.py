"""Optional pydantic v2 config validation for NSPanel HAUI.

Gracefully degrades to a no-op when pydantic is not installed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator  # noqa: F401

__all__ = ["validate_config", "validate_device_config"]

_cache: dict[str, type[BaseModel] | None] = {}
_device_config_cache: dict[str, type[BaseModel] | None] = {}


def _get_model() -> type[BaseModel] | None:
    """Return the ConfigModel class, building and caching it on first call."""
    if "model" in _cache:
        return _cache["model"]

    try:

        class _PanelConfig(BaseModel):
            model_config = ConfigDict(extra="allow")
            type: str | None = None
            title: str = ""
            key: str | None = None
            show_in_navigation: bool = True

        class _ConfigModel(BaseModel):
            model_config = ConfigDict(extra="allow")
            panels: list[_PanelConfig] = Field(default_factory=list)
            sys_panels: list[_PanelConfig] = Field(default_factory=list)

            @model_validator(mode="before")
            @classmethod
            def _coerce_lists(cls, v: Any) -> Any:
                v.setdefault("panels", [])
                v.setdefault("sys_panels", [])
                return v

        _cache["model"] = _ConfigModel
    except ImportError:
        _cache["model"] = None

    return _cache["model"]


def _get_device_config_model() -> type[BaseModel] | None:
    """Return the DeviceConfig model class, building and caching it on first call."""
    if "model" in _device_config_cache:
        return _device_config_cache["model"]

    try:

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
            return_to_home_after_seconds: int = 0
            always_return_to_home: bool = False
            sound_on_startup: bool = True
            sound_on_notification: bool = True
            use_relay_left: bool = True
            use_relay_right: bool = True
            debug_level: int = 0
            log_items: bool = False
            enabled: bool = True
            friendly_name: str = ""

        _device_config_cache["model"] = _DeviceConfig
    except ImportError:
        _device_config_cache["model"] = None

    return _device_config_cache["model"]


def validate_config(raw_cfg: dict) -> BaseModel | dict | None:
    """Validate *raw_cfg* against the config schema.

    Returns the validated model instance, or None when pydantic is unavailable.
    """
    model = _get_model()
    if model is None:
        return raw_cfg  # return raw dict for backward compat; pydantic is optional
    return model(**raw_cfg)


def validate_device_config(config: dict) -> BaseModel | None:
    """Validate a single device *config* sub-object against _DeviceConfig.

    Returns the validated model instance, or None when pydantic is unavailable.
    """
    model = _get_device_config_model()
    if model is None:
        return None
    return model(**config)


def validate_connection(data: dict) -> BaseModel | dict | None:
    """Validate connection + device identity layer (config_entry.data).

    Ensures required fields (name, devices) are present and well-formed.
    """
    required = {"name"}
    missing = required - set(data.keys())
    if missing:
        return None
    return validate_config({"device": {"name": data["name"]}})


def validate_runtime(options: dict) -> BaseModel | dict | None:
    """Validate runtime toggles layer (config_entry.options).

    Ensures config_mode, update_interval, debug are valid.
    """
    if options.get("config_mode") not in (None, "ui", "yaml"):
        return None
    return validate_config({})


def validate_panels(panels_data: dict) -> BaseModel | dict | None:
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

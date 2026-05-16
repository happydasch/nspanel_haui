"""Optional pydantic v2 config validation for NSPanel HAUI.

Gracefully degrades to a no-op when pydantic is not installed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["validate_config", "validate_device_config"]

# Pydantic's BaseModel metaclass triggers blocking importlib.metadata I/O
# (os.listdir, open, read_text) during class creation.  To avoid that on the
# HA event loop, we defer class creation until the first validate_* call by
# wrapping it in a lazy initializer function.  Callers on the event loop
# (e.g. api.py) already dispatch validation via async_add_executor_job, so
# the lazy init will run on a worker thread.
#
# The module-level from-import of BaseModel itself does NOT trigger blocking
# I/O — only creating subclasses does.
try:
    from pydantic import BaseModel, ConfigDict, Field, model_validator

    _HAVE_PYDANTIC = True
except ImportError:
    _HAVE_PYDANTIC = False

_CONFIG_MODEL: type | None = None
_DEVICE_CONFIG_MODEL: type | None = None


def _ensure_models() -> None:
    """Create Pydantic model classes lazily, outside any import path.

    Pydantic's metaclass triggers importlib.metadata I/O (listdir, read_text,
    open) that must not run on the HA event loop.  This function is called
    from the validate_* helpers, which are themselves invoked from executor
    jobs or sync worker threads.
    """
    global _CONFIG_MODEL, _DEVICE_CONFIG_MODEL  # noqa: PLW0603

    if not _HAVE_PYDANTIC or _CONFIG_MODEL is not None:
        return

    class _PanelConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        type: str | None = None
        title: str = ""
        key: str | None = None
        show_in_navigation: bool = True
        unlock_code: str | None = None

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

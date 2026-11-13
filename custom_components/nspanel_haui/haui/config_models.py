"""Pydantic v2 config validation for NSPanel HAUI.

Pydantic is a hard requirement (declared in ``manifest.json``); the model
classes are created lazily because importing pydantic does blocking
importlib I/O that must stay off the HA event loop.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from .device_config import DEVICE_CONFIG, LOG_LEVEL_OPTIONS
from .mapping.const import GESTURES
from .schedule import SUN_EVENTS, parse_boundary

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = [
    "PanelValidationError",
    "validate_config_model",
    "validate_device_config",
    "validate_panels",
    "validate_update_policy",
]

_LOGGER = logging.getLogger(__name__)

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

    class _PanelConfig(BaseModel):
        model_config = ConfigDict(extra="allow")
        type: str | None = None
        title: str = ""
        theme_id: str = ""
        key: str | None = None
        show_in_navigation: bool = True

    class _ScheduleEntry(BaseModel):
        """One entry of the ``schedule`` device setting.

        A value left out (``None``) is not set by the entry: the device setting
        of the same name applies.
        """

        model_config = ConfigDict(extra="forbid")
        start: str
        end: str
        sound: bool
        brightness: int | None = Field(None, ge=0, le=100)
        brightness_dim: int | None = Field(None, ge=0, le=100)
        display_off: bool
        timeout_dimming: int | None = Field(None, ge=0, le=3600)
        timeout_display_off: int | None = Field(None, ge=0, le=3600)
        duration_dimming: float | None = Field(None, ge=0, le=5)
        start_offset: int = Field(0, ge=-720, le=720)
        end_offset: int = Field(0, ge=-720, le=720)

        @field_validator("start", "end")
        @classmethod
        def _time_or_sun_event(cls, v: str) -> str:
            try:
                parse_boundary(v)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"expected HH:MM or one of {list(SUN_EVENTS)}, got {v!r}") from exc
            return v

        @model_validator(mode="after")
        def _window_not_empty(self) -> _ScheduleEntry:
            same_offset = self.start not in SUN_EVENTS or self.start_offset == self.end_offset
            if self.start == self.end and same_offset:
                raise ValueError("a schedule entry's start and end must differ")
            return self

    class _Gesture(BaseModel):
        """One entry of the ``gestures`` device setting.

        ``action`` is a ``GestureAction`` or a panel key.  An unfinished entry
        is valid, so a draft with an entry just added can be saved: the gesture
        controller ignores an entry with no swipes or no action.
        """

        model_config = ConfigDict(extra="forbid")
        swipes: list[str]
        action: str
        timeframe: int = Field(ge=1, le=60)

        @field_validator("swipes")
        @classmethod
        def _known_gestures(cls, v: list[str]) -> list[str]:
            unknown = [g for g in v if g not in GESTURES]
            if unknown:
                raise ValueError(f"unknown gesture(s) {unknown}; use one of {list(GESTURES)}")
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
        brightness: int | None = Field(None, ge=0, le=100)
        brightness_dim: int | None = Field(None, ge=0, le=100)
        schedule: list[_ScheduleEntry] = Field(default_factory=list)
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
        # Fade time of the dimming transition, in seconds (the firmware's
        # "Duration Dimming" number).
        duration_dimming: float = Field(2.0, ge=0, le=5)
        log_level: str = "INFO"
        stale_data_seconds: int = Field(0, ge=0, le=86400)
        auto_navigate_home_timeout: int = Field(0, ge=0, le=86400)
        theme_variant: Literal["dark", "light"] = "dark"
        theme_id: str = "dark"
        gestures: list[_Gesture] = Field(
            default_factory=lambda: [_Gesture(**entry) for entry in DEVICE_CONFIG["gestures"]]
        )
        enabled: bool = True

        @model_validator(mode="after")
        def _schedule_needs_brightness(self) -> _DeviceConfig:
            if self.schedule and self.brightness is None:
                raise ValueError(
                    "a schedule needs the brightness setting: it is the brightness "
                    "outside the schedule's windows"
                )
            return self

        @field_validator("log_level")
        @classmethod
        def _validate_log_level(cls, v: Any) -> str:
            """Only standard logging levels are accepted; normalize to upper case."""
            if not isinstance(v, str) or v.upper() not in LOG_LEVEL_OPTIONS:
                raise ValueError(f"unsupported log level {v!r}; use one of {LOG_LEVEL_OPTIONS}")
            return v.upper()

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
    validated = model(**config)
    # A device that overrides the hub's update policy keeps its own policy
    # fields in its ``update`` block: they take the hub policy's ranges.
    update = config.get("update")
    if isinstance(update, dict):
        from .mapping.const import UPDATE_POLICY_FIELDS

        validate_update_policy({key: update[key] for key in UPDATE_POLICY_FIELDS if key in update})
    return validated


_UPDATE_POLICY_MODEL: type | None = None


def validate_update_policy(policy: dict) -> dict:
    """Validate the hub's automatic update policy and fill in its defaults.

    Args:
        policy: The stored or submitted policy; fields left out take
            ``UPDATE_POLICY_DEFAULTS``.

    Returns:
        The complete policy.

    Raises:
        ValueError: An unknown field, or a value out of its range.
    """
    global _UPDATE_POLICY_MODEL  # noqa: PLW0603

    from .mapping.const import UPDATE_POLICY_DEFAULTS

    if _UPDATE_POLICY_MODEL is None:
        from pydantic import BaseModel, ConfigDict, Field

        class _UpdatePolicy(BaseModel):
            model_config = ConfigDict(extra="forbid")
            firmware_auto_update: bool = UPDATE_POLICY_DEFAULTS["firmware_auto_update"]
            auto_install: bool = UPDATE_POLICY_DEFAULTS["auto_install"]
            install_delay: int = Field(UPDATE_POLICY_DEFAULTS["install_delay"], ge=0, le=86400)
            max_attempts: int = Field(UPDATE_POLICY_DEFAULTS["max_attempts"], ge=1, le=10)
            retry_interval: int = Field(UPDATE_POLICY_DEFAULTS["retry_interval"], ge=300, le=604800)

        _UPDATE_POLICY_MODEL = _UpdatePolicy
    return _UPDATE_POLICY_MODEL(**policy).model_dump()


class PanelValidationError(ValueError):
    """Saved panels break the option rules of their page type.

    ``errors`` lists every broken rule as ``{"device", "panel", "field",
    "kind", "message"}``; the message of the exception names the first one.
    """

    def __init__(self, errors: list[dict[str, str]]) -> None:
        first = errors[0]
        super().__init__(f"Panel {first['panel']}: {first['field']}: {first['message']}")
        self.errors = errors


def _stored_panels(previous: dict | None, device: str) -> dict[Any, Any]:
    """The panels ``previous`` holds for ``device``, by key."""
    if previous is None:
        return {}
    stored = previous.get("devices", {}).get(device, {}).get("panels", [])
    return {panel.get("key"): panel for panel in stored if isinstance(panel, dict)}


def _rule_errors(panels_data: dict, previous: dict | None) -> list[dict[str, str]]:
    """The broken option rules of every new or changed panel.

    A panel equal to the stored panel of the same key is skipped: a panel saved
    before a rule existed must not block saving the device's other panels.
    """
    from .mapping.panel import PANEL_MAPPING, POPUP_PANEL_MAPPING
    from .option_rules import panel_option_errors

    errors: list[dict[str, str]] = []
    for device, dev_data in panels_data.get("devices", {}).items():
        stored = _stored_panels(previous, device)
        for panel in dev_data.get("panels", []):
            if not isinstance(panel, dict) or panel.get("type") not in PANEL_MAPPING:
                continue
            key = panel.get("key")
            descriptor = PANEL_MAPPING[panel["type"]][1].DESCRIPTOR  # type: ignore[attr-defined]
            broken = panel_option_errors(panel, descriptor, popup=key in POPUP_PANEL_MAPPING)
            if broken and previous is not None and stored.get(key) == panel:
                _LOGGER.warning(
                    "Panel %s of %s breaks a rule but is unchanged, kept: %s",
                    key,
                    device,
                    broken[0].message,
                )
                continue
            errors += [
                {
                    "device": device,
                    "panel": str(key),
                    "field": error.field,
                    "kind": error.kind,
                    "message": error.message,
                }
                for error in broken
            ]
    return errors


def validate_panels(panels_data: dict, previous: dict | None = None) -> BaseModel:
    """Validate panel store data.

    Ensures the panels dict has valid panel definitions, that each device's
    ``config`` sub-object has correct field types, and that new or changed
    panels keep the option rules of their page type (``option_rules.py``).

    Args:
        panels_data: The store data to save (``{"devices": {name: {...}}}``).
        previous: The stored data the save replaces. A panel equal to its
            stored version is not checked against the option rules; ``None``
            checks every panel (an import).

    Raises:
        ValueError: A panel uses the key of a system panel that is not a popup;
            only popups can be edited.
        PanelValidationError: A new or changed panel breaks an option rule.
    """
    from .mapping.panel import SYS_PANEL_MAPPING

    all_panels = []
    for dev_data in panels_data.get("devices", {}).values():
        for panel in dev_data.get("panels", []):
            key = panel.get("key") if isinstance(panel, dict) else None
            if key in SYS_PANEL_MAPPING:
                raise ValueError(f"System panel {key} cannot be edited")
        all_panels.extend(dev_data.get("panels", []))
        if "config" in dev_data:
            validate_device_config(dev_data["config"])
    model = validate_config_model({"panels": all_panels})
    errors = _rule_errors(panels_data, previous)
    if errors:
        raise PanelValidationError(errors)
    return model

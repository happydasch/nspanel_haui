"""Optional pydantic v2 config validation for NSPanel HAUI.

Gracefully degrades to a no-op when pydantic is not installed.
"""

from __future__ import annotations

# Attempt to import pydantic for validation. If unavailable, use minimal stubs.
try:
    from pydantic import BaseModel, ConfigDict, Field, model_validator
except ImportError:  # pragma: no cover
    # Define lightweight fallbacks to allow the module to be imported without pydantic.
    class BaseModel:
        """A minimal stub mimicking pydantic.BaseModel for attribute storage."""

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __repr__(self):
            attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
            return f"{self.__class__.__name__}({attrs})"

    class ConfigDict(dict):
        pass

    def Field(default=None, *_, **kwargs):  # noqa: D401
        """Return a default value; accepts ``default_factory`` like pydantic's Field."""
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default

    def model_validator(mode=None):  # pragma: no cover
        def decorator(fn):
            return fn
        return decorator


__all__ = ["validate_config"]

_cache: dict[str, type[BaseModel] | None] = {}


def _get_model() -> type[BaseModel] | None:
    """Return the ConfigModel class, building and caching it on first call."""
    if "model" in _cache:
        return _cache["model"]

    try:

        class _PanelConfig(BaseModel):
            model_config = ConfigDict(extra="allow")
            type: str | None = None
            key: str | None = None
            mode: str = "panel"
            title: str | None = None

        class _ConfigModel(BaseModel):
            model_config = ConfigDict(extra="allow")
            panels: list[_PanelConfig] = Field(default_factory=list)
            sys_panels: list[_PanelConfig] = Field(default_factory=list)

            @model_validator(mode="before")
            @classmethod
            def _coerce_lists(cls, v):
                v.setdefault("panels", [])
                v.setdefault("sys_panels", [])
                return v

        _cache["model"] = _ConfigModel
    except ImportError:
        _cache["model"] = None

    return _cache["model"]


def validate_config(raw_cfg: dict) -> BaseModel | None:
    """Validate *raw_cfg* against the config schema.

    Returns the validated model instance, or None when pydantic is unavailable.
    """
    model = _get_model()
    if model is None:
        return None
    return model(**raw_cfg)

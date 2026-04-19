"""Optional pydantic v2 config validation for NSPanel HAUI.

Gracefully degrades to a no-op when pydantic is not installed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

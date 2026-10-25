"""Tests for the icon list endpoint used by the editor's icon picker."""

from __future__ import annotations

import asyncio
import sys
import types
from functools import wraps
from typing import Any


def _install_ha_stubs() -> None:
    """Install the HA modules api.py imports, mirroring tests/test_api.py's stubs."""
    http_mod = types.ModuleType("homeassistant.helpers.http")

    class HomeAssistantView:
        def json(self, result: Any, status_code: int = 200) -> dict:
            return {"status_code": status_code, "body": result}

    http_mod.HomeAssistantView = HomeAssistantView

    decorators_mod = types.ModuleType("homeassistant.components.http.decorators")

    def require_admin(func):
        @wraps(func)
        async def with_admin(self, request, *args, **kwargs):
            if not request["hass_user"].is_admin:
                raise sys.modules["homeassistant.exceptions"].Unauthorized()
            return await func(self, request, *args, **kwargs)

        return with_admin

    decorators_mod.require_admin = require_admin

    storage_mod = types.ModuleType("homeassistant.helpers.storage")
    storage_mod.Store = object

    for name, mod in {
        "homeassistant.helpers.http": http_mod,
        "homeassistant.components.http.decorators": decorators_mod,
        "homeassistant.helpers.storage": storage_mod,
    }.items():
        sys.modules.setdefault(name, mod)


_install_ha_stubs()

from nspanel_haui import api  # noqa: E402
from nspanel_haui.haui.mapping.icon_names import ICON_NAMES  # noqa: E402


class _Request(dict):
    def __init__(self, query: dict | None = None) -> None:
        super().__init__()
        self.query = query or {}


def _get_icons(query: dict | None = None) -> list[str]:
    return asyncio.run(api.IconSearchView().get(_Request(query)))["body"]


def test_icon_list_without_query_has_every_icon():
    """The picker filters this list client-side, so it must not be truncated."""
    icons = _get_icons()

    assert len(icons) == len(ICON_NAMES)
    assert "weather-sunny" in icons
    assert "wifi" in icons


def test_icon_query_returns_every_match():
    icons = _get_icons({"q": "O"})

    assert icons == [name for name in ICON_NAMES if "o" in name]

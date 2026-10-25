"""Tests for the diagnostics platform (diagnostics.py)."""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out the HA modules diagnostics.py imports at module level.
# ---------------------------------------------------------------------------


def _make_ha_stubs() -> None:
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object

    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    device_registry.DeviceEntry = object

    stubs = {
        "homeassistant.config_entries": config_entries,
        "homeassistant.helpers.device_registry": device_registry,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_make_ha_stubs()

from nspanel_haui import diagnostics as diag  # noqa: E402
from nspanel_haui.const import DOMAIN  # noqa: E402


def _connection_stub() -> MagicMock:
    class _State:
        def __str__(self) -> str:
            return "CONNECTED"

    connection = MagicMock()
    connection.is_connected = True  # property-like flag on the real controller
    connection.connection_state = _State()
    connection.last_connection_time = 1_700_000_000.0
    connection.last_disconnect_reason = None
    connection.disconnected_since = None
    return connection


def _app_stub(name: str = "Kitchen") -> MagicMock:
    app = MagicMock()
    app._runtime_device_name = name
    app.device_slug = "kitchen"
    app._ha_device_id = "esp123"
    app._last_panel_update = "2026-10-24T10:00:00"
    app.device_config.get.return_value = []
    app.controller = {"connection": _connection_stub(), "update": None}
    return app


def test_config_entry_diagnostics_snapshot() -> None:
    entry = MagicMock()
    entry.entry_id = "hub1"
    entry.as_dict.return_value = {"entry_id": "hub1", "data": {"name": "Hub"}}
    hass = MagicMock()
    hass.data = {DOMAIN: {"hub1": {"Kitchen": _app_stub()}}}

    result = asyncio.run(diag.async_get_config_entry_diagnostics(hass, entry))

    assert result["entry"]["entry_id"] == "hub1"
    assert len(result["devices"]) == 1
    device = result["devices"][0]
    assert device["device"] == "Kitchen"
    assert device["ha_device_id"] == "esp123"
    assert device["connection"]["connected"] is True
    assert device["connection"]["state"] == "CONNECTED"
    assert device["panels"] == 0


def test_config_entry_diagnostics_unknown_entry_is_empty() -> None:
    entry = MagicMock()
    entry.entry_id = "missing"
    hass = MagicMock()
    hass.data = {DOMAIN: {}}

    result = asyncio.run(diag.async_get_config_entry_diagnostics(hass, entry))
    assert result["devices"] == []


def test_device_diagnostics_matches_by_identifier() -> None:
    entry = MagicMock()
    entry.entry_id = "hub1"
    device = MagicMock()
    device.identifiers = {("nspanel_haui", "Kitchen")}
    hass = MagicMock()
    hass.data = {DOMAIN: {"hub1": {"Kitchen": _app_stub()}}}

    result = asyncio.run(diag.async_get_device_diagnostics(hass, entry, device))
    assert result["device_name"] == "Kitchen"


def test_device_diagnostics_unknown_device() -> None:
    entry = MagicMock()
    entry.entry_id = "hub1"
    device = MagicMock()
    device.identifiers = {("nspanel_haui", "Other")}
    hass = MagicMock()
    hass.data = {DOMAIN: {"hub1": {"Kitchen": _app_stub()}}}

    result: dict[str, Any] = asyncio.run(diag.async_get_device_diagnostics(hass, entry, device))
    assert result["device"]["linked"] is False

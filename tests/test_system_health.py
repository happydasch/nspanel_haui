"""Tests for the system_health platform (system_health.py)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from nspanel_haui import system_health as sh


def _app_stub(connected: bool) -> MagicMock:
    app = MagicMock()
    app._runtime_device_name = "Kitchen"
    connection = MagicMock()
    connection.is_connected = connected
    app.controller = {"connection": connection}
    return app


def test_system_health_counts_devices_and_connections() -> None:
    hass = MagicMock()
    hass.data = {
        "nspanel_haui": {
            "hub1": {
                "Kitchen": _app_stub(True),
                "Living room": _app_stub(False),
            }
        }
    }
    integration = MagicMock()
    integration.version = "0.4.0"
    with patch(
        "nspanel_haui.system_health.async_get_loaded_integration",
        new=AsyncMock(return_value=integration),
    ):
        result = asyncio.run(sh.async_system_health_info(hass))

    assert result["version"] == "0.4.0"
    assert result["hubs"] == 1
    assert result["configured_devices"] == 2
    assert result["connected_devices"] == 1


def test_system_health_without_hub() -> None:
    hass = MagicMock()
    hass.data = {}
    integration = MagicMock()
    integration.version = "0.4.0"
    with patch(
        "nspanel_haui.system_health.async_get_loaded_integration",
        new=AsyncMock(return_value=integration),
    ):
        result: dict[str, Any] = asyncio.run(sh.async_system_health_info(hass))

    assert result["version"] == "0.4.0"
    assert result["hubs"] == 0
    assert "setup_state" in result

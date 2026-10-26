"""Provide info to the Home Assistant System Health platform."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import async_get_loaded_integration

from .const import DOMAIN

MANAGE_URL = "/config/integrations/integration/nspanel_haui"


@callback
def async_register(
    hass: HomeAssistant,
    register: Any,  # system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(async_system_health_info, MANAGE_URL)


async def async_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the System page."""
    integration = await async_get_loaded_integration(hass, DOMAIN)  # type: ignore[misc]
    apps = hass.data.get(DOMAIN, {})

    devices: list[str] = []
    connected = 0
    for entry_apps in apps.values():
        for _name, app in entry_apps.items():
            devices.append(app._runtime_device_name)
            connection = app.controller.get("connection")
            if connection is not None and connection.is_connected:
                connected += 1

    data: dict[str, Any] = {
        "version": f"{integration.version}",
        "hubs": len(apps),
        "configured_devices": len(devices),
        "connected_devices": connected,
    }
    if not apps:
        data["setup_state"] = "not_loaded (no config entries)"
    return data

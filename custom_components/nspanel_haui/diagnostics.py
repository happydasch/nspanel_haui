"""Diagnostics support for NSPanel HAUI."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN


def _app_snapshot(app: Any) -> dict[str, Any]:
    """Return a diagnostics snapshot for one running app instance.

    ``app`` is a :class:`~.nspanel_haui.NSPanelHAUI` instance.  Values are
    read synchronously from app state; the app runs on its own worker thread,
    so this is a best-effort snapshot (acceptable for diagnostics).
    """
    connection = app.controller.get("connection")
    update = app.controller.get("update")

    update_state: dict[str, Any] | None = None
    if update is not None:
        update_state = {
            "state": getattr(update, "_update_state", None),
            "version": getattr(update, "_update_version", None),
            "interval": getattr(update, "_interval", None),
        }

    return {
        "device_name": app._runtime_device_name,
        "device_slug": app.device_slug,
        "ha_device_id": app._ha_device_id,
        "last_panel_update": app._last_panel_update,
        "panels": len(app.device_config.get("panels", [])),
        "connection": {
            "connected": bool(connection is not None and connection.is_connected),
            "state": str(connection.connection_state) if connection is not None else None,
            "last_connection_time": (
                connection.last_connection_time if connection is not None else None
            ),
            "last_disconnect_reason": (
                connection.last_disconnect_reason if connection is not None else None
            ),
            "disconnected_since": (
                connection.disconnected_since if connection is not None else None
            ),
        },
        "update": update_state,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    apps = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    data: dict[str, Any] = {
        "entry": entry.as_dict(),
        "devices": [{"device": name, **_app_snapshot(app)} for name, app in apps.items()],
    }

    return data


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    apps = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    for name, app in apps.items():
        if any(
            identifier[0] == DOMAIN and identifier[1] == name
            for identifier in device.identifiers
        ):
            return _app_snapshot(app)
    return {
        "device": {
            "name": next(iter(device.identifiers))[1] if device.identifiers else "",
            "linked": False,
        }
    }

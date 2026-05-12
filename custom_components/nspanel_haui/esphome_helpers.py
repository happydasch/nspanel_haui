"""ESPHome device discovery and matching helpers."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ESPHome project.name substring that identifies HAUI firmware
_HAUI_MODEL = "nspanel_haui"

# ESPHome custom services that identify HAUI firmware (service-based fallback)
_HAUI_SERVICES: frozenset[str] = frozenset({
    "haui_discover",
    "send_command",
    "send_commands",
    "goto_page",
    "upload_tft_url",
    "set_brightness",
})


def normalize_device_name(name: str) -> str:
    """Normalize a device name for fuzzy comparison."""
    return name.lower().strip().replace("_", " ").replace("-", " ")


def find_esphome_device(hass, device_name: str) -> str | None:
    """Match NSPanel device name to ESPHome device entry using normalized comparison.

    Returns the entry_id string, or None when no match is found.
    """
    normalized_device_name = normalize_device_name(device_name)

    # Primary path: esphome integration stores entries in hass.data
    try:
        esphome_data = hass.data.get("esphome", {})
        if esphome_data:
            # Handle both dict and DomainData (HA 2024.x+)
            if not isinstance(esphome_data, dict):
                esphome_data = dict(esphome_data)
            for entry_id, entry_data in esphome_data.items():
                if not isinstance(entry_data, dict):
                    continue
                device_info = entry_data.get("device_info", {})
                if isinstance(device_info, dict):
                    # Match by name (normalized)
                    info_name = device_info.get("name", "")
                    if normalize_device_name(info_name) == normalized_device_name:
                        return entry_id
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("Error in find_esphome_device primary lookup", exc_info=True)

    # Fallback: scan entity registry for esphome platform entities
    try:
        from homeassistant.helpers import entity_registry

        er = entity_registry.async_get(hass)
        for entity in er.entities.values():
            if entity.platform == "esphome":
                if normalized_device_name in normalize_device_name(entity.name or ""):
                    return None  # confirmed match, entry_id not available
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("Error in find_esphome_device fallback lookup", exc_info=True)

    return None


def is_haui_device(hass: Any, entry: Any) -> bool:
    """Check whether an ESPHome config entry has HAUI firmware.

    Uses three strategies, checked in order:
    1. Model check: inspect ``entry.runtime_data.device_info.model`` for ``"nspanel_haui"``.
    2. Service check: inspect ``entry.runtime_data.services`` for HAUI-specific actions.
    3. Service registry fallback: check the HA service registry for HAUI-specific names.
    """
    # Strategy 1: ESPHome model (most definitive, available when device was ever online)
    try:
        if entry.runtime_data and hasattr(entry.runtime_data, "device_info"):
            di = entry.runtime_data.device_info
            if di and hasattr(di, "model") and di.model and _HAUI_MODEL in di.model:
                return True
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device model check failed", exc_info=True)

    # Strategy 2: runtime_data services (device is online / has been connected)
    try:
        if entry.runtime_data and hasattr(entry.runtime_data, "services"):
            for svc in entry.runtime_data.services.values():
                if hasattr(svc, "name") and svc.name in _HAUI_SERVICES:
                    return True
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device service check failed", exc_info=True)

    # Strategy 3: HA service registry (services persist after disconnect)
    try:
        device_name: str = entry.data.get("device_name", "")
        if device_name:
            # ESPHome's build_service_name() replaces hyphens with underscores,
            # so we must sanitize before matching against registered services.
            sanitized = device_name.lower().replace("-", "_")
            esphome_services = hass.services.async_services().get("esphome", {})
            for svc_name in esphome_services:
                if svc_name.startswith(f"{sanitized}_") and any(
                    svc_name.endswith(f"_{s}") for s in _HAUI_SERVICES
                ):
                    return True
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device service registry check failed", exc_info=True)

    return False


def resolve_ha_device_id(hass: Any, node_name: str) -> str | None:
    """Map an ESPHome node name to Home Assistant device registry id.

    Args:
        hass: Home Assistant core instance.
        node_name: The ESPHome node name (entry.data["device_name"]).

    Returns:
        Device registry UUID string, or ``None`` if the device is not
        yet registered (e.g. ESPHome integration has not finished loading).
    """
    sanitized = normalize_device_name(node_name)
    if not sanitized:
        return None

    try:
        from homeassistant.helpers import device_registry as dr
    except ImportError:
        return None

    for entry in hass.config_entries.async_entries("esphome"):
        dev_name = entry.data.get("device_name", "")
        if normalize_device_name(dev_name) == sanitized:
            dev_reg = dr.async_get(hass)
            for dev_entry in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
                return dev_entry.id
            break

    return None


async def discover_esphome_devices(hass: Any) -> list[dict]:
    """Discover NSPanel devices via ESPHome config entries.

    Only returns devices confirmed to have HAUI firmware installed.
    Iterates ESPHome config entries and returns a list of device dicts with
    ``name`` and ``esphome_device_id`` keys.
    """
    devices: list[dict] = []
    for entry in hass.config_entries.async_entries("esphome"):
        if not is_haui_device(hass, entry):
            continue
        device = entry.data.get("device") or entry.data
        # Real ESPHome node name lives in entry.data["device_name"].
        # entry.title is the display/friendly name and must not be used as identity.
        name = entry.data.get("device_name") or (
            device.get("name") if isinstance(device, dict) else None
        )
        devices.append(
            {
                "name": name or entry.title or entry.entry_id,
                "esphome_device_id": entry.entry_id,
            }
        )
    return devices

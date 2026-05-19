"""ESPHome device discovery and matching helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Identifiers for HAUI firmware.
# The ESPHome YAML sets ``esphome.project.name: happydasch.nspanel_haui``.
# The ESPHome integration splits this into manufacturer/model on the HA
# device registry entry, so a registry-based check works offline and is
# our most reliable detection method.
_HAUI_PROJECT_NAME = "happydasch.nspanel_haui"
_HAUI_MANUFACTURER = "happydasch"
_HAUI_MODEL = "nspanel_haui"

# ESPHome custom services that identify HAUI firmware (service-based fallback)
_HAUI_SERVICES: frozenset[str] = frozenset(
    {
        "haui_discover",
        "send_command",
        "send_commands",
        "goto_page",
        "upload_tft_url",
        "set_brightness",
    }
)


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

    Strategies, in order of reliability:
    1. HA device registry: any device tied to the entry with manufacturer
       ``happydasch`` and model ``nspanel_haui``. The ESPHome integration
       writes these from ``device_info.project_name`` and they persist
       across HA restarts even when the device is offline.
    2. ``entry.runtime_data.device_info`` (only populated while the device
       is connected via the ESPHome API).
    3. ``entry.runtime_data.services`` for HAUI-specific custom actions.
    4. HA service registry (services persist after disconnect).
    """
    # Strategy 1: device registry — authoritative, works offline.
    try:
        from homeassistant.helpers import device_registry as dr

        dev_reg = dr.async_get(hass)
        entry_id = getattr(entry, "entry_id", None)
        if entry_id:
            for dev_entry in dr.async_entries_for_config_entry(dev_reg, entry_id):
                mfg = (dev_entry.manufacturer or "").lower()
                model = (dev_entry.model or "").lower()
                if mfg == _HAUI_MANUFACTURER and _HAUI_MODEL in model:
                    return True
    except (ImportError, AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device device registry check failed", exc_info=True)

    # Strategy 2: ESPHome runtime device_info (device currently online).
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is not None:
        try:
            if hasattr(runtime_data, "device_info"):
                di = runtime_data.device_info
                if di is not None:
                    if (
                        hasattr(di, "project_name")
                        and di.project_name
                        and _HAUI_MODEL in di.project_name
                    ):
                        return True
                    if hasattr(di, "model") and di.model and _HAUI_MODEL in di.model:
                        return True
        except (AttributeError, KeyError, TypeError):
            _LOGGER.debug("is_haui_device device_info check failed", exc_info=True)

        # Strategy 3: runtime_data services.
        try:
            if hasattr(runtime_data, "services"):
                for svc in runtime_data.services.values():
                    if hasattr(svc, "name") and svc.name in _HAUI_SERVICES:
                        return True
        except (AttributeError, KeyError, TypeError):
            _LOGGER.debug("is_haui_device service check failed", exc_info=True)

    # Strategy 4: HA service registry.
    try:
        device_name: str = entry.data.get("device_name", "")
        if device_name:
            sanitized = device_name.lower().replace("-", "_")
            esphome_services = hass.services.async_services().get("esphome", {})
            for svc_name in esphome_services:
                if svc_name.startswith(f"{sanitized}_") and any(
                    svc_name.endswith(f"_{s}") for s in _HAUI_SERVICES
                ):
                    return True
    except (AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device service registry check failed", exc_info=True)

    # Strategy 5: entity registry — look up entities tied to this config
    # entry and check if their device registry entry has HAUI identifiers.
    # Entity + device registry entries persist across HA restarts (stored
    # in the HA database), so this works for devices that have connected at
    # least once in the past but are currently offline.
    try:
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(hass)
        entry_id = getattr(entry, "entry_id", None)
        if entry_id:
            dev_reg = dr.async_get(hass)
            for ent in ent_reg.entities.values():
                if ent.config_entry_id != entry_id:
                    continue
                if not ent.device_id:
                    continue
                dev = dev_reg.async_get(ent.device_id)
                if not dev:
                    continue
                mfg = (dev.manufacturer or "").lower()
                model = (dev.model or "").lower()
                if mfg == _HAUI_MANUFACTURER and _HAUI_MODEL in model:
                    return True
    except (ImportError, AttributeError, KeyError, TypeError):
        _LOGGER.debug("is_haui_device entity registry check failed", exc_info=True)

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


async def discover_esphome_devices(hass: Any, *, _is_retry: bool = False) -> list[dict]:
    """Discover NSPanel devices via ESPHome config entries.

    Only returns devices confirmed to have HAUI firmware installed.
    Iterates ESPHome config entries and returns a list of device dicts with
    ``name`` and ``esphome_device_id`` keys.

    Retries once after a short delay if no devices are found and this is
    the first call (services may not be registered yet at startup).
    """
    devices: list[dict] = []
    for entry in hass.config_entries.async_entries("esphome"):
        if not is_haui_device(hass, entry):
            continue
        device = entry.data.get("device") or entry.data
        name = entry.data.get("device_name") or (
            device.get("name") if isinstance(device, dict) else None
        )
        devices.append(
            {
                "name": name or entry.title or entry.entry_id,
                "friendly_name": entry.title or name or entry.entry_id,
                "esphome_device_id": entry.entry_id,
            }
        )

    if not devices and not _is_retry:
        # Only retry if there are ESPHome entries to scan — a retry when
        # no entries exist at all is pointless and slow.
        if hass.config_entries.async_entries("esphome"):
            _LOGGER.debug(
                "discover_esphome_devices: %d ESPHome entries but no HAUI matches "
                "on first pass, retrying after 5s delay",
                len(hass.config_entries.async_entries("esphome")),
            )
            await asyncio.sleep(5)
        return await discover_esphome_devices(hass, _is_retry=True)

    _LOGGER.debug("discover_esphome_devices: %d HAUI device(s)", len(devices))
    return devices

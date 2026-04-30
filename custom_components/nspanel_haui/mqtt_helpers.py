"""MQTT discovery and ESPHome device matching helpers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

MQTT_DISCOVERY_TIMEOUT = 5  # seconds


def normalize_device_name(name: str) -> str:
    """Normalize a device name for fuzzy comparison."""
    return name.lower().strip().replace("_", " ").replace("-", " ")


def find_esphome_device(hass, device_name: str) -> str | None:
    """Match NSPanel device name to ESPHome device entry using normalized comparison.

    Returns the ESPHome config entry ID if matched, or None.
    """
    normalized_mqtt = normalize_device_name(device_name)

    # Primary path: esphome integration stores entries in hass.data
    try:
        esphome_data = hass.data.get("esphome", {})
        if esphome_data:
            for entry_id, entry_data in esphome_data.items():
                if not isinstance(entry_data, dict):
                    continue
                device_info = entry_data.get("device_info", {})
                if isinstance(device_info, dict):
                    # Match by name (normalized)
                    info_name = device_info.get("name", "")
                    if normalize_device_name(info_name) == normalized_mqtt:
                        return entry_id

                    # Also match by friendly_name
                    friendly = device_info.get("friendly_name", "")
                    if friendly and normalize_device_name(friendly) == normalized_mqtt:
                        return entry_id
    except Exception:
        _LOGGER.debug("Error in find_esphome_device primary lookup", exc_info=True)

    # Fallback: scan entity registry for esphome platform entities
    try:
        from homeassistant.helpers import entity_registry

        er = entity_registry.async_get(hass)
        for entity in er.entities.values():
            if entity.platform == "esphome":
                if normalized_mqtt in normalize_device_name(entity.name or ""):
                    return None  # confirmed match, entry_id not available
    except Exception:
        _LOGGER.debug("Error in find_esphome_device fallback lookup", exc_info=True)

    return None


async def mqtt_available(hass: Any) -> bool:
    """Check whether MQTT integration is available and connected."""
    try:
        return mqtt.is_connected(hass)
    except Exception:
        return False


async def run_mqtt_discovery(
    hass: Any,
    prefix: str = "nspanel_haui",
    timeout: int = MQTT_DISCOVERY_TIMEOUT,
) -> list[dict]:
    """Subscribe to all NSPanel recv topics; collect device names + ESPHome matches."""
    found: set[str] = set()

    try:
        async def _on_message(msg: Any) -> None:
            try:
                data = json.loads(msg.payload)
                if data.get("name") == "connected":
                    parts = msg.topic.split("/")
                    if len(parts) == 3:
                        found.add(parts[1])
            except (json.JSONDecodeError, ValueError):
                pass

        unsub = await mqtt.async_subscribe(hass, f"{prefix}/+/recv", _on_message)

        # Poll in short intervals for responsiveness
        poll_interval = 0.5
        steps = int(timeout / poll_interval)
        for _ in range(steps):
            await asyncio.sleep(poll_interval)
            # Early exit: once we have devices, listen briefly for more then stop
            if found and steps > 0:
                pass

        unsub()
    except Exception as exc:
        _LOGGER.debug("MQTT discovery error: %s", exc, exc_info=True)

    # Enrich with ESPHome device matches
    result: list[dict] = []
    for name in sorted(found):
        result.append({
            "name": name,
            "esphome_device_id": find_esphome_device(hass, name),
        })
    return result

"""Lights of the hardware buttons drawn below a preview's screen.

Each button shows its relay; a button that switches an entity instead (relay
mode off and ``button_<side>_entity`` set) also shows that entity's state.
The sandbox (``virtual_panel.py``) reads the simulated states, the live
preview (``live_panel.py``) the real ones.
"""

from __future__ import annotations

from typing import Any

# The firmware's relay switches (esphome/nspanel_haui/switch.yaml).
RELAY_ENTITY_NAMES: dict[str, str] = {"left": "Relay Left", "right": "Relay Right"}

# ("relay" | "entity", side)
ButtonLight = tuple[str, str]


def button_entity_ids(device: Any) -> dict[ButtonLight, str | None]:
    """The entity each light shows, None for no light.

    Runs on the device's app worker: it resolves the ESPHome relay entities.
    """
    entity_ids: dict[ButtonLight, str | None] = {}
    for side, relay_name in RELAY_ENTITY_NAMES.items():
        entity_ids[("relay", side)] = device.find_esphome_entity_id("switch", relay_name)
        entity = None
        if not device.get(f"use_relay_{side}", True):
            entity = device.get(f"button_{side}_entity", None) or None
        entity_ids[("entity", side)] = entity
    return entity_ids


def light_state(state: Any, attributes: dict[str, Any] | None, entity_id: str) -> str:
    """Show a button entity as on or off, whatever its domain."""
    if state is None or state in ("unknown", "unavailable"):
        return "unknown"
    domain = entity_id.split(".", 1)[0]
    if domain == "cover":
        position = (attributes or {}).get("current_position")
        if isinstance(position, (int, float)) and not isinstance(position, bool):
            return "on" if position > 0 else "off"
        return "off" if state == "closed" else "on"
    if domain == "lock":
        return "on" if state in ("unlocked", "unlocking", "open", "opening") else "off"
    if domain == "climate":
        return "off" if state == "off" else "on"
    if domain == "alarm_control_panel":
        return "off" if state == "disarmed" else "on"
    if domain == "vacuum":
        return "off" if state in ("docked", "idle", "paused") else "on"
    if domain == "media_player":
        return "on" if state == "playing" else "off"
    if domain == "timer":
        return "on" if state == "active" else "off"
    if state == "on" or state is True or state == 1:
        return "on"
    if state == "off" or state is False or state == 0:
        return "off"
    return "unknown"


def lights_message(states: dict[ButtonLight, str]) -> dict[str, Any]:
    """The browser message with every light's state."""
    return {
        "type": "relays",
        "left": states.get(("relay", "left"), "unknown"),
        "right": states.get(("relay", "right"), "unknown"),
        # None: the button switches its relay, so it has no entity light.
        "entities": {side: states.get(("entity", side)) for side in RELAY_ENTITY_NAMES},
    }

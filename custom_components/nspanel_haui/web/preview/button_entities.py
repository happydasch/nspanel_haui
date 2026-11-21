"""The hardware buttons of the panel, as a preview's frame draws them.

Each of the panel's two hardware buttons switches its built-in relay, or - with
relay mode off and ``button_<side>_entity`` set - an entity of any domain. A
preview draws both under the screen: the button's light shows the entity it
switches, and a button that switches an entity also shows its relay as a small
dot, so the relay's own state stays visible.

``button_entity_ids`` says which entities those are, ``button_state`` what a
light shows for one, and ``buttons_message`` is the browser's whole view of the
two buttons: each button's entities and their states, in one message. The
sandbox (``virtual_panel.py``) reads simulated states; the live preview
(``live_panel.py`) and a dashboard card's frame read the real ones through
``ButtonEntities``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# The firmware's relay switches (esphome/nspanel_haui/switch.yaml).
RELAY_ENTITY_NAMES: dict[str, str] = {"left": "Relay Left", "right": "Relay Right"}
BUTTON_SIDES: tuple[str, ...] = tuple(RELAY_ENTITY_NAMES)

# ("relay" | "entity", side): the panel's own relay switch, or the entity a
# button switches in its place when relay mode is off.
ButtonSlot = tuple[str, str]


def button_entity_ids(device: Any) -> dict[ButtonSlot, str | None]:
    """The entity behind each of the panel's hardware buttons, None for none.

    Runs on the device's app worker: it resolves the ESPHome relay entities.
    """
    entity_ids: dict[ButtonSlot, str | None] = {}
    for side, relay_name in RELAY_ENTITY_NAMES.items():
        entity_ids[("relay", side)] = device.find_esphome_entity_id("switch", relay_name)
        entity = None
        if not device.get(f"use_relay_{side}", True):
            entity = device.get(f"button_{side}_entity", None) or None
        entity_ids[("entity", side)] = entity
    return entity_ids


def button_state(state: Any, attributes: dict[str, Any] | None, entity_id: str) -> str:
    """What a button's light shows for this entity: on or off, whatever its domain."""
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


def buttons_message(
    entity_ids: dict[ButtonSlot, str], states: dict[ButtonSlot, str]
) -> dict[str, Any]:
    """The browser's view of the hardware buttons: their entities and their lights.

    A press switches the button's entity when one is set without relay mode
    (``HAUIDevice._toggle_button_state``), otherwise its relay. ``entity`` is
    that entity, None in relay mode; ``state`` is what the light shows, and
    ``relay_state`` the relay's own state (the dot beside the light).
    """
    message: dict[str, Any] = {"type": "buttons"}
    for side in BUTTON_SIDES:
        relay_state = states.get(("relay", side), "unknown")
        entity_state = states.get(("entity", side))
        message[side] = {
            "relay": entity_ids.get(("relay", side)),
            "entity": entity_ids.get(("entity", side)),
            "state": relay_state if entity_state is None else entity_state,
            "relay_state": relay_state,
        }
    return message


class ButtonEntities:
    """The entities of one device's hardware buttons, from real Home Assistant states.

    The live preview and a dashboard card's frame both draw the buttons, so a
    device tracks its button entities once and every watcher reads the same
    message. A save re-tracks them on the new settings (``track`` with the
    result of ``button_entity_ids``).

    Runs on the event loop; the sink must be safe to call from anywhere.
    """

    def __init__(self, hass: Any, sink: Callable[[dict[str, Any]], None]) -> None:
        """
        Args:
            hass: Home Assistant core; its state events drive the buttons.
            sink: receives the ``buttons`` message.
        """
        self._hass = hass
        self._sink = sink
        self._untrack: Callable[[], None] | None = None
        self._entities: dict[ButtonSlot, str] = {}
        self._states: dict[ButtonSlot, str] = {}

    def track(self, entity_ids: dict[ButtonSlot, str | None]) -> None:
        """Follow these entities from now on; a side without one has no light."""
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_state_change_event

        self.stop()
        self._entities = {key: entity_id for key, entity_id in entity_ids.items() if entity_id}
        self._states = {key: self._state_of(eid) for key, eid in self._entities.items()}
        self._sink(buttons_message(self._entities, self._states))
        if not self._entities:
            return

        @callback
        def _changed(event: Any) -> None:
            entity_id = event.data["entity_id"]
            for key, tracked in self._entities.items():
                if tracked == entity_id:
                    self._states[key] = self._state_of(tracked)
            self._sink(buttons_message(self._entities, self._states))

        self._untrack = async_track_state_change_event(
            self._hass, sorted(set(self._entities.values())), _changed
        )

    def stop(self) -> None:
        """Release the state listeners and forget the tracked entities."""
        if self._untrack is not None:
            self._untrack()
            self._untrack = None
        self._entities = {}
        self._states = {}

    def _state_of(self, entity_id: str) -> str:
        state = self._hass.states.get(entity_id)
        if state is None:
            return button_state(None, None, entity_id)
        return button_state(state.state, dict(state.attributes), entity_id)

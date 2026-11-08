"""Simulated entity state for the virtual panel's sandbox mode.

A sandbox lays simulated states over Home Assistant's real ones: a read
returns the simulated state when there is one and the real state otherwise,
and a simulated service call changes only the simulated state. Touching a
light tile in the editor's live preview then shows the panel reacting without
switching the real light.

Only the common entity services are simulated (on/off, light brightness and
colour, cover position, climate setpoints and modes, media playback, locks,
alarm panels, vacuums, number/select/text values, timers). Any other service
leaves the state untouched; ``apply`` reports it so the caller can log it.
"""

from __future__ import annotations

import copy
import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimState:
    """One entity's simulated state, shaped like a Home Assistant ``State``."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


# Reads the real state of an entity: ``(state, attributes)`` or ``None``.
RealStateReader = Callable[[str], tuple[str, dict[str, Any]] | None]
Handler = Callable[[SimState, dict[str, Any]], SimState | None]

_ON_OFF_DOMAINS = frozenset(
    {
        "light",
        "switch",
        "fan",
        "input_boolean",
        "automation",
        "siren",
        "humidifier",
        "remote",
        "media_player",
        "climate",
        "water_heater",
    }
)

_ALARM_STATES = {
    "alarm_disarm": "disarmed",
    "alarm_arm_home": "armed_home",
    "alarm_arm_away": "armed_away",
    "alarm_arm_night": "armed_night",
    "alarm_arm_vacation": "armed_vacation",
    "alarm_arm_custom_bypass": "armed_custom_bypass",
    "alarm_trigger": "triggered",
}


def _changed(cur: SimState, state: str | None = None, **attrs: Any) -> SimState:
    attributes = dict(cur.attributes)
    for key, value in attrs.items():
        if value is None:
            attributes.pop(key, None)
        else:
            attributes[key] = value
    return SimState(cur.entity_id, cur.state if state is None else state, attributes)


def _climate_on_mode(cur: SimState) -> str:
    modes = [m for m in cur.attributes.get("hvac_modes", []) if m != "off"]
    return modes[0] if modes else "heat"


def _turn_on(cur: SimState, data: dict[str, Any]) -> SimState:
    domain = cur.entity_id.split(".", 1)[0]
    if domain == "climate":
        return _changed(cur, _climate_on_mode(cur))
    attrs: dict[str, Any] = {}
    if domain == "light":
        if "brightness_pct" in data:
            attrs["brightness"] = round(float(data["brightness_pct"]) * 255 / 100)
        elif "brightness" in data:
            attrs["brightness"] = int(data["brightness"])
        elif cur.attributes.get("brightness") is None:
            attrs["brightness"] = 255
        for key in ("rgb_color", "hs_color", "xy_color", "effect"):
            if key in data:
                attrs[key] = data[key]
        kelvin = data.get("color_temp_kelvin", data.get("kelvin"))
        if kelvin is not None:
            attrs["color_temp_kelvin"] = int(kelvin)
    elif domain == "fan" and "percentage" in data:
        attrs["percentage"] = int(data["percentage"])
    return _changed(cur, "on", **attrs)


def _turn_off(cur: SimState, data: dict[str, Any]) -> SimState:
    if cur.entity_id.startswith("light."):
        return _changed(cur, "off", brightness=None)
    return _changed(cur, "off")


def _toggle(cur: SimState, data: dict[str, Any]) -> SimState:
    domain = cur.entity_id.split(".", 1)[0]
    if domain == "cover":
        return _set_cover_position(cur, {"position": 0 if cur.state == "open" else 100})
    if domain == "lock":
        return _changed(cur, "unlocked" if cur.state == "locked" else "locked")
    if cur.state in ("off", "unavailable", "unknown"):
        return _turn_on(cur, data)
    return _turn_off(cur, data)


def _set_cover_position(cur: SimState, data: dict[str, Any]) -> SimState:
    position = int(data["position"])
    return _changed(cur, "open" if position > 0 else "closed", current_position=position)


def _set_temperature(cur: SimState, data: dict[str, Any]) -> SimState:
    attrs = {
        key: data[key]
        for key in ("temperature", "target_temp_low", "target_temp_high")
        if key in data
    }
    return _changed(cur, data.get("hvac_mode"), **attrs)


def _media_play_pause(cur: SimState, data: dict[str, Any]) -> SimState:
    return _changed(cur, "paused" if cur.state == "playing" else "playing")


def _select_step(step: int) -> Handler:
    def _handler(cur: SimState, data: dict[str, Any]) -> SimState:
        options = list(cur.attributes.get("options", []))
        if not options:
            return cur
        idx = options.index(cur.state) if cur.state in options else -step
        return _changed(cur, options[(idx + step) % len(options)])

    return _handler


def _set_state(state: str) -> Handler:
    return lambda cur, data: _changed(cur, state)


def _set_attr(attr: str, key: str) -> Handler:
    return lambda cur, data: _changed(cur, **{attr: data[key]})


def _value_to_state(key: str) -> Handler:
    return lambda cur, data: _changed(cur, str(data[key]))


def _pressed(cur: SimState, data: dict[str, Any]) -> SimState:
    return _changed(cur, datetime.datetime.now(datetime.UTC).isoformat())


def _unchanged(cur: SimState, data: dict[str, Any]) -> SimState:
    return cur


# (domain, service) -> handler; domain "*" applies to every on/off domain.
_HANDLERS: dict[tuple[str, str], Handler] = {
    ("*", "turn_on"): _turn_on,
    ("*", "turn_off"): _turn_off,
    ("*", "toggle"): _toggle,
    ("fan", "set_percentage"): lambda cur, data: _changed(
        cur, "on" if int(data["percentage"]) > 0 else "off", percentage=int(data["percentage"])
    ),
    ("fan", "set_preset_mode"): _set_attr("preset_mode", "preset_mode"),
    ("fan", "oscillate"): _set_attr("oscillating", "oscillating"),
    ("fan", "set_direction"): _set_attr("direction", "direction"),
    ("cover", "open_cover"): lambda cur, data: _set_cover_position(cur, {"position": 100}),
    ("cover", "close_cover"): lambda cur, data: _set_cover_position(cur, {"position": 0}),
    ("cover", "stop_cover"): _unchanged,
    ("cover", "toggle"): _toggle,
    ("cover", "set_cover_position"): _set_cover_position,
    ("cover", "set_cover_tilt_position"): _set_attr("current_tilt_position", "tilt_position"),
    ("cover", "open_cover_tilt"): lambda cur, data: _changed(cur, current_tilt_position=100),
    ("cover", "close_cover_tilt"): lambda cur, data: _changed(cur, current_tilt_position=0),
    ("climate", "set_temperature"): _set_temperature,
    ("climate", "set_hvac_mode"): _value_to_state("hvac_mode"),
    ("climate", "set_fan_mode"): _set_attr("fan_mode", "fan_mode"),
    ("climate", "set_preset_mode"): _set_attr("preset_mode", "preset_mode"),
    ("climate", "set_swing_mode"): _set_attr("swing_mode", "swing_mode"),
    ("climate", "set_humidity"): _set_attr("humidity", "humidity"),
    ("media_player", "media_play"): _set_state("playing"),
    ("media_player", "media_pause"): _set_state("paused"),
    ("media_player", "media_play_pause"): _media_play_pause,
    ("media_player", "media_stop"): _set_state("idle"),
    ("media_player", "media_next_track"): _unchanged,
    ("media_player", "media_previous_track"): _unchanged,
    ("media_player", "volume_set"): _set_attr("volume_level", "volume_level"),
    ("media_player", "volume_mute"): _set_attr("is_volume_muted", "is_volume_muted"),
    ("media_player", "select_source"): _set_attr("source", "source"),
    ("media_player", "shuffle_set"): _set_attr("shuffle", "shuffle"),
    ("media_player", "repeat_set"): _set_attr("repeat", "repeat"),
    ("lock", "lock"): _set_state("locked"),
    ("lock", "unlock"): _set_state("unlocked"),
    ("lock", "open"): _set_state("open"),
    **{("alarm_control_panel", svc): _set_state(st) for svc, st in _ALARM_STATES.items()},
    ("vacuum", "start"): _set_state("cleaning"),
    ("vacuum", "pause"): _set_state("paused"),
    ("vacuum", "stop"): _set_state("idle"),
    ("vacuum", "return_to_base"): _set_state("returning"),
    ("vacuum", "locate"): _unchanged,
    ("vacuum", "clean_spot"): _set_state("cleaning"),
    ("valve", "open_valve"): _set_state("open"),
    ("valve", "close_valve"): _set_state("closed"),
    ("number", "set_value"): _value_to_state("value"),
    ("input_number", "set_value"): _value_to_state("value"),
    ("text", "set_value"): _value_to_state("value"),
    ("input_text", "set_value"): _value_to_state("value"),
    ("select", "select_option"): _value_to_state("option"),
    ("input_select", "select_option"): _value_to_state("option"),
    ("select", "select_next"): _select_step(1),
    ("input_select", "select_next"): _select_step(1),
    ("select", "select_previous"): _select_step(-1),
    ("input_select", "select_previous"): _select_step(-1),
    ("button", "press"): _pressed,
    ("input_button", "press"): _pressed,
    ("timer", "start"): _set_state("active"),
    ("timer", "pause"): _set_state("paused"),
    ("timer", "cancel"): _set_state("idle"),
    ("timer", "finish"): _set_state("idle"),
    ("scene", "turn_on"): _unchanged,
    ("script", "turn_on"): _unchanged,
}


def _handler_for(domain: str, service: str) -> Handler | None:
    handler = _HANDLERS.get((domain, service))
    if handler is None and domain in _ON_OFF_DOMAINS:
        handler = _HANDLERS.get(("*", service))
    return handler


class Sandbox:
    """Simulated states layered over Home Assistant's real states.

    Not thread-safe on its own: the virtual panel reads and changes it only
    from its app's single worker thread.
    """

    def __init__(self, read_real: RealStateReader) -> None:
        self._read_real = read_real
        self._states: dict[str, SimState] = {}

    def get(self, entity_id: str) -> SimState | None:
        """Return the simulated state, else a snapshot of the real one, else ``None``."""
        sim = self._states.get(entity_id)
        if sim is not None:
            return sim
        real = self._read_real(entity_id)
        if real is None:
            return None
        state, attributes = real
        return SimState(entity_id, state, copy.deepcopy(dict(attributes)))

    def is_simulated(self, entity_id: str) -> bool:
        return entity_id in self._states

    def apply(
        self, domain: str, service: str, entity_ids: list[str], data: dict[str, Any]
    ) -> tuple[bool, list[tuple[str, SimState | None, SimState]]]:
        """Simulate ``domain.service`` on ``entity_ids``.

        Returns:
            ``(simulated, changes)``: ``simulated`` is ``False`` when the
            service has no simulation (nothing changed); ``changes`` lists
            ``(entity_id, old, new)`` for every entity whose state changed.
        """
        handler = _handler_for(domain, service)
        if handler is None:
            return False, []
        changes: list[tuple[str, SimState | None, SimState]] = []
        for entity_id in entity_ids:
            old = self.get(entity_id)
            base = old if old is not None else SimState(entity_id, "unknown")
            new = handler(base, data)
            if new is None or new is base:
                continue
            if old is not None and (new.state, new.attributes) == (old.state, old.attributes):
                continue
            self._states[entity_id] = new
            changes.append((entity_id, old, new))
        return True, changes

    def reset(self) -> list[str]:
        """Drop every simulated state; returns the entity ids that were simulated."""
        entity_ids = list(self._states)
        self._states.clear()
        return entity_ids

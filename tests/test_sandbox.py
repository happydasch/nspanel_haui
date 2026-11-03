"""Tests for the virtual panel's simulated entity state."""

from __future__ import annotations

import pytest
from nspanel_haui.sandbox import Sandbox

REAL = {
    "light.lamp": ("off", {"friendly_name": "Lamp"}),
    "cover.blind": ("closed", {"current_position": 0}),
    "climate.hall": ("off", {"hvac_modes": ["off", "heat", "cool"], "temperature": 19}),
    "media_player.tv": ("playing", {"volume_level": 0.2}),
    "input_select.mode": ("a", {"options": ["a", "b", "c"]}),
}


@pytest.fixture
def sandbox():
    return Sandbox(REAL.get)


def _state(sandbox, entity_id):
    sim = sandbox.get(entity_id)
    return sim.state, sim.attributes


def test_reads_fall_through_to_the_real_state_until_simulated(sandbox):
    assert _state(sandbox, "light.lamp") == ("off", {"friendly_name": "Lamp"})
    assert not sandbox.is_simulated("light.lamp")
    assert sandbox.get("light.missing") is None


def test_real_attributes_are_never_mutated(sandbox):
    sandbox.apply("light", "turn_on", ["light.lamp"], {"brightness_pct": 50})
    assert REAL["light.lamp"] == ("off", {"friendly_name": "Lamp"})


def test_light_turn_on_with_brightness_and_colour(sandbox):
    simulated, changes = sandbox.apply(
        "light", "turn_on", ["light.lamp"], {"brightness_pct": 50, "color_temp_kelvin": 3000}
    )
    assert simulated
    assert [eid for eid, _old, _new in changes] == ["light.lamp"]
    state, attrs = _state(sandbox, "light.lamp")
    assert state == "on"
    assert attrs["brightness"] == 128
    assert attrs["color_temp_kelvin"] == 3000
    assert attrs["friendly_name"] == "Lamp"


def test_light_turn_on_without_brightness_defaults_to_full(sandbox):
    sandbox.apply("light", "turn_on", ["light.lamp"], {})
    assert _state(sandbox, "light.lamp")[1]["brightness"] == 255


def test_toggle_twice_returns_to_off_and_drops_brightness(sandbox):
    sandbox.apply("light", "toggle", ["light.lamp"], {})
    sandbox.apply("light", "toggle", ["light.lamp"], {})
    state, attrs = _state(sandbox, "light.lamp")
    assert state == "off"
    assert "brightness" not in attrs


@pytest.mark.parametrize(
    ("service", "data", "state", "position"),
    [
        ("open_cover", {}, "open", 100),
        ("set_cover_position", {"position": 40}, "open", 40),
        ("set_cover_position", {"position": 0}, "closed", 0),
        ("toggle", {}, "open", 100),
    ],
)
def test_cover_services(sandbox, service, data, state, position):
    sandbox.apply("cover", service, ["cover.blind"], data)
    assert _state(sandbox, "cover.blind")[0] == state
    assert _state(sandbox, "cover.blind")[1]["current_position"] == position


def test_climate_turn_on_uses_the_first_non_off_mode(sandbox):
    sandbox.apply("climate", "turn_on", ["climate.hall"], {})
    assert _state(sandbox, "climate.hall")[0] == "heat"


def test_climate_set_temperature_and_mode(sandbox):
    sandbox.apply("climate", "set_temperature", ["climate.hall"], {"temperature": 22.5})
    sandbox.apply("climate", "set_hvac_mode", ["climate.hall"], {"hvac_mode": "cool"})
    state, attrs = _state(sandbox, "climate.hall")
    assert (state, attrs["temperature"]) == ("cool", 22.5)


def test_media_play_pause_and_volume(sandbox):
    sandbox.apply("media_player", "media_play_pause", ["media_player.tv"], {})
    sandbox.apply("media_player", "volume_set", ["media_player.tv"], {"volume_level": 0.6})
    state, attrs = _state(sandbox, "media_player.tv")
    assert (state, attrs["volume_level"]) == ("paused", 0.6)


def test_select_next_wraps_around(sandbox):
    for _ in range(3):
        sandbox.apply("input_select", "select_next", ["input_select.mode"], {})
    assert _state(sandbox, "input_select.mode")[0] == "a"


def test_alarm_and_lock_states(sandbox):
    sandbox.apply("alarm_control_panel", "alarm_arm_away", ["alarm_control_panel.home"], {})
    sandbox.apply("lock", "unlock", ["lock.door"], {})
    assert _state(sandbox, "alarm_control_panel.home")[0] == "armed_away"
    assert _state(sandbox, "lock.door")[0] == "unlocked"


def test_unknown_service_is_reported_and_changes_nothing(sandbox):
    assert sandbox.apply("light", "flash_wildly", ["light.lamp"], {}) == (False, [])
    assert not sandbox.is_simulated("light.lamp")


def test_turn_on_is_not_simulated_for_domains_without_on_off(sandbox):
    assert sandbox.apply("sensor", "turn_on", ["sensor.temp"], {}) == (False, [])


def test_a_call_that_changes_nothing_reports_no_change(sandbox):
    simulated, changes = sandbox.apply("cover", "stop_cover", ["cover.blind"], {})
    assert simulated
    assert changes == []
    assert not sandbox.is_simulated("cover.blind")


def test_reset_restores_the_real_states(sandbox):
    sandbox.apply("light", "turn_on", ["light.lamp"], {})
    assert sandbox.reset() == ["light.lamp"]
    assert _state(sandbox, "light.lamp")[0] == "off"
    assert sandbox.simulated_ids() == []

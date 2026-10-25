"""Tests for the climate page: entity resolution, setpoint control, HVAC modes.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands and service calls, so assertions are on what reaches the
display and Home Assistant.
"""

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.features import ClimateFeatures
from nspanel_haui.haui.page.climate import ClimatePage


class _Entity:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes
        self.calls = []

    def get_state(self):
        return self.state

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class _Controller:
    def __init__(self):
        self.cmds = []

    def send_cmd(self, command, value):
        self.cmds.extend(value if isinstance(value, list) else [value])

    def has_notifications(self):
        return False


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_locale(self):
        return "en_US"


class _DeviceConfig:
    def get_panels(self, nav_only):
        return ["home", "climate"]


class _App:
    def __init__(self, entities, temperature_unit="°C"):
        self.entities = entities
        self.temperature_unit = temperature_unit
        controller = _Controller()
        self.controller = {"esphome": controller, "notification": controller}
        self.device = _Device()
        self.device_config = _DeviceConfig()

    @property
    def cmds(self):
        return self.controller["esphome"].cmds

    def log(self, msg, **kwargs):
        pass

    def item_exists(self, entity_id):
        return entity_id in self.entities

    def get_item(self, entity_id):
        return self.entities[entity_id]

    def listen_state(self, cb, entity_id, attribute=None):
        return f"{entity_id}:{attribute}"

    def get_temperature_unit(self):
        return self.temperature_unit


class _SyncThread:
    """Runs service calls inline so tests can assert on them immediately."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def _sync_service_calls(monkeypatch):
    monkeypatch.setattr(haui_entity.threading, "Thread", _SyncThread)


def _climate(state="heat", **attrs):
    attributes = {
        "friendly_name": "Living Room",
        "supported_features": ClimateFeatures.TARGET_TEMPERATURE,
        "hvac_modes": ["off", "heat"],
        "current_temperature": 20.5,
        "temperature": 21.0,
        "min_temp": 7,
        "max_temp": 35,
    }
    attributes.update(attrs)
    return _Entity(state, attributes)


def _show(entity, *, unit="°C", **panel_cfg):
    app = _App({"climate.living": entity}, temperature_unit=unit)
    cfg = {"type": "climate", "item": {"item": "climate.living"}}
    cfg.update(panel_cfg)
    panel = HAUIPanel(app, cfg)
    page = ClimatePage(app, {"page_id": 16})
    page.set_panel(panel)
    return app, page


# item resolution


def test_editor_panel_controls_configured_item():
    entity = _climate()
    app, page = _show(entity)

    page.callback_function_component("bUp", "temp_up")

    assert 'tTitle.txt="Living Room"' in app.cmds
    assert entity.calls == [("set_temperature", {"temperature": 21.5})]


def test_popup_controls_item_passed_by_id():
    entity = _climate()
    app = _App({"climate.living": entity})
    panel = HAUIPanel(app, {"type": "climate"})
    panel.apply_kwargs({"item": "climate.living", "item_id": "climate.living"})
    page = ClimatePage(app, {"page_id": 16})
    page.set_panel(panel)

    page.callback_function_component("bDown", "temp_down")

    assert entity.calls == [("set_temperature", {"temperature": 20.5})]


# setpoint step


def test_entity_target_temp_step_is_used():
    entity = _climate(target_temp_step=1)
    _app, page = _show(entity)

    page.callback_function_component("bUp", "temp_up")

    assert entity.calls == [("set_temperature", {"temperature": 22.0})]


def test_fahrenheit_systems_step_by_one_degree_by_default():
    entity = _climate(temperature=70.0, min_temp=45, max_temp=95)
    _app, page = _show(entity, unit="°F")

    page.callback_function_component("bUp", "temp_up")

    assert entity.calls == [("set_temperature", {"temperature": 71.0})]


# unit


def test_temperatures_show_the_home_assistant_unit():
    entity = _climate(current_temperature=68.5)
    app, _page = _show(entity, unit="°F")

    assert 'tUnit.txt="°F"' in app.cmds
    assert 'tTemp.txt="68.5°F"' in app.cmds


def test_step_is_clamped_to_entity_range():
    entity = _climate(temperature=34.8)
    _app, page = _show(entity)

    page.callback_function_component("bUp", "temp_up")

    assert entity.calls == [("set_temperature", {"temperature": 35})]


# setpoint layout


def test_entity_with_single_and_range_setpoints_uses_single_setpoint():
    both = ClimateFeatures.TARGET_TEMPERATURE | ClimateFeatures.TARGET_TEMPERATURE_RANGE
    entity = _climate(supported_features=both)
    app, page = _show(entity)

    page.callback_function_component("bUp", "temp_up")

    assert "vis xSet,1" in app.cmds
    assert "vis bUp,1" in app.cmds
    assert "xSet.val=210" in app.cmds
    assert "vis xSet1,1" not in app.cmds
    assert entity.calls == [("set_temperature", {"temperature": 21.5})]


def test_setpoint_buttons_do_nothing_while_entity_uses_range_targets():
    both = ClimateFeatures.TARGET_TEMPERATURE | ClimateFeatures.TARGET_TEMPERATURE_RANGE
    entity = _climate(
        state="heat_cool",
        supported_features=both,
        temperature=None,
        target_temp_low=19,
        target_temp_high=24,
    )
    _app, page = _show(entity)

    page.callback_function_component("bUp", "temp_up")
    page.callback_function_component("bDown", "temp_down")

    assert entity.calls == []


def _range_climate(**attrs):
    values = {
        "state": "heat_cool",
        "supported_features": ClimateFeatures.TARGET_TEMPERATURE_RANGE,
        "temperature": None,
        "target_temp_low": 19,
        "target_temp_high": 24,
    }
    values.update(attrs)
    return _climate(**values)


def test_range_only_entity_shows_range_controls_and_hides_single():
    app, _page = _show(_range_climate())

    for name in ("xSet1", "xSet2", "bUp1", "bDown1", "bUp2", "bDown2"):
        assert f"vis {name},1" in app.cmds
    for name in ("xSet", "bUp", "bDown", "tUnit"):
        assert f"vis {name},1" not in app.cmds
    assert "xSet1.val=190" in app.cmds
    assert "xSet2.val=240" in app.cmds
    assert 'tUnit1.txt="°C"' in app.cmds
    assert 'tUnit2.txt="°C"' in app.cmds


def test_range_buttons_step_low_and_high_setpoints():
    entity = _range_climate()
    _app, page = _show(entity)

    page.callback_function_component("bUp1", "temp_low_up")
    page.callback_function_component("bDown1", "temp_low_down")
    page.callback_function_component("bUp2", "temp_high_up")
    page.callback_function_component("bDown2", "temp_high_down")

    assert entity.calls == [
        ("set_temperature", {"target_temp_low": 19.5, "target_temp_high": 24}),
        ("set_temperature", {"target_temp_low": 18.5, "target_temp_high": 24}),
        ("set_temperature", {"target_temp_low": 19, "target_temp_high": 24.5}),
        ("set_temperature", {"target_temp_low": 19, "target_temp_high": 23.5}),
    ]


def test_range_setpoints_use_entity_step_and_stay_in_bounds():
    entity = _range_climate(
        target_temp_step=2, target_temp_low=8, target_temp_high=9, min_temp=7, max_temp=10
    )
    _app, page = _show(entity)

    page.callback_function_component("bUp1", "temp_low_up")
    page.callback_function_component("bDown1", "temp_low_down")
    page.callback_function_component("bUp2", "temp_high_up")
    page.callback_function_component("bDown2", "temp_high_down")

    assert entity.calls == [
        ("set_temperature", {"target_temp_low": 9, "target_temp_high": 9}),
        ("set_temperature", {"target_temp_low": 7, "target_temp_high": 9}),
        ("set_temperature", {"target_temp_low": 8, "target_temp_high": 10}),
        ("set_temperature", {"target_temp_low": 8, "target_temp_high": 8}),
    ]


def test_range_step_defaults_to_one_degree_on_fahrenheit():
    entity = _range_climate(target_temp_low=66, target_temp_high=74, min_temp=45, max_temp=95)
    _app, page = _show(entity, unit="°F")

    page.callback_function_component("bUp2", "temp_high_up")

    assert entity.calls == [("set_temperature", {"target_temp_low": 66, "target_temp_high": 75})]


def test_setpoint_layout_follows_each_state_update():
    entity = _range_climate()
    app, page = _show(entity)
    app.cmds.clear()

    entity.attributes.update(temperature=21.0, target_temp_low=None, target_temp_high=None)
    page.callback_climate_item("climate.living", "temperature", None, 21.0, {})

    assert "vis xSet,1" in app.cmds
    assert "vis bUp,1" in app.cmds
    assert "xSet.val=210" in app.cmds
    for name in ("xSet1", "xSet2", "bUp1", "bDown1", "bUp2", "bDown2"):
        assert f"vis {name},0" in app.cmds


# hvac modes


def test_hvac_modes_default_to_entity_modes():
    entity = _climate(hvac_modes=["off", "heat", "cool"])
    _app, page = _show(entity)

    page.callback_function_component("btMode2", "hvac_mode")

    assert entity.calls == [("set_hvac_mode", {"hvac_mode": "heat"})]


def test_hvac_modes_option_overrides_entity_modes():
    entity = _climate(hvac_modes=["off", "heat", "cool"])
    app, page = _show(entity, hvac_modes=["cool", "off"])

    page.callback_function_component("btMode1", "hvac_mode")

    assert entity.calls == [("set_hvac_mode", {"hvac_mode": "cool"})]
    assert "vis btMode3,1" not in app.cmds


def test_hvac_modes_option_skips_modes_the_entity_lacks():
    entity = _climate(hvac_modes=["off", "heat"])
    _app, page = _show(entity, hvac_modes=["dry", "heat"])

    page.callback_function_component("btMode1", "hvac_mode")

    assert entity.calls == [("set_hvac_mode", {"hvac_mode": "heat"})]

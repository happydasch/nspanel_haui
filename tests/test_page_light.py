"""Tests for the light page: entity resolution, color temperature, effects.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands, opened popups and service calls, so assertions are on what
reaches the display, the navigation and Home Assistant.
"""

import json

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.mapping.const import ESPResponse, SysPanelKey
from nspanel_haui.haui.page.light import LightPage


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
    """Records display commands and opened popups in one ordered log."""

    page = None
    panel = None

    def __init__(self):
        self.cmds = []
        self.opened = []

    def send_cmd(self, command, value, force=False):
        self.cmds.extend(value if isinstance(value, list) else [value])

    def open_panel(self, key, **kwargs):
        self.opened.append((key, kwargs))
        self.cmds.append(f"<open {key}>")

    def close_panel(self):
        self.cmds.append("<close>")

    def has_notifications(self):
        return False


class _Device:
    is_portrait = False

    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_locale(self):
        return "en_US"


class _DeviceConfig:
    def get_panels(self, nav_only):
        return ["home", "light"]


class _App:
    def __init__(self, entities):
        self.entities = entities
        controller = _Controller()
        self.controller = {
            "esphome": controller,
            "navigation": controller,
            "notification": controller,
        }
        self.device = _Device()
        self.device_config = _DeviceConfig()

    @property
    def cmds(self):
        return self.controller["esphome"].cmds

    @property
    def opened(self):
        return self.controller["navigation"].opened

    def log(self, msg, **kwargs):
        pass

    def item_exists(self, entity_id):
        return entity_id in self.entities

    def get_item(self, entity_id):
        return self.entities[entity_id]

    def listen_state(self, cb, entity_id, attribute=None):
        return f"{entity_id}:{attribute}"


class _SyncThread:
    """Runs service calls inline so tests can assert on them immediately."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def _sync_service_calls(monkeypatch):
    monkeypatch.setattr(haui_entity.threading, "Thread", _SyncThread)


def _attributes(**attrs):
    attributes = {
        "friendly_name": "Desk Lamp",
        "supported_color_modes": ["color_temp"],
        "brightness": 128,
        "color_temp_kelvin": 4000,
        "min_color_temp_kelvin": 2000,
        "max_color_temp_kelvin": 6500,
        "effect_list": ["None", "Rainbow"],
    }
    attributes.update(attrs)
    return attributes


def _show(entity, **panel_cfg):
    app = _App({"light.desk": entity})
    cfg = {"type": "light", "item": {"item": "light.desk"}}
    cfg.update(panel_cfg)
    panel = HAUIPanel(app, cfg)
    page = LightPage(app, {"page_id": 13})
    page.set_panel(panel)
    return app, page


# light function buttons: brightness, color temperature, effect
BTN_COLOR_TEMP = LightPage.COMPONENTS.btn_light_fnc_2
BTN_EFFECT = LightPage.COMPONENTS.btn_light_fnc_3


def _drag_color_temp(page, value):
    slider = LightPage.COMPONENTS.h_color_temp
    page.request_component_value(slider)
    response = {"name": slider.name, "type": "number", "value": value}
    page.process_event(HAUIEvent(ESPResponse.READ_RESPONSE, json.dumps(response)))


# item resolution


def test_editor_panel_controls_configured_item():
    entity = _Entity("on", _attributes())
    app, page = _show(entity)

    page.callback_power(None, LightPage.COMPONENTS.btn_power)

    assert 'tTitle.txt="Desk Lamp"' in app.cmds
    assert entity.calls == [("turn_off", {})]


def test_popup_controls_item_passed_by_id():
    entity = _Entity("off", _attributes())
    app = _App({"light.desk": entity})
    panel = HAUIPanel(app, {"type": "light"})
    panel.apply_kwargs({"item": "light.desk", "item_id": "light.desk"})
    page = LightPage(app, {"page_id": 13})
    page.set_panel(panel)

    page.callback_power(None, LightPage.COMPONENTS.btn_power)

    assert entity.calls == [("turn_on", {})]


# color temperature


def test_show_kelvin_defaults_to_kelvin_in_editor_and_at_runtime():
    option = next(o for o in LightPage.DESCRIPTOR.options if o.key == "show_kelvin")
    app, page = _show(_Entity("on", _attributes()))

    page.callback_light_function_button(None, BTN_COLOR_TEMP)

    assert option.default is True
    assert 'tInfo.txt="4000K"' in app.cmds


def test_mired_display_converts_kelvin_for_display_only():
    entity = _Entity("on", _attributes())
    app, page = _show(entity, show_kelvin=False)

    page.callback_light_function_button(None, BTN_COLOR_TEMP)
    _drag_color_temp(page, 50)

    assert 'tInfo.txt="250Mired"' in app.cmds
    assert "hColorTemp.val=56" in app.cmds
    assert entity.calls == [("turn_on", {"color_temp_kelvin": 4250})]


def test_mired_display_follows_kelvin_attribute_changes():
    entity = _Entity("on", _attributes())
    app, page = _show(entity, show_kelvin=False)
    page.callback_light_function_button(None, BTN_COLOR_TEMP)

    entity.attributes["color_temp_kelvin"] = 3000
    page.callback_light_item("light.desk", "color_temp_kelvin", 4000, 3000, {})

    assert 'tInfo.txt="333Mired"' in app.cmds


def test_color_temp_range_is_read_when_light_becomes_available():
    restored = {"friendly_name": "Desk Lamp", "restored": True, "supported_features": 4}
    entity = _Entity("unavailable", restored)
    app, page = _show(entity)

    entity.state = "on"
    entity.attributes = _attributes()
    page.callback_light_item("light.desk", "state", "unavailable", "on", {})
    page.callback_light_function_button(None, BTN_COLOR_TEMP)
    _drag_color_temp(page, 0)

    assert "hColorTemp.val=56" in app.cmds
    assert entity.calls == [("turn_on", {"color_temp_kelvin": 6500})]


# effects


def test_effect_button_opens_effect_selection():
    entity = _Entity("on", _attributes())
    app, page = _show(entity)

    page.callback_light_function_button(None, BTN_EFFECT)

    ((key, kwargs),) = app.opened
    assert key == SysPanelKey.POPUP_SELECT
    assert [e["value"] for e in kwargs["items"]] == ["None", "Rainbow"]
    # the popup replaces the light page, so nothing may be drawn after it opens
    assert app.cmds[-1] == f"<open {SysPanelKey.POPUP_SELECT}>"

    kwargs["selection_callback_fnc"]("Rainbow")
    assert entity.calls == [("turn_on", {"effect": "Rainbow"})]


def test_light_without_effects_has_no_effect_button():
    app, _page = _show(_Entity("on", _attributes(effect_list=[])))

    assert "vis btLightFnc3,1" not in app.cmds


# unavailable light


def test_standalone_panel_stays_open_when_light_becomes_unavailable():
    entity = _Entity("on", _attributes())
    app, page = _show(entity)

    entity.state = "unavailable"
    entity.attributes = {"friendly_name": "Desk Lamp", "restored": True}
    page.callback_light_item("light.desk", "state", "on", "unavailable", {})

    assert "<close>" not in app.cmds


def test_popup_closes_when_its_light_becomes_unavailable():
    entity = _Entity("on", _attributes())
    app = _App({"light.desk": entity})
    panel = HAUIPanel(app, {"type": "light"})
    panel.apply_kwargs({"item": "light.desk", "item_id": "light.desk"})
    page = LightPage(app, {"page_id": 13})
    page.set_panel(panel)

    entity.state = "unavailable"
    entity.attributes = {"friendly_name": "Desk Lamp", "restored": True}
    page.callback_light_item("light.desk", "state", "on", "unavailable", {})

    assert "<close>" in app.cmds


# display model


def test_color_wheel_origin_follows_the_display_model():
    """The colour marker is drawn relative to pColorWheel, which sits elsewhere on the portrait TFT."""  # noqa: E501
    _, page = _show(_Entity("on", _attributes(supported_color_modes=["rgb"], rgb_color=[255, 0, 0])))  # noqa: E501
    assert page.color_rect_origin() == (125, 75)
    page.app.device.is_portrait = True
    assert page.color_rect_origin() == (90, 80)

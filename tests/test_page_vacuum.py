"""Tests for the vacuum page: entity resolution, action button, listeners.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands, state listeners and service calls, so assertions are on what
reaches the display and Home Assistant.
"""

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.features import VacuumFeatures
from nspanel_haui.haui.page.vacuum import VacuumPage
from nspanel_haui.haui.utils.icon import get_icon


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
        return ["home", "vacuum"]


class _App:
    def __init__(self, entities):
        self.entities = entities
        self.listeners = []
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
        self.listeners.append((entity_id, attribute))
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


BASE_FEATURES = VacuumFeatures.START | VacuumFeatures.RETURN_HOME | VacuumFeatures.STATE


def _vacuum(state="docked", features=BASE_FEATURES):
    return _Entity(state, {"friendly_name": "Robo", "supported_features": features})


def _show(vacuum, battery=None, **panel_cfg):
    entities = {"vacuum.robo": vacuum, "switch.mop": _Entity("off", {"friendly_name": "Mop"})}
    if battery is not None:
        entities["sensor.battery"] = battery
    app = _App(entities)
    cfg = {"type": "vacuum", "item": {"item": "vacuum.robo"}}
    cfg.update(panel_cfg)
    panel = HAUIPanel(app, cfg)
    page = VacuumPage(app, {"page_id": 15})
    page.set_panel(panel)
    return app, page


def _press_action(page):
    page.callback_function_component(VacuumPage.COMPONENTS.btn_action.name, "action")


# item resolution


def test_editor_panel_controls_configured_item_and_keeps_all_secondary_items():
    vacuum = _vacuum()
    app, page = _show(vacuum, items=[{"item": "switch.mop"}])

    _press_action(page)

    assert 'tTitle.txt="Robo"' in app.cmds
    assert vacuum.calls == [("start", {})]
    assert "vis bEntity1,1" in app.cmds


def test_popup_controls_item_passed_by_id():
    vacuum = _vacuum()
    app = _App({"vacuum.robo": vacuum})
    panel = HAUIPanel(app, {"type": "vacuum"})
    panel.apply_kwargs({"item": "vacuum.robo", "item_id": "vacuum.robo"})
    page = VacuumPage(app, {"page_id": 15})
    page.set_panel(panel)

    _press_action(page)

    assert vacuum.calls == [("start", {})]


# action button while cleaning


def test_cleaning_vacuum_with_pause_pauses():
    features = BASE_FEATURES | VacuumFeatures.PAUSE | VacuumFeatures.STOP
    vacuum = _vacuum(state="cleaning", features=features)
    _app, page = _show(vacuum)

    _press_action(page)

    assert vacuum.calls == [("pause", {})]


def test_cleaning_vacuum_without_pause_stops():
    vacuum = _vacuum(state="cleaning", features=BASE_FEATURES | VacuumFeatures.STOP)
    _app, page = _show(vacuum)

    _press_action(page)

    assert vacuum.calls == [("stop", {})]


# listeners


def test_page_listens_to_vacuum_state_only():
    vacuum = _vacuum()
    app, _page = _show(vacuum)

    assert [a for e, a in app.listeners if e == "vacuum.robo"] == [None]


# paused vacuum


def test_paused_vacuum_can_be_resumed():
    vacuum = _vacuum(state="paused", features=BASE_FEATURES | VacuumFeatures.PAUSE)
    app, page = _show(vacuum)

    _press_action(page)

    assert "tsw bAction,1" in app.cmds
    assert vacuum.calls == [("start", {})]


# battery


def _battery(level, icon=None):
    attributes = {"friendly_name": "Battery"}
    if icon:
        attributes["icon"] = icon
    return _Entity(level, attributes)


def test_battery_sensor_level_picks_the_header_icon():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert "vis bFncRSec,1" in app.cmds
    assert f'bFncRSec.txt="{get_icon("mdi:battery-90")}"' in app.cmds


def test_battery_sensor_icon_attribute_wins_over_the_level():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87", icon="mdi:battery-charging"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert f'bFncRSec.txt="{get_icon("mdi:battery-charging")}"' in app.cmds


def test_battery_sensor_accepts_a_plain_entity_id():
    vacuum = _vacuum()
    app, _page = _show(vacuum, battery=_battery("42"), battery_sensor="sensor.battery")

    assert "vis bFncRSec,1" in app.cmds
    assert f'bFncRSec.txt="{get_icon("mdi:battery-40")}"' in app.cmds


def test_page_listens_to_the_battery_sensor():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert [a for e, a in app.listeners if e == "sensor.battery"] == [None]


def test_no_battery_icon_without_a_battery_sensor():
    vacuum = _vacuum()
    app, _page = _show(vacuum)

    assert "vis bFncRSec,1" not in app.cmds


def test_secondary_item_button_opens_the_items_popup_like_grid():
    app, page = _show(_vacuum(), items=[{"item": "switch.mop"}])
    executed = []
    page.execute_item = executed.append

    page.callback_function_component("bEntity1", "item")

    assert [item.get_item_id() for item in executed] == ["switch.mop"]

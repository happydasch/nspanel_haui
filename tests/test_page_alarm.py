"""Tests for how the alarm page resolves its alarm entity.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands and service calls, so assertions are on what reaches the
display and Home Assistant.
"""

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.page.alarm import AlarmPage


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
        return {}.get(key, default)

    def get_locale(self):
        return "en_US"


class _DeviceConfig:
    def get_panels(self, nav_only):
        return ["home", "alarm"]


class _App:
    def __init__(self, entities):
        self.entities = entities
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


class _SyncThread:
    """Runs service calls inline so tests can assert on them immediately."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def _sync_service_calls(monkeypatch):
    monkeypatch.setattr(haui_entity.threading, "Thread", _SyncThread)


ENTITY_ID = "alarm_control_panel.home"
ARM_HOME_AND_AWAY = 1 | 2


def _alarm():
    return _Entity("disarmed", {"friendly_name": "Home", "supported_features": ARM_HOME_AND_AWAY})


def _show(panel_cfg, kwargs=None):
    entity = _alarm()
    app = _App({ENTITY_ID: entity})
    panel = HAUIPanel(app, {"type": "alarm", **panel_cfg})
    if kwargs is not None:
        panel.apply_kwargs(kwargs)
    page = AlarmPage(app, {"page_id": 17})
    page.set_panel(panel)
    return app, page, entity


def test_editor_panel_controls_configured_item():
    app, page, entity = _show({"item": {"item": ENTITY_ID}})

    page.callback_action(None, AlarmPage.COMPONENTS.b1_fnc)

    assert 'tTitle.txt="Disarmed"' in app.cmds
    assert entity.calls == [("alarm_arm_home", {})]


def test_popup_controls_item_passed_by_id():
    # execute_item opens popup_alarm with the item config and its entity id
    app, page, entity = _show({}, kwargs={"item": ENTITY_ID, "item_id": ENTITY_ID})

    page.callback_action(None, AlarmPage.COMPONENTS.b2_fnc)

    assert entity.calls == [("alarm_arm_away", {})]

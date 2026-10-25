"""Tests for the cover page: entity resolution and covers without a position.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands and service calls, so assertions are on what reaches the
display and Home Assistant.
"""

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.features import CoverFeatures
from nspanel_haui.haui.page.cover import CoverPage


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
        return ["home", "cover"]


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


OPEN_CLOSE_STOP = CoverFeatures.OPEN | CoverFeatures.CLOSE | CoverFeatures.STOP


def _cover(state="open", **attrs):
    attributes = {"friendly_name": "Garage Door", "supported_features": OPEN_CLOSE_STOP}
    attributes.update(attrs)
    return _Entity(state, attributes)


def _show(entity):
    app = _App({"cover.garage": entity})
    panel = HAUIPanel(app, {"type": "cover", "item": {"item": "cover.garage"}})
    page = CoverPage(app, {"page_id": 18})
    page.set_panel(panel)
    return app, page


def test_editor_panel_controls_configured_item():
    entity = _cover()
    app, page = _show(entity)

    page.callback_cover_down(None, CoverPage.COMPONENTS.btn_down)

    assert 'tTitle.txt="Garage Door"' in app.cmds
    assert entity.calls == [("close_cover", {})]


def test_popup_controls_item_passed_by_id():
    entity = _cover()
    app = _App({"cover.garage": entity})
    panel = HAUIPanel(app, {"type": "cover"})
    panel.apply_kwargs({"item": "cover.garage", "item_id": "cover.garage"})
    page = CoverPage(app, {"page_id": 18})
    page.set_panel(panel)

    page.callback_cover_up(None, CoverPage.COMPONENTS.btn_up)

    assert entity.calls == [("open_cover", {})]


def test_cover_without_position_shows_state_instead_of_zero_percent():
    app, _page = _show(_cover(state="open"))

    assert 'tInfo.txt="0%"' not in app.cmds
    assert 'tInfo.txt="Open"' in app.cmds


def test_open_cover_without_position_can_close_but_not_open():
    app, _page = _show(_cover(state="open"))

    assert "tsw bDown,1" in app.cmds
    assert "tsw bUp,0" in app.cmds


def test_closed_cover_without_position_can_open_but_not_close():
    app, _page = _show(_cover(state="closed"))

    assert "tsw bUp,1" in app.cmds
    assert "tsw bDown,0" in app.cmds


def test_unavailable_position_cover_leaves_slider_value_alone():
    features = OPEN_CLOSE_STOP | CoverFeatures.SET_POSITION
    app, _page = _show(_cover(state="unavailable", supported_features=features))

    assert not [cmd for cmd in app.cmds if cmd.startswith("hVertPos.val=")]


def test_cover_with_position_shows_percentage():
    features = OPEN_CLOSE_STOP | CoverFeatures.SET_POSITION
    app, _page = _show(_cover(state="open", supported_features=features, current_position=42))

    assert 'tInfo.txt="42%"' in app.cmds
    assert "hVertPos.val=42" in app.cmds
    assert "tsw bUp,1" in app.cmds
    assert "tsw bDown,1" in app.cmds

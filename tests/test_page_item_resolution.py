"""Tests for HAUIPage._resolve_panel_item."""

import types

import pytest
from nspanel_haui.haui.abstract.haui_page import HAUIPage


class _Panel:
    def __init__(self, cfg):
        self.cfg = cfg

    def get(self, key, default=None):
        return self.cfg.get(key, default)


def _page():
    page = HAUIPage.__new__(HAUIPage)
    page.app = types.SimpleNamespace(log=lambda *a, **k: None)
    return page


def test_item_id_wins_for_popups():
    item = _page()._resolve_panel_item(_Panel({"item_id": "light.a", "item": {"item": "light.b"}}))

    assert item is not None
    assert item.get_item_id() == "light.a"


def test_saved_item_config_is_used_without_item_id():
    item = _page()._resolve_panel_item(_Panel({"item": {"item": "light.b"}}))

    assert item is not None
    assert item.get_item_id() == "light.b"


def test_no_item_configured_returns_none():
    assert _page()._resolve_panel_item(_Panel({})) is None


class _UnavailableItem:
    def __init__(self, state):
        self.state = state
        self.executed = False

    def get_item_type(self):
        return "sensor"

    def get_item_state(self):
        return self.state

    def get_name(self):
        return "Missing sensor"

    def get_item_id(self):
        return "sensor.missing"

    def get_icon(self):
        return "mdi:alert"

    def has_item(self):
        return self.state is not None

    def execute(self):
        self.executed = True


@pytest.mark.parametrize("state", [None, "unknown", "unavailable"])
def test_unavailable_items_are_not_executed(state):
    opened = []
    page = _page()
    page.translate = lambda text: text
    page.log = lambda *args, **kwargs: None
    page.app.controller = {
        "navigation": types.SimpleNamespace(open_panel=lambda *a, **kw: opened.append((a, kw)))
    }
    item = _UnavailableItem(state)

    page.execute_item(item)

    assert item.executed is False
    assert len(opened) == 1

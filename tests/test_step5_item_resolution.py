"""Tests for HAUIPage._resolve_panel_item."""

import types

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

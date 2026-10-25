"""Tests for the stale-data indicator (dimmed value cells on the row page)."""

from __future__ import annotations

import types
from datetime import UTC, datetime, timedelta

from nspanel_haui.haui.abstract.haui_item import HAUIItem
from nspanel_haui.haui.page.row import RowPage


class _Entity:
    def __init__(self, last_updated):
        self.last_updated = last_updated

    def get_entity(self):
        return self

    def get_entity_type(self):
        return "sensor"


def _item(last_updated, entity_type="sensor"):
    item = HAUIItem.__new__(HAUIItem)
    item._entity = _Entity(last_updated)
    item._internal = False
    return item


def _internal_item():
    item = HAUIItem.__new__(HAUIItem)
    item._entity = None
    item._internal = True
    return item


# --- HAUIItem.is_stale ------------------------------------------------------


def test_old_value_is_stale():
    item = _item(datetime.now(UTC) - timedelta(minutes=10))
    assert item.is_stale(300) is True


def test_fresh_value_is_not_stale():
    item = _item(datetime.now(UTC) - timedelta(seconds=30))
    assert item.is_stale(300) is False


def test_disabled_threshold_never_stale():
    item = _item(datetime.now(UTC) - timedelta(days=1))
    assert item.is_stale(0) is False
    assert item.is_stale(-1) is False


def test_missing_entity_is_not_stale():
    item = HAUIItem.__new__(HAUIItem)
    item._entity = types.SimpleNamespace(get_entity=lambda: None)
    assert item.is_stale(300) is False


def test_internal_item_is_never_stale():
    assert _internal_item().is_stale(300) is False


def test_naive_timestamp_supported():
    item = _item(datetime.now().replace(tzinfo=None) - timedelta(minutes=10))
    assert item.is_stale(300) is True


# --- row page value cells ----------------------------------------------------


class _StubItem:
    def __init__(self, stale, value="21.5 °C"):
        self._stale = stale
        self._value = value

    def get_value(self):
        return self._value

    def is_stale(self, max_age):
        return self._stale

    def get_item_state(self):
        return "21.5"

    def get_item_attr(self, attr, default=None):
        return {"min": 0, "max": 100, "step": 1}.get(attr, default)

    def translate_item_state(self):
        return "translated"


def _row_page(stale):
    page = RowPage.__new__(RowPage)
    page.calls = []
    page.send_cmd = lambda cmd: page.calls.append(("cmd", cmd))
    page.get_color = lambda key: {"text_inactive": 111, "component_text": 222}.get(key, 0)
    page.app = types.SimpleNamespace(
        device=types.SimpleNamespace(
            get=lambda key, default=0: 300 if key == "stale_data_seconds" else default
        )
    )
    page.update_function_component = lambda fid, **kw: page.calls.append((fid, kw))
    page.set_slider_color = lambda slider: None
    page._fnc_items = {}
    return page, _StubItem(stale)


def test_row_text_cell_marks_stale_value():
    page, item = _row_page(stale=True)
    page.update_item_text(item, 1)
    fid, kw = page.calls[0]
    assert kw["text"] == "21.5 °C …"
    assert kw["color"] == 111  # text_inactive


def test_row_text_cell_restores_fresh_look():
    page, item = _row_page(stale=False)
    page.update_item_text(item, 1)
    fid, kw = page.calls[0]
    assert kw["text"] == "21.5 °C"
    assert kw["color"] == 222  # component_text


def test_row_slider_text_cell_marks_stale_value():
    page, item = _row_page(stale=True)
    slider_txt = RowPage.COMPONENTS.r1_slider_txt
    page.update_function_component(slider_txt[1], value=5, text="21.5", color=1)  # slider itself
    page.calls.clear()
    item2 = _StubItem(stale=True, value="21.5")
    page.update_item_slider(item2, 1)
    # The slider text cell is the one that received the dimmed text.
    texts = [kw.get("text") for _, kw in page.calls if isinstance(kw, dict)]
    colors = [kw.get("color") for _, kw in page.calls if isinstance(kw, dict)]
    assert "21.5 …" in texts
    assert 111 in colors

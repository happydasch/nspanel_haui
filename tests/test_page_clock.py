"""Clock page: weather entity vs. bottom item buttons."""

import pytest
from nspanel_haui.haui.abstract import haui_page
from nspanel_haui.haui.page.clock import ClockPage


class _Device:
    device_info: dict = {}

    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_slug(self):
        return "panel"


class _Blinker:
    def refresh(self):
        pass


class _Notification:
    blinker = _Blinker()

    def set_blinker_callback(self, callback):
        pass


class _App:
    def __init__(self):
        self.device = _Device()
        self.controller = {"notification": _Notification()}
        self.listened = []

    def log(self, msg, **kwargs):
        pass

    def subscribe_tick(self, period, callback):
        pass

    def run_every(self, cb, start, interval, **kwargs):
        return "interval"

    def listen_state(self, cb, entity_id, attribute=None, **kwargs):
        self.listened.append(entity_id)
        return "listener"


class _Item:
    def __init__(self, config):
        self.item_id = config["item"]

    def get_item_type(self):
        return self.item_id.split(".")[0]

    def get_item_id(self):
        return self.item_id

    def is_internal(self):
        return False

    def get_item_attr(self, attr, default=None):
        return {"temperature": 10}.get(attr, default)

    def get_icon(self):
        return f"icon-{self.item_id}"

    def get_color(self):
        return 0


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)


def _show(monkeypatch, **panel_config):
    monkeypatch.setattr(haui_page, "HAUIItem", lambda app, config: _Item(config))
    page = ClockPage(_App(), {"page_id": 7})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._render_cycle_card = lambda: None
    panel = _Panel(panel_config)
    page.start_panel(panel)
    page.render_panel(panel)
    return page


@pytest.mark.parametrize("weather", [None, {"item": "weather.home"}])
def test_items_fill_bottom_buttons_in_order(monkeypatch, weather):
    page = _show(
        monkeypatch,
        item=weather,
        items=[{"item": "light.kitchen"}, {"item": "switch.fan"}],
    )

    assert 'bEntity1.txt="icon-light.kitchen"' in page.cmds
    assert 'bEntity2.txt="icon-switch.fan"' in page.cmds
    assert 'tMainIcon.txt="icon-light.kitchen"' not in page.cmds


def test_weather_item_drives_weather_icon(monkeypatch):
    page = _show(monkeypatch, item={"item": "weather.home"}, items=[{"item": "light.kitchen"}])

    assert 'tMainIcon.txt="icon-weather.home"' in page.cmds
    # weather header (temperature, pressure), then the item button
    assert page.app.listened == ["weather.home", "weather.home", "light.kitchen"]


def test_no_weather_listener_without_weather_item(monkeypatch):
    page = _show(monkeypatch, items=[{"item": "weather.other"}])

    # only the item button's listener; a weather entity among the items doesn't
    # drive the weather header
    assert page.app.listened == ["weather.other"]
    assert 'bEntity1.txt="icon-weather.other"' in page.cmds
    assert 'tMainIcon.txt="icon-weather.other"' not in page.cmds


def test_item_button_opens_the_items_popup_like_grid(monkeypatch):
    """Clock item buttons go through execute_item (popup_key / default popups)."""
    page = _show(monkeypatch, items=[{"item": "light.kitchen"}])
    executed = []
    page.execute_item = executed.append

    page.callback_function_component("bEntity1", "item")

    assert [item.get_item_id() for item in executed] == ["light.kitchen"]


def test_item_buttons_follow_their_entities_state(monkeypatch):
    page = _show(monkeypatch, items=[{"item": "light.kitchen"}])

    assert "light.kitchen" in page.app.listened

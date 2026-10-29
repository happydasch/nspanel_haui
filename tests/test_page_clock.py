"""Clock page: weather entity vs. bottom item buttons."""

import pytest
from nspanel_haui.haui.abstract import haui_page
from nspanel_haui.haui.page.clock import ClockPage
from nspanel_haui.haui.utils.icon import parse_icon


class _Device:
    device_info: dict = {}

    def get(self, key, default=None):
        return {}.get(key, default)

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


def test_inside_temp_card_reads_the_resolved_sensor():
    """The inside-temp cycle card resolves the sensor via the entity registry
    when the device name differs from the ESPHome node name, and falls back to
    the classic sensor.{slug}_temperature id otherwise."""

    class _State:
        def __init__(self, state):
            self.state = state

        def get_state(self):
            return self.state

    class _TempApp(_App):
        def __init__(self, temp_entity_id):
            self.device = _Device()
            self.controller = {}
            self.temp_entity_id = temp_entity_id

        def find_entity_id(self, domain, name):
            return self.temp_entity_id

        def get_item(self, entity_id):
            expected = self.temp_entity_id or "sensor.panel_temperature"
            assert entity_id == expected
            return _State("21.4")

    for temp_entity_id in (None, "sensor.nspanel_bedroom_temperature"):
        page = ClockPage(_TempApp(temp_entity_id), {"page_id": 7})
        page.translate = lambda key: "INSIDE"

        main_text, sub_text = page._card_text_inside_temperature()

        assert (main_text, sub_text) == ("21°C", "INSIDE")


def test_inside_temp_card_uses_configured_sensor():
    """A panel-level inside_temp_item overrides the internal sensor lookup."""

    class _State:
        def __init__(self, state):
            self.state = state

        def get_state(self):
            return self.state

    class _ConfiguredApp(_App):
        def __init__(self):
            self.device = _Device()
            self.controller = {}
            self.requested = []

        def find_entity_id(self, domain, name):
            raise AssertionError("override must skip the registry lookup")

        def get_item(self, entity_id):
            self.requested.append(entity_id)
            return _State("23.1")

    app = _ConfiguredApp()
    page = ClockPage(app, {"page_id": 7})
    page.translate = lambda key: "INSIDE"
    page.panel = _Panel({"inside_temp_item": {"item": "sensor.office_temperature"}})

    main_text, sub_text = page._card_text_inside_temperature()

    assert app.requested == ["sensor.office_temperature"]
    assert (main_text, sub_text) == ("23°C", "INSIDE")


def test_outside_temp_missing_keeps_home_temp():
    """The clock header keeps the inside temperature when the weather entity
    has no temperature attribute."""

    class _State:
        def get_state(self):
            return "21.4"

    class _TempApp(_App):
        def __init__(self):
            self.device = _Device()
            self.controller = {}
            self.temp_entity_id = None

        def find_entity_id(self, domain, name):
            return self.temp_entity_id

        def get_item(self, entity_id):
            assert entity_id == "sensor.panel_temperature"
            return _State()

    class _NoTempWeather(_Item):
        def get_item_attr(self, attr, default=None):
            if attr == "temperature":
                return ""
            return super().get_item_attr(attr, default)

    page = ClockPage(_TempApp(), {"page_id": 7})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._weather_item = _NoTempWeather({"item": "weather.home"})
    page._show_home_temp = True
    page._weather_icons_mode = "monochrome"
    for name in ["t_main_text", "t_sub_text", "t_main_icon"]:
        component = getattr(ClockPage.COMPONENTS, name)
        page.set_function_component(component, component.name)

    page.update_main_weather()

    home = f"{parse_icon('mdi:home-thermometer')}21°C  "
    assert f'tMainText.txt="{home}"' in page.cmds
    assert f'{parse_icon("mdi:thermometer")}' not in "".join(page.cmds)


def test_dark_display_keeps_the_clock_current(monkeypatch):
    """With the hub connected the Nextion stays awake at brightness 0 while the
    display is "off", and a wake touch lights the backlight before the hub could
    redraw: time and weather must keep updating so the page is current on wake.
    Only the card-cycle animation pauses."""
    page = _show(monkeypatch)
    page.app.device.device_info = {"display_state": "off"}
    updated = []
    page._render_cycle_card = lambda: updated.append("time")
    page.update_main_weather = lambda: updated.append("weather")

    page.callback_update_time({})
    page.callback_weather("weather.home", "temperature", 10, 11, {})
    page._tick()

    assert updated == ["time", "weather"]
    assert page._card_timer == 0

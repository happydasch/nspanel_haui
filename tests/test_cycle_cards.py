"""Cycle cards shared by the clock and weather pages (``CycleCardsMixin``)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import time_machine

from custom_components.nspanel_haui.haui.abstract import haui_page
from custom_components.nspanel_haui.haui.abstract.mixins.cycle_cards_mixin import CARD_OPTIONS
from custom_components.nspanel_haui.haui.page import weather as weather_module
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.weather import WeatherPage
from custom_components.nspanel_haui.haui.utils.text import TextBox, fit_line

LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"

# Monday, 16 November 2026, 21:41 UTC
_NOW = datetime(2026, 11, 16, 21, 41, tzinfo=UTC)

_ENTITIES = {
    "weather.home": ("sunny", {"temperature": 21.4, "temperature_unit": "°C"}),
    "sensor.co2": ("612", {"unit_of_measurement": "ppm", "friendly_name": "CO2"}),
    "sensor.living": ("21.456", {"unit_of_measurement": "°C", "friendly_name": "Living"}),
}


class _Device:
    is_portrait = False

    def __init__(self):
        self.device_info = {}
        self.time_format = "%H:%M"

    def get(self, key, default=None):
        return default

    def get_slug(self):
        return "panel"

    def get_time_format(self):
        return self.time_format

    def get_date_format(self):
        return "%A, %d %B"

    def get_date_format_locale(self):
        return "EEEE, d MMMM"

    def get_locale(self):
        return "en"


class _Blinker:
    def refresh(self):
        pass


class _Notification:
    blinker = _Blinker()

    def set_blinker_callback(self, callback):
        pass

    def clear_blinker_callback(self):
        pass


class _State:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state


class _App:
    def __init__(self, states=None):
        self.device = _Device()
        self.device_config = {}
        self.controller = {"notification": _Notification()}
        self.states = states or {}
        self.listened = []
        self.timers = []

    def log(self, msg, **kwargs):
        pass

    def get_timezone(self):
        return "UTC"

    def subscribe_tick(self, period, callback):
        pass

    def unsubscribe_tick(self, period, callback):
        pass

    def run_every(self, callback, start, interval, **kwargs):
        self.timers.append(callback)
        return "tick"

    def cancel_timer(self, handle):
        self.timers.clear()

    def listen_state(self, callback, entity_id, attribute=None, **kwargs):
        self.listened.append((entity_id, attribute, callback))
        return f"handle-{len(self.listened)}"

    def find_entity_id(self, domain, name):
        return "sensor.panel_temperature"

    def get_item(self, entity_id):
        return _State(self.states.get(entity_id))


class _Item:
    def __init__(self, config):
        self.config = config
        self.state, self.attrs = _ENTITIES[config["item"]]

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_item_type(self):
        return self.config["item"].split(".")[0]

    def get_item_id(self):
        return self.config["item"]

    def has_item(self):
        return True

    def is_internal(self):
        return False

    def get_item_attr(self, attr, default=None):
        return self.attrs.get(attr, default)

    def get_value(self):
        return self.config.get("value") or self.state

    def get_name(self):
        return self.config.get("name") or self.attrs.get("friendly_name", "")

    def get_icon(self):
        return "icon"

    def get_color(self, *, variant=None):
        return 0


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)


def _show(monkeypatch, cls, app=None, **config):
    monkeypatch.setattr(haui_page, "HAUIItem", lambda app, config: _Item(config))
    monkeypatch.setattr(weather_module, "HAUIItem", lambda app, config: _Item(config))
    page = cls(app or _App(), {"page_id": cls.DESCRIPTOR.page_id})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page.translate = lambda text: text
    page.get_locale = lambda: "en"
    panel = _Panel(config)
    page.panel = panel
    with time_machine.travel(_NOW, tick=False):
        page.start_panel(panel)
        page.render_panel(panel)
    return page


def _show_card(page, kind):
    """Moves to the first card of *kind* and returns what the widgets show."""
    page._current_card_index = [card.kind for card in page._cycle_cards].index(kind)
    with time_machine.travel(_NOW, tick=False):
        page._render_cycle_card()
    return _drawn(page)


def _drawn(page):
    """The text tTime and tDate show: the last one sent (unchanged text is not resent)."""
    texts = {}
    for cmd in page.cmds:
        for widget in ("tTime", "tDate"):
            if cmd.startswith(f'{widget}.txt="'):
                texts[widget] = cmd[len(widget) + 6 : -1]
    return texts.get("tTime"), texts.get("tDate")


_WEATHER = {"item": {"item": "weather.home"}}
# the cards that are off by default
_CARDS = {"show_time_date": True, "show_time_outside_temp": True}


# fitting


def test_cycle_cards_use_page_theme_text_color(monkeypatch):
    page = _show(
        monkeypatch=monkeypatch,
        cls=ClockPage,
        **{**_WEATHER, **_CARDS},
    )

    assert "tTime.pco=0" in page.cmds
    assert "tDate.pco=0" in page.cmds


def test_fit_line_takes_the_first_candidate_that_fits():
    box = TextBox(262, 118, 2, 10)

    assert fit_line(["Mon 16", "16"], 6, box) == "16"
    assert fit_line(["21°C", "21°"], 6, box) == "21°C"


def test_fit_line_cuts_the_last_candidate_visibly():
    assert fit_line(["Living room CO2"], 6, TextBox(262, 118, 2, 10)) == "Livi.."


def test_fit_line_respects_the_stored_length():
    assert fit_line(["0123456789ab", "01"], 0, TextBox(480, 30, 0, 10)) == "01"


@pytest.mark.parametrize("cls", [ClockPage, WeatherPage])
def test_card_boxes_match_the_hmi_layouts(cls):
    """The fitting geometry must follow the HMIs (rerun gen_virtual_layout after changes)."""
    for orientation, boxes in cls.CARD_BOXES.items():
        layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
        page = layout["pages"][str(cls.DESCRIPTOR.page_id)]
        widgets = {c["name"]: c["attrs"] for c in page["components"]}
        assert set(boxes) == {"tTime", "tDate"}
        for name, card_box in boxes.items():
            attrs = widgets[name]
            assert card_box.box == (attrs["w"], attrs["h"], attrs["borderw"], attrs["txt_maxl"])
            assert card_box.font == attrs["font"], name


# cards on both pages


def test_both_pages_offer_the_same_card_options():
    for cls in (ClockPage, WeatherPage):
        options = [opt for opt in cls.DESCRIPTOR.options if opt.section == "Cycle cards"]
        assert options == CARD_OPTIONS, cls.__name__


@pytest.mark.parametrize("cls", [ClockPage, WeatherPage])
def test_by_default_only_the_time_shows_and_nothing_cycles(monkeypatch, cls):
    page = _show(monkeypatch, cls, **_WEATHER)

    assert [card.kind for card in page._cycle_cards] == ["time"]
    assert page.app.timers == []
    assert _drawn(page)[0] == "21:41"


@pytest.mark.parametrize("cls", [ClockPage, WeatherPage])
def test_enabled_cards_cycle(monkeypatch, cls):
    page = _show(monkeypatch, cls, **_WEATHER, **_CARDS)

    assert [card.kind for card in page._cycle_cards] == [
        "time",
        "date",
        "outside_temperature",
    ]
    assert page.app.timers == [page._tick]


def test_only_the_clock_time_area_takes_taps(monkeypatch):
    """The weather page's tTime sends no touch events: its cards only cycle."""
    clock = _show(monkeypatch, ClockPage, **_WEATHER)
    weather = _show(monkeypatch, WeatherPage, **_WEATHER)

    assert ClockPage.COMPONENTS.t_time.id in clock._callback_map
    assert WeatherPage.COMPONENTS.t_time.id not in weather._callback_map


def test_no_outside_card_without_a_weather_entity(monkeypatch):
    page = _show(monkeypatch, ClockPage, **_CARDS)

    assert [card.kind for card in page._cycle_cards] == ["time", "date"]


# texts fitted to the widget


def _time_font(page):
    """The font last sent to tTime, or None."""
    fonts = [cmd for cmd in page.cmds if cmd.startswith("tTime.font=")]
    return int(fonts[-1].split("=")[1]) if fonts else None


@pytest.mark.parametrize(("cls", "font"), [(ClockPage, 6), (WeatherPage, 4)])
def test_date_card_keeps_the_weekday_in_a_smaller_font(monkeypatch, cls, font):
    """ "Mon 16" is wider than tTime on both pages in landscape (fonts 7 and 6)."""
    page = _show(monkeypatch, cls, **_WEATHER, **_CARDS)

    assert _show_card(page, "date") == ("Mon 16", "Monday, 16 November")
    assert _time_font(page) == font


def test_next_card_restores_the_widget_font(monkeypatch):
    page = _show(monkeypatch, WeatherPage, **_WEATHER, **_CARDS)
    _show_card(page, "date")

    _show_card(page, "time")

    assert _time_font(page) == 6


def test_unchanged_font_is_not_resent(monkeypatch):
    page = _show(monkeypatch, WeatherPage, **_WEATHER, **_CARDS)
    assert _time_font(page) == 6
    page.cmds.clear()

    _show_card(page, "outside_temperature")

    assert _time_font(page) is None


def test_twelve_hour_time_drops_am_pm_when_too_wide(monkeypatch):
    app = _App()
    app.device.time_format = "%I:%M %p"
    page = _show(monkeypatch, WeatherPage, app=app, **_WEATHER)

    assert _show_card(page, "time")[0] == "09:41"


def test_outside_temperature_card(monkeypatch):
    page = _show(monkeypatch, WeatherPage, **_WEATHER, **_CARDS)

    assert _show_card(page, "outside_temperature") == ("21°C", "OUTSIDE")


def test_wide_temperature_drops_the_unit_letter(monkeypatch):
    page = _show(monkeypatch, WeatherPage, **_WEATHER, **_CARDS)
    page._weather_item.attrs = {"temperature": 104, "temperature_unit": "°F"}
    page._temp_unit = "°F"

    assert _show_card(page, "outside_temperature")[0] == "104°"


@pytest.mark.parametrize(("cls", "expected"), [(ClockPage, "21.5°C"), (WeatherPage, "21°C")])
def test_entity_card_rounds_before_dropping_the_unit(monkeypatch, cls, expected):
    page = _show(monkeypatch, cls, card_items=[{"item": "sensor.living"}], **_WEATHER)

    assert _show_card(page, "item") == (expected, "Living")


def test_entity_card_drops_a_unit_that_does_not_fit(monkeypatch):
    page = _show(monkeypatch, WeatherPage, card_items=[{"item": "sensor.co2"}], **_WEATHER)

    assert _show_card(page, "item") == ("612", "CO2")


def test_entity_card_skips_fonts_without_its_characters(monkeypatch):
    """The big fonts hold Latin-1 only: the "ę" of a Polish state needs font 4."""
    items = [{"item": "sensor.co2", "value": "zamknięta", "name": "Door"}]
    page = _show(monkeypatch, ClockPage, card_items=items)

    assert _show_card(page, "item") == ("zamknięta", "Door")
    assert _time_font(page) == 4


def test_entity_card_value_template_keeps_its_own_format(monkeypatch):
    items = [{"item": "sensor.co2", "value": "Good", "name": "Air"}]
    page = _show(monkeypatch, ClockPage, card_items=items, **_WEATHER)

    assert _show_card(page, "item") == ("Good", "Air")


# timing


def test_card_timing_settings(monkeypatch):
    page = _show(
        monkeypatch,
        ClockPage,
        show_time_date=True,
        card_interval=2,
        card_pause=3,
    )
    shown = []
    page._render_cycle_card = lambda: shown.append(page._current_card_index)

    for _ in range(9):
        page._tick()

    # 2 s per card, the first card stays 3 s after a full cycle
    assert shown == [1, 0, 0, 1]


def test_unset_card_timing_uses_the_option_defaults(monkeypatch):
    """The editor unsets a cleared number field."""
    page = _show(monkeypatch, ClockPage, show_time_date=True)

    assert (page._card_interval, page._card_pause) == (5, 15)


# live updates


def test_inside_sensor_redraws_header_and_card(monkeypatch):
    app = _App(states={"sensor.panel_temperature": "20.6"})
    page = _show(monkeypatch, ClockPage, app=app, show_time_inside_temp=True, **_WEATHER)
    assert ("sensor.panel_temperature", None) in [(e, a) for e, a, _cb in app.listened]
    assert _show_card(page, "inside_temperature") == ("21°C", "INSIDE")
    weather = []
    page.update_main_weather = lambda: weather.append(True)

    app.states["sensor.panel_temperature"] = "23.2"
    page.callback_inside_temp("sensor.panel_temperature", "state", "20.6", "23.2", {})

    assert weather == [True]
    assert _drawn(page) == ("23°C", "INSIDE")


def test_no_inside_listener_when_nothing_shows_it(monkeypatch):
    app = _App()
    _show(monkeypatch, WeatherPage, app=app, **_WEATHER)

    assert "sensor.panel_temperature" not in [entity for entity, _a, _cb in app.listened]


def test_entity_card_follows_its_entity(monkeypatch):
    app = _App()
    page = _show(monkeypatch, WeatherPage, app=app, card_items=[{"item": "sensor.co2"}], **_WEATHER)
    _show_card(page, "item")
    callback = next(cb for entity, _a, cb in app.listened if entity == "sensor.co2")

    page._cycle_cards[page._current_card_index].item.state = "640"
    callback("sensor.co2", "state", "612", "640", {})

    assert _drawn(page) == ("640", "CO2")


def test_entity_change_redraws_only_its_own_card(monkeypatch):
    app = _App()
    items = [{"item": "sensor.co2"}, {"item": "sensor.living"}]
    page = _show(monkeypatch, WeatherPage, app=app, card_items=items, **_WEATHER)
    _show_card(page, "item")  # sensor.co2
    redrawn = []
    page._render_cycle_card = lambda: redrawn.append(page._current_card_index)
    living = next(cb for entity, _a, cb in app.listened if entity == "sensor.living")
    co2 = next(cb for entity, _a, cb in app.listened if entity == "sensor.co2")

    living("sensor.living", "state", "21.456", "22", {})
    co2("sensor.co2", "state", "612", "640", {})

    assert redrawn == [page._current_card_index]


def test_weather_change_redraws_only_a_visible_temperature_card(monkeypatch):
    page = _show(monkeypatch, WeatherPage, **_WEATHER, **_CARDS)
    redrawn = []
    page._render_cycle_card = lambda: redrawn.append(page._current_card_index)

    page.callback_weather("weather.home", "temperature", 21.4, 22.0, {})
    page._current_card_index = 2  # outside temperature
    page.callback_weather("weather.home", "temperature", 22.0, 22.5, {})

    assert redrawn == [2]

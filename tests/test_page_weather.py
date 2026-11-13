"""Weather page rendering with incomplete data."""

import pytest

from custom_components.nspanel_haui.haui.mapping.color import (
    WEATHER_COLORS,
    WEATHER_COLORS_LIGHT,
    Theme,
)
from custom_components.nspanel_haui.haui.page.weather import WeatherPage
from custom_components.nspanel_haui.haui.utils.icon import parse_icon

_ENTITY_ID = "weather.home"


class _Device:
    def get(self, key, default=None):
        return {}.get(key, default)

    def get_slug(self):
        return "panel"


class _State:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state


class _App:
    def __init__(
        self,
        forecast=None,
        inside_temp=None,
        temp_entity_id="sensor.panel_temperature",
        defer_off_worker=False,
    ):
        self.device = _Device()
        self.theme = Theme()
        self.controller = {}
        self.forecast = forecast
        self.inside_temp = inside_temp
        self.temp_entity_id = temp_entity_id
        self.defer_off_worker = defer_off_worker
        self.off_worker_jobs = []

    def log(self, msg, **kwargs):
        pass

    def call_service(self, service, **kwargs):
        return {"result": {"response": {_ENTITY_ID: {"forecast": self.forecast}}}}

    def submit_off_worker(self, fn, *args, on_done=None):
        self.off_worker_jobs.append((fn, args, on_done))
        if not self.defer_off_worker:
            self.run_off_worker_job(-1)

    def run_off_worker_job(self, index):
        fn, args, on_done = self.off_worker_jobs.pop(index)
        try:
            result, error = fn(*args), None
        except Exception as exc:
            result, error = None, exc
        on_done(result, error)

    def find_entity_id(self, domain, name):
        return self.temp_entity_id

    def get_item(self, entity_id):
        assert entity_id == self.temp_entity_id
        return _State(self.inside_temp)


class _WeatherItem:
    def __init__(self, attrs):
        self.attrs = attrs
        self.last_variant = None

    def get_item_id(self):
        return _ENTITY_ID

    def get_item_attr(self, attr, default=None):
        return self.attrs.get(attr, default)

    def get_icon(self):
        return "icon"

    def get_color(self, *, variant=None):
        self.last_variant = variant
        return 0


def _weather_page(app, attrs):
    page = WeatherPage(app, {"page_id": 6})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page.get_locale = lambda: "en"
    page._weather_item = _WeatherItem(attrs)
    for name in ["t_main_icon", "t_main_text", "t_sub_text"]:
        component = getattr(WeatherPage.COMPONENTS, name)
        page.set_function_component(component, component.name)
    return page


def _forecast(day):
    return {
        "datetime": f"2026-01-0{day}T00:00:00+00:00",
        "condition": "sunny",
        "temperature": 10 + day,
        "templow": day,
    }


def test_short_forecast_clears_unused_slots():
    page = _weather_page(_App(forecast=[_forecast(1), _forecast(2)]), {})
    page._forecast_type = "daily"

    page.render_forecast()

    assert 'f1Val.txt="11°C"' in page.cmds
    assert 'f2Val.txt="12°C"' in page.cmds
    for idx in (3, 4, 5):
        for name in ("Name", "Icon", "Val", "SubVal"):
            assert f'f{idx}{name}.txt=""' in page.cmds


def test_the_forecast_is_fetched_off_the_worker_and_drawn_when_it_arrives():
    app = _App(forecast=[_forecast(1)], defer_off_worker=True)
    page = _weather_page(app, {})
    page._forecast_type = "daily"

    page.render_forecast()

    assert not [cmd for cmd in page.cmds if cmd.startswith("f1Val")]
    app.run_off_worker_job(0)
    assert 'f1Val.txt="11°C"' in page.cmds


def test_a_forecast_that_arrives_after_a_newer_request_is_dropped():
    app = _App(defer_off_worker=True)
    page = _weather_page(app, {})
    page._forecast_type = "daily"
    page.render_forecast()
    page.render_forecast()

    app.forecast = [_forecast(2)]
    app.run_off_worker_job(1)
    app.forecast = [_forecast(1)]
    app.run_off_worker_job(0)

    assert 'f1Val.txt="12°C"' in page.cmds
    assert 'f1Val.txt="11°C"' not in page.cmds


def test_a_forecast_requested_for_the_previous_panel_is_not_drawn():
    app = _App(defer_off_worker=True)
    page = _weather_page(app, {})
    page._forecast_type = "daily"
    page.render_forecast()

    # the page starts its next panel from its defaults and asks again
    page.prepare()
    page._weather_item = _WeatherItem({})
    page._forecast_type = "daily"
    page.render_forecast()
    app.forecast = [_forecast(1)]
    app.run_off_worker_job(0)

    assert not [cmd for cmd in page.cmds if cmd.startswith("f1Val")]


@pytest.mark.parametrize("failure", ["no response", "malformed response", "service exception"])
@pytest.mark.parametrize("has_previous", [True, False])
def test_forecast_failure_reuses_last_result_or_clears_empty_slots(failure, has_previous):
    previous = [_forecast(1)] if has_previous else None
    app = _App(forecast=previous)
    if failure == "no response":
        app.call_service = lambda _service, **_kwargs: None
    elif failure == "malformed response":
        app.call_service = lambda _service, **_kwargs: {"result": {}}
    else:

        def raise_service_error(_service, **_kwargs):
            raise RuntimeError("temporary weather service failure")

        app.call_service = raise_service_error

    page = _weather_page(app, {})
    page._forecast_type = "daily"
    page._previous_forecast = previous

    page.render_forecast()

    if has_previous:
        assert 'f1Val.txt="11°C"' in page.cmds
        assert 'f1Name.txt="Thu"' in page.cmds
        assert page._previous_forecast is previous
    else:
        for idx in range(1, page.NUM_FORECAST + 1):
            for part in ("Name", "Icon", "Val", "SubVal"):
                assert f'f{idx}{part}.txt=""' in page.cmds
        assert page._previous_forecast is None


def test_home_temp_unavailable_shows_outside_temp_only():
    page = _weather_page(_App(inside_temp="unavailable"), {"temperature": 12})
    page._show_home_temp = True

    page.update_main_weather()

    assert f'tMainText.txt="{parse_icon("mdi:thermometer")}12°C"' in page.cmds


def test_home_temp_missing_entity_shows_outside_temp_only():
    page = _weather_page(_App(inside_temp="21.4", temp_entity_id=None), {"temperature": 12})
    page._show_home_temp = True

    page.update_main_weather()

    assert f'tMainText.txt="{parse_icon("mdi:thermometer")}12°C"' in page.cmds


def test_home_temp_shown_when_available():
    page = _weather_page(_App(inside_temp="21.4"), {"temperature": 12})
    page._show_home_temp = True

    page.update_main_weather()

    home = f"{parse_icon('mdi:home-thermometer')}21°C  "
    assert f'tMainText.txt="{home}{parse_icon("mdi:thermometer")}12°C"' in page.cmds


def test_home_temp_reads_registry_resolved_entity_id():
    """The sensor is resolved via the entity registry when the device name
    differs from the ESPHome node name (renames, area-prefixed entity ids)."""
    page = _weather_page(
        _App(inside_temp="21.4", temp_entity_id="sensor.nspanel_bedroom_temperature"),
        {"temperature": 12},
    )
    page._show_home_temp = True

    page.update_main_weather()

    home = f"{parse_icon('mdi:home-thermometer')}21°C  "
    assert f'tMainText.txt="{home}{parse_icon("mdi:thermometer")}12°C"' in page.cmds


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)


class _OverrideApp(_App):
    def __init__(self):
        super().__init__(inside_temp="22.7")
        self.requested = []

    def find_entity_id(self, domain, name):
        raise AssertionError("override must skip the registry lookup")

    def get_item(self, entity_id):
        self.requested.append(entity_id)
        return _State(self.inside_temp)


def test_outside_temp_of_zero_degrees_is_shown():
    """0 °C is a temperature, not a missing value."""
    page = _weather_page(_App(), {"temperature": 0.0, "pressure": 1012, "pressure_unit": "hPa"})

    page.update_main_weather()

    assert f'tMainText.txt="{parse_icon("mdi:thermometer")}0°C"' in page.cmds
    assert 'tSubText.txt="1012hPa"' in page.cmds


def test_whole_pressure_prints_without_a_trailing_zero():
    """HA reports pressure as a float; 1012.0 prints like 1012, as the preview shows it."""
    page = _weather_page(_App(), {"temperature": 5, "pressure": 1012.0, "pressure_unit": "hPa"})

    page.update_main_weather()

    assert 'tSubText.txt="1012hPa"' in page.cmds


def test_home_temp_shown_when_outside_temp_missing():
    """A missing outside temperature must not hide the inside temperature."""
    page = _weather_page(_App(inside_temp="21.4"), {"temperature": ""})
    page._show_home_temp = True

    page.update_main_weather()

    home = f"{parse_icon('mdi:home-thermometer')}21°C  "
    assert f'tMainText.txt="{home}"' in page.cmds
    assert parse_icon("mdi:thermometer") not in "".join(page.cmds)


def test_configured_inside_temp_sensor_used():
    """A panel-level inside_temp_item overrides the internal sensor."""
    app = _OverrideApp()
    page = _weather_page(app, {"temperature": 12})
    page._show_home_temp = True
    page.panel = _Panel({"inside_temp_item": {"item": "sensor.office_temperature"}})

    page.update_main_weather()

    assert app.requested == ["sensor.office_temperature"]
    home = f"{parse_icon('mdi:home-thermometer')}23°C  "
    assert f'tMainText.txt="{home}{parse_icon("mdi:thermometer")}12°C"' in page.cmds


def test_light_background_selects_light_weather_palette():
    page = _weather_page(_App(forecast=[_forecast(1)]), {})
    page.app.theme = Theme("light")
    page._forecast_type = "daily"
    page._weather_icons_mode = "color"
    page._light_background = True
    colors = []
    page._set_component_text_color = lambda component, color: colors.append(color)

    page.render_forecast()

    assert WEATHER_COLORS_LIGHT["sunny"] in colors


def test_light_background_selects_light_palette_for_main_weather_icon():
    page = _weather_page(_App(), {"temperature": 20})
    page._light_background = True

    page.update_main_weather()

    assert page._weather_item.last_variant == "light"
    assert page.app.theme.get_icon_color("weather", "sunny") == WEATHER_COLORS["sunny"]


def test_dark_display_keeps_the_weather_page_current():
    """The dark display is awake; see test_dark_display_keeps_the_clock_current."""
    page = _weather_page(_App(), {})
    page.app.device.device_info = {"display_state": "off"}
    page.started = True
    updated = []
    page._render_cycle_card = lambda: updated.append("time card")
    page.update_main_weather = lambda: updated.append("weather")
    page.render_info_panels = lambda: None
    page.render_forecast = lambda: None

    page.callback_update_time({})
    page.callback_update_date({})
    page.callback_weather(_ENTITY_ID, "temperature", 10, 11, {})
    page._tick()

    assert updated == ["time card", "time card", "weather"]
    assert page._card_timer == 0

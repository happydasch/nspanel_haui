"""Weather page rendering with incomplete data."""

from nspanel_haui.haui.page.weather import WeatherPage
from nspanel_haui.haui.utils.icon import parse_icon

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
    def __init__(self, forecast=None, inside_temp=None, temp_entity_id=None):
        self.device = _Device()
        self.controller = {}
        self.forecast = forecast
        self.inside_temp = inside_temp
        # Entity id the app's registry lookup would resolve; None lets the
        # page fall back to the classic sensor.{device_slug}_temperature id.
        self.temp_entity_id = temp_entity_id

    def log(self, msg, **kwargs):
        pass

    def call_service(self, service, **kwargs):
        return {"result": {"response": {_ENTITY_ID: {"forecast": self.forecast}}}}

    def find_entity_id(self, domain, name):
        return self.temp_entity_id

    def get_item(self, entity_id):
        expected = self.temp_entity_id or "sensor.panel_temperature"
        assert entity_id == expected
        return _State(self.inside_temp)


class _WeatherItem:
    def __init__(self, attrs):
        self.attrs = attrs

    def get_item_id(self):
        return _ENTITY_ID

    def get_item_attr(self, attr, default=None):
        return self.attrs.get(attr, default)

    def get_icon(self):
        return "icon"

    def get_color(self):
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


def test_home_temp_unavailable_shows_outside_temp_only():
    page = _weather_page(_App(inside_temp="unavailable"), {"temperature": 12})
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


def test_dark_display_keeps_the_weather_page_current():
    """The dark display is awake; see test_dark_display_keeps_the_clock_current."""
    page = _weather_page(_App(), {})
    page.app.device.device_info = {"display_state": "off"}
    page.started = True
    updated = []
    page.update_time = lambda: updated.append("time")
    page.update_date = lambda: updated.append("date")
    page.update_main_weather = lambda: updated.append("weather")
    page.render_info_panels = lambda: None
    page.render_forecast = lambda: None

    page.callback_update_time({})
    page.callback_update_date({})
    page.callback_weather(_ENTITY_ID, "temperature", 10, 11, {})

    assert updated == ["time", "date", "weather"]

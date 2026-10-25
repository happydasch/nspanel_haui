"""Weather page rendering with incomplete data."""

from nspanel_haui.haui.page.weather import WeatherPage
from nspanel_haui.haui.utils.icon import parse_icon

_ENTITY_ID = "weather.home"


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_slug(self):
        return "panel"


class _State:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state


class _App:
    def __init__(self, forecast=None, inside_temp=None):
        self.device = _Device()
        self.controller = {}
        self.forecast = forecast
        self.inside_temp = inside_temp

    def log(self, msg, **kwargs):
        pass

    def call_service(self, service, **kwargs):
        return {"result": {"response": {_ENTITY_ID: {"forecast": self.forecast}}}}

    def get_item(self, entity_id):
        assert entity_id == "sensor.panel_temperature"
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

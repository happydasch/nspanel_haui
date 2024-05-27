import dateutil.parser as dp
import datetime

from ..mapping.background import BACKGROUNDS
from ..mapping.icon import WEATHER_MAPPING
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..helper.datetime import (
    get_time_localized, get_date_localized, format_datetime)
from ..config import HAUIConfigEntity

from . import HAUIPage


class WeatherPage(HAUIPage):
    # time and date display
    TXT_TIME, TXT_DATE = (2, "tTime"), (3, "tDate")
    # main weather icon
    ICO_MAIN, TXT_MAIN, TXT_SUB = (4, "tMainIcon"), (5, "tMainText"), (6, "tSubText")
    # icons below main icon
    D1_ICO, D2_ICO, D3_ICO = (7, "d1Icon"), (8, "d2Icon"), (9, "d2Icon")
    D1_VAL, D2_VAL, D3_VAL = (10, "d1Val"), (11, "d2Val"), (12, "d3Val")
    # bottom weather forecast row
    F1_NAME, F2_NAME, F3_NAME, F4_NAME, F5_NAME = (
        (13, "f1Name"),
        (14, "f2Name"),
        (15, "f3Name"),
        (16, "f4Name"),
        (17, "f5Name"),
    )
    F1_ICO, F2_ICO, F3_ICO, F4_ICO, F5_ICO = (
        (18, "f1Icon"),
        (19, "f2Icon"),
        (20, "f3Icon"),
        (21, "f4Icon"),
        (22, "f5Icon"),
    )
    F1_VAL, F2_VAL, F3_VAL, F4_VAL, F5_VAL = (
        (23, "f1Val"),
        (24, "f2Val"),
        (25, "f3Val"),
        (26, "f4Val"),
        (27, "f5Val"),
    )
    F1_SUBVAL, F2_SUBVAL, F3_SUBVAL, F4_SUBVAL, F5_SUBVAL = (
        (28, "f1SubVal"),
        (29, "f2SubVal"),
        (30, "f3SubVal"),
        (31, "f4SubVal"),
        (32, "f5SubVal"),
    )

    NUM_FORECAST = 5

    _time_timer = None
    _date_timer = None
    _show_forecast = False
    _temp_unit = "°C"

    # panel

    def create_panel(self, panel):
        # setting: background
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"weather.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._time_timer = self.app.run_minutely(self.callback_update_time, time)
        # setup date callback
        self._date_timer = self.app.run_hourly(self.callback_update_date, time)
        # entity listener
        self._handles = []
        found = False
        for entity in panel.get_entities():
            if entity.get_entity_type() == "weather":
                self.add_entity_listener(entity.get_entity_id(), self.callback_weather)
                # if a weather entity is found, update the temperature unit
                self._temp_unit = entity.get_entity_attr("temperature_unit", "°C")
                found = True
        if not found:
            self.app.log.warning("No weather entity found in config")
        # setting: forecast
        if not panel.get("forecast", False):
            self.hide_forecast()
        else:
            self.show_forecast()

    def stop_panel(self, panel):
        # cancel time and date timer
        if self._time_timer:
            self.app.cancel_timer(self._time_timer)
            self._time_timer = None
        if self._date_timer:
            self.app.cancel_timer(self._date_timer)
            self._date_timer = None

    def render_panel(self, panel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())

    # misc

    def show_forecast(self):
        self._show_forecast = True
        for i in range(self.NUM_FORECAST):
            idx = i + 1
            name = getattr(self, f"F{idx}_NAME")
            ico = getattr(self, f"F{idx}_ICO")
            val = getattr(self, f"F{idx}_VAL")
            subval = getattr(self, f"F{idx}_SUBVAL")
            self.show_component(name)
            self.show_component(ico)
            self.show_component(val)
            self.show_component(subval)

    def hide_forecast(self):
        self._show_forecast = False
        for i in range(self.NUM_FORECAST):
            idx = i + 1
            name = getattr(self, f"F{idx}_NAME")
            ico = getattr(self, f"F{idx}_ICO")
            val = getattr(self, f"F{idx}_VAL")
            subval = getattr(self, f"F{idx}_SUBVAL")
            self.hide_component(name)
            self.hide_component(ico)
            self.hide_component(val)
            self.hide_component(subval)

    def update_time(self):
        timeformat = self.app.config.get("time_format")
        time = get_time_localized(timeformat)
        self.set_component_text(self.TXT_TIME, time)

    def update_date(self):
        strftime_format = self.app.config.get("date_format")
        babel_format = self.app.config.get("date_format_babel")
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.set_component_text(self.TXT_DATE, date)

    def update_entities(self, entities):
        # if only one entry, create new entities which will be used for
        # forecast
        if len(entities) == 1:
            for i in range(self.NUM_FORECAST):
                config = {"entity": entities[0].get("entity"), "forecast_index": i}
                entities.append(HAUIConfigEntity(self.app, config))

        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self.update_main_weather(main)

        # next 3 are entities below main weather
        info = []
        for i in range(3):
            if len(entities) == 0:
                break
            info.append(entities.pop(0))
            if len(info) == 3:
                break
        for i in range(len(info)):
            self.update_info(i, info[i])

        # forecast
        if self._show_forecast:
            forecast_entity = HAUIConfigEntity(
                self.app, {"entity": self.panel.get('forecast')})
            forecast = forecast_entity.get_entity_attr("forecast", [])
            for i in range(1, self.NUM_FORECAST + 1):
                forecast_data = forecast[i] if i < len(forecast) else None
                self.update_forecast(i, forecast_data)

    def update_main_weather(self, haui_entity):
        # set up main weather details
        icon = haui_entity.get_icon()
        color = haui_entity.get_color()
        msg = haui_entity.get_value()
        msg_sub = haui_entity.get_entity_attr("pressure", "")
        if msg_sub:
            pressure_unit = haui_entity.get_entity_attr("pressure_unit")
            msg_sub = f"{msg_sub}{pressure_unit}"
        self.set_component_text_color(self.ICO_MAIN, color)
        self.set_component_text(self.ICO_MAIN, icon)
        self.set_component_text(self.TXT_MAIN, msg)
        self.set_component_text(self.TXT_SUB, msg_sub)

    def update_forecast(self, idx, data):
        if idx < 1 or idx > self.NUM_FORECAST:
            self.log("Weather Forecast index outside bounds")
            return
        if data is None:
            self.log(f"No weather forecast for index {idx}")
            return
        forecast_temp = data.get("temperature", 20)
        forecast_mintemp = data.get("templow", 0)

        forecast_name = getattr(self, f"F{idx}_NAME")
        forecast_icon = getattr(self, f"F{idx}_ICO")
        forecast_val = getattr(self, f"F{idx}_VAL")
        forecast_subval = getattr(self, f"F{idx}_SUBVAL")
        fdate = dp.parse(data["datetime"])
        name = format_datetime(fdate, "%a", "E", self.get_locale())
        condition = data.get("condition", "")
        icon = WEATHER_MAPPING.get(condition)
        icon = get_icon(icon)

        color_name = f"weather_{condition.replace('-', '_')}"
        color = COLORS.get(color_name, COLORS["weather_default"])
        self.set_component_text_color(forecast_icon, color)
        self.set_component_text(forecast_name, name)
        self.set_component_text(forecast_icon, icon)
        self.set_component_text(forecast_val, f"{forecast_temp}{self._temp_unit}")
        self.set_component_text(forecast_subval, f"{forecast_mintemp}{self._temp_unit}")

    def update_info(self, idx, haui_entity):
        if idx < 1 or idx > 3:
            self.log("Weather Info uses index 1-3")
            return
        info_icon = getattr(self, f"D{idx}_ICO")
        info_val = getattr(self, f"D{idx}_VAL")
        self.set_component_text_color(info_icon, haui_entity.get_color())
        self.set_component_text(info_icon, haui_entity.get_icon())
        self.set_component_text(info_val, haui_entity.get_value())

    # callback

    def callback_update_time(self, cb_args):
        if self.app.device.sleeping:
            return
        self.update_time()

    def callback_update_date(self, cb_args):
        if self.app.device.sleeping:
            return
        self.update_date()

    def callback_weather(self, entity, attribute, old, new, kwargs):
        if self.app.device.sleeping:
            return
        self.refresh_panel()

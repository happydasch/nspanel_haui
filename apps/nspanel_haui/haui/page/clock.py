from typing import List
import dateutil.parser as dp
import datetime

from ..mapping.background import BACKGROUNDS
from ..mapping.icon import WEATHER_MAPPING
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..helper.datetime import (
    get_time_localized, get_date_localized, format_datetime)
from ..config import HAUIConfigEntity, HAUIConfigPanel

from . import HAUIPage


class ClockPage(HAUIPage):
    # main components
    TXT_TIME_MID, TXT_DATE_MID = (2, "tTimeMid"), (3, "tDateMid")
    TXT_TIME, TXT_DATE = (4, "tTime"), (5, "tDate")
    ICO_MAIN, TXT_MAIN = (6, "tMainIcon"), (7, "tMainText")
    # bottom weather forecast row
    F1_NAME, F2_NAME, F3_NAME, F4_NAME = (
        (8, "f1Name"),
        (9, "f2Name"),
        (10, "f3Name"),
        (11, "f4Name"),
    )
    F1_ICO, F2_ICO, F3_ICO, F4_ICO = (
        (12, "f1Icon"),
        (13, "f2Icon"),
        (14, "f3Icon"),
        (15, "f4Icon"),
    )
    F1_VAL, F2_VAL, F3_VAL, F4_VAL = (
        (16, "f1Val"),
        (17, "f2Val"),
        (18, "f3Val"),
        (19, "f4Val"),
    )
    F1_SUBVAL, F2_SUBVAL, F3_SUBVAL, F4_SUBVAL = (
        (20, "f1SubVal"),
        (21, "f2SubVal"),
        (22, "f3SubVal"),
        (23, "f4SubVal"),
    )

    NUM_FORECAST = 4

    _date_timer = None
    _date_component = None
    _time_timer = None
    _time_component = None
    _show_forecast = False
    _temp_unit = "°C"

    # panel

    def create_panel(self, panel: HAUIConfigPanel):
        # setting: background
        # set before showing panel
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"clock.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIConfigPanel):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._time_timer = self.app.run_minutely(self.callback_update_time, time)
        # date update callback
        self._date_timer = self.app.run_hourly(self.callback_update_date, time)
        # entity listeners
        for entity in panel.get_entities():
            if entity.get_entity_type() == "weather":
                self.add_entity_listener(entity.get_entity_id(), self.callback_weather)
                # if a weather entity is found, update the temperature unit
                self._temp_unit = entity.get_entity_attr("temperature_unit", "°C")
        # setting: show_weather
        if not panel.get("show_weather", True):
            self.hide_component(self.ICO_MAIN)
        # setting: show_temp
        if not panel.get("show_temp", True):
            self.hide_component(self.TXT_MAIN)
        # setting: forecast
        if not panel.get("forecast", False):
            self._time_component = self.TXT_TIME_MID
            self._date_component = self.TXT_DATE_MID
            self.hide_forecast()
        else:
            self._time_component = self.TXT_TIME
            self._date_component = self.TXT_DATE
            self.show_forecast()
        self.show_component(self._time_component)
        self.show_component(self._date_component)

    def render_panel(self, panel: HAUIConfigPanel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())

    def stop_panel(self, panel: HAUIConfigPanel):
        # cancel time and date timer
        if self._time_timer:
            self.app.cancel_timer(self._time_timer)
            self._time_timer = None
        if self._date_timer:
            self.app.cancel_timer(self._date_timer)
            self._date_timer = None

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
        self.set_component_text(self._time_component, time)

    def update_date(self):
        strftime_format = self.app.config.get("date_format")
        babel_format = self.app.config.get("date_format_babel")
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.set_component_text(self._date_component, date)

    def update_entities(self, entities: List[HAUIConfigEntity]):
        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self.update_main_weather(main)

        # forecast
        if self._show_forecast:
            forecast_entity = HAUIConfigEntity(
                self.app, {"entity": self.panel.get('forecast')})
            forecast = forecast_entity.get_entity_attr("forecast", [])
            for i in range(1, self.NUM_FORECAST + 1):
                forecast_data = forecast[i] if i < len(forecast) else None
                self.update_forecast(i, forecast_data)

    def update_main_weather(self, haui_entity: HAUIConfigEntity):
        # set up main weather details
        icon = haui_entity.get_icon()
        color = haui_entity.get_color()
        msg = haui_entity.get_value()
        self.set_component_text_color(self.ICO_MAIN, color)
        self.set_component_text(self.ICO_MAIN, icon)
        self.set_component_text(self.TXT_MAIN, msg)

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

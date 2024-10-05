from typing import List
import dateutil.parser as dp
import datetime

from ..mapping.background import BACKGROUNDS
from ..mapping.icon import WEATHER_MAPPING
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..helper.datetime import (
    get_time_localized, get_date_localized, format_datetime)
from ..abstract.panel import HAUIPanel
from ..abstract.entity import HAUIEntity

from . import HAUIPage


class ClockPage(HAUIPage):
    # main components
    TXT_TIME, TXT_DATE = (3, "tTime"), (4, "tDate")
    ICO_MAIN, TXT_MAIN, TXT_SUB = (5, "tMainIcon"), (6, "tMainText"), (7, "tSubText")
    # bottom weather forecast row
    F1_NAME, F2_NAME, F3_NAME = (
        (8, "f1Name"), (9, "f2Name"), (10, "f3Name"),
    )
    F1_ICO, F2_ICO, F3_ICO = (
        (11, "f1Icon"), (12, "f2Icon"), (13, "f3Icon"),
    )
    F1_VAL, F2_VAL, F3_VAL = (
        (14, "f1Val"), (15, "f2Val"), (16, "f3Val"),
    )
    F1_SUBVAL, F2_SUBVAL, F3_SUBVAL = (
        (17, "f1SubVal"), (18, "f2SubVal"), (19, "f3SubVal"),
    )

    NUM_FORECAST = 3

    _date_timer = None
    _time_timer = None
    _show_forecast = False
    _temp_unit = "°C"

    # panel

    def create_panel(self, panel: HAUIPanel):
        # setting: background
        # set before showing panel
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"clock.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel):
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
            self.hide_forecast()
        else:
            self.show_forecast()
        self.show_component(self.TXT_TIME)
        self.show_component(self.TXT_DATE)

    def render_panel(self, panel: HAUIPanel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())

    def stop_panel(self, panel: HAUIPanel):
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
        self.set_component_text(self.TXT_TIME, time)

    def update_date(self):
        strftime_format = self.app.config.get("date_format")
        babel_format = self.app.config.get("date_format_babel")
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.set_component_text(self.TXT_DATE, date)

    def update_entities(self, entities: List[HAUIEntity]):
        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self.update_main_weather(main)

        # forecast
        if self._show_forecast:
            forecast_entity = HAUIEntity(
                self.app, {"entity": self.panel.get('forecast')})
            forecast = forecast_entity.get_entity_attr("forecast", [])
            for i in range(1, self.NUM_FORECAST + 1):
                forecast_data = forecast[i] if i < len(forecast) else None
                self.update_forecast(i, forecast_data)

    def update_main_weather(self, haui_entity: HAUIEntity):
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

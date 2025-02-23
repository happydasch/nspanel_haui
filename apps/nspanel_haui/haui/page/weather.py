from typing import List, Optional
import dateutil.parser as dp
import datetime
import threading

from ..mapping.background import BACKGROUNDS
from ..mapping.icon import WEATHER_MAPPING
from ..mapping.color import COLORS
from ..mapping.const import ESP_RESPONSE, NOTIF_EVENT
from ..helper.icon import get_icon
from ..helper.datetime import get_time_localized, get_date_localized, format_datetime
from ..abstract.panel import HAUIPanel
from ..abstract.entity import HAUIEntity
from ..abstract.event import HAUIEvent

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
    TXT_NOTIF = (34, "tNotif")

    NUM_FORECAST = 5
    DISPLAY_UPDATE_INTERVAL = 1.0

    _timer_time = None
    _timer_date = None
    _timer_notifications = None
    _show_notifications = True
    _new_notifications = False
    _show_forecast = False
    _temp_unit = "°C"
    _weather_entity: Optional[HAUIEntity] = None

    # panel

    def create_panel(self, panel: HAUIPanel):
        # setting: background
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"weather.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._timer_time = self.app.run_minutely(self.callback_update_time, time)
        # setup date callback
        self._timer_date = self.app.run_hourly(self.callback_update_date, time)
        # entity listener
        self._handles = []
        found = False
        for entity in panel.get_entities():
            if entity.get_entity_type() == "weather":
                self.add_entity_listener(
                    entity.get_entity_id(), self.callback_weather, "temperature"
                )
                self.add_entity_listener(
                    entity.get_entity_id(), self.callback_weather, "pressure"
                )
                found = True
                break
        if not found:
            self.app.log.warning("No weather entity found in config")
        # setting: forecast
        if not panel.get("forecast", False):
            self.hide_forecast()
        else:
            self.show_forecast()
        # notification
        self._show_notifications = panel.get("show_notifications", True)
        self.set_function_component(
            self.TXT_NOTIF, self.TXT_NOTIF[1], visible=self._show_notifications
        )

    def render_panel(self, panel: HAUIPanel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())
        # notifications
        self.update_notifications()

    def stop_panel(self, panel: HAUIPanel):
        # cancel time and date timer
        if self._timer_time is not None:
            self.app.cancel_timer(self._timer_time)
            self._timer_time = None
        if self._timer_date is not None:
            self.app.cancel_timer(self._timer_date)
            self._timer_date = None
        # update display timer
        if self._timer_notifications is not None:
            self._timer_notifications.cancel()
            self._timer_notifications = None

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
        # if only one entry, create new entities which will be used for
        # forecast
        if len(entities) == 1:
            for i in range(self.NUM_FORECAST):
                config = {"entity": entities[0].get("entity"), "forecast_index": i}
                entities.append(HAUIEntity(self.app, config))

        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self._weather_entity = main
            self._temp_unit = main.get_entity_attr("temperature_unit", "°C")
            self.update_main_weather()

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
            forecast_entity = HAUIEntity(
                self.app, {"entity": self.panel.get("forecast")}
            )
            forecast = forecast_entity.get_entity_attr("forecast", [])
            for i in range(1, self.NUM_FORECAST + 1):
                forecast_data = forecast[i - 1] if i - 1 < len(forecast) else None
                self.update_forecast(i, forecast_data)

    def update_main_weather(self) -> None:
        if self._weather_entity is None:
            return
        # set up main weather details
        icon = self._weather_entity.get_icon()
        color = self._weather_entity.get_color()
        msg = self._weather_entity.get_entity_attr("temperature", "")
        msg_sub = self._weather_entity.get_entity_attr("pressure", "")
        if msg:
            msg = f"{msg}{self._temp_unit}"
        if msg_sub:
            pressure_unit = self._weather_entity.get_entity_attr("pressure_unit")
            msg_sub = f"{msg_sub}{pressure_unit}"
        self.update_function_component(
            self.ICO_MAIN[1], icon=icon, color=color, visible=self._show_weather
        )
        self.update_function_component(
            self.TXT_MAIN[1], text=msg, visible=self._show_temp
        )
        self.update_function_component(
            self.TXT_SUB[1], text=msg_sub, visible=self._show_temp
        )

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

    def update_info(self, idx, haui_entity: HAUIEntity):
        if idx < 1 or idx > 3:
            self.log("Weather Info uses index 1-3")
            return
        info_icon = getattr(self, f"D{idx}_ICO")
        info_val = getattr(self, f"D{idx}_VAL")
        self.set_component_text_color(info_icon, haui_entity.get_color())
        self.set_component_text(info_icon, haui_entity.get_icon())
        self.set_component_text(info_val, haui_entity.get_value())

    def update_notifications(self):
        if not self._show_notifications:
            return
        notification = self.app.controller["notification"]
        if self._new_notifications:
            color = COLORS["component_accent"]
        else:
            color = COLORS["component"]
        if self._new_notifications:
            if datetime.datetime.now().second % 2:
                visible = False
            else:
                visible = True
        else:
            visible = notification.has_notifications()
        notif_kwargs = {
            "icon": self.ICO_MESSAGE,
            "visible": visible,
            "color": color,
        }
        self.update_function_component(self.TXT_NOTIF[1], **notif_kwargs)
        if self._new_notifications:
            self._timer_notifications = threading.Timer(
                self.DISPLAY_UPDATE_INTERVAL, self.update_notifications
            )
            self._timer_notifications.start()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        if event.name in [
            ESP_RESPONSE["send_notification"],
            NOTIF_EVENT["notif_add"],
            NOTIF_EVENT["notif_remove"],
            NOTIF_EVENT["notif_clear"],
        ]:
            if event.name == NOTIF_EVENT["notif_add"]:
                self._new_notifications = True
            elif event.name == NOTIF_EVENT["notif_clear"]:
                self._new_notifications = False
            self.update_notifications()

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
        self.update_main_weather()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.TXT_NOTIF[1]:
            navigation = self.app.controller["navigation"]
            navigation.open_popup("popup_notification")

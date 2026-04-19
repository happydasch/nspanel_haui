import datetime
import threading

import dateutil.parser as dp

from ..abstract.entity import HAUIEntity
from ..abstract.event import HAUIEvent
from ..abstract.panel import HAUIPanel
from ..helper.datetime import format_datetime, get_date_localized, get_time_localized
from ..helper.icon import get_icon, parse_icon
from ..mapping.background import BACKGROUNDS
from ..mapping.color import COLORS
from ..mapping.const import ESP_RESPONSE, NOTIF_EVENT
from ..mapping.icon import WEATHER_MAPPING
from . import HAUIPage


class WeatherPage(HAUIPage):
    # time and date display
    TXT_TIME, TXT_DATE = (3, "tTime"), (4, "tDate")
    # main weather icon
    ICO_MAIN, TXT_MAIN, TXT_SUB = (5, "tMainIcon"), (6, "tMainText"), (7, "tSubText")
    # icons below main icon
    D1_ICO, D2_ICO = (8, "d1Icon"), (9, "d2Icon")
    D1_VAL, D2_VAL = (10, "d1Val"), (11, "d2Val")
    # bottom weather forecast row
    F1_NAME, F2_NAME, F3_NAME, F4_NAME, F5_NAME = (
        (12, "f1Name"),
        (13, "f2Name"),
        (14, "f3Name"),
        (15, "f4Name"),
        (16, "f5Name"),
    )
    F1_ICO, F2_ICO, F3_ICO, F4_ICO, F5_ICO = (
        (17, "f1Icon"),
        (18, "f2Icon"),
        (19, "f3Icon"),
        (20, "f4Icon"),
        (21, "f5Icon"),
    )
    F1_VAL, F2_VAL, F3_VAL, F4_VAL, F5_VAL = (
        (22, "f1Val"),
        (23, "f2Val"),
        (24, "f3Val"),
        (25, "f4Val"),
        (26, "f5Val"),
    )
    F1_SUBVAL, F2_SUBVAL, F3_SUBVAL, F4_SUBVAL, F5_SUBVAL = (
        (27, "f1SubVal"),
        (28, "f2SubVal"),
        (29, "f3SubVal"),
        (30, "f4SubVal"),
        (31, "f5SubVal"),
    )
    TXT_NOTIF = (32, "tNotif")
    # entities
    BTN_ENTITY_1, BTN_ENTITY_2, BTN_ENTITY_3 = (
        (33, "bEntity1"),
        (34, "bEntity2"),
        (35, "bEntity3"),
    )
    BTN_ENTITY_4, BTN_ENTITY_5, BTN_ENTITY_6 = (
        (36, "bEntity4"),
        (37, "bEntity5"),
        (38, "bEntity6"),
    )

    NUM_ENTITIES = 6
    NUM_FORECAST = 5
    DISPLAY_UPDATE_INTERVAL = 1.0

    # panel

    def start_page(self) -> None:
        self._timer_time: str | None = None
        self._timer_date: str | None = None
        self._timer_notifications: threading.Timer | None = None
        self._show_notifications = True
        self._new_notifications = False
        self._previous_forecast = None
        self._show_forecast = False
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._temp_precision = 1
        self._forecast_precision = 0
        self._weather_entity: HAUIEntity | None = None

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"weather.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel) -> None:
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
            self.app.log("WARNING: No weather entity found in config")
        # setting: temp_precision
        self._temp_precision = panel.get("temp_precision", self._temp_precision)
        # setting: forecast_precision
        self._forecast_precision = panel.get(
            "forecast_precision", self._forecast_precision
        )
        # setting: show_weather
        if not panel.get("show_weather", True):
            self._show_weather = False
        self.set_function_component(
            self.ICO_MAIN, self.ICO_MAIN[1], visible=self._show_weather
        )
        # setting: show_temp
        if not panel.get("show_temp", True):
            self._show_temp = False

        self.set_function_component(
            self.TXT_MAIN, self.TXT_MAIN[1], visible=self._show_temp
        )
        self.set_function_component(
            self.TXT_SUB, self.TXT_SUB[1], visible=self._show_temp
        )
        # setting: show_home_temp
        if panel.get("show_home_temp", False):
            self._show_home_temp = True
        # setting: forecast
        self._show_forecast = panel.get("show_forecast", False)
        if not self._show_forecast:
            self.hide_forecast()
        else:
            self.show_forecast()
        # main components
        self.set_function_component(self.TXT_TIME, self.TXT_TIME[1], visible=True)
        self.set_function_component(self.TXT_DATE, self.TXT_DATE[1], visible=True)
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
        timeformat = self.app.device_config.get("time_format")
        time = get_time_localized(timeformat)
        self.update_function_component(self.TXT_TIME[1], text=time)

    def update_date(self):
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.update_function_component(self.TXT_DATE[1], text=date)

    def update_entities(self, entities: list[HAUIEntity]):
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

        # next 2 are entities below main weather
        info = []
        for i in range(2):
            if len(entities) == 0:
                break
            info.append(entities.pop(0))
            if len(info) == 2:
                break
        for i in range(1, len(info) + 1):
            self.update_info(i, info[i - 1])

        # forecast
        if self._show_forecast and self._weather_entity is not None:
            weather_id = self._weather_entity.get_entity_id()
            forecast = None
            try:
                result = self.app.call_service(
                    "weather/get_forecasts",
                    target={"entity_id": weather_id},
                    service_data={"type": self._show_forecast},
                )
                forecast = result["result"]["response"][weather_id]["forecast"]
            except Exception:
                if self._previous_forecast is not None:
                    forecast = self._previous_forecast
                else:
                    # ATT: possible recursion
                    self.update_entities(entities=entities)
            if forecast is None:
                return
            for i in range(0, self.NUM_FORECAST):
                forecast_data = forecast[i] if i < len(forecast) else {}
                self.update_forecast(i, forecast_data)
            self._previous_forecast = forecast

    def update_main_weather(self) -> None:
        if self._weather_entity is None:
            return

        # set up main weather details
        name = self.app.device.get_name()
        icon = self._weather_entity.get_icon()
        color = self._weather_entity.get_color()
        temp_outside = round(
            float(self._weather_entity.get_entity_attr("temperature", "")),
            self._temp_precision,
        )
        msg = ""
        if self._show_home_temp:
            temp_inside_entity = self.app.get_entity(f"sensor.{name}_temperature")
            temp_inside: float | int = round(
                float(temp_inside_entity.get_state()), self._temp_precision
            )
            if not self._temp_precision:
                temp_inside = int(temp_inside)
            msg = (
                f"{parse_icon('mdi:home-thermometer')}{temp_inside}{self._temp_unit}  "
            )
        if not self._temp_precision:
            temp_outside = int(temp_outside)
        msg = f"{msg}{parse_icon('mdi:thermometer')}{temp_outside}{self._temp_unit}"
        msg_sub = self._weather_entity.get_entity_attr("pressure", "")
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

    def update_forecast(self, idx: int, data: dict) -> None:
        if idx < 0 or idx > self.NUM_FORECAST:
            self.log("Weather Forecast index outside bounds")
            return
        if data is None:
            self.log(f"No weather forecast for index {idx}")
            return
        forecast_idx = idx + 1
        forecast_temp = round(
            float(data.get("temperature", 20)), self._forecast_precision
        )
        forecast_mintemp = round(
            float(data.get("templow", 0)), self._forecast_precision
        )
        if not self._forecast_precision:
            forecast_temp = int(forecast_temp)
            forecast_mintemp = int(forecast_mintemp)

        forecast_name = getattr(self, f"F{forecast_idx}_NAME")
        forecast_icon = getattr(self, f"F{forecast_idx}_ICO")
        forecast_val = getattr(self, f"F{forecast_idx}_VAL")
        forecast_subval = getattr(self, f"F{forecast_idx}_SUBVAL")
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
        if idx < 1 or idx > 2:
            self.log(f"Weather Info uses index 1-2, got {idx}")
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
        self.send_cmd(f"ref {self.ICO_MAIN[1]}")

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

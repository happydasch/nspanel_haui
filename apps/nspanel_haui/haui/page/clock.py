from typing import List, Optional
import dateutil.parser as dp
import datetime
import threading

from ..mapping.background import BACKGROUNDS
from ..mapping.icon import WEATHER_MAPPING
from ..mapping.color import COLORS
from ..mapping.const import ESP_RESPONSE, NOTIF_EVENT
from ..helper.icon import get_icon, parse_icon
from ..helper.datetime import get_time_localized, get_date_localized, format_datetime
from ..abstract.panel import HAUIPanel
from ..abstract.entity import HAUIEntity
from ..abstract.event import HAUIEvent

from . import HAUIPage


class ClockPage(HAUIPage):
    # main components
    TXT_TIME, TXT_DATE = (3, "tTime"), (4, "tDate")
    ICO_MAIN, TXT_MAIN, TXT_SUB = (5, "tMainIcon"), (6, "tMainText"), (7, "tSubText")
    TXT_NOTIF = (8, "tNotif")
    # entities
    BTN_ENTITY_1, BTN_ENTITY_2, BTN_ENTITY_3 = (
        (9, "bEntity1"),
        (10, "bEntity2"),
        (11, "bEntity3"),
    )
    BTN_ENTITY_4, BTN_ENTITY_5, BTN_ENTITY_6 = (
        (12, "bEntity4"),
        (13, "bEntity5"),
        (14, "bEntity6"),
    )

    NUM_ENTITIES = 6
    DISPLAY_UPDATE_INTERVAL = 1.0

    _timer_date = None
    _timer_time = None
    _timer_notifications = None
    _show_notifications = True
    _new_notifications = False
    _show_weather = True
    _show_temp = True
    _show_home_temp = False
    _temp_unit = "°C"
    _temp_precision = 1
    _weather_entity: Optional[HAUIEntity] = None
    _entities: List[HAUIEntity] = []

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
        self._timer_time = self.app.run_minutely(self.callback_update_time, time)
        # date update callback
        self._timer_date = self.app.run_hourly(self.callback_update_date, time)
        # entity listeners
        for entity in panel.get_entities():
            if entity.get_entity_type() == "weather":
                self.add_entity_listener(
                    entity.get_entity_id(), self.callback_weather, "temperature"
                )
                self.add_entity_listener(entity.get_entity_id(), self.callback_weather, "pressure")
                break
        # setting: temp_precision
        self._temp_precision = panel.get("temp_precision", self._temp_precision)
        # setting: show_weather
        if not panel.get("show_weather", True):
            self._show_weather = False
        self.set_function_component(self.ICO_MAIN, self.ICO_MAIN[1], visible=self._show_weather)
        # setting: show_temp
        if not panel.get("show_temp", True):
            self._show_temp = False
        self.set_function_component(self.TXT_MAIN, self.TXT_MAIN[1], visible=self._show_temp)
        self.set_function_component(self.TXT_SUB, self.TXT_SUB[1], visible=self._show_temp)
        # setting: show_home_temp
        if panel.get("show_home_temp", False):
            self._show_home_temp = True
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

    def update_time(self):
        timeformat = self.app.config.get("time_format")
        time = get_time_localized(timeformat)
        self.update_function_component(self.TXT_TIME[1], text=time)

    def update_date(self):
        strftime_format = self.app.config.get("date_format")
        babel_format = self.app.config.get("date_format_babel")
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.update_function_component(self.TXT_DATE[1], text=date)

    def update_main_weather(self) -> None:
        if self._weather_entity is None:
            return

        # set up main weather details
        name = self.app.device.get_name()
        icon = self._weather_entity.get_icon()
        color = self._weather_entity.get_color()
        msg = round(
            float(self._weather_entity.get_entity_attr("temperature", "")), self._temp_precision
        )
        if not self._temp_precision:
            msg = int(msg)
        if msg:
            msg = f"{msg}{self._temp_unit}mdi:thermometer"
        if self._show_home_temp:
            internal_temp = self.app.get_entity(f"sensor.{name}_temperature")
            internal_temp = round(float(internal_temp.get_state()), self._temp_precision)
            if not self._temp_precision:
                internal_temp = int(internal_temp)
            if msg != "":
                msg = f"  {msg}"
            msg = f"{internal_temp}{self._temp_unit}mdi:home-thermometer{msg}"

        msg = parse_icon(msg)
        msg_sub = self._weather_entity.get_entity_attr("pressure", "")
        if msg_sub:
            pressure_unit = self._weather_entity.get_entity_attr("pressure_unit")
            msg_sub = f"{msg_sub}{pressure_unit}"
        self.update_function_component(
            self.ICO_MAIN[1], icon=icon, color=color, visible=self._show_weather
        )
        self.update_function_component(self.TXT_MAIN[1], text=msg, visible=self._show_temp)
        self.update_function_component(self.TXT_SUB[1], text=msg_sub, visible=self._show_temp)

    def update_entities(self, entities: List[HAUIEntity]) -> None:
        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self._weather_entity = main
            self._temp_unit = main.get_entity_attr("temperature_unit", "°C")
            self.update_main_weather()
        # entity buttons
        total_entities = len(self._entities)
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ""
            color = COLORS["text"]
            if i < total_entities:
                entity = self._entities[i]
                icon = entity.get_icon()
                color = entity.get_color()
                visible = True
            else:
                entity = None
            component = getattr(self, f"BTN_ENTITY_{i + 1}")
            self.set_function_component(
                component,
                component[1],
                "entity",
                entity=entity,
                icon=icon,
                color=color,
                visible=visible,
            )

    def update_notifications(self) -> None:
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

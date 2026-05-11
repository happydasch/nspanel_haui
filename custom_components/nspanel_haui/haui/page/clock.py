from __future__ import annotations

import datetime
import threading
from typing import Any

from ..abstract.event import HAUIEvent
from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..mapping.background import BACKGROUNDS
from ..mapping.color import COLORS
from ..mapping.const import ESPResponse, NotifEvent
from ..mapping.descriptor import PageDescriptor, PageOption
from ..utils.datetime import get_date_localized, get_time_localized
from ..utils.icon import parse_icon
from . import HAUIPage


class ClockPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="clock",
        page_name="clock",
        label="Clock",
        description="Digital clock with date and notification indicator.",
        options=[
            PageOption(
                key="background",
                kind="select",
                default="default",
                label="Background",
                choices=[
                    ("default", "Default"),
                    ("spring", "Spring"),
                    ("summer", "Summer"),
                    ("autumn", "Autumn"),
                    ("winter", "Winter"),
                    ("dog_1", "Dog 1"),
                    ("dog_2", "Dog 2"),
                    ("cat", "Cat"),
                ],
            ),
            PageOption(key="temp_precision", kind="int", default=1, label="Temperature precision"),
            PageOption(
                key="item",
                kind="item",
                domain="weather",
                label="Weather item",
            ),
            PageOption(key="show_weather", kind="bool", default=True, label="Show weather"),
            PageOption(key="show_temp", kind="bool", default=True, label="Show temperature"),
            PageOption(
                key="show_home_temp", kind="bool", default=False, label="Show home temperature"
            ),
            PageOption(
                key="show_notifications", kind="bool", default=True, label="Show notifications"
            ),
        ],
    )

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

    # panel

    def start_page(self) -> None:
        self._timer_weather_refresh: str | None = None
        self._timer_notifications: threading.Timer | None = None
        self._show_notifications = True
        self._new_notifications = False
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._temp_precision = 1
        self._weather_item: HAUIItem | None = None
        self._items: list[HAUIItem] = []

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background
        # set before showing panel
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"clock.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel) -> None:
        # time update callback (shared device-wide tick)
        self.app.subscribe_tick("minute", self.callback_update_time)
        # date update callback (shared device-wide tick)
        self.app.subscribe_tick("hour", self.callback_update_date)
        # item listeners
        for item in panel.get_items():
            if item.get_item_type() == "weather":
                self.add_item_listener(
                    item.get_item_id(), self.callback_weather, "temperature"
                )
                self.add_item_listener(item.get_item_id(), self.callback_weather, "pressure")
                break
        # periodic weather re-read (5-minute interval)
        # Reads the weather entity's current state even when no state change
        # event fires, keeping the displayed temperature/pressure current.
        self._timer_weather_refresh = self.app.run_every(
            self._callback_weather_refresh, "now+300", 300
        )
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
        # Pre-register entity button components so config_panel registers
        # touch callbacks.  No display kwargs here - update_items()
        # applies the correct state once entity data is available.
        for i in range(self.NUM_ENTITIES):
            component = getattr(self, f"BTN_ENTITY_{i + 1}")
            self.set_function_component(component, component[1], "item")

    def render_panel(self, panel: HAUIPanel) -> None:
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_items(panel.get_items())
        # notifications
        self.update_notifications()

    def stop_panel(self, panel: HAUIPanel) -> None:
        super().stop_panel(panel)
        while self._handles:
            self.remove_item_listener(self._handles.pop())
        # cancel time and date tick subscriptions
        self.app.unsubscribe_tick("minute", self.callback_update_time)
        self.app.unsubscribe_tick("hour", self.callback_update_date)
        if self._timer_weather_refresh is not None:
            self.app.cancel_timer(self._timer_weather_refresh)
            self._timer_weather_refresh = None
        # update display timer
        if self._timer_notifications is not None:
            self._timer_notifications.cancel()
            self._timer_notifications = None

    # misc

    def update_time(self) -> None:
        timeformat = self.app.device_config.get("time_format")
        timezone = self.app.hass.config.time_zone
        time = get_time_localized(timeformat, timezone)
        self.update_function_component(self.TXT_TIME[1], text=time)
        self.send_cmd(f"ref {self.ICO_MAIN[1]}")

    def update_date(self) -> None:
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get(
            "date_format_locale"
        ) or self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        timezone = self.app.hass.config.time_zone
        date = get_date_localized(strftime_format, babel_format, locale, timezone)
        self.update_function_component(self.TXT_DATE[1], text=date)

    def update_main_weather(self) -> None:
        if self._weather_item is None:
            return

        # set up main weather details
        name = self.app.device.get_name()
        icon = self._weather_item.get_icon()
        color = self._weather_item.get_color()
        try:
            temp_outside = round(
                float(self._weather_item.get_item_attr("temperature", "")),
                self._temp_precision,
            )
        except (ValueError, TypeError):
            return
        msg = ""
        if self._show_home_temp:
            temp_inside_entity = self.app.get_item(f"sensor.{name}_temperature")
            try:
                temp_inside: float | int | None = round(
                    float(temp_inside_entity.get_state()), self._temp_precision
                )
            except (ValueError, TypeError):
                temp_inside = None
            if temp_inside is not None:
                if not self._temp_precision:
                    temp_inside = int(temp_inside)
                msg = f"{parse_icon('mdi:home-thermometer')}{temp_inside}{self._temp_unit}  "
        if not self._temp_precision:
            temp_outside = int(temp_outside)
        msg = f"{msg}{parse_icon('mdi:thermometer')}{temp_outside}{self._temp_unit}"
        msg_sub = self._weather_item.get_item_attr("pressure", "")
        if msg_sub:
            pressure_unit = self._weather_item.get_item_attr("pressure_unit")
            msg_sub = f"{msg_sub}{pressure_unit}"
        self.update_function_component(self.TXT_MAIN[1], text=msg, visible=self._show_temp)
        self.update_function_component(self.TXT_SUB[1], text=msg_sub, visible=self._show_temp)
        self.update_function_component(
            self.ICO_MAIN[1], icon=icon, color=color, visible=self._show_weather
        )

    def update_items(self, items: list[HAUIItem]) -> None:
        # first item is main weather item
        main = None
        if len(items):
            main = items.pop(0)
        if main is not None:
            self._weather_item = main
            self._temp_unit = main.get_item_attr("temperature_unit", "°C")
            self.update_main_weather()
        # Store remaining items for entity button display
        self._items = items
        # item buttons
        total_items = len(self._items)
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ""
            color = COLORS["text"]
            if i < total_items:
                item = self._items[i]
                icon = item.get_icon()
                color = item.get_color()
                visible = True
            else:
                item = None
            component = getattr(self, f"BTN_ENTITY_{i + 1}")
            self.set_function_component(
                component,
                component[1],
                "item",
                item=item,
                icon=icon,
                color=color,
                visible=visible,
            )
            self.update_function_component(component[1])

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
        self.update_function_component(self.TXT_NOTIF[1], None, **notif_kwargs)
        if self._new_notifications:
            self._timer_notifications = threading.Timer(
                self.DISPLAY_UPDATE_INTERVAL, self.update_notifications
            )
            self._timer_notifications.start()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        if event.name in [
            ESPResponse.SEND_NOTIFICATION,
            NotifEvent.NOTIF_ADD,
            NotifEvent.NOTIF_REMOVE,
            NotifEvent.NOTIF_CLEAR,
        ]:
            if event.name == NotifEvent.NOTIF_ADD:
                self._new_notifications = True
            elif event.name == NotifEvent.NOTIF_CLEAR:
                self._new_notifications = False
            self.update_notifications()

    # callback

    def callback_update_time(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_time()

    def callback_update_date(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_date()

    def callback_weather(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_main_weather()

    def _callback_weather_refresh(self, cb_args: Any) -> None:
        """Periodic weather re-read callback (5-minute timer).

        Re-reads the weather entity's current state so the displayed
        temperature/pressure stays current even when the weather entity
        does not publish frequent state change events.
        """
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_main_weather()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.TXT_NOTIF[1]:
            navigation = self.app.controller["navigation"]
            navigation.open_popup("popup_notify")
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()

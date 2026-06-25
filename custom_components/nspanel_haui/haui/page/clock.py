from __future__ import annotations

from datetime import datetime
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.background import BACKGROUNDS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_MESSAGE
from ..utils.datetime import get_date_localized, get_time_localized
from ..utils.icon import parse_icon


class ClockPage(HAUIPage):
    PICTURE_BACKGROUND = True
    USE_SYSTEM_COLORS = False
    DESCRIPTOR = PageDescriptor(
        type_key="clock",
        page_name="clock",
        label=_("Clock"),
        description=_("Digital clock with date and notification indicator."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="weather",
                description=_("Weather entity to display temperature, pressure and weather icon."),
                section=_("Weather"),
            ),
            PageOption(
                key="background",
                kind="select",
                default="default",
                label=_("Background"),
                description=_("Background image theme for the clock display."),
                choices=[
                    ("default", _("Default")),
                    ("spring", _("Spring")),
                    ("summer", _("Summer")),
                    ("autumn", _("Autumn")),
                    ("winter", _("Winter")),
                    ("dog_1", _("Dog 1")),
                    ("dog_2", _("Dog 2")),
                    ("cat", _("Cat")),
                ],
                section=_("Appearance"),
            ),
            PageOption(
                key="show_weather",
                kind="bool",
                default=True,
                label=_("Show weather"),
                description=_("Show weather icon and temperature on the clock screen."),
                section=_("Weather"),
            ),
            PageOption(
                key="show_temp",
                kind="bool",
                default=True,
                label=_("Show temperature"),
                description=_("Show temperature value text on the clock screen."),
                section=_("Weather"),
            ),
            PageOption(
                key="show_home_temp",
                kind="bool",
                default=False,
                label=_("Show home temperature"),
                description=_("Show internal NSPanel temperature alongside weather temperature."),
                section=_("Weather"),
            ),
            PageOption(
                key="weather_icons",
                kind="select",
                default="color",
                label=_("Weather icon color"),
                description=_("Use condition-based colors or monochrome for the weather icon."),
                choices=[("color", _("Color")), ("monochrome", _("Monochrome"))],
                section=_("Weather"),
            ),
            PageOption(
                key="temp_precision",
                kind="int",
                default=1,
                label=_("Temperature precision"),
                description=_("Number of decimal places for temperature display (0 = whole number)."),
                section=_("Precision"),
            ),
            PageOption(
                key="show_notifications",
                kind="bool",
                default=True,
                label=_("Show notifications"),
                description=_("Show notification indicator when there are pending notifications."),
                section=_("Notifications"),
            ),
        ],
        icon="mdi:clock-outline",
        has_header=False,
    )

    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        t_time=Component(3, "tTime"),
        t_date=Component(4, "tDate"),
        t_main_icon=Component(5, "tMainIcon"),
        t_main_text=Component(6, "tMainText"),
        t_sub_text=Component(7, "tSubText"),
        t_notif=Component(8, "tNotif"),
        btn_entity_1=Component(9, "bEntity1"),
        btn_entity_2=Component(10, "bEntity2"),
        btn_entity_3=Component(11, "bEntity3"),
        btn_entity_4=Component(12, "bEntity4"),
        btn_entity_5=Component(13, "bEntity5"),
        btn_entity_6=Component(14, "bEntity6"),
    )

    NUM_ENTITIES = 6
    DISPLAY_UPDATE_INTERVAL = 1.0

    # panel
    def prepare(self) -> None:

        self._show_notifications = True
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._temp_precision = 1
        self._background = "default"
        self._weather_icons_mode = "color"
        self._weather_item: HAUIItem | None = None
        self._items: list[HAUIItem] = []

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background (rendered in start_panel after page is confirmed)
        self._background = self.render_template(panel.get("background", "default"), False)

    def start_panel(self, panel: HAUIPanel) -> None:
        # setting: background — set before rendering content
        if self._background in BACKGROUNDS:
            self.send_cmd(f"clock.background.val={BACKGROUNDS[self._background]}")
        # time update callback (shared device-wide tick)
        self.app.subscribe_tick("minute", self.callback_update_time)
        # date update callback (shared device-wide tick)
        self.app.subscribe_tick("hour", self.callback_update_date)
        # item listeners
        for item in self._build_items_from_panel(panel, "item", "items"):
            if item.get_item_type() == "weather":
                self.add_item_listener(item.get_item_id(), self.callback_weather, "temperature")
                self.add_item_listener(item.get_item_id(), self.callback_weather, "pressure")
                break
        # Register notification indicator with the shared blinker
        self.app.controller["notification"].set_blinker_callback(self._refresh_notif)
        # setting: temp_precision
        self._temp_precision = int(panel.get("temp_precision", 1))
        # setting: show_weather
        self._show_weather = panel.get("show_weather", True)
        self.set_function_component(
            self.COMPONENTS.t_main_icon, self.COMPONENTS.t_main_icon[1], visible=self._show_weather
        )
        # setting: show_temp
        self._show_temp = panel.get("show_temp", True)
        self.set_function_component(
            self.COMPONENTS.t_main_text, self.COMPONENTS.t_main_text[1], visible=self._show_temp
        )
        self.set_function_component(
            self.COMPONENTS.t_sub_text, self.COMPONENTS.t_sub_text[1], visible=self._show_temp
        )
        # setting: show_home_temp
        self._show_home_temp = panel.get("show_home_temp", False)
        # setting: weather_icons
        self._weather_icons_mode = panel.get("weather_icons", "color")
        # main components
        self.set_function_component(self.COMPONENTS.t_time, self.COMPONENTS.t_time[1], visible=True)
        self.set_function_component(self.COMPONENTS.t_date, self.COMPONENTS.t_date[1], visible=True)
        # notification
        self._show_notifications = panel.get("show_notifications", True)
        self.set_function_component(
            self.COMPONENTS.t_notif, self.COMPONENTS.t_notif[1], visible=self._show_notifications
        )
        # Pre-register entity button components so config_panel registers
        # touch callbacks.  Start hidden — update_items() applies the
        # correct visible/icon/color state once entity data is available.
        for i in range(self.NUM_ENTITIES):
            component = getattr(self.COMPONENTS, f"btn_entity_{i + 1}")
            self.set_function_component(component, component.name, "item", visible=False)

    def render_panel(self, panel: HAUIPanel) -> None:
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_items(self._build_items_from_panel(panel, "item", "items"))
        # notifications
        self.app.controller["notification"].blinker.refresh()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel time and date tick subscriptions
        self.app.unsubscribe_tick("minute", self.callback_update_time)
        self.app.unsubscribe_tick("hour", self.callback_update_date)
        # unregister notification indicator from shared blinker
        self.app.controller["notification"].clear_blinker_callback()

    # misc

    def update_time(self) -> None:
        timeformat = self.app.device_config.get("time_format")
        timezone = self.app.hass.config.time_zone
        time = get_time_localized(timeformat, timezone)
        self.update_function_component(self.COMPONENTS.t_time[1], text=time)
        self.send_cmd(f"ref {self.COMPONENTS.t_main_icon[1]}")

    def update_date(self) -> None:
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get(
            "date_format_locale"
        ) or self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        timezone = self.app.hass.config.time_zone
        date = get_date_localized(strftime_format, babel_format, locale, timezone)
        self.update_function_component(self.COMPONENTS.t_date[1], text=date)

    def update_main_weather(self) -> None:
        if self._weather_item is None:
            return

        # set up main weather details
        name = self.app.device.get_name()
        name_slug = name.lower().replace("-", "_").replace(" ", "_")
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
            temp_inside_entity = self.app.get_item(f"sensor.{name_slug}_temperature")
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
        self.update_function_component(
            self.COMPONENTS.t_main_text[1], text=msg, visible=self._show_temp
        )
        self.update_function_component(
            self.COMPONENTS.t_sub_text[1], text=msg_sub, visible=self._show_temp
        )
        self.update_function_component(
            self.COMPONENTS.t_main_icon[1],
            icon=icon,
            color=None if self._weather_icons_mode == "monochrome" else color,
            visible=self._show_weather,
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
            color = self.get_color("text")
            if i < total_items:
                item = self._items[i]
                icon = item.get_icon()
                color = item.get_color()
                visible = True
            else:
                item = None
            component = getattr(self.COMPONENTS, f"btn_entity_{i + 1}")
            self.set_function_component(
                component,
                component.name,
                "item",
                item=item,
                icon=icon,
                color=color,
                visible=visible,
            )
            self.update_function_component(component.name)

    def _refresh_notif(self) -> None:
        if not self._show_notifications:
            return
        notification = self.app.controller["notification"]
        notif_blinker = notification.blinker
        if notif_blinker.new_notifications:
            color = self.get_color("component_accent")
            visible = datetime.now().second % 2 == 0
        else:
            color = self.get_color("component_text")
            visible = notification.has_notifications()
        # Batch the single notification-icon update so it doesn't interleave
        # with a panel render in progress.
        with self.rec_cmd:
            self.update_function_component(
                self.COMPONENTS.t_notif[1],
                icon=ICO_MESSAGE,
                visible=visible,
                color=color,
            )

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)

    # callback

    def callback_update_time(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        # Batch time update commands so they don't interleave with a panel
        # render in progress on another executor thread.
        with self.rec_cmd:
            self.update_time()

    def callback_update_date(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self.update_date()

    def callback_weather(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self.update_main_weather()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.COMPONENTS.t_notif[1]:
            navigation = self.app.controller["navigation"]
            navigation.open_panel(SysPanelKey.POPUP_NOTIFY)
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..abstract.mixins.cycle_cards_mixin import CARD_OPTIONS, Card, CardBox, CycleCardsMixin
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_MESSAGE
from ..utils.icon import parse_icon
from ..utils.text import TextBox
from ..utils.value import format_number
from .clock_common import (
    background_commands,
    background_option,
    readable_foreground_color,
    release_ticks,
    set_background_mode,
    subscribe_ticks,
)


class ClockPage(CycleCardsMixin, HAUIPage):
    USE_SYSTEM_COLORS = False
    DESCRIPTOR = PageDescriptor(
        type_key="clock",
        page_name="clock",
        page_id=7,
        label=_("Clock"),
        description=_("Digital clock with date and notification indicator."),
        options=[
            background_option(),
            *CARD_OPTIONS,
            PageOption(
                key="item",
                kind="item",
                domain="weather",
                description=_("Weather entity to display temperature, pressure and weather icon."),
                section=_("Weather"),
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
                key="inside_temp_item",
                kind="item",
                domain="sensor",
                label=_("Inside temperature sensor"),
                description=_("Leave empty to use the NSPanel's internal temperature sensor."),
                section=_("Temperature"),
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
                key="items",
                kind="item_list",
                max_items=6,
                label=_("Items"),
                description=_("Items to display at the bottom (6 max)."),
                section=_("Items"),
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

    # no header: the page has no function buttons, ids 3-6 are other widgets
    COMPONENTS = ComponentRegistry(
        t_time=Component(3, "tTime"),
        t_date=Component(4, "tDate"),
        t_main_icon=Component(5, "tMainIcon"),
        t_main_text=Component(6, "tMainText"),
        t_sub_text=Component(7, "tSubText"),
        btn_entity_1=Component(8, "bEntity1"),
        btn_entity_2=Component(9, "bEntity2"),
        btn_entity_3=Component(10, "bEntity3"),
        btn_entity_4=Component(11, "bEntity4"),
        btn_entity_5=Component(12, "bEntity5"),
        btn_entity_6=Component(13, "bEntity6"),
    )

    NUM_ENTITIES = 6
    TEMP_PRECISION = 0
    # tTime and tDate per orientation (w, h, borderw, txt_maxl; font), as in the HMIs
    CARD_BOXES = {
        "landscape": {
            "tTime": CardBox(TextBox(450, 140, 2, 10), 7),
            "tDate": CardBox(TextBox(450, 32, 2, 40), 1),
        },
        "portrait": {
            "tTime": CardBox(TextBox(320, 140, 2, 10), 6),
            "tDate": CardBox(TextBox(320, 32, 2, 40), 1),
        },
    }

    # panel
    def prepare(self) -> None:
        self._show_notifications = True
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._weather_icons_mode = "color"
        self._light_background = False
        self._weather_item: HAUIItem | None = None
        self._items: list[HAUIItem] = []
        self._init_cards()

    def page_load_commands(self, panel: HAUIPanel) -> list[str]:
        return [*super().page_load_commands(panel), *background_commands(self, panel)]

    def start_panel(self, panel: HAUIPanel) -> None:
        set_background_mode(self, panel)
        subscribe_ticks(self)
        for component in (self.COMPONENTS.t_time, self.COMPONENTS.t_date):
            self.set_component_text_color(component, self.get_color("text"))
        # weather item listeners
        weather_item = self._get_weather_item(panel)
        if weather_item is not None:
            self.add_item_listener(weather_item.get_item_id(), self.callback_weather, "temperature")
            self.add_item_listener(weather_item.get_item_id(), self.callback_weather, "pressure")
        # item buttons follow their entities' state
        self.listen_items(
            self._build_items_from_panel(panel, "items"), lambda: self.update_items(self._items)
        )
        # Register notification indicator with the shared blinker
        self.app.controller["notification"].set_blinker_callback(self._refresh_notif)
        # setting: show_weather
        self._show_weather = panel.get("show_weather", True)
        self.set_function_component(
            self.COMPONENTS.t_main_icon,
            self.COMPONENTS.t_main_icon.name,
            visible=self._show_weather,
        )
        # setting: show_temp
        self._show_temp = panel.get("show_temp", True)
        # setting: show_home_temp
        self._show_home_temp = panel.get("show_home_temp", False)
        # setting: weather_icons
        self._weather_icons_mode = panel.get("weather_icons", "color")
        self._start_cards(panel, has_weather=weather_item is not None)
        # Tap-to-advance on the big time area
        self.on_release(
            {self.COMPONENTS.t_time: self._advance_card},
        )
        # setting: show_temp (header temp/pressure text only, independent of the Time cards)
        self.set_function_component(
            self.COMPONENTS.t_main_text,
            self.COMPONENTS.t_main_text.name,
            visible=self._show_temp,
        )
        self.set_function_component(
            self.COMPONENTS.t_sub_text,
            self.COMPONENTS.t_sub_text.name,
            visible=self._show_temp,
        )
        # notification (shares t_main_icon with the weather icon)
        self._show_notifications = panel.get("show_notifications", True)
        # Pre-register entity button components so config_panel registers
        # touch callbacks.  Start hidden — update_items() applies the
        # correct visible/icon/color state once entity data is available.
        for i in range(self.NUM_ENTITIES):
            component = getattr(self.COMPONENTS, f"btn_entity_{i + 1}")
            self.set_function_component(component, component.name, "item", visible=False)

    def render_panel(self, panel: HAUIPanel) -> None:
        # weather header first: the temperature cards read this panel's item
        self.set_weather_item(self._get_weather_item(panel))
        self._render_cards()
        # item buttons
        self.update_items(self._build_items_from_panel(panel, "items"))
        # notifications
        self.app.controller["notification"].blinker.refresh()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        self._stop_cards()
        release_ticks(self)

    # misc

    def update_main_weather(self) -> None:
        if self._weather_item is None:
            self.update_function_component(self.COMPONENTS.t_main_icon.name, visible=False)
            return

        # set up main weather details
        icon = self._weather_item.get_icon()
        color = readable_foreground_color(
            self._weather_item.get_color(scheme="light" if self._light_background else "dark"),
            self._light_background,
            self.get_color("text"),
        )
        try:
            temp_outside_str = self._weather_item.get_item_attr("temperature", "")
            # compare against empty values: 0 °C is falsy but a real temperature
            temp_outside = (
                None
                if temp_outside_str in (None, "")
                else round(float(temp_outside_str), self.TEMP_PRECISION)
            )
        except ValueError, TypeError:
            temp_outside = None
        msg = ""
        if self._show_home_temp:
            inside_temp_id = self.get_inside_temp_entity_id(self.panel)
            temp_inside_state = (
                self.app.get_item(inside_temp_id).get_state()
                if inside_temp_id is not None
                else None
            )
            if temp_inside_state not in (None, "", "unavailable", "unknown"):
                try:
                    temp_inside: float | int | None = round(
                        float(temp_inside_state), self.TEMP_PRECISION
                    )
                except ValueError, TypeError:
                    temp_inside = None
                if temp_inside is not None:
                    if not self.TEMP_PRECISION:
                        temp_inside = int(temp_inside)
                    msg = f"{parse_icon('mdi:home-thermometer')}{temp_inside}{self._temp_unit}  "
        if temp_outside is not None:
            if not self.TEMP_PRECISION:
                temp_outside = int(temp_outside)
            msg = f"{msg}{parse_icon('mdi:thermometer')}{temp_outside}{self._temp_unit}"
        msg_sub = self._weather_item.get_item_attr("pressure", "")
        if msg_sub:
            pressure_unit = self._weather_item.get_item_attr("pressure_unit")
            msg_sub = f"{format_number(msg_sub)}{pressure_unit}"
        # Hide the text widgets only when there is nothing to show at all; the
        # weather icon stays visible either way.
        has_text = bool(msg or msg_sub)
        self.update_function_component(
            self.COMPONENTS.t_main_text.name, text=msg, visible=self._show_temp and has_text
        )
        self.update_function_component(
            self.COMPONENTS.t_sub_text.name, text=msg_sub, visible=self._show_temp and has_text
        )
        self.update_function_component(
            self.COMPONENTS.t_main_icon.name,
            icon=icon,
            color=None if self._weather_icons_mode == "monochrome" else color,
            visible=self._show_weather,
        )

    def _get_weather_item(self, panel: HAUIPanel) -> HAUIItem | None:
        return next(
            (
                item
                for item in self._build_items_from_panel(panel, "item")
                if item.get_item_type() == "weather" and item.has_item()
            ),
            None,
        )

    def set_weather_item(self, item: HAUIItem | None) -> None:
        self._weather_item = item
        if item is not None:
            self._temp_unit = item.get_item_attr("temperature_unit", "°C")
        self.update_main_weather()

    def update_items(self, items: list[HAUIItem]) -> None:
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
                color = readable_foreground_color(
                    item.get_color(scheme="light" if self._light_background else "dark"),
                    self._light_background,
                    self.get_color("text"),
                )
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
        """Show the notification bell on t_main_icon, or fall back to the weather icon."""
        if not self._show_notifications:
            return
        notification = self.app.controller["notification"]
        notif_blinker = notification.blinker
        if notif_blinker.new_notifications:
            show_bell = datetime.now().second % 2 == 0
            color = self.get_color("component_accent")
        else:
            show_bell = notification.has_notifications()
            color = self.get_color("component_text")
        # Batch the single icon update so it doesn't interleave with a panel
        # render in progress.
        with self.rec_cmd:
            if show_bell:
                self.update_function_component(
                    self.COMPONENTS.t_main_icon.name,
                    icon=ICO_MESSAGE,
                    visible=True,
                    color=color,
                )
            else:
                self.update_main_weather()

    # callback

    def callback_update_time(self, cb_args: dict[str, Any]) -> None:
        with self.rec_cmd:
            self._refresh_card(Card("time"))

    def callback_update_date(self, cb_args: dict[str, Any]) -> None:
        # the time card shows the date below the time
        with self.rec_cmd:
            self._refresh_card(Card("time"), Card("date"))

    def callback_weather(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        with self.rec_cmd:
            self.update_main_weather()
            self._refresh_card(Card("outside_temperature"))

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        notification = self.app.controller["notification"]
        if fnc_id == self.COMPONENTS.t_main_icon.name and notification.has_notifications():
            notification.open_notifications()
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                self.execute_item(item)

from __future__ import annotations

import zoneinfo
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
from ..utils.datetime import format_datetime, get_date_localized, get_time_localized
from ..utils.icon import parse_icon


class ClockPage(HAUIPage):
    PICTURE_BACKGROUND = True
    USE_SYSTEM_COLORS = False
    DESCRIPTOR = PageDescriptor(
        type_key="clock",
        page_name="clock",
        page_id=7,
        label=_("Clock"),
        description=_("Digital clock with date and notification indicator."),
        options=[
            PageOption(
                key="background",
                kind="select",
                default="dark",
                label=_("Background"),
                description=_("Background image theme for the clock display."),
                choices=[
                    ("dark", _("Dark")),
                    ("modern", _("Modern")),
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
                key="show_time_time",
                kind="bool",
                default=True,
                label=_("Show time"),
                description=_("Show current time as a cycle card."),
                section=_("Time"),
            ),
            PageOption(
                key="show_time_date",
                kind="bool",
                default=True,
                label=_("Show date"),
                description=_("Show current date as a cycle card."),
                section=_("Time"),
            ),
            PageOption(
                key="show_time_outside_temp",
                kind="bool",
                default=True,
                label=_("Show outside temperature"),
                description=_("Show outside temperature as a cycle card."),
                section=_("Time"),
            ),
            PageOption(
                key="show_time_inside_temp",
                kind="bool",
                default=False,
                label=_("Show inside temperature"),
                description=_("Show inside (NSPanel) temperature as a cycle card."),
                section=_("Time"),
            ),
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
        btn_entity_1=Component(8, "bEntity1"),
        btn_entity_2=Component(9, "bEntity2"),
        btn_entity_3=Component(10, "bEntity3"),
        btn_entity_4=Component(11, "bEntity4"),
        btn_entity_5=Component(12, "bEntity5"),
        btn_entity_6=Component(13, "bEntity6"),
    )

    NUM_ENTITIES = 6
    DISPLAY_UPDATE_INTERVAL = 1.0
    TEMP_PRECISION = 0

    # Card cycle constants
    _CARD_INTERVAL = 5  # seconds between card advances during cycling
    _CARD_PAUSE_DURATION = 15  # seconds to pause on the first card after a full cycle

    # panel
    def prepare(self) -> None:
        self._show_notifications = True
        self._show_time_time = True
        self._show_time_date = True
        self._show_time_inside_temp = False
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._background = "dark"
        self._weather_icons_mode = "color"
        self._weather_item: HAUIItem | None = None
        self._items: list[HAUIItem] = []
        # Card cycling state
        self._cycle_cards: list[str] = ["time"]
        self._current_card_index: int = 0
        self._card_timer: int = 0
        self._cycle_state: str = "cycling"  # "cycling" or "paused"
        self._tick_handle: Any = None

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background (rendered in start_panel after page is confirmed)
        self._background = self.render_template(panel.get("background", "dark"), False)

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
        # setting: show_weather
        self._show_weather = panel.get("show_weather", True)
        self.set_function_component(
            self.COMPONENTS.t_main_icon, self.COMPONENTS.t_main_icon[1], visible=self._show_weather
        )
        # setting: show_temp
        self._show_temp = panel.get("show_temp", True)
        # setting: show_home_temp
        self._show_home_temp = panel.get("show_home_temp", False)
        # setting: weather_icons
        self._weather_icons_mode = panel.get("weather_icons", "color")
        # Read card enable flags from panel config
        self._show_time_time = panel.get("show_time_time", True)
        self._show_time_date = panel.get("show_time_date", True)
        self._show_time_outside_temp = panel.get("show_time_outside_temp", True)
        self._show_time_inside_temp = panel.get("show_time_inside_temp", False)
        # Build cycle list from enabled cards
        self._cycle_cards = []
        if self._show_time_time:
            self._cycle_cards.append("time")
        if self._show_time_date:
            self._cycle_cards.append("date")
        if self._show_time_outside_temp:
            self._cycle_cards.append("outside_temperature")
        if self._show_time_inside_temp:
            self._cycle_cards.append("inside_temperature")
        if not self._cycle_cards:
            self._cycle_cards = ["time"]
        # Reset card position
        self._current_card_index = 0
        self._card_timer = 0
        self._cycle_state = "cycling"
        # Start cycle timer if multiple cards enabled
        if self._tick_handle is None and len(self._cycle_cards) > 1:
            self._tick_handle = self.app.run_every(self._tick, 0, 1.0)
        # Tap-to-advance on the big time area
        self.on_release(
            {self.COMPONENTS.t_time: self._advance_card},
        )
        # setting: show_temp (header temp/pressure text only, independent of the Time cards)
        self.set_function_component(
            self.COMPONENTS.t_main_text,
            self.COMPONENTS.t_main_text[1],
            visible=self._show_temp,
        )
        self.set_function_component(
            self.COMPONENTS.t_sub_text,
            self.COMPONENTS.t_sub_text[1],
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
        # Reset and render current card
        self._current_card_index = 0
        self._card_timer = 0
        self._cycle_state = "cycling"
        self._render_cycle_card()
        # weather header
        self.update_items(self._build_items_from_panel(panel, "item", "items"))
        # notifications
        self.app.controller["notification"].blinker.refresh()

    def _get_date_text(self, timezone: str) -> str:
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get(
            "date_format_locale"
        ) or self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        return get_date_localized(strftime_format, babel_format, locale, timezone)

    def _get_short_date_text(self, timezone: str) -> str:
        """Short date that fits in tTime (max 10 chars)."""
        now = datetime.now(zoneinfo.ZoneInfo(timezone))
        # "Mon 16" style — ~7 chars, localized weekday abbreviation
        dow = format_datetime(now, "%a", "E", self.get_locale())
        return f"{dow} {now.day}"

    def _card_text_time(self, timeformat: str, timezone: str) -> tuple[str, str]:
        return get_time_localized(timeformat, timezone), self._get_date_text(timezone)

    def _card_text_date(self, timezone: str) -> tuple[str, str]:
        return self._get_short_date_text(timezone), self._get_date_text(timezone)

    def _card_text_outside_temperature(self) -> tuple[str, str]:
        label = self.translate("OUTSIDE")
        if self._weather_item is None:
            return "--°C", label
        try:
            temp = round(
                float(self._weather_item.get_item_attr("temperature", "")), self.TEMP_PRECISION
            )
        except (ValueError, TypeError):
            return "--°C", label
        if not self.TEMP_PRECISION:
            temp = int(temp)
        return f"{temp}{self._temp_unit}", label

    def _card_text_inside_temperature(self) -> tuple[str, str]:
        label = self.translate("INSIDE")
        name_slug = self.app.device.get_name().lower().replace("-", "_").replace(" ", "_")
        temp_inside_entity = self.app.get_item(f"sensor.{name_slug}_temperature")
        try:
            temp = round(float(temp_inside_entity.get_state()), self.TEMP_PRECISION)
        except (ValueError, TypeError):
            return "--°C", label
        unit = self._temp_unit if self._weather_item is not None else "°C"
        if not self.TEMP_PRECISION:
            temp = int(temp)
        return f"{temp}{unit}", label

    def _render_cycle_card(self) -> None:
        """Render the current cycle card in the big text area."""
        if not self._cycle_cards or self._current_card_index >= len(self._cycle_cards):
            return
        card = self._cycle_cards[self._current_card_index]
        timezone = self.app.hass.config.time_zone
        if card == "time":
            timeformat = self.app.device_config.get("time_format")
            main_text, sub_text = self._card_text_time(timeformat, timezone)
        elif card == "date":
            main_text, sub_text = self._card_text_date(timezone)
        elif card == "outside_temperature":
            main_text, sub_text = self._card_text_outside_temperature()
        elif card == "inside_temperature":
            main_text, sub_text = self._card_text_inside_temperature()
        else:
            return
        self.set_function_component(self.COMPONENTS.t_time, self.COMPONENTS.t_time[1], visible=True)
        self.update_function_component(self.COMPONENTS.t_time[1], text=main_text)
        self.set_function_component(self.COMPONENTS.t_date, self.COMPONENTS.t_date[1], visible=True)
        self.update_function_component(self.COMPONENTS.t_date[1], text=sub_text)
        self.send_cmd(f"ref {self.COMPONENTS.t_main_icon[1]}")

    def _tick(self, _data: dict | None = None) -> None:
        """Called every second. Advance cycle card when interval elapses."""
        if self.app.device.device_info.get("display_state") == "off":
            return
        self._card_timer += 1
        threshold = (
            self._CARD_PAUSE_DURATION if self._cycle_state == "paused" else self._CARD_INTERVAL
        )
        if self._card_timer >= threshold:
            with self.rec_cmd:
                self._advance_card()

    def _advance_card(self, _event: HAUIEvent | None = None) -> None:
        """Advance to the next cycle card or enter/exit pause state."""
        if self._cycle_state == "paused":
            # Pause period over — start a new cycle from the beginning
            self._cycle_state = "cycling"
            self._current_card_index = 0
            self._card_timer = 0
            self._render_cycle_card()
            return

        next_index = self._current_card_index + 1
        if next_index >= len(self._cycle_cards):
            # Last card shown — enter pause on the first card
            self._cycle_state = "paused"
            self._current_card_index = 0
            self._card_timer = 0
            self._render_cycle_card()
            return

        self._current_card_index = next_index
        self._card_timer = 0
        self._render_cycle_card()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel cycle timer
        if self._tick_handle is not None:
            self.app.cancel_timer(self._tick_handle)
            self._tick_handle = None
        # cancel time and date tick subscriptions
        self.app.unsubscribe_tick("minute", self.callback_update_time)
        self.app.unsubscribe_tick("hour", self.callback_update_date)
        # unregister notification indicator from shared blinker
        self.app.controller["notification"].clear_blinker_callback()

    # misc

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
                self.TEMP_PRECISION,
            )
        except (ValueError, TypeError):
            return
        msg = ""
        if self._show_home_temp:
            temp_inside_entity = self.app.get_item(f"sensor.{name_slug}_temperature")
            try:
                temp_inside: float | int | None = round(
                    float(temp_inside_entity.get_state()), self.TEMP_PRECISION
                )
            except (ValueError, TypeError):
                temp_inside = None
            if temp_inside is not None:
                if not self.TEMP_PRECISION:
                    temp_inside = int(temp_inside)
                msg = f"{parse_icon('mdi:home-thermometer')}{temp_inside}{self._temp_unit}  "
        if not self.TEMP_PRECISION:
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
                    self.COMPONENTS.t_main_icon[1],
                    icon=ICO_MESSAGE,
                    visible=True,
                    color=color,
                )
            else:
                self.update_main_weather()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)

    # callback

    def callback_update_time(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self._render_cycle_card()

    def callback_update_date(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self._render_cycle_card()

    def callback_weather(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self.update_main_weather()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        notification = self.app.controller["notification"]
        if (
            fnc_id == self.COMPONENTS.t_main_icon[1]
            and notification.has_notifications()
        ):
            navigation = self.app.controller["navigation"]
            if len(notification.get_notifications()) == 1:
                notif = notification.get_notifications()[0]
                navigation.open_panel(
                    SysPanelKey.POPUP_NOTIFY,
                    icon=notif[2],
                    title=notif[0],
                    notification=notif[1],
                    close_on_button=True,
                    close_timeout=notif[3] if notif[3] > 0 else 0,
                )
            else:
                notification.open_notification_list()
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import dateutil.parser as dp

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.background import BACKGROUNDS
from ..mapping.color import WEATHER_COLORS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icon_mapping import WEATHER_MAPPING
from ..mapping.icons import ICO_MESSAGE
from ..utils.datetime import format_datetime, get_date_localized, get_time_localized
from ..utils.icon import get_icon, parse_icon

if TYPE_CHECKING:
    pass


class WeatherPage(HAUIPage):
    PICTURE_BACKGROUND = True
    USE_SYSTEM_COLORS = False
    DESCRIPTOR = PageDescriptor(
        type_key="weather",
        page_name="weather",
        label=_("Weather"),
        description=_("Weather display with time, date and forecast."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="weather",
                description=_("Weather entity to display conditions, temperature and forecast."),
                section=_("Items"),
            ),
            PageOption(
                key="info_items",
                kind="item_list",
                label=_("Info Items"),
                description=_("Additional sensor entities to display as info panels (max 2)."),
                section=_("Items"),
                max_items=2,
            ),
            PageOption(
                key="background",
                kind="select",
                default="default",
                label=_("Background"),
                description=_("Background image theme for the weather display."),
                section=_("Appearance"),
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
            ),
            PageOption(
                key="forecast_type",
                kind="select",
                default="",
                label=_("Forecast type"),
                description=_("Show daily or hourly weather forecast on the bottom row."),
                section=_("Appearance"),
                choices=[("", _("Off")), ("daily", _("Daily")), ("hourly", _("Hourly"))],
            ),
            PageOption(
                key="show_weather",
                kind="bool",
                default=True,
                label=_("Show weather"),
                description=_("Show the main weather icon and condition text."),
                section=_("Appearance"),
            ),
            PageOption(
                key="weather_icons",
                kind="select",
                default="color",
                label=_("Weather icon color"),
                description=_(
                    "Use condition-based colors or monochrome (text color) for weather icons."
                ),
                choices=[("color", _("Color")), ("monochrome", _("Monochrome"))],
                section=_("Appearance"),
            ),
            PageOption(
                key="show_temp",
                kind="bool",
                default=True,
                label=_("Show temperature"),
                description=_("Show the current temperature value."),
                section=_("Appearance"),
            ),
            PageOption(
                key="show_home_temp",
                kind="bool",
                default=False,
                label=_("Show home temperature"),
                description=_("Show internal NSPanel temperature sensor alongside weather data."),
                section=_("Appearance"),
            ),
            PageOption(
                key="temp_precision",
                kind="int",
                default=1,
                label=_("Temperature precision"),
                description=_(
                    "Number of decimal places for temperature values (0 = whole number)."
                ),
                section=_("Precision"),
            ),
            PageOption(
                key="forecast_precision",
                kind="int",
                default=0,
                label=_("Forecast precision"),
                description=_("Decimal places for forecast temperature values (0 = whole number)."),
                section=_("Precision"),
            ),
            PageOption(
                key="show_notifications",
                kind="bool",
                default=True,
                label=_("Show notifications"),
                description=_("Show notification indicator icon on the weather screen."),
                section=_("Notifications"),
            ),
        ],
        icon="mdi:weather-partly-cloudy",
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
        d1_ico=Component(8, "d1Icon"),
        d2_ico=Component(9, "d2Icon"),
        d1_val=Component(10, "d1Val"),
        d2_val=Component(11, "d2Val"),
        f1_name=Component(12, "f1Name"),
        f2_name=Component(13, "f2Name"),
        f3_name=Component(14, "f3Name"),
        f4_name=Component(15, "f4Name"),
        f5_name=Component(16, "f5Name"),
        f1_ico=Component(17, "f1Icon"),
        f2_ico=Component(18, "f2Icon"),
        f3_ico=Component(19, "f3Icon"),
        f4_ico=Component(20, "f4Icon"),
        f5_ico=Component(21, "f5Icon"),
        f1_val=Component(22, "f1Val"),
        f2_val=Component(23, "f2Val"),
        f3_val=Component(24, "f3Val"),
        f4_val=Component(25, "f4Val"),
        f5_val=Component(26, "f5Val"),
        f1_subval=Component(27, "f1SubVal"),
        f2_subval=Component(28, "f2SubVal"),
        f3_subval=Component(29, "f3SubVal"),
        f4_subval=Component(30, "f4SubVal"),
        f5_subval=Component(31, "f5SubVal"),
        t_notif=Component(32, "tNotif"),
    )

    NUM_ENTITIES = 6
    NUM_FORECAST = 5
    DISPLAY_UPDATE_INTERVAL = 1.0

    # panel

    def prepare(self) -> None:

        self._show_notifications = True
        self._previous_forecast = None
        self._forecast_type = ""
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._temp_precision = 1
        self._forecast_precision = 0
        self._background = "default"
        self._weather_icons_mode = "color"
        self._weather_item: HAUIItem | None = None
        self._info_items: list[HAUIItem] = []
        self._entity_button_items: list[HAUIItem] = []

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background (rendered in start_panel after page is confirmed)
        self._background = self.render_template(panel.get("background", "default"), False)

    @staticmethod
    def _extract_entity_id(value: Any) -> str | None:
        """Extract entity ID from a config value that may be plain string or {item: ...} dict.

        The frontend serializes ``kind="item"`` fields through ``serializeItem()``,
        which stores them as ``{item: "entity_id"}`` dicts.
        """
        if isinstance(value, dict):
            return value.get("item")
        return value

    def start_panel(self, panel: HAUIPanel) -> None:
        # setting: background — set before rendering content
        if self._background in BACKGROUNDS:
            self.send_cmd(f"weather.background.val={BACKGROUNDS[self._background]}")
        # time update callback (shared device-wide tick)
        self.app.subscribe_tick("minute", self.callback_update_time)
        # setup date callback (shared device-wide tick)
        self.app.subscribe_tick("hour", self.callback_update_date)
        # Register notification indicator with the shared blinker
        self.app.controller["notification"].set_blinker_callback(self._refresh_notif)
        # Weather entity - role-based creation from explicit config keys
        weather_entity_id = self._extract_entity_id(panel.get("item", None))
        if weather_entity_id:
            self._weather_item = HAUIItem(self.app, {"item": weather_entity_id})
            self._temp_unit = self._weather_item.get_item_attr("temperature_unit", "°C")
            self.add_item_listener(weather_entity_id, self.callback_weather, "temperature")
            self.add_item_listener(weather_entity_id, self.callback_weather, "pressure")
        else:
            self.app.log("WARNING: No weather entity found in config")

        # Info items (D1/D2) - explicit item_list key
        self._info_items.clear()
        for entity_id in panel.get("info_items", []):
            entity_id = self._extract_entity_id(entity_id)
            if entity_id:
                self._info_items.append(HAUIItem(self.app, {"item": entity_id}))

        # setting: temp_precision
        self._temp_precision = int(panel.get("temp_precision", 1))
        # setting: forecast_precision
        self._forecast_precision = int(panel.get("forecast_precision", 0))
        # setting: show_weather
        self._show_weather = panel.get("show_weather", True)
        self.set_function_component(
            self.COMPONENTS.t_main_icon, self.COMPONENTS.t_main_icon[1], visible=self._show_weather
        )
        # setting: weather_icons
        self._weather_icons_mode = panel.get("weather_icons", "color")
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
        # setting: forecast
        self._forecast_type = panel.get("forecast_type", "") or panel.get("show_forecast", "")
        if self._forecast_type:
            self.show_forecast()
        # main components
        self.set_function_component(self.COMPONENTS.t_time, self.COMPONENTS.t_time[1], visible=True)
        self.set_function_component(self.COMPONENTS.t_date, self.COMPONENTS.t_date[1], visible=True)
        # notification
        self._show_notifications = panel.get("show_notifications", True)
        self.set_function_component(
            self.COMPONENTS.t_notif, self.COMPONENTS.t_notif[1], visible=self._show_notifications
        )

    def render_panel(self, panel: HAUIPanel) -> None:
        # time display
        self.update_time()
        # date display
        self.update_date()
        # main weather entity
        self.render_main_weather()
        # info panels (D1/D2)
        self.render_info_panels()
        # forecast
        self.render_forecast()
        # notifications
        self.app.controller["notification"].blinker.refresh()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel time and date tick subscriptions
        self.app.unsubscribe_tick("minute", self.callback_update_time)
        self.app.unsubscribe_tick("hour", self.callback_update_date)
        # unregister notification indicator from shared blinker
        self.app.controller["notification"].clear_blinker_callback()

    # misc

    def show_forecast(self) -> None:
        for i in range(self.NUM_FORECAST):
            idx = i + 1
            name = getattr(self.COMPONENTS, f"f{idx}_name")
            ico = getattr(self.COMPONENTS, f"f{idx}_ico")
            val = getattr(self.COMPONENTS, f"f{idx}_val")
            subval = getattr(self.COMPONENTS, f"f{idx}_subval")
            self.show_component(name)
            self.show_component(ico)
            self.show_component(val)
            self.show_component(subval)

    def update_time(self) -> None:
        timeformat = self.app.device_config.get("time_format")
        timezone = self.app.hass.config.time_zone
        time = get_time_localized(timeformat, timezone)
        self.update_function_component(self.COMPONENTS.t_time[1], text=time)

    def update_date(self) -> None:
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get(
            "date_format_locale"
        ) or self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        timezone = self.app.hass.config.time_zone
        date = get_date_localized(strftime_format, babel_format, locale, timezone)
        self.update_function_component(self.COMPONENTS.t_date[1], text=date)

    def render_main_weather(self) -> None:
        if self._weather_item is not None:
            self._temp_unit = self._weather_item.get_item_attr("temperature_unit", "°C")
        self.update_main_weather()

    def render_info_panels(self) -> None:
        for i, item in enumerate(self._info_items, start=1):
            self.update_info(i, item)

    def render_forecast(self) -> None:
        if not self._forecast_type or self._weather_item is None:
            return
        weather_id = self._weather_item.get_item_id()
        if not weather_id:
            self.log("Weather forecast skipped: no entity ID", level="DEBUG")
            return
        forecast = None
        try:
            result = self.app.call_service(
                "weather/get_forecasts",
                return_response=True,
                target={"entity_id": weather_id},
                service_data={"type": self._forecast_type},
            )
            if result is None:
                self.log(
                    f"Weather forecast service returned no result for '{self._forecast_type}'",
                    level="WARNING",
                )
            else:
                forecast = result["result"]["response"][weather_id]["forecast"]
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            self.log(
                f"Weather forecast extract failed for '{self._forecast_type}': {exc}",
                level="WARNING",
            )
            forecast = self._previous_forecast
        except Exception:
            self.log(
                f"Weather forecast service call failed for '{self._forecast_type}'",
                level="WARNING",
                exc_info=True,
            )
            if self._previous_forecast is not None:
                forecast = self._previous_forecast
            else:
                return
        if forecast is None:
            return
        for i in range(0, self.NUM_FORECAST):
            forecast_data = forecast[i] if i < len(forecast) else {}
            self.update_forecast(i, forecast_data)
        self._previous_forecast = forecast

    def update_main_weather(self) -> None:
        if self._weather_item is None:
            return

        # set up main weather details
        name = self.app.device.get_name()
        name_slug = name.lower().replace("-", "_").replace(" ", "_")
        icon = self._weather_item.get_icon()
        color = self._weather_item.get_color()
        temp_outside_str = self._weather_item.get_item_attr("temperature", "")
        if not temp_outside_str:
            self.update_function_component(
                self.COMPONENTS.t_main_icon[1],
                icon=icon,
                color=None if self._weather_icons_mode == "monochrome" else color,
                visible=self._show_weather,
            )
            self.update_function_component(self.COMPONENTS.t_main_text[1], visible=False)
            self.update_function_component(self.COMPONENTS.t_sub_text[1], visible=False)
            return
        temp_outside = round(
            float(temp_outside_str),
            self._temp_precision,
        )
        msg = ""
        if self._show_home_temp:
            temp_inside_entity = self.app.get_item(f"sensor.{name_slug}_temperature")
            if (temp_inside_state := temp_inside_entity.get_state()) is not None:
                temp_inside: float | int = round(float(temp_inside_state), self._temp_precision)
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
            self.COMPONENTS.t_main_icon[1],
            icon=icon,
            color=None if self._weather_icons_mode == "monochrome" else color,
            visible=self._show_weather,
        )
        self.update_function_component(
            self.COMPONENTS.t_main_text[1], text=msg, visible=self._show_temp
        )
        self.update_function_component(
            self.COMPONENTS.t_sub_text[1], text=msg_sub, visible=self._show_temp
        )

    def update_forecast(self, idx: int, data: dict) -> None:
        if idx < 0 or idx > self.NUM_FORECAST:
            self.log("Weather Forecast index outside bounds")
            return
        if data is None:
            self.log(f"No weather forecast for index {idx}")
            return
        forecast_idx = idx + 1
        forecast_temp = round(float(data.get("temperature", 20)), self._forecast_precision)
        forecast_mintemp = round(float(data.get("templow", 0)), self._forecast_precision)
        if not self._forecast_precision:
            forecast_temp = int(forecast_temp)
            forecast_mintemp = int(forecast_mintemp)

        forecast_name = getattr(self.COMPONENTS, f"f{forecast_idx}_name")
        forecast_icon = getattr(self.COMPONENTS, f"f{forecast_idx}_ico")
        forecast_val = getattr(self.COMPONENTS, f"f{forecast_idx}_val")
        forecast_subval = getattr(self.COMPONENTS, f"f{forecast_idx}_subval")
        fdate = dp.parse(data["datetime"])
        name = format_datetime(fdate, "%a", "E", self.get_locale())
        condition = data.get("condition", "")
        icon = WEATHER_MAPPING.get(condition, "")
        icon = get_icon(icon) or ""

        color = WEATHER_COLORS.get(condition.replace("-", "_"), WEATHER_COLORS["default"])
        if self._weather_icons_mode != "monochrome":
            self.set_component_text_color(forecast_icon, color)
        self.set_component_text(forecast_name, name)
        self.set_component_text(forecast_icon, icon)
        self.set_component_text(forecast_val, f"{forecast_temp}{self._temp_unit}")
        self.set_component_text(forecast_subval, f"{forecast_mintemp}{self._temp_unit}")

    def update_info(self, idx: int, haui_item: HAUIItem) -> None:
        if idx < 1 or idx > 2:
            self.log(f"Weather Info uses index 1-2, got {idx}")
            return
        info_icon = getattr(self.COMPONENTS, f"d{idx}_ico")
        info_val = getattr(self.COMPONENTS, f"d{idx}_val")
        self.set_component_text_color(info_icon, haui_item.get_color())
        self.set_component_text(info_icon, haui_item.get_icon())
        self.set_component_text(info_val, haui_item.get_value())

    def _update_info_panels(self) -> None:
        """Re-render info panel (D1/D2) data using stored items.

        Called from callback_weather and periodic refresh to ensure info
        panels stay current even when the weather entity does not publish
        frequent state change events.
        """
        self.render_info_panels()

    def _update_forecast_data(self) -> None:
        """Re-fetch and re-render the weather forecast.

        Falls back to the previous forecast data if the service call fails.
        Called from callback_weather and periodic refresh to keep forecast
        data current without requiring a full panel re-render.
        """
        self.render_forecast()

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

    def callback_update_time(self, cb_args: Any) -> None:
        if not self.started:
            return
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_time()
        self.send_cmd(f"ref {self.COMPONENTS.t_main_icon[1]}")

    def callback_update_date(self, cb_args: Any) -> None:
        if not self.started:
            return
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_date()

    def callback_weather(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_main_weather()
        self._update_info_panels()
        self._update_forecast_data()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.COMPONENTS.t_notif[1]:
            navigation = self.app.controller["navigation"]
            navigation.open_panel(SysPanelKey.POPUP_NOTIFY)
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()

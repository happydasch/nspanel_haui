from __future__ import annotations

import datetime
import threading
from typing import Any

import dateutil.parser as dp

from ..abstract.event import HAUIEvent
from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..mapping.background import BACKGROUNDS
from ..mapping.color import COLORS
from ..mapping.const import ESPResponse, NotifEvent
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icon import WEATHER_MAPPING
from ..utils.datetime import format_datetime, get_date_localized, get_time_localized
from ..utils.icon import get_icon, parse_icon
from . import HAUIPage


class WeatherPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="weather",
        page_name="weather",
        label="Weather",
        description="Weather display with time, date and forecast.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="weather",
                description="Weather entity to display conditions, temperature and forecast.",
                section="Items",
            ),
            PageOption(
                key="info_items",
                kind="item_list",
                label="Info Items",
                description="Additional sensor entities to display as info panels (max 2).",
                section="Items",
                max_items=2,
            ),
            PageOption(
                key="entity_buttons",
                kind="item_list",
                label="Entity buttons",
                description="Quick-action buttons below the weather display (max 6).",
                section="Items",
                max_items=6,
            ),
            PageOption(
                key="background",
                kind="select",
                default="default",
                label="Background",
                description="Background image theme for the weather display.",
                section="Appearance",
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
            PageOption(
                key="forecast_type",
                kind="select",
                default="",
                label="Forecast type",
                description="Show daily or hourly weather forecast on the bottom row.",
                section="Appearance",
                choices=[("", "Off"), ("daily", "Daily"), ("hourly", "Hourly")],
            ),
            PageOption(
                key="show_weather",
                kind="bool",
                default=True,
                label="Show weather",
                description="Show the main weather icon and condition text.",
                section="Appearance",
            ),
            PageOption(
                key="show_temp",
                kind="bool",
                default=True,
                label="Show temperature",
                description="Show the current temperature value.",
                section="Appearance",
            ),
            PageOption(
                key="show_home_temp",
                kind="bool",
                default=False,
                label="Show home temperature",
                description="Show internal NSPanel temperature sensor alongside weather data.",
                section="Appearance",
            ),
            PageOption(
                key="temp_precision",
                kind="int",
                default=1,
                label="Temperature precision",
                description="Number of decimal places for temperature values (0 = whole number).",
                section="Precision",
            ),
            PageOption(
                key="forecast_precision",
                kind="int",
                default=0,
                label="Forecast precision",
                description="Decimal places for forecast temperature values (0 = whole number).",
                section="Precision",
            ),
            PageOption(
                key="show_notifications",
                kind="bool",
                default=True,
                label="Show notifications",
                description="Show notification indicator icon on the weather screen.",
                section="Notifications",
            ),
        ],
        icon="mdi:weather-partly-cloudy",
    )

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
        self._timer_weather_refresh: str | None = None
        self._timer_notifications: threading.Timer | None = None
        self._show_notifications = True
        self._new_notifications = False
        self._previous_forecast = None
        self._forecast_type = ""
        self._show_weather = True
        self._show_temp = True
        self._show_home_temp = False
        self._temp_unit = "°C"
        self._temp_precision = 1
        self._forecast_precision = 0
        self._weather_item: HAUIItem | None = None
        self._info_items: list[HAUIItem] = []
        self._entity_button_items: list[HAUIItem] = []

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f"weather.background.val={BACKGROUNDS[background]}")

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
        # time update callback (shared device-wide tick)
        self.app.subscribe_tick("minute", self.callback_update_time)
        # setup date callback (shared device-wide tick)
        self.app.subscribe_tick("hour", self.callback_update_date)
        # periodic weather refresh (re-fetches forecast & info panels)
        # Uses a 15-minute interval so forecast data stays current even when
        # the weather entity does not publish frequent state change events.
        self._timer_weather_refresh = self.app.run_every(
            self._callback_weather_refresh, "now+900", 900
        )
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

        # Entity buttons - explicit item_list key
        self._entity_button_items.clear()
        for entity_id in panel.get("entity_buttons", []):
            entity_id = self._extract_entity_id(entity_id)
            if entity_id:
                self._entity_button_items.append(HAUIItem(self.app, {"item": entity_id}))

        # setting: temp_precision
        self._temp_precision = int(panel.get("temp_precision", 1))
        # setting: forecast_precision
        self._forecast_precision = int(panel.get("forecast_precision", 0))
        # setting: show_weather
        self._show_weather = panel.get("show_weather", True)
        self.set_function_component(self.ICO_MAIN, self.ICO_MAIN[1], visible=self._show_weather)
        # setting: show_temp
        self._show_temp = panel.get("show_temp", True)
        self.set_function_component(self.TXT_MAIN, self.TXT_MAIN[1], visible=self._show_temp)
        self.set_function_component(self.TXT_SUB, self.TXT_SUB[1], visible=self._show_temp)
        # setting: show_home_temp
        self._show_home_temp = panel.get("show_home_temp", False)
        # setting: forecast
        self._forecast_type = panel.get("forecast_type", "") or panel.get("show_forecast", "")
        if not self._forecast_type:
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
        # Pre-register entity button components so config_panel registers
        # touch callbacks.  No display kwargs here - render_entity_buttons()
        # applies the correct state once entity data is available.
        for i in range(self.NUM_ENTITIES):
            component = getattr(self, f"BTN_ENTITY_{i + 1}")
            self.set_function_component(component, component[1], "item")

    def render_panel(self, panel: HAUIPanel) -> None:
        # time display
        self.update_time()
        # date display
        self.update_date()
        # main weather entity
        self.render_main_weather()
        # info panels (D1/D2)
        self.render_info_panels()
        # entity buttons
        self.render_entity_buttons()
        # forecast
        self.render_forecast()
        # notifications
        self.update_notifications()

    def stop_panel(self, panel: HAUIPanel) -> None:
        super().stop_panel(panel)
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

    def show_forecast(self) -> None:
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

    def hide_forecast(self) -> None:
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

    def update_time(self) -> None:
        timeformat = self.app.device_config.get("time_format")
        timezone = self.app.hass.config.time_zone
        time = get_time_localized(timeformat, timezone)
        self.update_function_component(self.TXT_TIME[1], text=time)

    def update_date(self) -> None:
        strftime_format = self.app.device_config.get("date_format")
        babel_format = self.app.device_config.get(
            "date_format_locale"
        ) or self.app.device_config.get("date_format_babel")
        locale = self.app.device.get_locale()
        timezone = self.app.hass.config.time_zone
        date = get_date_localized(strftime_format, babel_format, locale, timezone)
        self.update_function_component(self.TXT_DATE[1], text=date)

    def render_main_weather(self) -> None:
        if self._weather_item is not None:
            self._temp_unit = self._weather_item.get_item_attr("temperature_unit", "°C")
        self.update_main_weather()

    def render_entity_buttons(self) -> None:
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ""
            color = COLORS["text"]
            if i < len(self._entity_button_items):
                item = self._entity_button_items[i]
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
                self.ICO_MAIN[1], icon=icon, color=color, visible=self._show_weather
            )
            self.update_function_component(self.TXT_MAIN[1], visible=False)
            self.update_function_component(self.TXT_SUB[1], visible=False)
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
            self.ICO_MAIN[1], icon=icon, color=color, visible=self._show_weather
        )
        self.update_function_component(self.TXT_MAIN[1], text=msg, visible=self._show_temp)
        self.update_function_component(self.TXT_SUB[1], text=msg_sub, visible=self._show_temp)

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

        forecast_name = getattr(self, f"F{forecast_idx}_NAME")
        forecast_icon = getattr(self, f"F{forecast_idx}_ICO")
        forecast_val = getattr(self, f"F{forecast_idx}_VAL")
        forecast_subval = getattr(self, f"F{forecast_idx}_SUBVAL")
        fdate = dp.parse(data["datetime"])
        name = format_datetime(fdate, "%a", "E", self.get_locale())
        condition = data.get("condition", "")
        icon = WEATHER_MAPPING.get(condition, "")
        icon = get_icon(icon) or ""

        color_name = f"weather_{condition.replace('-', '_')}"
        color = COLORS.get(color_name, COLORS["weather_default"])
        self.set_component_text_color(forecast_icon, color)
        self.set_component_text(forecast_name, name)
        self.set_component_text(forecast_icon, icon)
        self.set_component_text(forecast_val, f"{forecast_temp}{self._temp_unit}")
        self.set_component_text(forecast_subval, f"{forecast_mintemp}{self._temp_unit}")

    def update_info(self, idx: int, haui_item: HAUIItem) -> None:
        if idx < 1 or idx > 2:
            self.log(f"Weather Info uses index 1-2, got {idx}")
            return
        info_icon = getattr(self, f"D{idx}_ICO")
        info_val = getattr(self, f"D{idx}_VAL")
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

    def callback_update_time(self, cb_args: Any) -> None:
        if not self.started:
            return
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_time()
        self.send_cmd(f"ref {self.ICO_MAIN[1]}")

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

    def _callback_weather_refresh(self, cb_args: Any) -> None:
        """Periodic weather refresh callback (15-minute timer).

        Re-fetches forecast and info panel data to keep the display current
        even when the weather entity does not publish state change events.
        """
        if self.app.device.device_info.get("display_state") == "off":
            return
        self._update_info_panels()
        self._update_forecast_data()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.TXT_NOTIF[1]:
            navigation = self.app.controller["navigation"]
            navigation.open_popup("popup_notify")
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()

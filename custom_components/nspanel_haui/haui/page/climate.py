from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import ClimateFeatures
from ..mapping.color import CLIMATE_COLORS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icon_mapping import CLIMATE_MAPPING
from ..mapping.icons import ICO_DOWN, ICO_FAN, ICO_POWER, ICO_PRESET, ICO_SWING, ICO_UP
from ..utils.icon import get_icon


class ClimatePage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="climate",
        page_name="climate",
        label="Climate",
        description="Climate item with temperature and mode controls.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="climate",
                description="Climate/HVAC entity for temperature control and mode switching.",
                section="Climate",
            ),
            PageOption(
                key="hvac_modes",
                kind="list_items",
                default=[],
                choices=[
                    ("off", "Off"),
                    ("heat", "Heat"),
                    ("cool", "Cool"),
                    ("heat_cool", "Heat/Cool"),
                    ("auto", "Auto"),
                    ("dry", "Dry"),
                    ("fan_only", "Fan Only"),
                ],
                label="HVAC modes override",
                description="Override HVAC modes shown on this panel.",
                section="Climate",
            ),
        ],
        can_show_popup=True,
        icon="mdi:thermostat",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        t_temp=Component(8, "tTemp"),
        btn_up=Component(9, "bUp"),
        btn_down=Component(10, "bDown"),
        x_set=Component(11, "xSet"),
        t_unit=Component(12, "tUnit"),
        btn_up_1=Component(13, "bUp1"),
        btn_down_1=Component(14, "bDown1"),
        x_set_1=Component(15, "xSet1"),
        t_unit_1=Component(16, "tUnit1"),
        btn_up_2=Component(17, "bUp2"),
        btn_down_2=Component(18, "bDown2"),
        x_set_2=Component(19, "xSet2"),
        t_unit_2=Component(20, "tUnit2"),
        bt_mode_1=Component(21, "btMode1"),
        bt_mode_2=Component(22, "btMode2"),
        bt_mode_3=Component(23, "btMode3"),
        bt_mode_4=Component(24, "btMode4"),
        bt_mode_5=Component(25, "btMode5"),
        bt_mode_6=Component(26, "btMode6"),
        btn_fan=Component(27, "bFan"),
        btn_preset=Component(28, "bPreset"),
        btn_swing=Component(29, "bSwing"),
    )

    NUM_MODES = 6

    _title = ""
    _climate_item: HAUIItem | None = None
    _hvac_modes: list[str] | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        power_off_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "power_off",
            "fnc_args": {
                "icon": ICO_POWER,
                "color": self.get_color("header_accent"),
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            power_off_btn,
        )
        # set item
        item = None
        entity_id = panel.get("item_id")
        if entity_id:
            item = HAUIItem(self.app, {"item": entity_id})
        self.set_climate_item(item)
        # set title
        title = panel.get_title(self.translate("Climate"))
        if item is not None:
            title = item.get_item_attr("friendly_name", title)
        self._title = title
        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, self._title)
        self.update_climate_item()

    # misc

    def set_climate_item(self, item: HAUIItem | None) -> None:
        self._climate_item = item
        if not item or not item.has_item_id():
            return
        # add listener
        self.add_item_listener(item.get_item_id(), self.callback_climate_item)
        self.add_item_listener(
            item.get_item_id(),
            self.callback_climate_item,
            attribute="current_temperature",
        )
        self.add_item_listener(
            item.get_item_id(),
            self.callback_climate_item,
            attribute="temperature",
        )
        # use features of climate
        features = item.get_item_attr("supported_features", 0)
        # temperature input
        temp_setting = None
        if features & ClimateFeatures.TARGET_TEMPERATURE_RANGE:
            temp_setting = True
        elif features & ClimateFeatures.TARGET_TEMPERATURE:
            temp_setting = False
        if temp_setting is not None:
            # set temperature if False, set temperature_range if True
            if not temp_setting:
                self.show_component(self.COMPONENTS.x_set)
                self.show_component(self.COMPONENTS.t_unit)
                self.set_function_component(
                    self.COMPONENTS.btn_up,
                    self.COMPONENTS.btn_up[1],
                    "temp_up",
                    color=self.get_color("component_active"),
                    icon=ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.COMPONENTS.btn_down,
                    self.COMPONENTS.btn_down[1],
                    "temp_down",
                    color=self.get_color("component_active"),
                    icon=ICO_DOWN,
                    visible=True,
                )
            else:
                self.show_component(self.COMPONENTS.x_set_1)
                self.show_component(self.COMPONENTS.t_unit_1)
                self.show_component(self.COMPONENTS.x_set_2)
                self.show_component(self.COMPONENTS.t_unit_2)
                self.set_function_component(
                    self.COMPONENTS.btn_up_1,
                    self.COMPONENTS.btn_up_1[1],
                    "temp_up_1",
                    color=self.get_color("component_active"),
                    icon=ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.COMPONENTS.btn_down_1,
                    self.COMPONENTS.btn_down_1[1],
                    "temp_down_1",
                    color=self.get_color("component_active"),
                    icon=ICO_DOWN,
                    visible=True,
                )
                self.set_function_component(
                    self.COMPONENTS.btn_up_2,
                    self.COMPONENTS.btn_up_2[1],
                    "temp_up_2",
                    color=self.get_color("component_active"),
                    icon=ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.COMPONENTS.btn_down_2,
                    self.COMPONENTS.btn_down_2[1],
                    "temp_down_2",
                    color=self.get_color("component_active"),
                    icon=ICO_DOWN,
                    visible=True,
                )
        # hvac mode buttons
        self._hvac_modes = item.get_item_attr("hvac_modes", [])
        self._hvac_modes = self.get("hvac_modes", self._hvac_modes)
        for i in range(self.NUM_MODES):
            visible = False
            icon = ""
            color_pressed = self.get_color("component_active")
            if i < len(self._hvac_modes):
                hvac_mode = self._hvac_modes[i]
                visible = True
                if hvac_mode in CLIMATE_MAPPING:
                    icon = CLIMATE_MAPPING[hvac_mode]
                if hvac_mode in CLIMATE_COLORS:
                    color_pressed = CLIMATE_COLORS[hvac_mode]
            component = getattr(self.COMPONENTS, f"bt_mode_{i + 1}")
            self.set_function_component(
                component,
                component.name,
                "hvac_mode",
                item=item,
                icon=get_icon(icon),
                color_pressed=color_pressed,
                visible=visible,
            )
        # fan button
        fan_mode = False
        color = self.get_color("text_inactive")
        if features & ClimateFeatures.FAN_MODE:
            fan_mode = True
            color = self.get_color("component_active")
        self.set_function_component(
            self.COMPONENTS.btn_fan,
            self.COMPONENTS.btn_fan[1],
            "fan_mode",
            icon=ICO_FAN,
            visible=True,
            color=color,
            touch=fan_mode,
        )
        # preset button
        preset_mode = False
        color = self.get_color("text_inactive")
        if features & ClimateFeatures.PRESET_MODE:
            preset_mode = True
            color = self.get_color("component_active")
        self.set_function_component(
            self.COMPONENTS.btn_preset,
            self.COMPONENTS.btn_preset[1],
            "preset_mode",
            icon=ICO_PRESET,
            visible=True,
            color=color,
            touch=preset_mode,
        )
        # swing button
        swing_mode = False
        color = self.get_color("text_inactive")
        if features & ClimateFeatures.SWING_MODE:
            swing_mode = True
            color = self.get_color("component_active")
        self.set_function_component(
            self.COMPONENTS.btn_swing,
            self.COMPONENTS.btn_swing[1],
            "swing_mode",
            icon=ICO_SWING,
            visible=True,
            color=color,
            touch=swing_mode,
        )

    def update_climate_item(self) -> None:
        if self._climate_item is None:
            return
        item = self._climate_item
        self.update_climate_control(item)
        self.update_climate_info(item)
        self.update_hvac_modes(item)

    def update_climate_control(self, item: HAUIItem) -> None:
        features = item.get_item_attr("supported_features", 0)
        if features & ClimateFeatures.TARGET_TEMPERATURE_RANGE:
            # TODO: implement target_temperature_range mode
            pass
        elif features & ClimateFeatures.TARGET_TEMPERATURE:
            target_temp = item.get_item_attr("temperature", 0)
            self.set_component_value(self.COMPONENTS.x_set, int(target_temp * 10))
        # fan mode
        fan_mode = False
        if features & ClimateFeatures.FAN_MODE:
            fan_mode = True
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(fan_mode)
        self.update_function_component(
            self.COMPONENTS.btn_fan[1],
            touch=fan_mode,
            color=color,
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )
        # preset mode
        preset_mode = False
        if features & ClimateFeatures.PRESET_MODE:
            preset_mode = True
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(preset_mode)
        self.update_function_component(
            self.COMPONENTS.btn_preset[1],
            touch=preset_mode,
            color=color,
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )
        # swing mode
        swing_mode = False
        if features & ClimateFeatures.SWING_MODE:
            swing_mode = True
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(swing_mode)
        self.update_function_component(
            self.COMPONENTS.btn_swing[1],
            touch=swing_mode,
            color=color,
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )
        # hvac_mode
        hvac_mode = item.get_item_state()
        if hvac_mode != "off":
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    def update_climate_info(self, item: HAUIItem) -> None:
        current_temp = item.get_item_attr("current_temperature", 0)
        unit = item.get_item_attr("temperature_unit", "°C")
        self.set_component_text(self.COMPONENTS.t_unit, unit)
        self.set_component_text(self.COMPONENTS.t_temp, f"{current_temp}{unit}")

    def update_hvac_modes(self, item: HAUIItem) -> None:
        hvac_mode = item.get_item_state()
        color_active = self.get_color("component_active")
        color_inactive = self.get_color("component_text")
        if hvac_mode in CLIMATE_COLORS:
            color_active = CLIMATE_COLORS[hvac_mode]
        for i in range(self.NUM_MODES):
            component = getattr(self.COMPONENTS, f"bt_mode_{i + 1}")
            color = color_inactive
            value = 0
            if (
                self._hvac_modes is not None
                and i < len(self._hvac_modes)
                and self._hvac_modes[i] == hvac_mode
            ):
                color = color_active
                value = 1
            self.update_function_component(component.name, color=color)
            self.set_component_value(component, value)

    # callback

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if self._climate_item is None:
            return
        haui_item = self._climate_item
        self.log(f"callback_function_component: {fnc_id}, {fnc_name}")
        if fnc_name == "temp_up":
            temp = haui_item.get_item_attr("temperature", 0)
            max_temp = haui_item.get_item_attr("max_temp", 0)
            target_temp_step = haui_item.get_item_attr("target_temp_step", 0)
            temp = min(max_temp, temp + target_temp_step)
            self.log(f"temp_up {temp}")
            haui_item.call_item_service("set_temperature", temperature=temp)
        elif fnc_name == "temp_down":
            temp = haui_item.get_item_attr("temperature", 0)
            min_temp = haui_item.get_item_attr("min_temp", 0)
            target_temp_step = haui_item.get_item_attr("target_temp_step", 0)
            temp = max(min_temp, temp - target_temp_step)
            self.log(f"temp_down {temp}")
            haui_item.call_item_service("set_temperature", temperature=temp)

        elif fnc_name == "hvac_mode":
            hvac_mode = "off"
            for i in range(self.NUM_MODES):
                component = getattr(self.COMPONENTS, f"bt_mode_{i + 1}")
                if (
                    self._hvac_modes is not None
                    and i < len(self._hvac_modes)
                    and component.name == fnc_id
                ):
                    hvac_mode = self._hvac_modes[i]
                    break
            haui_item.call_item_service("set_hvac_mode", hvac_mode=hvac_mode)
        elif fnc_name == "fan_mode":
            self.log("fan_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_item.get_item_attr("fan_modes", [])
            selected = self._climate_item.get_item_attr("fan_mode", "")
            fan_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="fan_mode")
                fan_modes.append({"value": value, "name": name})
            if len(fan_modes) > 0:
                navigation.open_panel(
                    SysPanelKey.POPUP_SELECT,
                    title=self.translate("Select fan mode"),
                    items=fan_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_fan_mode,
                    close_on_select=True,
                )
        elif fnc_name == "preset_mode":
            self.log("preset_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_item.get_item_attr("preset_modes", [])
            selected = self._climate_item.get_item_attr("preset_mode", "")
            preset_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="preset_mode")
                preset_modes.append({"value": value, "name": name})
            if len(preset_modes) > 0:
                navigation.open_panel(
                    SysPanelKey.POPUP_SELECT,
                    title=self.translate("Select preset mode"),
                    items=preset_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_preset_mode,
                    close_on_select=True,
                )
        elif fnc_name == "swing_mode":
            self.log("swing_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_item.get_item_attr("swing_modes", [])
            selected = self._climate_item.get_item_attr("swing_mode", "")
            swing_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="swing_mode")
                swing_modes.append({"value": value, "name": name})
            if len(swing_modes) > 0:
                navigation.open_panel(
                    SysPanelKey.POPUP_SELECT,
                    title=self.translate("Select swing mode"),
                    items=swing_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_swing_mode,
                    close_on_select=True,
                )
        elif fnc_name == "power_off":
            self.log("power_off")
            if self._climate_item.get_item_state() != "off":
                self._climate_item.call_item_service("set_hvac_mode", hvac_mode="off")

    def callback_fan_mode(self, selection: str) -> None:
        self.log(f"Got fan mode selection: {selection}")
        if self._climate_item is not None:
            self._climate_item.call_item_service("set_fan_mode", fan_mode=selection)

    def callback_preset_mode(self, selection: str) -> None:
        self.log(f"Got preset mode selection: {selection}")
        if self._climate_item is not None:
            self._climate_item.call_item_service("set_preset_mode", preset_mode=selection)

    def callback_swing_mode(self, selection: str) -> None:
        self.log(f"Got swing mode selection: {selection}")
        if self._climate_item is not None:
            self._climate_item.call_item_service("set_swing_mode", swing_mode=selection)

    def callback_climate_item(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        with self.rec_cmd:
            self.update_climate_item()

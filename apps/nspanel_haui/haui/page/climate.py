from typing import List

from ..mapping.color import COLORS
from ..mapping.icon import CLIMATE_MAPPING
from ..helper.icon import get_icon
from ..config import HAUIConfigEntity, HAUIConfigPanel
from ..features import ClimateFeatures

from . import HAUIPage


class ClimatePage(HAUIPage):

    # https://developers.home-assistant.io/docs/core/entity/climate

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # info
    TXT_TEMP = (7, "tTemp")
    # control
    BTN_UP, BTN_DOWN, X_SET, TXT_UNIT = (
        (8, "bUp"),
        (9, "bDown"),
        (10, "xSet"),
        (11, "tUnit")
    )
    BTN_UP_1, BTN_DOWN_1, X_SET_1, TXT_UNIT_1 = (
        (12, "bUp1"),
        (13, "bDown1"),
        (14, "xSet1"),
        (15, "tUnit1"),
    )
    BTN_UP_2, BTN_DOWN_2, X_SET_2, TXT_UNIT_2 = (
        (16, "bUp2"),
        (17, "bDown2"),
        (18, "xSet2"),
        (19, "tUnit2"),
    )
    # modes
    BT_MODE_1, BT_MODE_2, BT_MODE_3 = (
        (20, "btMode1"),
        (21, "btMode2"),
        (22, "btMode3"),
    )
    BT_MODE_4, BT_MODE_5, BT_MODE_6 = (
        (23, "btMode4"),
        (24, "btMode5"),
        (25, "btMode6"),
    )
    # functions
    BTN_FAN, BTN_PRESET, BTN_SWING = (
        (26, "bFan"),
        (27, "bPreset"),
        (28, "bSwing"),
    )

    ICO_UP = get_icon("mdi:chevron-up")
    ICO_DOWN = get_icon("mdi:chevron-down")
    ICO_FAN = get_icon("mdi:fan")
    ICO_PRESET = get_icon("mdi:view-list")
    ICO_SWING = get_icon("mdi:arrow-all")
    ICO_POWER = get_icon("mdi:power")

    NUM_MODES = 6

    _title = ""
    _climate_entity: HAUIConfigEntity = None
    _hvac_modes: List[str] = None

    # panel

    def start_panel(self, panel: HAUIConfigPanel):
        # set function buttons
        power_off_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "power_off",
            "fnc_args": {
                "icon": self.ICO_POWER,
                "color": COLORS["component_accent"],
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            power_off_btn,
        )
        # set entity
        entity = None
        entity_id = panel.get("entity_id")
        if entity_id:
            entity = HAUIConfigEntity(self.app, {"entity": entity_id})
        self.set_climate_entity(entity)
        # set title
        title = panel.get_title(self.translate("Climate"))
        if entity is not None:
            title = entity.get_entity_attr("friendly_name", title)
        self._title = title

    def render_panel(self, panel: HAUIConfigPanel):
        self.set_component_text(self.TXT_TITLE, self._title)
        self.update_climate_entity()

    # misc

    def set_climate_entity(self, entity: HAUIConfigEntity):
        self._climate_entity = entity
        if not entity or not entity.has_entity_id():
            return
        # add listener
        self.add_entity_listener(entity.get_entity_id(), self.callback_climate_entity)
        self.add_entity_listener(entity.get_entity_id(), self.callback_climate_entity, attribute="current_temperature")
        self.add_entity_listener(entity.get_entity_id(), self.callback_climate_entity, attribute="temperature")
        # use features of climate
        features = entity.get_entity_attr("supported_features", 0)
        # temperature input
        temp_setting = None
        if features & ClimateFeatures.TARGET_TEMPERATURE_RANGE:
            temp_setting = True
        elif features & ClimateFeatures.TARGET_TEMPERATURE:
            temp_setting = False
        if temp_setting is not None:
            # set temperature if False, set temperature_range if True
            if not temp_setting:
                self.hide_component(self.BTN_UP_1)
                self.hide_component(self.BTN_DOWN_1)
                self.hide_component(self.X_SET_1)
                self.hide_component(self.TXT_UNIT_1)
                self.hide_component(self.BTN_UP_2)
                self.hide_component(self.BTN_DOWN_2)
                self.hide_component(self.X_SET_2)
                self.hide_component(self.TXT_UNIT_2)
                #
                self.show_component(self.X_SET)
                self.show_component(self.TXT_UNIT)
                self.set_function_component(
                    self.BTN_UP,
                    self.BTN_UP[1],
                    "temp_up",
                    color=COLORS["component_active"],
                    icon=self.ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.BTN_DOWN,
                    self.BTN_DOWN[1],
                    "temp_down",
                    color=COLORS["component_active"],
                    icon=self.ICO_DOWN,
                    visible=True,
                )
            else:
                self.hide_component(self.BTN_UP)
                self.hide_component(self.BTN_DOWN)
                self.hide_component(self.X_SET)
                self.hide_component(self.TXT_UNIT)
                #
                self.show_component(self.X_SET_1)
                self.show_component(self.TXT_UNIT_1)
                self.show_component(self.X_SET_2)
                self.show_component(self.TXT_UNIT_2)
                self.set_function_component(
                    self.BTN_UP_1,
                    self.BTN_UP_1[1],
                    "temp_up_1",
                    color=COLORS["component_active"],
                    icon=self.ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.BTN_DOWN_1,
                    self.BTN_DOWN_1[1],
                    "temp_down_1",
                    color=COLORS["component_active"],
                    icon=self.ICO_DOWN,
                    visible=True,
                )
                self.set_function_component(
                    self.BTN_UP_2,
                    self.BTN_UP_2[1],
                    "temp_up_2",
                    color=COLORS["component_active"],
                    icon=self.ICO_UP,
                    visible=True,
                )
                self.set_function_component(
                    self.BTN_DOWN_2,
                    self.BTN_DOWN_2[1],
                    "temp_down_2",
                    color=COLORS["component_active"],
                    icon=self.ICO_DOWN,
                    visible=True,
                )
        else:
            for x in [self.BTN_UP, self.BTN_DOWN,
                      self.BTN_UP_1, self.BTN_DOWN_1,
                      self.BTN_UP_2, self.BTN_DOWN_2,
                      self.X_SET, self.X_SET_1, self.X_SET_2,
                      self.TXT_UNIT, self.TXT_UNIT_1, self.TXT_UNIT_2]:
                self.hide_component(x)
        # hvac mode buttons
        self._hvac_modes = entity.get_entity_attr("hvac_modes", [])
        self._hvac_modes = self.get("hvac_modes", self._hvac_modes)
        for i in range(self.NUM_MODES):
            visible = False
            icon = ""
            color_pressed = COLORS["component_active"]
            if i < len(self._hvac_modes):
                hvac_mode = self._hvac_modes[i]
                visible = True
                if hvac_mode in CLIMATE_MAPPING:
                    icon = CLIMATE_MAPPING[hvac_mode]
                if f"climate_{hvac_mode}" in COLORS:
                    color_pressed = COLORS[f"climate_{hvac_mode}"]
            component = getattr(self, f"BT_MODE_{i+1}")
            self.set_function_component(
                component,
                component[1],
                "hvac_mode",
                entity=entity,
                icon=get_icon(icon),
                color_pressed=color_pressed,
                visible=visible,
            )
        # fan button
        fan_mode = False
        color = COLORS["text_inactive"]
        if features & ClimateFeatures.FAN_MODE:
            fan_mode = True
            color = COLORS["component_active"]
        self.set_function_component(
            self.BTN_FAN,
            self.BTN_FAN[1],
            "fan_mode",
            icon=self.ICO_FAN,
            visible=True,
            color=color,
            touch=fan_mode,
        )
        # preset button
        preset_mode = False
        color = COLORS["text_inactive"]
        if features & ClimateFeatures.PRESET_MODE:
            preset_mode = True
            color = COLORS["component_active"]
        self.set_function_component(
            self.BTN_PRESET,
            self.BTN_PRESET[1],
            "preset_mode",
            icon=self.ICO_PRESET,
            visible=True,
            color=color,
            touch=preset_mode,
        )
        # swing button
        swing_mode = False
        color = COLORS["text_inactive"]
        if features & ClimateFeatures.SWING_MODE:
            swing_mode = True
            color = COLORS["component_active"]
        self.set_function_component(
            self.BTN_SWING,
            self.BTN_SWING[1],
            "swing_mode",
            icon=self.ICO_SWING,
            visible=True,
            color=color,
            touch=swing_mode,
        )

    def update_climate_entity(self):
        if self._climate_entity is None:
            return
        entity = self._climate_entity
        self.update_climate_control(entity)
        self.update_climate_info(entity)
        self.update_hvac_modes(entity)

    def update_climate_control(self, entity: HAUIConfigEntity):
        features = entity.get_entity_attr("supported_features", 0)
        if features & ClimateFeatures.TARGET_TEMPERATURE_RANGE:
            # TODO
            pass
        elif features & ClimateFeatures.TARGET_TEMPERATURE:
            target_temp = entity.get_entity_attr("temperature", 0)
            self.set_component_value(self.X_SET, int(target_temp * 10))
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
            self.BTN_FAN[1],
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
            self.BTN_PRESET[1],
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
            self.BTN_SWING[1],
            touch=swing_mode,
            color=color,
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )
        # hvac_mode
        hvac_mode = entity.get_entity_state()
        if hvac_mode != "off":
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    def update_climate_info(self, entity: HAUIConfigEntity):
        current_temp = entity.get_entity_attr("current_temperature", 0)
        unit = entity.get_entity_attr("temperature_unit", "°C")
        self.set_component_text(self.TXT_UNIT, unit)
        self.set_component_text(self.TXT_TEMP, f"{current_temp}{unit}")

    def update_hvac_modes(self, entity: HAUIConfigEntity):
        hvac_mode = entity.get_entity_state()
        color_active = COLORS["component_active"]
        color_inactive = COLORS["component"]
        if f"climate_{hvac_mode}" in COLORS:
            color_active = COLORS[f"climate_{hvac_mode}"]
        for i in range(self.NUM_MODES):
            component = getattr(self, f"BT_MODE_{i+1}")
            color = color_inactive
            value = 0
            if i < len(self._hvac_modes) and self._hvac_modes[i] == hvac_mode:
                color = color_active
                value = 1
            self.update_function_component(component[1], color=color)
            self.set_component_value(component, value)

    # callback

    def callback_function_component(self, fnc_id, fnc_name):
        haui_entity = self._climate_entity
        self.log(f"callback_function_component: {fnc_id}, {fnc_name}")
        if fnc_name == "temp_up":
            temp = haui_entity.get_entity_attr("temperature", 0)
            max_temp = haui_entity.get_entity_attr("max_temp", 0)
            target_temp_step = haui_entity.get_entity_attr("target_temp_step", 0)
            temp = min(max_temp, temp + target_temp_step)
            self.log(f"temp_up {temp}")
            haui_entity.call_entity_service("set_temperature", temperature=temp)
        elif fnc_name == "temp_down":
            temp = haui_entity.get_entity_attr("temperature", 0)
            min_temp = haui_entity.get_entity_attr("min_temp", 0)
            target_temp_step = haui_entity.get_entity_attr("target_temp_step", 0)
            temp = max(min_temp, temp - target_temp_step)
            self.log(f"temp_down {temp}")
            haui_entity.call_entity_service("set_temperature", temperature=temp)

        elif fnc_name == "hvac_mode":
            hvac_mode = "off"
            for i in range(self.NUM_MODES):
                component = getattr(self, f"BT_MODE_{i+1}")
                if i < len(self._hvac_modes) and component[1] == fnc_id:
                    hvac_mode = self._hvac_modes[i]
                    break
            haui_entity.call_entity_service("set_hvac_mode", hvac_mode=hvac_mode)
        elif fnc_name == "fan_mode":
            self.log("fan_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_entity.get_entity_attr("fan_modes", [])
            selected = self._climate_entity.get_entity_attr("fan_mode", "")
            fan_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="fan_mode")
                fan_modes.append({"value": value, "name": name})
            if len(fan_modes) > 0:
                navigation.open_popup(
                    "popup_select",
                    title=self.translate("Select fan mode"),
                    items=fan_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_fan_mode,
                    close_on_select=True,
                )
        elif fnc_name == "preset_mode":
            self.log("preset_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_entity.get_entity_attr("preset_modes", [])
            selected = self._climate_entity.get_entity_attr("preset_mode", "")
            preset_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="preset_mode")
                preset_modes.append({"value": value, "name": name})
            if len(preset_modes) > 0:
                navigation.open_popup(
                    "popup_select",
                    title=self.translate("Select preset mode"),
                    items=preset_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_preset_mode,
                    close_on_select=True,
                )
        elif fnc_name == "swing_mode":
            self.log("swing_mode")
            navigation = self.app.controller["navigation"]
            selection = self._climate_entity.get_entity_attr("swing_modes", [])
            selected = self._climate_entity.get_entity_attr("swing_mode", "")
            swing_modes = []
            for value in selection:
                name = self.translate_state("climate", value, attr="swing_mode")
                swing_modes.append({"value": value, "name": name})
            if len(swing_modes) > 0:
                navigation.open_popup(
                    "popup_select",
                    title=self.translate("Select swing mode"),
                    items=swing_modes,
                    selected=selected,
                    selection_callback_fnc=self.callback_swing_mode,
                    close_on_select=True,
                )
        elif fnc_name == "power_off":
            self.log("power_off")
            if self._climate_entity.get_entity_state() != "off":
                self._climate_entity.call_entity_service("set_hvac_mode", hvac_mode="off")

    def callback_fan_mode(self, selection):
        self.log(f"Got fan mode selection: {selection}")
        self._climate_entity.call_entity_service("set_fan_mode", fan_mode=selection)

    def callback_preset_mode(self, selection):
        self.log(f"Got preset mode selection: {selection}")
        self._climate_entity.call_entity_service("set_preset_mode", preset_mode=selection)

    def callback_swing_mode(self, selection):
        self.log(f"Got swing mode selection: {selection}")
        self._climate_entity.call_entity_service("set_swing_mode", swing_mode=selection)

    def callback_climate_entity(self, entity, attribute, old, new, kwargs):
        self.start_rec_cmd()
        self.update_climate_entity()
        self.stop_rec_cmd(send_commands=True)

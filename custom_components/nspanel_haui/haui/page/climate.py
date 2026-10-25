from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import ClimateFeatures
from ..mapping.color import CLIMATE_COLORS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icon_mapping import CLIMATE_MAPPING
from ..mapping.icons import ICO_DOWN, ICO_FAN, ICO_NAV_UP, ICO_POWER, ICO_PRESET, ICO_SWING
from ..utils.icon import get_icon


class ClimatePage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="climate",
        page_name="climate",
        page_id=16,
        label=_("Climate"),
        description=_("Climate item with temperature and mode controls."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="climate",
                description=_("Climate/HVAC entity for temperature control and mode switching."),
                section=_("Climate"),
            ),
            PageOption(
                key="hvac_modes",
                kind="list_items",
                default=[],
                choices=[
                    ("off", _("Off")),
                    ("heat", _("Heat")),
                    ("cool", _("Cool")),
                    ("heat_cool", _("Heat/Cool")),
                    ("auto", _("Auto")),
                    ("dry", _("Dry")),
                    ("fan_only", _("Fan Only")),
                ],
                label=_("HVAC modes override"),
                description=_("Override HVAC modes shown on this panel."),
                section=_("Climate"),
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

    # (component, fnc_name, icon, feature flag) of the fan/preset/swing buttons
    _MODE_BUTTONS = (
        (COMPONENTS.btn_fan, "fan_mode", ICO_FAN, ClimateFeatures.FAN_MODE),
        (COMPONENTS.btn_preset, "preset_mode", ICO_PRESET, ClimateFeatures.PRESET_MODE),
        (COMPONENTS.btn_swing, "swing_mode", ICO_SWING, ClimateFeatures.SWING_MODE),
    )

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
        item = self._resolve_panel_item(panel)
        self.set_climate_item(item, panel.get("hvac_modes", []))
        # set title
        self._title = self._panel_title(panel, item, self.translate("Climate"))
        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, self._title)
        self.update_climate_item()

    # misc

    def set_climate_item(self, item: HAUIItem | None, hvac_modes: list[str]) -> None:
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
        for attribute in ("target_temp_low", "target_temp_high"):
            self.add_item_listener(
                item.get_item_id(), self.callback_climate_item, attribute=attribute
            )
        # setpoint buttons are registered hidden; update_climate_control shows
        # the single or the range setpoint depending on the entity's current values
        for component, fnc_name, icon in (
            (self.COMPONENTS.btn_up, "temp_up", ICO_NAV_UP),
            (self.COMPONENTS.btn_down, "temp_down", ICO_DOWN),
            (self.COMPONENTS.btn_up_1, "temp_low_up", ICO_NAV_UP),
            (self.COMPONENTS.btn_down_1, "temp_low_down", ICO_DOWN),
            (self.COMPONENTS.btn_up_2, "temp_high_up", ICO_NAV_UP),
            (self.COMPONENTS.btn_down_2, "temp_high_down", ICO_DOWN),
        ):
            self.set_function_component(
                component,
                component.name,
                fnc_name,
                color=self.get_color("component_active"),
                icon=icon,
                visible=False,
            )
        # hvac mode buttons
        entity_modes = item.get_item_attr("hvac_modes", [])
        if hvac_modes:
            # modes the entity lacks would only fail in set_hvac_mode
            self._hvac_modes = [mode for mode in hvac_modes if mode in entity_modes]
        else:
            self._hvac_modes = entity_modes
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
        # fan, preset and swing buttons
        for component, fnc_name, icon, flag in self._MODE_BUTTONS:
            supported = item.supports(flag)
            self.set_function_component(
                component,
                component.name,
                fnc_name,
                icon=icon,
                visible=True,
                color=self.get_color("component_active" if supported else "text_inactive"),
                touch=supported,
            )

    def update_climate_item(self) -> None:
        if self._climate_item is None:
            return
        item = self._climate_item
        self.update_climate_control(item)
        self.update_climate_info(item)
        self.update_hvac_modes(item)

    def update_climate_control(self, item: HAUIItem) -> None:
        self.update_setpoints(item)
        for component, _fnc_name, _icon, flag in self._MODE_BUTTONS:
            supported = item.supports(flag)
            self.update_function_component(
                component.name, touch=supported, **self.button_color_args(supported)
            )
        # hvac_mode
        hvac_mode = item.get_item_state()
        if hvac_mode != "off":
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    def update_setpoints(self, item: HAUIItem) -> None:
        # Same rule as HA's frontend: the attributes present decide the layout,
        # since entities supporting both kinds report only one at a time.
        target = item.get_item_attr("temperature")
        low = item.get_item_attr("target_temp_low")
        high = item.get_item_attr("target_temp_high")
        single = target is not None
        ranged = low is not None and high is not None
        for component, shown in (
            (self.COMPONENTS.x_set, single),
            (self.COMPONENTS.t_unit, single),
            (self.COMPONENTS.x_set_1, ranged),
            (self.COMPONENTS.t_unit_1, ranged),
            (self.COMPONENTS.x_set_2, ranged),
            (self.COMPONENTS.t_unit_2, ranged),
        ):
            if shown:
                self.show_component(component)
            else:
                self.hide_component(component)
        for component, shown in (
            (self.COMPONENTS.btn_up, single),
            (self.COMPONENTS.btn_down, single),
            (self.COMPONENTS.btn_up_1, ranged),
            (self.COMPONENTS.btn_down_1, ranged),
            (self.COMPONENTS.btn_up_2, ranged),
            (self.COMPONENTS.btn_down_2, ranged),
        ):
            self.update_function_component(component.name, visible=shown)
        if single:
            self.set_component_value(self.COMPONENTS.x_set, int(target * 10))
        if ranged:
            self.set_component_value(self.COMPONENTS.x_set_1, int(low * 10))
            self.set_component_value(self.COMPONENTS.x_set_2, int(high * 10))

    def _step_range(self, item: HAUIItem, fnc_name: str) -> None:
        low = item.get_item_attr("target_temp_low")
        high = item.get_item_attr("target_temp_high")
        if low is None or high is None:
            self.log(f"{fnc_name} ignored: entity has no target range", level="WARNING")
            return
        min_temp = item.get_item_attr("min_temp", 0)
        max_temp = item.get_item_attr("max_temp", 0)
        step = item.get_item_attr("target_temp_step", self._default_temp_step())
        if fnc_name == "temp_low_up":
            low = min(high, low + step)
        elif fnc_name == "temp_low_down":
            low = max(min_temp, low - step)
        elif fnc_name == "temp_high_up":
            high = min(max_temp, high + step)
        else:
            high = max(low, high - step)
        self.log(f"{fnc_name} {low}-{high}")
        item.call_item_service("set_temperature", target_temp_low=low, target_temp_high=high)

    def _default_temp_step(self) -> float:
        # Climate entities only expose target_temp_step when their integration
        # sets one; HA's own frontend then steps by 1 on Fahrenheit systems and
        # 0.5 otherwise.
        return 1.0 if self.app.get_temperature_unit() == "°F" else 0.5

    def update_climate_info(self, item: HAUIItem) -> None:
        current_temp = item.get_item_attr("current_temperature", 0)
        unit = self.app.get_temperature_unit()
        for component in (
            self.COMPONENTS.t_unit,
            self.COMPONENTS.t_unit_1,
            self.COMPONENTS.t_unit_2,
        ):
            self.set_component_text(component, unit)
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
        if fnc_name in ("temp_up", "temp_down") and haui_item.get_item_attr("temperature") is None:
            # entities supporting both setpoint kinds report no single target in
            # range modes such as heat_cool; stepping from nothing would send a
            # bogus setpoint
            self.log(
                f"{fnc_name} ignored: entity has no single target temperature",
                level="WARNING",
            )
        elif fnc_name == "temp_up":
            temp = haui_item.get_item_attr("temperature")
            max_temp = haui_item.get_item_attr("max_temp", 0)
            target_temp_step = haui_item.get_item_attr(
                "target_temp_step", self._default_temp_step()
            )
            temp = min(max_temp, temp + target_temp_step)
            self.log(f"temp_up {temp}")
            haui_item.call_item_service("set_temperature", temperature=temp)
        elif fnc_name == "temp_down":
            temp = haui_item.get_item_attr("temperature")
            min_temp = haui_item.get_item_attr("min_temp", 0)
            target_temp_step = haui_item.get_item_attr(
                "target_temp_step", self._default_temp_step()
            )
            temp = max(min_temp, temp - target_temp_step)
            self.log(f"temp_down {temp}")
            haui_item.call_item_service("set_temperature", temperature=temp)

        elif fnc_name in ("temp_low_up", "temp_low_down", "temp_high_up", "temp_high_down"):
            self._step_range(haui_item, fnc_name)
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
            self._open_mode_select(
                haui_item, "fan_mode", self.translate("Select fan mode"), self.callback_fan_mode
            )
        elif fnc_name == "preset_mode":
            self._open_mode_select(
                haui_item,
                "preset_mode",
                self.translate("Select preset mode"),
                self.callback_preset_mode,
            )
        elif fnc_name == "swing_mode":
            self._open_mode_select(
                haui_item,
                "swing_mode",
                self.translate("Select swing mode"),
                self.callback_swing_mode,
            )
        elif fnc_name == "power_off":
            self.log("power_off")
            if self._climate_item.get_item_state() != "off":
                self._climate_item.call_item_service("set_hvac_mode", hvac_mode="off")

    def _open_mode_select(
        self, item: HAUIItem, mode: str, title: str, callback: Callable[[str], None]
    ) -> None:
        """Opens the selection popup for a fan/preset/swing mode.

        Args:
            item: The climate item.
            mode: Attribute holding the current mode; its ``<mode>s`` list holds the choices.
            title: Translated popup title.
            callback: Receives the selected value.
        """
        self.log(mode)
        modes = [
            {"value": value, "name": self.translate_state("climate", value, attr=mode)}
            for value in item.get_item_attr(f"{mode}s", [])
        ]
        if len(modes) > 0:
            self.app.controller["navigation"].open_panel(
                SysPanelKey.POPUP_SELECT,
                title=title,
                items=modes,
                selected=item.get_item_attr(mode, ""),
                selection_callback_fnc=callback,
                close_on_select=True,
            )

    def _select_mode(self, mode: str, selection: str) -> None:
        self.log(f"Got {mode.replace('_', ' ')} selection: {selection}")
        if self._climate_item is not None:
            self._climate_item.call_item_service(f"set_{mode}", **{mode: selection})

    def callback_fan_mode(self, selection: str) -> None:
        self._select_mode("fan_mode", selection)

    def callback_preset_mode(self, selection: str) -> None:
        self._select_mode("preset_mode", selection)

    def callback_swing_mode(self, selection: str) -> None:
        self._select_mode("swing_mode", selection)

    def callback_climate_item(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        with self.rec_cmd:
            self.update_climate_item()

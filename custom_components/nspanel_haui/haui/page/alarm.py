from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, PageOption


class AlarmPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="alarm",
        page_name="alarm",
        label="Alarm",
        description="Alarm control panel with numeric keypad.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="alarm_control_panel",
                description="Alarm control panel item for arming/disarming the security system.",
                section="Alarm",
            ),
        ],
        icon="mdi:shield-lock-outline",
    )

    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        title=Component(2, "tTitle"),
        btn_key_1=Component(7, "bKey1"),
        btn_key_2=Component(8, "bKey2"),
        btn_key_3=Component(9, "bKey3"),
        btn_key_4=Component(10, "bKey4"),
        btn_key_5=Component(11, "bKey5"),
        btn_key_6=Component(12, "bKey6"),
        btn_key_7=Component(13, "bKey7"),
        btn_key_8=Component(14, "bKey8"),
        btn_key_9=Component(15, "bKey9"),
        btn_key_clr=Component(16, "bKeyClr"),
        btn_key_0=Component(17, "bKey0"),
        btn_key_del=Component(18, "bKeyDel"),
        b1_fnc=Component(19, "b1Fnc"),
        b2_fnc=Component(20, "b2Fnc"),
        b3_fnc=Component(21, "b3Fnc"),
        b4_fnc=Component(22, "b4Fnc"),
    )

    # alarm state icons
    _ALARM_ICONS = {
        "disarmed": "mdi:shield-off-outline",
        "armed_home": "mdi:shield-home-outline",
        "armed_away": "mdi:shield-lock-outline",
        "armed_night": "mdi:weather-night",
        "armed_vacation": "mdi:shield-airplane-outline",
        "armed_custom_bypass": "mdi:shield-check-outline",
        "pending": "mdi:shield-outline",
        "triggered": "mdi:alert-circle-outline",
        "arming": "mdi:shield-sync-outline",
    }

    _ALARM_COLOR_KEYS = {
        "disarmed": "alarm_disarmed",
        "armed_home": "alarm_armed",
        "armed_away": "alarm_armed",
        "armed_night": "alarm_armed",
        "armed_vacation": "alarm_armed",
        "armed_custom_bypass": "alarm_armed",
        "pending": "alarm_arming",
        "triggered": "alarm_armed",
        "arming": "alarm_arming",
    }

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )
        self.set_function_component(
            self.COMPONENTS.fnc_right_sec, self.FNC_BTN_R_SEC, "armed_indicator"
        )
        # register alarm item state listener
        items = self._build_items_from_panel(panel, "items")
        if items:
            item = items[0]
            self.add_item_listener(item.get_item_id(), self.callback_alarm_state, "state")
            # initial state render
            self.update_armed_indicator(item)

    # callback

    def callback_alarm_state(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            self.update_function_component(
                self.FNC_BTN_R_SEC,
                icon=self._ALARM_ICONS.get(new, ""),
                color=self.get_color(self._ALARM_COLOR_KEYS.get(new, "text")),
                visible=True,
            )

    def update_armed_indicator(self, item: HAUIItem) -> None:
        state = item.get_item_state() or ""
        icon = self._ALARM_ICONS.get(state, "")
        color = self.get_color(self._ALARM_COLOR_KEYS.get(state, "text"))
        self.update_function_component(
            self.FNC_BTN_R_SEC,
            icon=icon,
            color=color,
            visible=True,
        )

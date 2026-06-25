from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.color import ALARM_COLORS
from ..mapping.descriptor import PageDescriptor, PageOption, _


class AlarmPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="alarm",
        page_name="alarm",
        label=_("Alarm"),
        description=_("Alarm control panel with numeric keypad."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="alarm_control_panel",
                description=_("Alarm control panel item for arming/disarming the security system."),
                section=_("Alarm"),
            ),
        ],
        icon="mdi:shield-lock-outline",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_key_1=Component(8, "bKey1"),
        btn_key_2=Component(9, "bKey2"),
        btn_key_3=Component(10, "bKey3"),
        btn_key_4=Component(11, "bKey4"),
        btn_key_5=Component(12, "bKey5"),
        btn_key_6=Component(13, "bKey6"),
        btn_key_7=Component(14, "bKey7"),
        btn_key_8=Component(15, "bKey8"),
        btn_key_9=Component(16, "bKey9"),
        btn_key_clr=Component(17, "bKeyClr"),
        btn_key_0=Component(18, "bKey0"),
        btn_key_del=Component(19, "bKeyDel"),
        b1_fnc=Component(20, "b1Fnc"),
        b2_fnc=Component(21, "b2Fnc"),
        b3_fnc=Component(22, "b3Fnc"),
        b4_fnc=Component(23, "b4Fnc"),
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

    # alarm state -> ALARM_COLORS palette key
    _ALARM_COLOR_KEYS = {
        "disarmed": "disarmed",
        "armed_home": "armed",
        "armed_away": "armed",
        "armed_night": "armed",
        "armed_vacation": "armed",
        "armed_custom_bypass": "armed",
        "pending": "arming",
        "triggered": "armed",
        "arming": "arming",
    }

    def _alarm_color(self, state: str) -> int:
        """Resolve the icon color for an alarm *state* from ALARM_COLORS.

        Falls back to the global ``text`` color for unmapped states.
        """
        key = self._ALARM_COLOR_KEYS.get(state)
        return ALARM_COLORS[key] if key is not None else self.get_color("text")

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
        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

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
                color=self._alarm_color(new),
                visible=True,
            )

    def update_armed_indicator(self, item: HAUIItem) -> None:
        state = item.get_item_state() or ""
        icon = self._ALARM_ICONS.get(state, "")
        color = self._alarm_color(state)
        self.update_function_component(
            self.FNC_BTN_R_SEC,
            icon=icon,
            color=color,
            visible=True,
        )

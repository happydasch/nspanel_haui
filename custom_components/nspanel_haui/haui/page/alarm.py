from typing import Any

from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..mapping.color import COLORS
from ..mapping.descriptor import PageDescriptor, PageOption
from . import HAUIPage


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

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # keypad
    BTN_KEY_1, BTN_KEY_2, BTN_KEY_3 = (7, "bKey1"), (8, "bKey2"), (9, "bKey3")
    BTN_KEY_4, BTN_KEY_5, BTN_KEY_6 = (10, "bKey4"), (11, "bKey5"), (12, "bKey6")
    BTN_KEY_7, BTN_KEY_8, BTN_KEY_9 = (13, "bKey7"), (14, "bKey8"), (15, "bKey9")
    BTN_KEY_CLR, BTN_KEY_0, BTN_KEY_DEL = (
        (16, "bKeyClr"),
        (17, "bKey0"),
        (18, "bKeyDel"),
    )
    # functions
    B1_FNC, B2_FNC, B3_FNC, B4_FNC = (
        (19, "b1Fnc"),
        (20, "b2Fnc"),
        (21, "b3Fnc"),
        (22, "b4Fnc"),
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

    _ALARM_COLORS = {
        "disarmed": COLORS["alarm_disarmed"],
        "armed_home": COLORS["alarm_armed"],
        "armed_away": COLORS["alarm_armed"],
        "armed_night": COLORS["alarm_armed"],
        "armed_vacation": COLORS["alarm_armed"],
        "armed_custom_bypass": COLORS["alarm_armed"],
        "pending": COLORS["alarm_arming"],
        "triggered": COLORS["alarm_armed"],
        "arming": COLORS["alarm_arming"],
    }

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )
        self.set_function_component(self.BTN_FNC_RIGHT_SEC, self.FNC_BTN_R_SEC, "armed_indicator")
        # register alarm item state listener
        items = self._build_items_from_panel(panel, "items")
        if items:
            item = items[0]
            self.add_item_listener(item.get_item_id(), self.callback_alarm_state, "state")
            # initial state render
            self.update_armed_indicator(item)

    def stop_panel(self, panel: HAUIPanel) -> None:
        super().stop_panel(panel)

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
                color=self._ALARM_COLORS.get(new, COLORS["text"]),
                visible=True,
            )

    def update_armed_indicator(self, item: HAUIItem) -> None:
        state = item.get_item_state() or ""
        icon = self._ALARM_ICONS.get(state, "")
        color = self._ALARM_COLORS.get(state, COLORS["text"])
        self.update_function_component(
            self.FNC_BTN_R_SEC,
            icon=icon,
            color=color,
            visible=True,
        )

from . import HAUIPage


class ThermoPage(HAUIPage):
    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # entities
    BT1_ENTITY, BT2_ENTITY, BT3_ENTITY = (
        (7, "btEntity1"),
        (8, "btEntity2"),
        (9, "btEntity3"),
    )
    BT4_ENTITY, BT5_ENTITY, BT6_ENTITY = (
        (10, "btEntity4"),
        (10, "btEntity5"),
        (12, "btEntity6"),
    )
    BT7_ENTITY, BT8_ENTITY = (13, "btEntity7"), (14, "btEntity8")
    # info
    TXT_CURR_TEMP, TXT_CURR_TEMP_VAL = (15, "tCurrTemp"), (16, "tCurrTempVal")
    TXT_STATE, TXT_STATE_VAL = (17, "tState"), (18, "tStateVal")
    # control
    BT_DOWN, BT_UP, BT_DETAIL = (19, "btDown"), (20, "btUp"), (21, "btDetail")
    X_SET, TXT_UNIT = (22, "xSet"), (23, "tUnit")
    BT_DOWN_1, BT_UP_1, X_SET_1, TXT_UNIT_1 = (
        (24, "btDown1"),
        (25, "btUp1"),
        (26, "xSet1"),
        (27, "tUnit1"),
    )
    BT_DOWN_2, BT_UP_2, X_SET_2, TXT_UNIT_2 = (
        (28, "btDown2"),
        (29, "btUp2"),
        (30, "xSet2"),
        (31, "tUnit2"),
    )

    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())


def PopupThermoPage(ThermoPage):
    pass

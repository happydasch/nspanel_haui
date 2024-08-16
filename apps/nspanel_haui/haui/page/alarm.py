from ..abstract.panel import HAUIPanel

from . import HAUIPage


class AlarmPage(HAUIPage):
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

    # panel

    def start_panel(self, panel: HAUIPanel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )
        self.set_function_component(
            self.BTN_FNC_RIGHT_SEC, self.FNC_BTN_R_SEC, "armed_indicator"
        )

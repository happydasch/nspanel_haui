from . import HAUIPage


class PowerPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')

    # home
    TXT_HOME, TXT_HOME_TOP, TXT_HOME_TOP_VAL = (7, 'tHome'), (8, 'tHomeTop'), (9, 'tHomeTopVal')
    TXT_HOME_BOT, TXT_HOME_BOT_VAL = (10, 'tHomeBot'), (11, 'tHomeBotVal')
    # p1
    TXT_ICON_1, H_SLIDER_1, TXT_ABOVE_1, TXT_BELOW_1 = (12, 'tIcon1'), (13, 'hSlider1'), (14, 'tAbove1'), (15, 'tBelow1')
    # p2
    TXT_ICON_2, H_SLIDER_2, TXT_ABOVE_2, TXT_BELOW_2 = (16, 'tIcon2'), (17, 'hSlider2'), (18, 'tAbove2'), (19, 'tBelow2')
    # p3
    TXT_ICON_3, H_SLIDER_3, TXT_ABOVE_3, TXT_BELOW_3 = (20, 'tIcon3'), (21, 'hSlider3'), (22, 'tAbove3'), (23, 'tBelow3')
    # p4
    TXT_ICON_4, H_SLIDER_4, TXT_ABOVE_4, TXT_BELOW_4 = (24, 'tIcon4'), (25, 'hSlider4'), (26, 'tAbove4'), (27, 'tBelow4')
    # p5
    TXT_ICON_5, H_SLIDER_5, TXT_ABOVE_5, TXT_BELOW_5 = (28, 'tIcon5'), (29, 'hSlider5'), (30, 'tAbove5'), (31, 'tBelow5')
    # p6
    TXT_ICON_6, H_SLIDER_6, TXT_ABOVE_6, TXT_BELOW_6 = (32, 'tIcon6'), (33, 'hSlider6'), (34, 'tAbove6'), (35, 'tBelow6')

    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, self.BTN_FNC_RIGHT_SEC)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())

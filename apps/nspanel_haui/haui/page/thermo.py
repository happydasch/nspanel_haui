from . import HAUIPage


class ThermostatPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')
    # entities
    BT1_ENTITY, BT2_ENTITY, BT3_ENTITY = (7, 'btEntity1'), (8, 'btEntity2'), (9, 'btEntity3')
    BT4_ENTITY, BT5_ENTITY, BT6_ENTITY = (10, 'btEntity4'), (10, 'btEntity5'), (12, 'btEntity6')
    BT7_ENTITY, BT8_ENTITY = (13, 'btEntity7'), (14, 'btEntity8')
    # info
    TXT_CURR_TEMP, TXT_CURR_TEMP_VAL = (15, 'tCurrTemp'), (16, 'tCurrTempVal')
    TXT_STATE, TXT_STATE_VAL = (17, 'tState'), (18, 'tStateVal')
    # control
    BT_DOWN, BT_UP, BT_DETAIL = (19, 'btDown'), (20, 'btUp'), (21, 'btDetail')
    X_SET, TXT_UNIT = (22, 'xSet'), (23, 'tUnit')
    BT_DOWN_1, BT_UP_1, X_SET_1, TXT_UNIT_1 = (24, 'btDown1'), (25, 'btUp1'), (26, 'xSet1'), (27, 'tUnit1')
    BT_DOWN_2, BT_UP_2, X_SET_2, TXT_UNIT_2 = (28, 'btDown2'), (29, 'btUp2'), (30, 'xSet2'), (31, 'tUnit2')

    # panel

    def start_panel(self, panel):
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_prev_next_nav_buttons(self.BTN_NAV_LEFT, self.BTN_NAV_RIGHT)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())

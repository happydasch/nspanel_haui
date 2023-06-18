from . import HAUIPage


class PopupTimerPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')

    # panel

    def start_panel(self, panel):
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_close_nav_button(self.BTN_NAV_CLOSE)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())

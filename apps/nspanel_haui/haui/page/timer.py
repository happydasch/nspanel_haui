from . import HAUIPage


class PopupTimerPage(HAUIPage):

    # common components
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')

    # panel

    def start_panel(self, panel):
        self.set_close_nav_button(self.BTN_NAV_CLOSE)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())

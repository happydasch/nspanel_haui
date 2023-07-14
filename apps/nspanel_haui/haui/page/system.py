from . import HAUIPage


class SystemPage(HAUIPage):

    # qr code with url
    QR_URL = (1, 'qrUrl')
    # spinner animation
    H_SPINNER = (2, 'hSpinner')
    # text components
    TXT_TITLE = (3, 'tTitle')
    TXT_MSG1 = (4, 'tMsg1')
    TXT_MSG2 = (5, 'tMsg2')

    # panel

    def render_panel(self, panel):
        # update default text
        self.set_title(self.translate('Waiting for Connection'))
        self.set_message(
            self.translate('This is taking longer than usual,'),
            self.translate('please check your configuration'))

    def after_render_panel(self, panel, rendered):
        # open home panel
        navigation = self.app.controller['navigation']
        navigation.open_home_panel()

    # misc

    def set_title(self, title):
        self.set_component_text(self.TXT_TITLE, title)

    def set_message(self, text_1, text_2):
        self.set_component_text(self.TXT_MSG1, text_1)
        self.set_component_text(self.TXT_MSG2, text_2)

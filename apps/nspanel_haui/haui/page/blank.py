from ..config import HAUIConfigPanel
from . import HAUIPage


class BlankPage(HAUIPage):
    H_BLANK = (1, "hBlank")

    # panel

    def start_panel(self, panel: HAUIConfigPanel):
        self.add_component_callback(self.H_BLANK, self.callback_blank)

    # callback

    def callback_blank(self, event, component, button_state):
        self.log("Blank callback")

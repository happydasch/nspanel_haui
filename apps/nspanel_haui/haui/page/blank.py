from ..abstract.panel import HAUIPanel
from . import HAUIPage


class BlankPage(HAUIPage):
    H_BLANK = (1, "hBlank")

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        self.add_component_callback(self.H_BLANK, self.callback_blank)

    # callback

    def callback_blank(self, event, component, button_state) -> None:
        self.log("Blank callback")

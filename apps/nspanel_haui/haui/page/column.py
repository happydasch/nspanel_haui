from ..mapping.color import COLORS
from ..helper.icon import get_icon, get_icon_name_by_action
from . import HAUIPage


class ColumnPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')

    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, self.BTN_FNC_RIGHT_SEC)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())

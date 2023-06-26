from ..mapping.color import COLORS
from ..helper.icon import get_icon, get_icon_name_by_action
from . import HAUIPage


class ColumnPage(HAUIPage):

    # common components
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')

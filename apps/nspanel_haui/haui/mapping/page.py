# system panels
from ..page.blank import BlankPage
from ..page.system import SystemPage
from ..page.settings import SettingsPage
from ..page.about import AboutPage
# default panels
from ..page.weather import WeatherPage
from ..page.clock import ClockPage
from ..page.grid import GridPage
from ..page.row import RowPage
from ..page.column import ColumnPage
from ..page.split import SplitPage
from ..page.qr import QRPage
from ..page.media import MediaPage
from ..page.thermo import ThermoPage
from ..page.alarm import AlarmPage
from ..page.power import PowerPage
# popup panels
from ..page.alarm import PopupUnlockPage
from ..page.notify import PopupNotifyPage
from ..page.select import PopupSelectPage
from ..page.light import PopupLightPage
from ..page.thermo import PopupThermoPage
from ..page.timer import PopupTimerPage


# page id mapping
# page classes are contained in panel mapping
# since page classes may be different on panels
# using the same page
# page_id -> page_name
PAGE_MAPPING = {
    0: 'blank',
    1: 'system',
    2: 'settings',
    3: 'about',
    4: 'weather',
    5: 'clock',
    6: 'grid',
    7: 'row',
    8: 'column',
    9: 'split',
    10: 'light',
    11: 'thermo',
    12: 'media',
    13: 'qr',
    14: 'alarm',
    15: 'timer',
    16: 'power',
    17: 'notify',
    18: 'select',
}


# system panel mapping
# sys_panel_key -> panel_type
SYS_PANEL_MAPPING = {
    # sys pages
    'sys_blank': 'blank',
    'sys_system': 'system',
    'sys_settings': 'system_settings',
    'sys_about': 'system_about',
    # popups
    'popup_unlock': 'popup_unlock',
    'popup_notify': 'popup_notify',
    'popup_select': 'popup_select',
    'popup_light': 'popup_light',
    'popup_thermo': 'popup_thermo',
    'popup_timer': 'popup_timer',
}


# panel types mapping
# panel_type -> (page_name, page_class)
PANEL_MAPPING = {
    # sys panels
    'blank': ('blank', BlankPage),
    'system': ('system', SystemPage),
    'system_settings': ('settings', SettingsPage),
    'system_about': ('about', AboutPage),
    # panels
    'weather': ('weather', WeatherPage),
    'clock': ('clock', ClockPage),
    'grid': ('grid', GridPage),
    'row': ('row', RowPage),
    'column': ('column', ColumnPage),
    'split': ('split', SplitPage),
    'qr': ('qr', QRPage),
    'media': ('media', MediaPage),
    'thermo': ('thermo', ThermoPage),
    'alarm': ('alarm', AlarmPage),
    'power': ('power', PowerPage),
    # popups
    'popup_unlock': ('alarm', PopupUnlockPage),
    'popup_notify': ('notify', PopupNotifyPage),
    'popup_select': ('select', PopupSelectPage),
    'popup_light': ('light', PopupLightPage),
    'popup_thermo': ('thermo', PopupThermoPage),
    'popup_timer': ('timer', PopupTimerPage),
}

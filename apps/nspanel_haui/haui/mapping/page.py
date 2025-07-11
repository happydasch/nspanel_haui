# system panels
from ..page.blank import BlankPage
from ..page.system import SystemPage
from ..page.settings import SettingsPage
from ..page.about import AboutPage

# default panels
from ..page.weather import WeatherPage
from ..page.clock import ClockPage
from ..page.clocktwo import ClockTwoPage
from ..page.grid import GridPage
from ..page.row import RowPage
from ..page.light import LightPage
from ..page.media import MediaPage
from ..page.vacuum import VacuumPage
from ..page.timer import TimerPage
from ..page.qr import QRPage
from ..page.climate import ClimatePage
from ..page.alarm import AlarmPage
from ..page.cover import CoverPage

# misc panels
from ..page.unlock import UnlockPage
from ..page.notify import NotifyPage, NotificationPage
from ..page.select import SelectPage


# page id mapping
# page classes are contained in panel mapping
# since page classes may be different on panels
# using the same page
# page_id -> page_name
PAGE_MAPPING = {
    0: "blank",
    1: "system",
    2: "about",
    3: "settings",
    4: "notify",
    5: "select",
    6: "weather",
    7: "clock",
    8: "clocktwo",
    9: "grid",
    10: "row",
    11: "qr",
    12: "timer",
    13: "light",
    14: "media",
    15: "vacuum",
    16: "climate",
    17: "alarm",
    18: "cover",
}

# system panel mapping
# sys_panel_key -> panel_type
SYS_PANEL_MAPPING = {
    # sys pages
    "sys_blank": "blank",
    "sys_system": "system",
    "sys_settings": "system_settings",
    "sys_about": "system_about",
    # popups
    "popup_unlock": "popup_unlock",
    "popup_notify": "popup_notify",
    "popup_notification": "popup_notification",
    "popup_select": "popup_select",
    "popup_light": "popup_light",
    "popup_media_player": "popup_media_player",
    "popup_vacuum": "popup_vacuum",
    "popup_climate": "popup_climate",
    "popup_timer": "popup_timer",
    "popup_cover": "popup_cover",
}


# panel types mapping
# panel_type -> (page_name, page_class)
PANEL_MAPPING = {
    # sys panels
    "blank": ("blank", BlankPage),
    "system": ("system", SystemPage),
    "system_settings": ("settings", SettingsPage),
    "system_about": ("about", AboutPage),
    # panels
    "weather": ("weather", WeatherPage),
    "clock": ("clock", ClockPage),
    "clocktwo": ("clocktwo", ClockTwoPage),
    "grid": ("grid", GridPage),
    "row": ("row", RowPage),
    "light": ("light", LightPage),
    "media": ("media", MediaPage),
    "vacuum": ("vacuum", VacuumPage),
    "timer": ("timer", TimerPage),
    "qr": ("qr", QRPage),
    "climate": ("climate", ClimatePage),
    "alarm": ("alarm", AlarmPage),
    "cover": ("cover", CoverPage),
    # popups
    "popup_unlock": ("alarm", UnlockPage),
    "popup_notify": ("notify", NotifyPage),
    "popup_notification": ("notify", NotificationPage),
    "popup_select": ("select", SelectPage),
    "popup_light": ("light", LightPage),
    "popup_media_player": ("media", MediaPage),
    "popup_vacuum": ("vacuum", VacuumPage),
    "popup_climate": ("climate", ClimatePage),
    "popup_timer": ("timer", TimerPage),
    "popup_cover": ("cover", CoverPage),
}

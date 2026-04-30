from __future__ import annotations

from .descriptor import PageDescriptor

# system panels
from ..page.about import AboutPage
from ..page.alarm import AlarmPage
from ..page.blank import BlankPage
from ..page.climate import ClimatePage
from ..page.clock import ClockPage
from ..page.clocktwo import ClockTwoPage
from ..page.cover import CoverPage
from ..page.grid import GridPage
from ..page.light import LightPage
from ..page.media import MediaPage
from ..page.notify import NotifsPage, NotifyPage
from ..page.qr import QRPage
from ..page.row import RowPage
from ..page.select import SelectPage
from ..page.settings import SettingsPage
from ..page.system import SystemPage
from ..page.timer import TimerPage
from ..page.unlock import UnlockPage
from ..page.vacuum import VacuumPage
from ..page.weather import WeatherPage

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
    "popup_notifs": "popup_notifs",
    "popup_select": "popup_select",
    "popup_light": "popup_light",
    "popup_media_player": "popup_media_player",
    "popup_vacuum": "popup_vacuum",
    "popup_climate": "popup_climate",
    "popup_timer": "popup_timer",
    "popup_cover": "popup_cover",
}

# Collect descriptors from all page classes that define one,
# then add popup aliases which reuse existing page classes.
def _build_panel_mapping() -> dict[str, tuple[str, type]]:
    _page_classes = [
        AboutPage, AlarmPage, BlankPage, ClimatePage, ClockPage, ClockTwoPage,
        CoverPage, GridPage, LightPage, MediaPage, NotifsPage, NotifyPage,
        QRPage, RowPage, SelectPage, SettingsPage, SystemPage, TimerPage,
        UnlockPage, VacuumPage, WeatherPage,
    ]
    mapping: dict[str, tuple[str, type]] = {}
    for cls in _page_classes:
        d: PageDescriptor | None = getattr(cls, "DESCRIPTOR", None)
        if d is not None:
            mapping[d.type_key] = (d.page_name, cls)

    # popup aliases — share page classes with their non-popup counterparts
    popup_aliases = {
        "popup_unlock":       ("alarm",  UnlockPage),
        "popup_notify":       ("notify", NotifyPage),
        "popup_notifs":       ("notifs", NotifsPage),
        "popup_select":       ("select", SelectPage),
        "popup_light":        ("light",  LightPage),
        "popup_media_player": ("media",  MediaPage),
        "popup_vacuum":       ("vacuum", VacuumPage),
        "popup_climate":      ("climate", ClimatePage),
        "popup_timer":        ("timer",  TimerPage),
        "popup_cover":        ("cover",  CoverPage),
    }
    mapping.update(popup_aliases)
    return mapping


PANEL_MAPPING: dict[str, tuple[str, type]] = _build_panel_mapping()

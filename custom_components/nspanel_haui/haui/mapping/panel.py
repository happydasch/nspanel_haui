from __future__ import annotations

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
from .descriptor import PageDescriptor

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
        AboutPage,
        AlarmPage,
        BlankPage,
        ClimatePage,
        ClockPage,
        ClockTwoPage,
        CoverPage,
        GridPage,
        LightPage,
        MediaPage,
        NotifsPage,
        NotifyPage,
        QRPage,
        RowPage,
        SelectPage,
        SettingsPage,
        SystemPage,
        TimerPage,
        UnlockPage,
        VacuumPage,
        WeatherPage,
    ]
    mapping: dict[str, tuple[str, type]] = {}
    for cls in _page_classes:
        d: PageDescriptor | None = getattr(cls, "DESCRIPTOR", None)
        if d is not None:
            mapping[d.type_key] = (d.page_name, cls)

    # popup aliases - share page classes with their non-popup counterparts
    popup_aliases = {
        "popup_unlock": ("alarm", UnlockPage),
        "popup_notify": ("notify", NotifyPage),
        "popup_notifs": ("notifs", NotifsPage),
        "popup_select": ("select", SelectPage),
        "popup_light": ("light", LightPage),
        "popup_media_player": ("media", MediaPage),
        "popup_vacuum": ("vacuum", VacuumPage),
        "popup_climate": ("climate", ClimatePage),
        "popup_timer": ("timer", TimerPage),
        "popup_cover": ("cover", CoverPage),
    }
    mapping.update(popup_aliases)
    return mapping


PANEL_MAPPING: dict[str, tuple[str, type]] = _build_panel_mapping()


def get_user_panel_type_descriptors() -> list[dict]:
    """Return serialized descriptors for user-visible (non-system, non-popup) panel types."""
    result: list[dict] = []
    for type_key, (_, cls) in PANEL_MAPPING.items():
        d = getattr(cls, "DESCRIPTOR", None)
        if d is not None and type_key == d.type_key and not d.is_system:
            result.append(
                {
                    "type_key": d.type_key,
                    "label": d.label,
                    "description": d.description,
                    "icon": d.icon,
                    "item_options": d.item_options,
                    "options": [
                        {
                            "key": o.key,
                            "kind": o.kind,
                            "default": o.default,
                            "label": o.label,
                            "description": o.description,
                            "domain": o.domain,
                            "section": o.section,
                            "max_items": o.max_items,
                            "choices": [{"value": k, "label": lbl} for k, lbl in (o.choices or [])],
                        }
                        for o in d.options
                    ],
                }
            )
    return sorted(result, key=lambda x: x["label"])


def get_system_panel_entries() -> list[dict]:
    """Return all system panel entries (sys pages + popups) keyed by SYS_PANEL_MAPPING."""
    result: list[dict] = []
    for sys_key, type_key in SYS_PANEL_MAPPING.items():
        if type_key in PANEL_MAPPING:
            _, cls = PANEL_MAPPING[type_key]
            d = getattr(cls, "DESCRIPTOR", None)
            if d is not None:
                result.append(
                    {
                        "type": type_key,
                        "key": sys_key,
                        "label": d.label,
                        "description": d.description,
                        "icon": d.icon,
                    }
                )
    return result

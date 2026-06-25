from __future__ import annotations

from ..mapping.const import SysPanelKey

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
from ..utils.text import get_translation
from .descriptor import PageDescriptor

# system panel mapping
# sys_panel_key -> panel_type
SYS_PANEL_MAPPING = {
    # sys pages
    SysPanelKey.SYS_SYSTEM: "system",
    SysPanelKey.SYS_ABOUT: "system_about",
    SysPanelKey.SYS_BLANK: "blank",
    SysPanelKey.SYS_SETTINGS: "system_settings",
    # popups
    SysPanelKey.POPUP_UNLOCK: "popup_unlock",
    SysPanelKey.POPUP_NOTIFY: "popup_notify",
    SysPanelKey.POPUP_NOTIFS: "popup_notifs",
    SysPanelKey.POPUP_SELECT: "popup_select",
    SysPanelKey.POPUP_LIGHT: "popup_light",
    SysPanelKey.POPUP_MEDIA_PLAYER: "popup_media_player",
    SysPanelKey.POPUP_VACUUM: "popup_vacuum",
    SysPanelKey.POPUP_CLIMATE: "popup_climate",
    SysPanelKey.POPUP_TIMER: "popup_timer",
    SysPanelKey.POPUP_COVER: "popup_cover",
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
    # Explicit dict is the clearest approach since the alias key differs from
    # the base type_key in non-trivial ways (e.g. "media" -> "popup_media_player").
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


def build_sys_panels_defaults() -> list[dict]:
    """Build the DEFAULT_CONFIG["sys_panels"] list from SYS_PANEL_MAPPING.

    Iterates ``SYS_PANEL_MAPPING`` (the authoritative list of system panel keys)
    and for each entry looks up the page class in ``PANEL_MAPPING``:
    - If the page class's ``DESCRIPTOR.sys_panel_default`` is set, that dict
      is used (with ``type`` patched in).
    - Otherwise a minimal default with ``show_in_navigation=False`` is generated.
    """
    defaults: list[dict] = []
    seen_keys: set[str] = set()

    for sys_key, type_key in SYS_PANEL_MAPPING.items():
        if sys_key in seen_keys:
            continue
        seen_keys.add(sys_key)

        entry = PANEL_MAPPING.get(type_key)
        if entry is None:
            # Fallback: minimal default
            defaults.append(
                {
                    "type": type_key,
                    "key": sys_key,
                    "show_in_navigation": False,
                }
            )
            continue

        _, cls = entry
        d = getattr(cls, "DESCRIPTOR", None)
        pdef = d.sys_panel_default if d and d.sys_panel_default else {}
        pdef = dict(pdef)
        pdef.setdefault("show_in_navigation", False)
        pdef["key"] = sys_key
        pdef["type"] = type_key
        defaults.append(pdef)

    return defaults


def get_user_panel_type_descriptors(language: str = "en") -> list[dict]:
    """Return serialized descriptors for user-visible (non-system, non-popup) panel types.

    When ``language`` is provided, string fields (label, description, option labels,
    etc.) are translated before being returned.
    """
    result: list[dict] = []
    for type_key, (_, cls) in PANEL_MAPPING.items():
        d = getattr(cls, "DESCRIPTOR", None)
        if d is not None and type_key == d.type_key and not d.is_system:
            result.append(
                {
                    "type_key": d.type_key,
                    "label": get_translation(d.label, language),
                    "description": get_translation(d.description, language),
                    "icon": d.icon,
                    "has_header": d.has_header,
                    "can_show_popup": d.can_show_popup,
                    "item_options": d.item_options,
                    "options": [
                        {
                            "key": o.key,
                            "kind": o.kind,
                            "default": o.default,
                            "label": get_translation(o.label, language)
                                if o.label else None,
                            "description": get_translation(o.description, language)
                                if o.description else None,
                            "domain": o.domain,
                            "section": get_translation(o.section, language) if o.section else None,
                            "max_items": o.max_items,
                            "choices": [
                                {"value": k, "label": get_translation(lbl, language)}
                                for k, lbl in (o.choices or [])
                            ],
                        }
                        for o in d.options
                    ],
                }
            )
    return sorted(result, key=lambda x: x["label"])


def get_system_panel_entries(language: str = "en") -> list[dict]:
    """Return all system panel entries (sys pages + popups) keyed by SYS_PANEL_MAPPING.

    When ``language`` is provided, string fields (label, description) are translated
    before being returned.
    """
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
                        "label": get_translation(d.label, language),
                        "description": get_translation(d.description, language),
                        "icon": d.icon,
                        "has_header": d.has_header,
                        "can_show_popup": d.can_show_popup,
                    }
                )
    return result

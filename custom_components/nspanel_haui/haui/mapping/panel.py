from __future__ import annotations

from ..abstract.component import ComponentRegistry
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
from ..page.notify import NotifyPage
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

# ── Page class registry ──────────────────────────────────────────────────

_page_classes: list[type] = [
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


def _build_panel_mapping() -> dict[str, tuple[str, type]]:
    """Build PANEL_MAPPING from page class DESCRIPTORs.

    Each page class registers under its ``type_key``.  Popup aliases are
    derived from descriptor fields:
    * ``popup_alias_for`` — different class, same Nextion page (UnlockPage)
    * ``can_show_popup`` and not ``is_system`` — same class, ``popup_<name>`` key
    * ``is_system`` with ``sys_panel_default["key"]`` starting with ``popup_``
      — system popup (notify, select)
    """
    mapping: dict[str, tuple[str, type]] = {}
    for cls in _page_classes:
        d: PageDescriptor | None = getattr(cls, "DESCRIPTOR", None)
        if d is not None:
            mapping[d.type_key] = (d.page_name, cls)

    for cls in _page_classes:
        d = getattr(cls, "DESCRIPTOR", None)
        if d is None:
            continue

        # 1) popup_alias_for — different class, e.g. UnlockPage → alarm
        if d.popup_alias_for:
            mapping[d.type_key] = (d.popup_alias_for, cls)
        # 2) Non-system pages with can_show_popup — same class, popup_<name>
        elif d.can_show_popup and not d.is_system:
            page_name = d.page_name
            alias_key = "popup_media_player" if page_name == "media" else f"popup_{page_name}"
            mapping[alias_key] = (page_name, cls)
        # 3) System popup pages (notify, select) — sys_panel_default key
        elif d.is_system and d.sys_panel_default:
            sys_key = d.sys_panel_default.get("key", "")
            if sys_key.startswith("popup_"):
                mapping[sys_key] = (d.page_name, cls)

    return mapping


PANEL_MAPPING: dict[str, tuple[str, type]] = _build_panel_mapping()


# ── PAGE_MAPPING: derived from DESCRIPTOR.page_id ─────────────────────────


def _build_page_mapping() -> dict[int, str]:
    """Build PAGE_MAPPING from DESCRIPTOR.page_id, skipping popup aliases."""
    mapping: dict[int, str] = {}
    for type_key, (_, cls) in PANEL_MAPPING.items():
        d = getattr(cls, "DESCRIPTOR", None)
        if d is None or d.page_id is None:
            continue
        # Skip popup aliases — they share a page_id with their parent
        # (e.g. UnlockPage shares page_id=17 with AlarmPage)
        if d.popup_alias_for is not None:
            continue
        # Only register the primary entry, not alias entries
        if type_key != d.type_key:
            continue
        mapping[d.page_id] = d.page_name
    return mapping


PAGE_MAPPING: dict[int, str] = _build_page_mapping()


# ── SYS_PANEL_MAPPING: derived from PANEL_MAPPING descriptors ─────────────


def _build_sys_panel_mapping() -> dict[str, str]:
    """Build SYS_PANEL_MAPPING from PANEL_MAPPING descriptors.

    ``sys_key -> type_key`` for system pages and popup aliases.
    """
    mapping: dict[str, str] = {}
    for type_key, (_, cls) in PANEL_MAPPING.items():
        d = getattr(cls, "DESCRIPTOR", None)
        if d is None:
            continue
        # System pages: use sys_panel_default["key"]
        # Only the native type_key entry (not alias entries) registers
        if d.is_system and d.sys_panel_default and type_key == d.type_key:
            sys_key = d.sys_panel_default.get("key")
            if sys_key:
                mapping[sys_key] = type_key
        # Popup aliases: identity mapping (sys_key == type_key)
        # Only for non-system entries — system pages register via the if branch above
        elif type_key != d.type_key and not d.is_system:
            mapping[type_key] = type_key
    return mapping


SYS_PANEL_MAPPING: dict[str, str] = _build_sys_panel_mapping()


# ── Derived config builders ───────────────────────────────────────────────


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


def _serialize_components(cls: type) -> list[dict]:
    """Serialize a page class's ComponentRegistry to a list of {id, name} dicts."""
    reg: ComponentRegistry | None = getattr(cls, "COMPONENTS", None)
    if reg is None:
        return []
    return [{"id": c.id, "name": c.name} for c in reg.values()]


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
                    "components": _serialize_components(cls),
                    "options": [
                        {
                            "key": o.key,
                            "kind": o.kind,
                            "default": o.default,
                            "label": get_translation(o.label, language) if o.label else None,
                            "description": get_translation(o.description, language)
                            if o.description
                            else None,
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
                        "components": _serialize_components(cls),
                    }
                )
    return result

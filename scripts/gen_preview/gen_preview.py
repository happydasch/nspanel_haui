#!/usr/bin/env python3
"""NSPanel HAUI - Preview renderer stub generator.

Reads each page class's ComponentRegistry and DESCRIPTOR metadata,
then generates a JS preview renderer stub file.

Usage:
    # Generate all stubs
    python scripts/gen_preview/gen_preview.py --all

    # Generate a single type
    python scripts/gen_preview/gen_preview.py --type grid

    # Check for missing renderers (exit non-zero if any found)
    python scripts/gen_preview/gen_preview.py --check-missing

    # Dry-run — print to stdout instead of writing files
    python scripts/gen_preview/gen_preview.py --all --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# HA stubs — required because haui core imports from homeassistant
# ---------------------------------------------------------------------------


def _install_ha_stubs() -> None:
    """Install a meta-path finder that stubs any homeassistant.* import on demand."""
    import types

    # Pre-stub the top-level homeassistant package with common constants
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.__path__ = []
    ha_const.__dict__.update(
        {
            "__name__": "homeassistant.const",
            "STATE_ON": "on",
            "STATE_OFF": "off",
            "STATE_HOME": "home",
            "STATE_NOT_HOME": "not_home",
            "STATE_OPEN": "open",
            "STATE_CLOSED": "closed",
            "STATE_LOCKED": "locked",
            "STATE_UNLOCKED": "unlocked",
            "STATE_UNKNOWN": "unknown",
            "STATE_UNAVAILABLE": "unavailable",
            "SERVICE_TURN_ON": "turn_on",
            "SERVICE_TURN_OFF": "turn_off",
            "SERVICE_TOGGLE": "toggle",
            "EVENT_HOMEASSISTANT_STOP": "homeassistant_stop",
            "EVENT_HOMEASSISTANT_START": "homeassistant_start",
            "EVENT_STATE_CHANGED": "state_changed",
            "ATTR_ENTITY_ID": "entity_id",
            "ATTR_DEVICE_ID": "device_id",
            "ATTR_AREA_ID": "area_id",
            "ATTR_NAME": "name",
            "ATTR_ICON": "icon",
            "ATTR_STATE": "state",
            "ATTR_UNIT_OF_MEASUREMENT": "unit_of_measurement",
            "ATTR_DEVICE_CLASS": "device_class",
            "CONF_NAME": "name",
            "CONF_ENTITY_ID": "entity_id",
            "CONF_UNIQUE_ID": "unique_id",
            "CONF_DEVICE_ID": "device_id",
            "CONF_DEVICES": "devices",
            "CONF_DOMAIN": "domain",
            "PLATFORM_SCHEMA": {},
            "CONFIG_SCHEMA": {},
        }
    )

    ha = types.ModuleType("homeassistant")
    ha.const = ha_const
    ha.__path__ = []  # Make it a proper package so submodules can be found
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.const"] = ha_const

    # Add callable stubs for commonly accessed attributes
    _STUB_ATTRS: dict[str, dict[str, object]] = {
        "homeassistant.helpers.config_validation": {
            "boolean": lambda x: x,
            "string": lambda x: str(x),
            "entity_id": lambda x: str(x),
            "entity_ids": lambda xs: [str(x) for x in xs],
            "entity_domain": lambda *a: lambda x: str(x),
            "ensure_list": lambda x: x if isinstance(x, list) else [x],
            "multi_select": lambda *a: lambda x: x,
            "has_at_least_one": lambda *a: lambda x: str(x),
            "empty_config_schema": lambda d: {},
            "PLATFORM_SCHEMA": {},
            "CONFIG_SCHEMA": {},
        },
        "homeassistant.core": {
            "HomeAssistant": type("HomeAssistant", (), {}),
            "State": type("State", (), {}),
            "Event": type("Event", (), {}),
            "ServiceCall": type("ServiceCall", (), {}),
            "Callback": type("Callback", (), {}),
            "DOMAIN": "homeassistant",
        },
        "homeassistant.config_entries": {
            "ConfigEntry": type("ConfigEntry", (), {}),
            "ConfigFlow": type("ConfigFlow", (), {}),
            "OptionsFlow": type("OptionsFlow", (), {}),
            "CONN_CLASS_CLOUD_POLL": "cloud_poll",
            "CONN_CLASS_CLOUD_PUSH": "cloud_push",
            "CONN_CLASS_LOCAL_POLL": "local_poll",
            "CONN_CLASS_LOCAL_PUSH": "local_push",
            "CONN_CLASS_ASSUMED": "assumed",
            "CONN_CLASS_UNKNOWN": "unknown",
        },
        "homeassistant.loader": {
            "async_get_integration": lambda *a: None,
        },
        "homeassistant.exceptions": {
            "HomeAssistantError": type("HomeAssistantError", (Exception,), {}),
            "ConfigEntryNotReady": type("ConfigEntryNotReady", (Exception,), {}),
        },
        "homeassistant.data_entry_flow": {
            "FlowHandler": type("FlowHandler", (), {}),
            "FlowResult": type("FlowResult", (), {}),
        },
        "homeassistant.util.unit_system": {
            "UnitSystem": type("UnitSystem", (), {}),
        },
    }

    for mod_name, attrs in _STUB_ATTRS.items():
        parts = mod_name.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent not in sys.modules:
                parent_mod = types.ModuleType(parent)
                parent_mod.__path__ = []
                sys.modules[parent] = parent_mod
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            mod.__path__ = []
            sys.modules[mod_name] = mod
        mod = sys.modules[mod_name]
        mod.__dict__.update(attrs)

    # Meta-path finder: any remaining homeassistant.* import gets a stub module
    class _HAStubFinder:
        _PREFIX = "homeassistant."

        @classmethod
        def find_spec(cls, fullname, path=None, target=None):
            if not fullname.startswith(cls._PREFIX) and fullname != "homeassistant":
                return None
            if fullname in sys.modules:
                return None
            # Create a new stub module
            mod = types.ModuleType(fullname)
            mod.__package__ = fullname.rpartition(".")[0]
            mod.__path__ = []  # Make it a package so submodules can be found
            mod.__spec__ = types.SimpleNamespace(
                name=fullname,
                loader=None,
                origin="stub",
                has_location=False,
                submodule_search_locations=[],
            )
            sys.modules[fullname] = mod
            return mod.__spec__

    sys.meta_path.insert(0, _HAStubFinder)


_install_ha_stubs()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve project root (scripts/gen_preview -> repo root)
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

# Where the frontend lives
_FRONTEND_DIR = _PROJECT_ROOT / "custom_components" / "nspanel_haui" / "frontend"
_PREVIEWS_DIR = _FRONTEND_DIR / "previews"
_REGISTRATION_FILE = _FRONTEND_DIR / "panel-previews.js"

# Where the Python page classes live
_PAGE_PACKAGE = "custom_components.nspanel_haui.haui.page"

# ---------------------------------------------------------------------------
# Page discovery — mirrors the import list in haui/mapping/panel.py
# ---------------------------------------------------------------------------

_PAGE_CLASSES: dict[str, str] = {
    "AboutPage": "about",
    "AlarmPage": "alarm",
    "BlankPage": "blank",
    "CardClockPage": "cardclock",
    "ClimatePage": "climate",
    "ClockPage": "clock",
    "ClockTwoPage": "clocktwo",
    "CoverPage": "cover",
    "GridPage": "grid",
    "LightPage": "light",
    "MediaPage": "media",
    "NotifyPage": "notify",
    "QRPage": "qr",
    "RowPage": "row",
    "SelectPage": "select",
    "SettingsPage": "settings",
    "SystemPage": "system",
    "TimerPage": "timer",
    "UnlockPage": "unlock",
    "VacuumPage": "vacuum",
    "WeatherPage": "weather",
}


def _import_page_classes() -> dict[str, type]:
    """Dynamically import every page class and return {type_key: class}."""
    from importlib import import_module

    classes: dict[str, type] = {}
    for class_name, module_name in _PAGE_CLASSES.items():
        try:
            mod = import_module(f"{_PAGE_PACKAGE}.{module_name}")
            cls = getattr(mod, class_name, None)
            if cls is None:
                continue
            d = getattr(cls, "DESCRIPTOR", None)
            if d is not None:
                classes[d.type_key] = cls
        except (ImportError, ModuleNotFoundError):
            pass
    return classes


# ---------------------------------------------------------------------------
# Option classification helpers
# ---------------------------------------------------------------------------

_ITEM_OPTION_KINDS = frozenset({"item", "item_list", "list_items", "list_entities"})
_TEXT_OPTION_KINDS = frozenset({"str", "int", "float", "generic", "select", "list_str"})
_TOGGLE_OPTION_KINDS = frozenset({"bool"})
_COLOR_ICON_OPTION_KINDS = frozenset({"color", "icon"})


def _classify_option(opt) -> str:
    """Return a short human label for the option kind."""
    k = opt.kind
    if k in _ITEM_OPTION_KINDS:
        return "entity"
    if k in _TOGGLE_OPTION_KINDS:
        return "toggle"
    if k in _COLOR_ICON_OPTION_KINDS:
        return k
    if k in _TEXT_OPTION_KINDS:
        return "text"
    return k


# ---------------------------------------------------------------------------
# Widget name classification
# ---------------------------------------------------------------------------

_WIDGET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(b|btn|bFnc)"), "button"),
    (re.compile(r"^h"), "slider"),
    (re.compile(r"^(t|tTitle|tHeader|tInfo|tMain|tSub|tTime|tDate|tNotif)"), "text"),
    (re.compile(r"^(g|grid)"), "item_grid"),
    (re.compile(r"^temp"), "temp"),
    (re.compile(r"^(time|clock)"), "time"),
    (re.compile(r"^ico"), "icon"),
    (re.compile(r"^pic"), "picture"),
    (re.compile(r"^q"), "qrcode"),
    (re.compile(r"^s"), "spinner"),
    (re.compile(r"^scroll"), "scroll"),
]


def _classify_widget_name(name: str) -> str:
    """Guess the visual role of a Nextion widget from its name."""
    for pattern, role in _WIDGET_PATTERNS:
        if pattern.match(name):
            return role
    return "other"


# ---------------------------------------------------------------------------
# JS stub generation
# ---------------------------------------------------------------------------

_RENDERER_TEMPLATE = """\
/**
 * NSPanel HAUI - Panel preview: {type_key}.
 *
 * Auto-generated stub — replace the placeholder content with actual
 * visual layout using primitives from primitives.js.
 *
 * Available Nextion components:
{component_comment}
 * Panel options:
{option_comment}
 */
import {{ html }} from '../lit-import.js';
import {{ getItems, backgroundClass }} from './utils.js';
// import {{
//   simTile, simItemTile, simSlider, simButtonRow, simItemGrid, simTimeDisplay, simTempDisplay
// }} from './primitives.js';

export function render{render_name}Preview(host, panel, _pIdx, _pt) {{
  return {{
    content: html`
      <div class="pg-preview-content-top">
        <ha-icon icon="{icon}"></ha-icon>
        <div class="pg-card-preview-line"></div>
      </div>`,
{header_override}
  }};
}}
"""


def _render_name(type_key: str) -> str:
    """Convert type_key to a PascalCase renderer name (e.g. 'cardclock' -> 'CardClock')."""
    if "_" in type_key:
        result = "".join(word.capitalize() for word in type_key.split("_"))
    else:
        _WORD_SPLIT = re.compile(
            r"(card|clock|two|system|settings|about|popup|unlock|notify|"
            r"select|media|vacuum|climate|timer|cover|light|grid|row|alarm|weather|qr|blank)"
        )
        parts = [p for p in _WORD_SPLIT.split(type_key) if p]
        if len(parts) > 1:
            result = "".join(p.capitalize() for p in parts)
        else:
            result = type_key.capitalize()

    # Post-process known special cases
    _SPECIAL_CAPS: dict[str, str] = {"Qr": "QR"}
    for old, new in _SPECIAL_CAPS.items():
        result = result.replace(old, new)
    return result


def _generate_stub(type_key: str, cls: type) -> str:
    """Generate JS preview renderer stub content for a page class."""
    d = getattr(cls, "DESCRIPTOR", None)
    reg = getattr(cls, "COMPONENTS", None)

    icon = d.icon if d and d.icon else "mdi:view-dashboard-outline"
    has_header = d.has_header if d else True
    options = d.options if d else []

    # Component descriptions
    comp_lines: list[str] = []
    if reg is not None:
        for c in reg.values():
            role = _classify_widget_name(c.name)
            comp_lines.append(f" *   {c.name} (id={c.id}) — {role}")
    if not comp_lines:
        comp_lines.append(" *   (none)")

    # Option descriptions
    opt_lines: list[str] = []
    for o in options:
        cls_label = _classify_option(o)
        opt_lines.append(f" *   {o.key} ({cls_label})")
    if not opt_lines:
        opt_lines.append(" *   (none)")

    # Header override
    header_override = ""
    if not has_header:
        header_override = "    containerClass: backgroundClass(panel),"

    return _RENDERER_TEMPLATE.format(
        type_key=type_key,
        render_name=_render_name(type_key),
        component_comment="\n".join(comp_lines),
        option_comment="\n".join(opt_lines),
        icon=icon,
        header_override=header_override,
    )


# ---------------------------------------------------------------------------
# Known preview renderers (from panel-previews.js)
# ---------------------------------------------------------------------------

# Mapping from type_key to registered renderer function name
_EXISTING_RENDERERS: dict[str, str] = {
    "cardclock": "renderCardClockPreview",
    "grid": "renderGridPreview",
    "row": "renderRowPreview",
    "light": "renderLightPreview",
    "climate": "renderClimatePreview",
    "media": "renderMediaPreview",
    "cover": "renderCoverPreview",
    "vacuum": "renderVacuumPreview",
    "timer": "renderTimerPreview",
    "alarm": "renderAlarmPreview",
    "clock": "renderClockPreview",
    "clocktwo": "renderClockTwoPreview",
    "weather": "renderWeatherPreview",
    "qr": "renderQRPreview",
    "notify": "renderNotifyPreview",
    "select": "renderSelectPreview",
    "system_settings": "renderSettingsPreview",
    "system_about": "renderAboutPreview",
    "system": "renderSystemPreview",
    "blank": "renderBlankPreview",
    "popup_unlock": "renderUnlockPreview",
    "popup_notify": "renderNotifyPreview",
    "popup_select": "renderSelectPreview",
    "popup_light": "renderLightPreview",
    "popup_media_player": "renderMediaPreview",
    "popup_vacuum": "renderVacuumPreview",
    "popup_climate": "renderClimatePreview",
    "popup_timer": "renderTimerPreview",
    "popup_cover": "renderCoverPreview",
}

# Popup aliases share renderers with their base types
_POPUP_ALIASES: dict[str, str] = {
    "popup_unlock": "alarm",
    "popup_notify": "notify",
    "popup_select": "select",
    "popup_light": "light",
    "popup_media_player": "media",
    "popup_vacuum": "vacuum",
    "popup_climate": "climate",
    "popup_timer": "timer",
    "popup_cover": "cover",
}

# User-visible panel types (exclude system panels)
_SYSTEM_TYPES = frozenset(
    {
        "system",
        "system_about",
        "system_settings",
        "blank",
        "popup_unlock",
        "popup_notify",
        "popup_select",
        "popup_light",
        "popup_media_player",
        "popup_vacuum",
        "popup_climate",
        "popup_timer",
        "popup_cover",
        "notify",
        "select",
        "alarm",
    }
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/check preview renderer stubs for NSPanel HAUI panel types."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Generate stubs for all panel types")
    group.add_argument("--type", type=str, help="Generate stub for a single panel type")
    group.add_argument(
        "--check-missing",
        action="store_true",
        help="Check for missing renderers (exit non-zero if found)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stubs to stdout instead of writing files",
    )
    return parser.parse_args()


def _get_missing(classes: dict[str, type]) -> list[str]:
    """Return user-visible type keys that have no registered renderer."""
    missing: list[str] = []
    for type_key in classes:
        if type_key in _SYSTEM_TYPES:
            continue
        # Check if type_key or its popup alias has a renderer
        if type_key in _EXISTING_RENDERERS:
            continue
        alias = _POPUP_ALIASES.get(type_key)
        if alias and alias in _EXISTING_RENDERERS:
            continue
        missing.append(type_key)
    return sorted(missing)


def _generate_all(classes: dict[str, type], dry_run: bool) -> None:
    """Generate stubs for all panel types that don't have a renderer yet."""
    missing = _get_missing(classes)
    if not dry_run:
        _PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    for type_key in missing:
        cls = classes[type_key]
        stub = _generate_stub(type_key, cls)
        filename = f"{type_key.replace('_', '') if type_key.startswith('popup_') else type_key}.js"
        # Special case: popup types share same file as their base
        if type_key in _POPUP_ALIASES:
            filename = f"{_POPUP_ALIASES[type_key]}.js"
            print(f"  [{type_key}] → shares renderer with {_POPUP_ALIASES[type_key]}, skipping")
            continue

        filepath = _PREVIEWS_DIR / filename
        if dry_run:
            print(f"--- {type_key} ({filename}) ---")
            print(stub)
            print()
        else:
            filepath.write_text(stub)
            print(f"  ✓ {type_key} → {filepath.relative_to(_PROJECT_ROOT)}")


def _generate_single(classes: dict[str, type], type_key: str, dry_run: bool) -> None:
    """Generate a stub for a single type."""
    cls = classes.get(type_key)
    if cls is None:
        print(f"✗ Unknown panel type: {type_key}", file=sys.stderr)
        sys.exit(1)

    stub = _generate_stub(type_key, cls)
    filename = f"{type_key}.js"
    filepath = _PREVIEWS_DIR / filename

    if dry_run:
        print(stub)
    else:
        _PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        filepath.write_text(stub)
        print(f"  ✓ {type_key} → {filepath.relative_to(_PROJECT_ROOT)}")


def _check_missing(classes: dict[str, type]) -> None:
    """Check for missing renderers and exit non-zero if any found."""
    missing = _get_missing(classes)
    if not missing:
        print("✓ All panel types have preview renderers.")
        sys.exit(0)

    print(f"✗ {len(missing)} panel type(s) missing preview renderer:")
    for type_key in missing:
        print(f"  - {type_key}")
    print()
    print("Run `python scripts/gen_preview/gen_preview.py --all` to generate stubs.")
    sys.exit(1)


def main() -> None:
    args = _parse_args()

    # Ensure page package is importable
    page_pkg_path = str(_PROJECT_ROOT)
    sys.path.insert(0, page_pkg_path)

    classes = _import_page_classes()

    if args.check_missing:
        _check_missing(classes)
    elif args.type:
        _generate_single(classes, args.type, args.dry_run)
    elif args.all:
        _generate_all(classes, args.dry_run)
    else:
        # Default: show missing
        missing = _get_missing(classes)
        if missing:
            print(f"Panel types without renderer: {', '.join(missing)}")
            print("Use --all to generate stubs.")
        else:
            print("All panel types have preview renderers.")


if __name__ == "__main__":
    main()

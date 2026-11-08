#!/usr/bin/env python3
"""Export the Nextion HMI layouts for the editor's virtual panel (live preview).

Reads ``nextion/nspanel_haui.HMI`` (landscape) and
``nextion/nspanel_haui_portrait.HMI`` (portrait) and writes, per orientation,
``custom_components/nspanel_haui/frontend/virtual/layout_<orientation>.json``:
every page (by the hub's page id) with its widgets' attributes and event code,
the fonts and the global variables. The pictures the pages reference are
written as WebP next to it (``pictures/<orientation>/<id>.webp``) from the
source PNGs in ``nextion/images``: the HMI stores pictures in the Nextion's own
compressed format. It also writes the fonts' glyph widths to
``custom_components/nspanel_haui/haui/mapping/font_metrics.json``, which the hub
fits text with.

It checks the theme code of the solid-colour pages, too: each such page paints
itself in the device's theme in its Preinitialize event, from the Program.s
globals the hub sets before every page switch (``THEME_GLOBALS``), so no colour
changes after the page is shown. ``--theme-code`` prints the code each page
needs, generated from the colours its widgets are compiled with; paste it into
the page's Preinitialize event in both HMIs.

Run it after every HMI change; ``--check`` (run by the test suite) fails when a
layout file is out of date or a page's theme code is missing or stale.

Usage::

    python -m scripts.hmi_layout.gen_virtual_layout [--check]
    python -m scripts.hmi_layout.gen_virtual_layout --theme-code [PAGE ...]
"""

from __future__ import annotations

# The stub import must run before the HAUI imports below.
# ruff: noqa: I001

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from scripts import _ha_stubs  # noqa: F401
from scripts.nextion2text import Nextion2Text
from custom_components.nspanel_haui.haui.mapping.background import BACKGROUNDS
from custom_components.nspanel_haui.haui.mapping.color import COLORS, THEME_GLOBALS
from custom_components.nspanel_haui.haui.mapping.icon_mapping import ICON_MAPPING
from custom_components.nspanel_haui.haui.mapping.panel import PAGE_MAPPING

ROOT = Path(__file__).resolve().parents[2]

NEXTION = ROOT / "nextion"
OUT_DIR = ROOT / "custom_components" / "nspanel_haui" / "frontend" / "virtual"
ICON_MAP_FILE = OUT_DIR / "icon_map.json"
# Glyph widths for the hub's text fitting (haui/utils/text.py).
FONT_METRICS_FILE = ROOT / "custom_components/nspanel_haui/haui/mapping/font_metrics.json"
TYPE_PAGE = 121
TYPE_SLIDER = 1
STA_SOLID = 1  # background fill: solid colour (`bco`/`bco2`)
# First line of every page's theme code; the check finds the code by it.
THEME_CODE_HEADER = "// theme colours: gen_virtual_layout.py --theme-code"

HMI_FILES = {
    "landscape": (NEXTION / "nspanel_haui.HMI", 480, 320),
    "portrait": (NEXTION / "nspanel_haui_portrait.HMI", 320, 480),
}
# The landscape panel's rightmost 30 px sit under the bezel: touchable, not
# visible (esphome/nspanel_haui/scripts_interaction.yaml, process_touch_gesture).
VISIBLE_WIDTH = {"landscape": 450, "portrait": 320}

# Picture id -> source PNG ({o} = orientation). Picture 0 is the pGrid design
# grid; the backgrounds follow the ids in BACKGROUNDS, then the spinner sheets,
# colour wheel and logos. The ids shift when backgrounds are inserted.
_BACKGROUND_FILES = {name: "system" if name == "modern" else name for name in BACKGROUNDS}
_FIRST_EXTRA_PICTURE = max(BACKGROUNDS.values()) + 1
PICTURES: dict[int, str] = {
    0: "grid_{o}.png",
    **{pic: f"bkg/{{o}}/{_BACKGROUND_FILES[name]}.png" for name, pic in BACKGROUNDS.items()},
    _FIRST_EXTRA_PICTURE: "spinner_{o}_1.png",
    _FIRST_EXTRA_PICTURE + 1: "spinner_{o}_2.png",
    _FIRST_EXTRA_PICTURE + 2: "colors.png",
    _FIRST_EXTRA_PICTURE + 3: "logo_esphome.png",
    _FIRST_EXTRA_PICTURE + 4: "logo_ha.png",
}

EVENT_NAMES = {
    "codesload": "load",
    "codesloadend": "loadend",
    "codesdown": "down",
    "codesup": "up",
    "codesunload": "unload",
    "codestimer": "timer",
}

# Editor-only attributes the display never uses at runtime.
_DROPPED_ATTRS = frozenset(
    {"movex", "movey", "effect", "first", "time", "lockobj", "groupid0", "groupid1", "endx"}
    | {"endy", "model"}
)


def _utf8(text: str) -> str:
    """Nextion2Text decodes text as ISO-8859-1; the HMI stores UTF-8."""
    return text.encode("iso_8859_1").decode("utf-8", errors="replace")


def _fonts(raw: bytes) -> list[dict[str, Any]]:
    """Embedded fonts; ids grow with the size (docs/design.md)."""
    fonts = []
    for obj in Nextion2Text.HMIHeader(raw).content:
        if not obj.name.endswith(".zi"):
            continue
        block = raw[obj.start : obj.start + 200]
        height = block[7]
        name = re.search(rb"Roboto-(\w+?)utf", block)
        weight = 300 if name and name.group(1) == b"Light" else 400
        fonts.append({"size": height, "family": "Roboto", "weight": weight})
    fonts.sort(key=lambda f: f["size"])
    return [{"id": i, **font} for i, font in enumerate(fonts)]


def _font_metrics(raw: bytes) -> list[dict[str, Any]]:
    """Glyph advance widths of every font's text characters (below the icon range).

    The hub wraps and pages text with them as the display draws it
    (``haui/utils/text.py`` ``fit_text``).  Same ids as ``_fonts``.  A ZI v5
    font is a 0x2C-byte header (height at 7, glyph count at 0x0C, the length of
    the name + encoding strings at 0x11), those strings, then one 10-byte entry
    per glyph: codepoint u16, width, kerning left/right, data offset u24 (from
    the table start), data length u16.
    """
    fonts = []
    for obj in Nextion2Text.HMIHeader(raw).content:
        if not obj.name.endswith(".zi"):
            continue
        base = obj.start
        height = raw[base + 7]
        count = struct.unpack_from("<I", raw, base + 0x0C)[0]
        table = base + 0x2C + raw[base + 0x11]
        if int.from_bytes(raw[table + 5 : table + 8], "little") != count * 10:
            raise ValueError(f"{obj.name}: unexpected ZI glyph table layout")
        widths = []
        for index in range(count):
            codepoint, width, kern_left, kern_right = struct.unpack_from(
                "<HBBB", raw, table + index * 10
            )
            if codepoint >= 0xE000:
                break
            if codepoint != index or kern_left or kern_right:
                raise ValueError(f"{obj.name}: text glyphs are not a plain 0..n range")
            widths.append(width)
        fonts.append({"height": height, "widths": widths})
    fonts.sort(key=lambda f: f["height"])
    return [{"id": i, **font} for i, font in enumerate(fonts)]


def _render_font_metrics() -> tuple[str, list[str]]:
    """The hub's font metrics file, and a problem when the HMIs' fonts differ."""
    metrics = [_font_metrics(path.read_bytes()) for path, _w, _h in HMI_FILES.values()]
    problems = [] if all(m == metrics[0] for m in metrics) else ["the HMIs' fonts differ"]
    text = json.dumps({"fonts": metrics[0]}, separators=(",", ":")) + "\n"
    return text, problems


def _theme_key(comp: dict[str, Any], attr: str) -> str | None:
    """The ``COLORS`` key a solid widget's colour attribute is painted with, or None.

    The colour the HMI compiles names the key: the page colour fills flat
    widgets (``bco``) and the pressed state of flat-pressed buttons (``bco2``),
    the header colour the header's widgets, whose text is ``header_text``, and
    buttons press in ``component_pressed``. A slider's track is always
    ``component_background``, whatever the HMI compiles; the hub sets only the
    handle (``HAUIPage.set_slider_color``).
    """
    attrs = comp["attrs"]
    value = attrs.get(attr)
    if comp["type"] == TYPE_SLIDER and attr == "bco":
        return "component_background"
    if attr in ("bco", "bco2") and value == COLORS["background"]:
        return "background"
    if attr == "bco" and value == COLORS["header_background"]:
        return "header_background"
    header = attrs.get("bco") == COLORS["header_background"]
    if attr == "pco" and header and value == COLORS["header_text"]:
        return "header_text"
    if attr == "bco2" and value == COLORS["component_pressed"]:
        return "component_pressed"
    return None


def theme_code(page: dict[str, Any]) -> str | None:
    """The Preinitialize code that paints a solid-colour page in the theme.

    One assignment per page colour and per widget colour the HMI compiles with a
    theme colour, read from the theme globals (``THEME_GLOBALS``). None for a
    picture-background page: it keeps its picture and palette.
    """
    comps = page["components"]
    page_attrs = next(c for c in comps if c["type"] == TYPE_PAGE)["attrs"]
    if page_attrs["sta"] != STA_SOLID:
        return None
    lines = [THEME_CODE_HEADER, f"{page['name']}.bco={THEME_GLOBALS['background']}"]
    for comp in comps:
        if comp["type"] == TYPE_PAGE or comp["attrs"].get("sta") != STA_SOLID:
            continue
        for attr in ("bco", "bco2", "pco"):
            key = _theme_key(comp, attr)
            if key is not None:
                lines.append(f"{comp['name']}.{attr}={THEME_GLOBALS[key]}")
    return "\n".join(lines)


def _code_lines(code: str) -> list[str]:
    return [line.strip() for line in code.splitlines() if line.strip()]


def _contains_code(event: str, code: str) -> bool:
    """Whether ``event`` holds the lines of ``code`` one after another."""
    have, want = _code_lines(event), _code_lines(code)
    return any(have[i : i + len(want)] == want for i in range(len(have) - len(want) + 1))


def check_theme_code(layouts: list[dict[str, Any]]) -> list[str]:
    """Problems with the theme code: globals, each solid page's Preinitialize, parity."""
    problems: list[str] = []
    codes = []
    for layout in layouts:
        hmi = HMI_FILES[layout["orientation"]][0].name
        for key, name in THEME_GLOBALS.items():
            if layout["globals"].get(name) != COLORS[key]:
                problems.append(f"{hmi}: Program.s must declare int {name}={COLORS[key]} ({key})")
        code = {}
        for page in layout["pages"].values():
            page_code = theme_code(page)
            if page_code is None:
                continue
            code[page["name"]] = page_code
            page_comp = next(c for c in page["components"] if c["type"] == TYPE_PAGE)
            page_attrs = page_comp["attrs"]
            if page_attrs["bco"] != COLORS["background"]:
                problems.append(
                    f"{hmi}: page {page['name']} is compiled with bco={page_attrs['bco']}, "
                    f"not the default background {COLORS['background']}"
                )
            if not _contains_code(page_comp["events"].get("load", ""), page_code):
                problems.append(
                    f"{hmi}: page {page['name']}'s Preinitialize event lacks its theme code "
                    f"(gen_virtual_layout.py --theme-code {page['name']})"
                )
        codes.append(code)
    if any(code != codes[0] for code in codes):
        problems.append("the HMIs' theme code differs: their widgets or colours differ")
    return problems


def print_theme_code(layout: dict[str, Any], pages: list[str]) -> int:
    """Print the theme code of the given solid pages (all when empty)."""
    codes = {page["name"]: theme_code(page) for page in layout["pages"].values()}
    unknown = [name for name in pages if codes.get(name) is None]
    if unknown:
        print(f"no solid-colour page named {', '.join(unknown)}", file=sys.stderr)
        return 1
    for name, code in codes.items():
        if code is not None and (not pages or name in pages):
            print(f"== {name} ==\n{code}\n")
    return 0


def _picture_sizes(raw: bytes) -> list[tuple[int, int]]:
    sizes = []
    for obj in Nextion2Text.HMIHeader(raw).content:
        if obj.isImage():
            sizes.append(struct.unpack_from("<HH", raw, obj.start + 12))
    return sorted(sizes)


def _globals(program_s: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for decl in re.findall(r"^\s*int\s+([^/\n]+)", program_s, re.M):
        for part in decl.split(","):
            name, _, value = part.strip().partition("=")
            found[name.strip()] = int(value or 0)
    return found


def _component(comp: Any) -> dict[str, Any]:
    att = comp.rawData["att"]
    attrs = {}
    for key, value in att.items():
        if key in _DROPPED_ATTRS or key in ("id", "objname", "type"):
            continue
        attrs[key] = _utf8(value) if isinstance(value, str) else value
    events = {}
    for key, name in EVENT_NAMES.items():
        code = comp.rawData.get(key)
        if code and code.strip():
            events[name] = _utf8(code)
    return {
        "id": att["id"],
        "name": att["objname"],
        "type": att["type"],
        "attrs": attrs,
        "events": events,
    }


def build_layout(orientation: str) -> dict[str, Any]:
    path, width, height = HMI_FILES[orientation]
    hmi = Nextion2Text.HMI(str(path))
    page_ids = {name: page_id for page_id, name in PAGE_MAPPING.items()}
    pages: dict[str, Any] = {}
    for page in hmi.pages:
        comps = sorted((_component(c) for c in page.components), key=lambda c: c["id"])
        page_comp = next(c for c in comps if c["type"] == TYPE_PAGE)
        name = page_comp["name"]
        if name not in page_ids:
            raise SystemExit(f"{path.name}: page '{name}' has no page id in PAGE_MAPPING")
        pages[str(page_ids[name])] = {"name": name, "components": comps}
    missing = set(page_ids) - {p["name"] for p in pages.values()}
    if missing:
        raise SystemExit(f"{path.name}: pages missing from the HMI: {sorted(missing)}")
    return {
        "orientation": orientation,
        "width": width,
        "height": height,
        "visible_width": VISIBLE_WIDTH[orientation],
        "fonts": _fonts(hmi.raw),
        "globals": _globals(_utf8(hmi.programS)),
        "pictures": {str(pic): f"pictures/{orientation}/{pic}.webp" for pic in sorted(PICTURES)},
        "pages": dict(sorted(pages.items(), key=lambda kv: int(kv[0]))),
    }


def _picture_sources(orientation: str) -> dict[int, Path]:
    return {pic: NEXTION / "images" / src.format(o=orientation) for pic, src in PICTURES.items()}


def check_pictures(orientation: str) -> list[str]:
    """Problems with the picture mapping: sizes must match the HMI's pictures."""
    from PIL import Image

    path = HMI_FILES[orientation][0]
    sources = _picture_sources(orientation)
    problems = [f"missing source {p}" for p in sources.values() if not p.exists()]
    if problems:
        return problems
    mapped = sorted(Image.open(p).size for p in sources.values())
    if mapped != _picture_sizes(path.read_bytes()):
        problems.append(f"{path.name}: picture sizes differ from the mapped source PNGs")
    for pic in sources:
        out = OUT_DIR / "pictures" / orientation / f"{pic}.webp"
        if not out.exists():
            problems.append(f"missing {out.relative_to(ROOT)}")
    return problems


def check_spinner(layout: dict[str, Any]) -> list[str]:
    """The system page's spinner timer must draw the spinner sheets.

    Its ``xpic`` calls name the sheets by picture id, and the Nextion Editor
    does not renumber event code when a picture is inserted before them.
    """
    sheets = [pic for pic, src in sorted(PICTURES.items()) if src.startswith("spinner_")]
    page = next(p for p in layout["pages"].values() if p["name"] == "system")
    timer = next(c for c in page["components"] if c["name"] == "tmSpinner")
    code = timer["events"]["timer"]
    drawn = [int(pic) for pic in re.findall(r"^\s*xpic .*,(\d+)\s*$", code, re.M)]
    if drawn != sheets:
        return [
            f"{layout['orientation']}: system.tmSpinner draws pictures {drawn}, "
            f"the spinner sheets are {sheets}"
        ]
    return []


def write_pictures(orientation: str) -> None:
    from PIL import Image

    out_dir = OUT_DIR / "pictures" / orientation
    out_dir.mkdir(parents=True, exist_ok=True)
    for pic, src in _picture_sources(orientation).items():
        Image.open(src).convert("RGB").save(out_dir / f"{pic}.webp", "WEBP", quality=85, method=6)


def _render(layout: dict[str, Any]) -> str:
    return json.dumps(layout, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"


def _icon_map() -> dict[str, str]:
    """Reverse the display font's name→char mapping into the char→name JSON the
    editors render icons with (same logic as api.py's IconCharsView)."""
    chars: dict[str, str] = {}
    for icon_name, char in ICON_MAPPING.items():
        chars.setdefault(char, icon_name)
    return chars


def _render_icon_map() -> str:
    return json.dumps(_icon_map(), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail when a layout is out of date")
    parser.add_argument(
        "--theme-code",
        nargs="*",
        metavar="PAGE",
        help="print the Preinitialize theme code of these solid pages (all when none given)",
    )
    args = parser.parse_args(argv)
    if args.theme_code is not None:
        return print_theme_code(build_layout("landscape"), args.theme_code)

    problems: list[str] = []
    layouts = []
    for orientation in HMI_FILES:
        layouts.append(build_layout(orientation))
        text = _render(layouts[-1])
        out = OUT_DIR / f"layout_{orientation}.json"
        if args.check:
            if not out.exists() or out.read_text(encoding="utf-8") != text:
                problems.append(f"{out.relative_to(ROOT)} is out of date")
            problems += check_pictures(orientation)
        else:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            write_pictures(orientation)
            problems += check_pictures(orientation)
            print(f"wrote {out.relative_to(ROOT)}")

    icon_text = _render_icon_map()
    if args.check:
        if not ICON_MAP_FILE.exists() or ICON_MAP_FILE.read_text(encoding="utf-8") != icon_text:
            problems.append(f"{ICON_MAP_FILE.relative_to(ROOT)} is out of date")
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ICON_MAP_FILE.write_text(icon_text, encoding="utf-8")
        print(f"wrote {ICON_MAP_FILE.relative_to(ROOT)}")

    metrics_text, metrics_problems = _render_font_metrics()
    problems += metrics_problems
    if args.check:
        if (
            not FONT_METRICS_FILE.exists()
            or FONT_METRICS_FILE.read_text(encoding="utf-8") != metrics_text
        ):
            problems.append(f"{FONT_METRICS_FILE.relative_to(ROOT)} is out of date")
    else:
        FONT_METRICS_FILE.write_text(metrics_text, encoding="utf-8")
        print(f"wrote {FONT_METRICS_FILE.relative_to(ROOT)}")

    problems += check_theme_code(layouts)
    for layout in layouts:
        problems += check_spinner(layout)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems and args.check:
        print("Run: python -m scripts.hmi_layout.gen_virtual_layout", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

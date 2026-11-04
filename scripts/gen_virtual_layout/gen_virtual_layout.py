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

Run it after every HMI change; ``--check`` (run by the test suite) fails when a
layout file is out of date.

Usage::

    python scripts/gen_virtual_layout/gen_virtual_layout.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "nextion2text"))
sys.path.insert(0, str(ROOT / "scripts"))

import _ha_stubs  # noqa: E402,F401  (installs the homeassistant stubs on import)
import Nextion2Text  # noqa: E402

from custom_components.nspanel_haui.haui.mapping.background import BACKGROUNDS  # noqa: E402
from custom_components.nspanel_haui.haui.mapping.icon_mapping import ICON_MAPPING  # noqa: E402
from custom_components.nspanel_haui.haui.mapping.panel import PAGE_MAPPING  # noqa: E402

NEXTION = ROOT / "nextion"
OUT_DIR = ROOT / "custom_components" / "nspanel_haui" / "frontend" / "virtual"
ICON_MAP_FILE = OUT_DIR / "icon_map.json"
# Glyph widths for the hub's text fitting (haui/utils/text.py).
FONT_METRICS_FILE = ROOT / "custom_components/nspanel_haui/haui/mapping/font_metrics.json"

HMI_FILES = {
    "landscape": (NEXTION / "nspanel_haui.HMI", 480, 320),
    "portrait": (NEXTION / "nspanel_haui_portrait.HMI", 320, 480),
}
# The landscape panel's rightmost 30 px sit under the bezel: touchable, not
# visible (esphome/nspanel_haui/scripts_interaction.yaml, process_touch_gesture).
VISIBLE_WIDTH = {"landscape": 450, "portrait": 320}

# Picture id -> source PNG ({o} = orientation). The ids follow the pages'
# usage: 0 is the pGrid design grid, 1-9 the backgrounds of BACKGROUNDS
# (``modern`` is the ``system`` tile), 10/11 the system page's spinner sheets,
# 12 the light page's colour wheel and 13/14 the about page's ESPHome and Home
# Assistant logos.
_BACKGROUND_FILES = {name: "system" if name == "modern" else name for name in BACKGROUNDS}
PICTURES: dict[int, str] = {
    0: "grid_{o}.png",
    **{pic: f"bkg/{{o}}/{_BACKGROUND_FILES[name]}.png" for name, pic in BACKGROUNDS.items()},
    10: "spinner_{o}_1.png",
    11: "spinner_{o}_2.png",
    12: "colors.png",
    13: "logo_esphome.png",
    14: "logo_ha.png",
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
        page_comp = next(c for c in comps if c["type"] == 121)
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
    args = parser.parse_args(argv)

    problems: list[str] = []
    for orientation in HMI_FILES:
        text = _render(build_layout(orientation))
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
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems and args.check:
        print("Run: python scripts/gen_virtual_layout/gen_virtual_layout.py", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

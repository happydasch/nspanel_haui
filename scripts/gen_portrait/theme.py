"""Compiled widget colours shared by ``landscape_layout.py`` and ``portrait_layout.py``.

The 0.4 dark theme has the hub clear every non-picture page to ``background``
#101010 (RGB565 4226, ``haui/mapping/color.py``) while the header bar stays
#181818 (6339).  Widgets with a solid background were compiled with #181818, so
text and buttons the hub does not recolour drew lighter boxes on the page
(media controls, the cover/light info text, settings, rows, ...).  ``THEME_ATTRS``
compiles them with the page colour; the header widgets keep #181818.  Widgets the
hub recolours at render time (grid tiles, select options, alarm keys) are listed
too, so the compiled page matches before the first render.
"""

from __future__ import annotations

Attrs = dict[str, dict[str, dict[str, int]]]

PAGE_BACKGROUND = 4226

_BG = {"bco": PAGE_BACKGROUND}
_FLAT = {"bco": PAGE_BACKGROUND, "bco2": PAGE_BACKGROUND}  # pressed state stays flat


def _on_page(page: str, *names: str) -> dict[str, dict[str, int]]:
    """The page component and ``names`` drawn on the page background."""
    return {page: _BG, **{name: _BG for name in names}}


def _numbered(template: str, count: int) -> list[str]:
    return [template.format(n=n) for n in range(1, count + 1)]


THEME_ATTRS: Attrs = {
    "blank": _on_page("blank"),
    "light": {
        **_on_page("light", *_numbered("btLightFnc{n}", 4), "tInfo"),
        "bPower": _FLAT,
    },
    "cover": _on_page("cover", "bUp", "bStop", "bDown", "tInfo"),
    "media": {
        **_on_page(
            "media",
            "tIcon",
            "tMTitle",
            "tMInterpret",
            "bShuffle",
            "bPrev",
            "bPlay",
            "bNext",
            "bRepeat",
            "bVolDown",
            "bVolUp",
            *[f"m{n}{part}" for n in range(1, 4) for part in ("Btn", "Icon", "Name")],
        ),
        "bPower": _FLAT,
    },
    "settings": _on_page(
        "settings", "tBrghtTitle", "tBrghtIco", "tBrghtPct", "tBrghtDimIco", "tBrghtDimPct"
    ),
    "notify": _on_page("notify", "tTextFull", "tText", "tIcon", "bBtnLeft", "bBtnRight"),
    "select": _on_page("select", *_numbered("bSelFull{n}", 4), *_numbered("bSel{n}", 12)),
    "qr": _on_page(
        "qr", *[f"q{n}{part}" for n in (1, 2) for part in ("Icon", "Title", "Text", "TextAdd")]
    ),
    "vacuum": _on_page(
        "vacuum", "bFan", "bAction", "bHome", "bLocate", "tStatus", *_numbered("bEntity{n}", 6)
    ),
    "climate": _on_page(
        "climate",
        "tTemp",
        "bUp",
        "bDown",
        "xSet",
        "tUnit",
        *[f"{part}{n}" for n in (1, 2) for part in ("bUp", "bDown", "xSet", "tUnit")],
        *_numbered("btMode{n}", 6),
        "bFan",
        "bPreset",
        "bSwing",
    ),
    "grid": _on_page(
        "grid",
        *[f"g{n}{part}" for n in range(1, 7) for part in ("Btn", "Icon", "Name", "Power")],
    ),
    "timer": _on_page(
        "timer",
        "tMin",
        "tSpace",
        "tSec",
        *_numbered("bUp{n}", 4),
        *_numbered("bDown{n}", 4),
        "bStart",
        "bStop",
    ),
    "alarm": _on_page(
        "alarm",
        *[f"bKey{key}" for key in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "0", "Del")],
        *_numbered("b{n}Fnc", 4),
    ),
    "row": _on_page(
        "row",
        *[
            f"r{n}{part}"
            for n in range(1, 6)
            for part in ("Icon", "Name", "BtnUp", "BtnStop", "BtnDown", "SliderTxt", "BtnText")
        ],
    ),
}


def with_theme(attrs: Attrs) -> Attrs:
    """Merge ``THEME_ATTRS`` under a spec's own per-widget attributes."""
    merged: Attrs = {
        page: {name: dict(values) for name, values in widgets.items()}
        for page, widgets in THEME_ATTRS.items()
    }
    for page, widgets in attrs.items():
        for name, values in widgets.items():
            merged.setdefault(page, {}).setdefault(name, {}).update(values)
    return merged

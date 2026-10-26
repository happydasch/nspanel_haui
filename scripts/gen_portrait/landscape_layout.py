"""Landscape (480x320) refinements for ``nspanel_haui.HMI`` — the 0.4 visual refresh.

Unlike ``portrait_layout.py`` this spec is *partial*: it lists only the widgets
it changes, every other widget keeps the geometry the Nextion Editor saved.
Apply it with ``python scripts/gen_portrait/gen_portrait.py --spec landscape_layout``.

Both HMIs are addressed by the same Python ``COMPONENTS`` registries, so every
change made here (sizes, slider attributes, new widgets in the editor) must be
mirrored in ``portrait_layout.py`` — and the other way round.

Rules:

- 12 px side margins; the EU bezel hides x >= 450, so content ends at x 438.
- 8 px gutters between controls, 50 px header.
- Grid tiles and sliders keep the original (pre-0.4) design, which reads
  better on the device than the refresh's 8 px gaps and 50 px knob tracks:
  140 px tiles with 4 px gaps, slim 30 px settings and volume tracks with a
  small 25 px knob, and flat fill bars without a knob on the light, cover and
  row pages (``ATTRS`` sets the cursor size; the hub colours the knob at
  render time).
"""

from __future__ import annotations

from theme import with_theme

Rect = tuple[int, int, int, int]

WIDTH = 480
HEIGHT = 320
VISIBLE_W = 450
MARGIN = 12
RIGHT = VISIBLE_W - MARGIN  # 438
CONTENT_W = RIGHT - MARGIN  # 426
HMI_NAME = "nspanel_haui.HMI"
PARTIAL = True

# Slider cursor attributes.  ``pco`` is the compiled fallback knob colour; the
# hub overrides it at render time (see set_slider_color).  A 0 x 0 cursor draws
# no knob, so those sliders read as a plain fill bar.
_H_SLIDER = {"wid": 25, "hig": 30, "pco": 15416}
_V_SLIDER = {"wid": 0, "hig": 0, "pco": 12678}
_ROW_SLIDER = {"wid": 0, "hig": 0, "pco": 19773}

# Six 50 px buttons spread evenly across the content width (clock, vacuum,
# climate modes): 12, 87, 162, 237, 313, 388.
_SIX_ACROSS = [MARGIN + round(i * (CONTENT_W - 50) / 5) for i in range(6)]


def _grid() -> dict[str, Rect]:
    """3 x 2 tiles of 140 px with 4 px gaps, ending at x 438."""
    layout: dict[str, Rect] = {}
    tile_w, tile_h, gap = 140, 123, 4
    for n in range(6):
        x = 11 + (tile_w + gap) * (n % 3)
        y = 56 + (tile_h + gap) * (n // 3)
        g = f"g{n + 1}"
        layout.update(
            {
                f"{g}Btn": (x, y, tile_w, tile_h),
                f"{g}Icon": (x + 6, y + 29, 128, 48),
                f"{g}Name": (x + 6, y + 80, 128, 30),
                f"{g}Overlay": (x, y, tile_w, tile_h),
                f"{g}Power": (x + tile_w - 48, y, 48, 48),
            }
        )
    return layout


def _row() -> dict[str, Rect]:
    """Rows keep their 51 px pitch; a 40 px slider bar ends where its value text starts."""
    layout: dict[str, Rect] = {}
    for i in range(5):
        y = 56 + 51 * i
        r = f"r{i + 1}"
        layout.update(
            {
                f"{r}Slider": (282, y + 5, 118, 40),
                f"{r}SliderTxt": (400, y, 50, 50),
            }
        )
    return layout


def _select() -> dict[str, Rect]:
    layout: dict[str, Rect] = {}
    rows = (64, 127, 190, 253)
    for i, y in enumerate(rows):
        layout[f"bSelFull{i + 1}"] = (MARGIN, y, CONTENT_W, 55)
    for n in range(12):
        layout[f"bSel{n + 1}"] = (MARGIN + 144 * (n % 3), rows[n // 3], 136, 55)
    return layout


def _alarm() -> dict[str, Rect]:
    layout: dict[str, Rect] = {}
    cols = (MARGIN, MARGIN + 78, MARGIN + 156)
    rows = (60, 123, 186, 249)
    keys = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "0", "Del")
    for i, key in enumerate(keys):
        layout[f"bKey{key}"] = (cols[i % 3], rows[i // 3], 70, 55)
    for i, y in enumerate(rows):
        layout[f"b{i + 1}Fnc"] = (250, y, RIGHT - 250, 55)
    return layout


def _weather() -> dict[str, Rect]:
    layout: dict[str, Rect] = {
        "tMainText": (MARGIN, 8, 136, 32),
        "tSubText": (MARGIN, 40, 136, 24),
        "tDate": (150, 8, RIGHT - 150, 32),
        "tTime": (176, 37, RIGHT - 176, 118),
        "tMainIcon": (MARGIN, 80, 72, 72),
        "d1Icon": (90, 93, 24, 24),
        "d2Icon": (90, 117, 24, 24),
        "d1Val": (118, 92, 56, 24),
        "d2Val": (118, 117, 56, 24),
    }
    for i in range(5):
        x = MARGIN + 86 * i  # 82 px columns, 4 px apart, ending at 438
        f = f"f{i + 1}"
        layout.update(
            {
                f"{f}Name": (x, 192, 82, 24),
                f"{f}Icon": (x, 216, 82, 48),
                f"{f}Val": (x, 264, 82, 24),
                f"{f}SubVal": (x, 288, 82, 24),
            }
        )
    return layout


def _six_buttons(prefix: str, y: int) -> dict[str, Rect]:
    return {f"{prefix}{i + 1}": (x, y, 50, 50) for i, x in enumerate(_SIX_ACROSS)}


LAYOUT: dict[str, dict[str, Rect]] = {
    "settings": {
        "tBrghtTitle": (MARGIN, 71, CONTENT_W, 32),
        "tBrghtIco": (22, 120, 32, 40),
        "hBrght": (78, 125, 295, 30),
        "tBrghtPct": (378, 120, 60, 40),
        "tBrghtDimIco": (22, 165, 32, 40),
        "hBrghtDim": (78, 170, 295, 30),
        "tBrghtDimPct": (378, 165, 60, 40),
    },
    "light": {
        "btLightFnc1": (MARGIN, 75, 50, 50),
        "btLightFnc2": (MARGIN, 133, 50, 50),
        "btLightFnc3": (MARGIN, 191, 50, 50),
        "btLightFnc4": (MARGIN, 249, 50, 50),
        "hBrightness": (180, 75, 95, 200),
        "hColorTemp": (180, 75, 95, 200),
        "tInfo": (280, 150, RIGHT - 280, 32),
    },
    "cover": {
        "hVertPos": (180, 75, 95, 200),
        "tInfo": (280, 150, RIGHT - 280, 32),
    },
    "media": {
        "tMTitle": (70, 62, RIGHT - 70, 32),
        "tMInterpret": (70, 96, RIGHT - 70, 24),
        "hVolume": (78, 198, 295, 30),
        "m2Btn": (155, 258, 140, 50),
        "m2Icon": (155, 258, 50, 50),
        "m2Name": (205, 258, 90, 50),
        "m2Overlay": (155, 258, 140, 50),
    },
    "row": _row(),
    "grid": _grid(),
    "select": _select(),
    "alarm": _alarm(),
    "climate": {
        "bFan": (MARGIN, 75, 50, 50),
        "bPreset": (MARGIN, 133, 50, 50),
        "bSwing": (MARGIN, 191, 50, 50),
        **_six_buttons("btMode", 260),
    },
    "timer": {
        "bStart": (165, 250, 60, 60),
        "bStop": (235, 250, 60, 60),
    },
    "vacuum": {
        "bFan": (MARGIN, 100, 60, 60),
        "bAction": (134, 100, 60, 60),
        "bHome": (256, 100, 60, 60),
        "bLocate": (378, 100, 60, 60),
        **_six_buttons("bEntity", 260),
    },
    "clock": _six_buttons("bEntity", 260),
    "weather": _weather(),
    "qr": {"qrCode": (MARGIN, 85, 180, 180)},
    "notify": {
        "tTextFull": (MARGIN, 70, CONTENT_W, 170),
        "tIcon": (MARGIN, 70, 134, 170),
        "tText": (154, 70, RIGHT - 154, 170),
        "bBtnLeft": (MARGIN, 253, 209, 55),
        "bBtnRight": (229, 253, 209, 55),
    },
    "about": {
        "tAbout1": (MARGIN, 64, CONTENT_W, 32),
        "tAbout2": (MARGIN, 96, CONTENT_W, 32),
        "p0": (MARGIN, 160, 50, 50),
        "p1": (MARGIN, 218, 50, 50),
        "tDeviceName": (215, 160, RIGHT - 215, 30),
        "tIP": (215, 190, RIGHT - 215, 24),
        "tTftVersVal": (365, 222, RIGHT - 365, 24),
        "tYamlVersVal": (365, 246, RIGHT - 365, 24),
        "tADVersVal": (365, 271, RIGHT - 365, 24),
    },
    "system": {
        "tTitle": (0, 12, VISIBLE_W, 32),
        "tMsg1": (0, 240, VISIBLE_W, 24),
        "tMsg2": (0, 270, VISIBLE_W, 24),
    },
}

# Slider cursors plus the page-background colour of every solid widget (theme.py).
ATTRS: dict[str, dict[str, dict[str, int]]] = with_theme(
    {
        "settings": {"hBrght": _H_SLIDER, "hBrghtDim": _H_SLIDER},
        "light": {"hBrightness": _V_SLIDER, "hColorTemp": _V_SLIDER},
        "cover": {"hVertPos": _V_SLIDER},
        "media": {"hVolume": _H_SLIDER},
        "row": {f"r{i + 1}Slider": _ROW_SLIDER for i in range(5)},
    }
)


def check_bounds() -> list[str]:
    """Return a description of every widget that leaves the visible 450x320 area."""
    problems = []
    for page, widgets in LAYOUT.items():
        for name, (x, y, w, h) in widgets.items():
            if x < 0 or y < 0 or x + w > VISIBLE_W or y + h > HEIGHT:
                problems.append(f"{page}.{name}: ({x}, {y}, {w}, {h}) leaves the visible area")
    return problems

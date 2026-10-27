"""Portrait (320x480) widget geometry for every page of ``nspanel_haui_portrait.HMI``.

The portrait TFT is a rotated sibling of the landscape project: same pages, same
object names and ids, different geometry.  This module is the single source of
truth for that geometry.  ``gen_portrait.py`` applies it to a copy of the HMI
and refuses to run when a page's visual widgets and this spec disagree, so a
widget added to the landscape project must be added here too.

Both HMIs are addressed by the same Python ``COMPONENTS`` registries: every
change applied to the landscape HMI (widgets, attributes, the refinements in
``landscape_layout.py``) needs its counterpart here, and the other way round.

Coordinates are ``(x, y, w, h)`` in display pixels on the 320x480 canvas.

Layout rules (see ``docs/nextion-editor.md``):

- 12 px side margins: content spans x 12..308.
- Pages with a header keep ``tHeader``/``tTitle`` across the full top 50 px and
  move the four function buttons into a bottom bar at y 430..480, so the
  content area is y 50..430.
- Picture-only pages (clock, clocktwo, weather, system) use the whole height.
"""

from __future__ import annotations

from theme import with_theme

Rect = tuple[int, int, int, int]

WIDTH = 320
HEIGHT = 480
MARGIN = 12
CONTENT_W = WIDTH - 2 * MARGIN  # 296
HEADER_H = 50
BAR_Y = HEIGHT - HEADER_H  # 430: top of the bottom function-button bar


def _header(title: bool = True, bar: bool = True) -> dict[str, Rect]:
    """Common header/footer widgets of a page with function buttons."""
    layout: dict[str, Rect] = {"pGrid": (0, 0, WIDTH, HEIGHT)}
    if title:
        layout["tHeader"] = (0, 0, WIDTH, HEADER_H)
        layout["tTitle"] = (0, 0, WIDTH, HEADER_H)
    if bar:
        layout.update(
            {
                "bFncLPri": (0, BAR_Y, 50, 50),
                "bFncLSec": (50, BAR_Y, 50, 50),
                "bFncRSec": (220, BAR_Y, 50, 50),
                "bFncRPri": (270, BAR_Y, 50, 50),
            }
        )
    return layout


def _about() -> dict[str, Rect]:
    layout = _header()
    del layout["tHeader"]  # the about page has no header background widget
    layout.update(
        {
            # the two about sentences word-wrap onto two lines each (PORTRAIT_ATTRS)
            "tAbout1": (12, 56, 296, 48),
            "tAbout2": (12, 104, 296, 48),
            "tDeviceName": (12, 160, 296, 30),
            "tIP": (12, 190, 296, 24),
            "tTftVers": (12, 222, 200, 24),
            "tTftVersVal": (240, 222, 68, 24),
            "tYamlVers": (12, 246, 200, 24),
            "tYamlVersVal": (240, 246, 68, 24),
            "tADVers": (12, 271, 200, 24),
            "tADVersVal": (240, 271, 68, 24),
            "p0": (12, 360, 50, 50),
            "p1": (72, 360, 50, 50),
        }
    )
    return layout


def _alarm() -> dict[str, Rect]:
    layout = _header()
    cols = (12, 114, 216)
    rows = (58, 121, 184, 247)
    keys = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "0", "Del")
    for i, key in enumerate(keys):
        layout[f"bKey{key}"] = (cols[i % 3], rows[i // 3], 92, 55)
    layout.update(
        {
            "b1Fnc": (12, 312, 143, 55),
            "b2Fnc": (165, 312, 143, 55),
            "b3Fnc": (12, 372, 143, 55),
            "b4Fnc": (165, 372, 143, 55),
        }
    )
    return layout


def _blank() -> dict[str, Rect]:
    return {"hBlank": (0, 0, WIDTH, HEIGHT)}


def _climate() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "tTemp": (0, 54, WIDTH, 32),
            "bFan": (12, 95, 50, 50),
            "bPreset": (12, 151, 50, 50),
            "bSwing": (12, 207, 50, 50),
            # single set-point: up / number / down stacked vertically
            "bUp": (140, 92, 60, 50),
            "xSet": (70, 146, 200, 112),
            "tUnit": (270, 166, 32, 32),
            "bDown": (140, 262, 60, 50),
            # dual set-point: two stacked blocks, up/down to the right
            "xSet1": (70, 92, 150, 96),
            "tUnit1": (222, 112, 32, 32),
            "bUp1": (258, 92, 50, 50),
            "bDown1": (258, 142, 50, 50),
            "xSet2": (70, 200, 150, 96),
            "tUnit2": (222, 220, 32, 32),
            "bUp2": (258, 200, 50, 50),
            "bDown2": (258, 250, 50, 50),
        }
    )
    for i in range(6):
        layout[f"btMode{i + 1}"] = (10 + 50 * i, 330, 50, 50)
    return layout


def _entity_rows(layout: dict[str, Rect], y_rows: tuple[int, int]) -> None:
    """Six entity shortcut buttons as two rows of three."""
    for i in range(6):
        layout[f"bEntity{i + 1}"] = (35 + 100 * (i % 3), y_rows[i // 3], 50, 50)


def _clock() -> dict[str, Rect]:
    layout = _header(title=False, bar=False)
    layout.update(
        {
            "tMainIcon": (224, 0, 96, 96),
            "tMainText": (10, 4, 210, 48),
            "tSubText": (10, 44, 210, 32),
            "tTime": (0, 120, WIDTH, 140),
            "tDate": (0, 262, WIDTH, 32),
        }
    )
    _entity_rows(layout, (310, 370))
    return layout


def _clocktwo() -> dict[str, Rect]:
    layout = _header(title=False, bar=False)
    # 11 x 10 letter matrix, reading order unchanged
    for k in range(110):
        layout[f"l{k + 1}"] = (17 + 26 * (k % 11), 90 + 30 * (k // 11), 24, 24)
    layout.update(
        {
            "s1": (17, 56, 24, 24),
            "s2": (277, 56, 24, 24),
            "s3": (17, 396, 24, 24),
            "s4": (277, 396, 24, 24),
            "tNotif": (136, 420, 48, 48),
        }
    )
    return layout


def _cover() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "bUp": (30, 90, 60, 60),
            "bStop": (30, 160, 60, 60),
            "bDown": (30, 230, 60, 60),
            "hVertPos": (113, 80, 95, 250),
            "tInfo": (12, 350, 296, 32),
        }
    )
    return layout


def _grid() -> dict[str, Rect]:
    layout = _header()
    tile_w, tile_h = 147, 120
    for n in range(6):
        x = 11 + 151 * (n % 2)
        y = 56 + 124 * (n // 2)
        g = f"g{n + 1}"
        layout.update(
            {
                f"{g}Btn": (x, y, tile_w, tile_h),
                f"{g}Icon": (x + 6, y + 28, 135, 48),
                f"{g}Name": (x + 6, y + 78, 135, 30),
                f"{g}Overlay": (x, y, tile_w, tile_h),
                f"{g}Power": (x + 99, y, 48, 48),
            }
        )
    return layout


def _light() -> dict[str, Rect]:
    layout = _header()
    for i in range(4):
        layout[f"btLightFnc{i + 1}"] = (12, 80 + 50 * i, 50, 50)
    layout.update(
        {
            "pColorWheel": (90, 80, 200, 200),
            "hBrightness": (138, 80, 95, 250),
            "hColorTemp": (138, 80, 95, 250),
            "bPower": (108, 160, 105, 95),
            "tInfo": (12, 350, 296, 32),
        }
    )
    return layout


def _media() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "tIcon": (12, 58, 50, 50),
            "tMTitle": (70, 56, 238, 32),
            "tMInterpret": (70, 88, 238, 24),
            "bVolDown": (12, 184, 50, 50),
            "hVolume": (78, 194, 164, 30),
            "bVolUp": (258, 184, 50, 50),
            "bPower": (108, 120, 105, 95),
            "jProgress": (0, BAR_Y - 6, WIDTH, 6),
        }
    )
    for i, name in enumerate(("bShuffle", "bPrev", "bPlay", "bNext", "bRepeat")):
        layout[name] = (12 + 60 * i, 122, 50, 50)
    for i in range(3):
        y = 246 + 56 * i
        m = f"m{i + 1}"
        layout.update(
            {
                f"{m}Btn": (12, y, CONTENT_W, 50),
                f"{m}Icon": (12, y, 50, 50),
                f"{m}Name": (62, y, 234, 50),
                f"{m}Overlay": (12, y, CONTENT_W, 50),
            }
        )
    return layout


def _notify() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "tTextFull": (12, 58, 296, 306),
            "tIcon": (12, 58, 296, 90),
            "tText": (12, 154, 296, 210),
            "bBtnLeft": (12, 372, 145, 55),
            "bBtnRight": (163, 372, 145, 55),
        }
    )
    return layout


def _qr() -> dict[str, Rect]:
    layout = _header()
    layout.update({"qrCodeBig": (40, 100, 240, 240), "qrCode": (70, 56, 180, 180)})
    for i, y in enumerate((246, 340)):
        q = f"q{i + 1}"
        layout.update(
            {
                f"{q}Icon": (12, y, 48, 32),
                f"{q}Title": (60, y, 248, 32),
                f"{q}Text": (12, y + 34, 296, 26),
                f"{q}TextAdd": (12, y + 60, 296, 26),
            }
        )
    return layout


def _row() -> dict[str, Rect]:
    layout = _header()
    for i in range(5):
        y = 56 + 74 * i
        r = f"r{i + 1}"
        layout.update(
            {
                f"{r}Icon": (12, y + 12, 50, 50),
                f"{r}Name": (62, y, 246, 30),
                f"{r}Overlay": (12, y, CONTENT_W, 74),
                f"{r}BtnUp": (150, y + 30, 50, 44),
                f"{r}BtnStop": (203, y + 30, 50, 44),
                f"{r}BtnDown": (256, y + 30, 50, 44),
                f"{r}Slider": (150, y + 32, 100, 40),
                f"{r}SliderTxt": (254, y + 30, 54, 44),
                f"{r}BtnText": (158, y + 30, 150, 44),
                f"{r}Toggle": (258, y + 30, 50, 44),
            }
        )
    return layout


def _select() -> dict[str, Rect]:
    layout = _header()
    for i in range(4):
        layout[f"bSelFull{i + 1}"] = (12, 56 + 63 * i, CONTENT_W, 55)
    for n in range(12):
        layout[f"bSel{n + 1}"] = (12 + 151 * (n % 2), 56 + 63 * (n // 2), 145, 55)
    return layout


def _settings() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "tBrghtTitle": (12, 60, 296, 32),
            "tBrghtIco": (12, 108, 44, 50),
            "hBrght": (64, 118, 184, 30),
            "tBrghtPct": (252, 108, 56, 50),
            "tBrghtDimIco": (12, 178, 44, 50),
            "hBrghtDim": (64, 188, 184, 30),
            "tBrghtDimPct": (252, 178, 56, 50),
        }
    )
    return layout


def _system() -> dict[str, Rect]:
    return {
        "tTitle": (0, 40, WIDTH, 32),
        "qrUrl": (90, 130, 140, 140),
        "hSpinner": (90, 135, 140, 140),
        "tMsg1": (0, 320, WIDTH, 24),
        "tMsg2": (0, 350, WIDTH, 24),
    }


def _timer() -> dict[str, Rect]:
    layout = _header()
    layout.update(
        {
            "tMin": (30, 150, 110, 96),
            "tSpace": (140, 150, 40, 96),
            "tSec": (180, 150, 110, 96),
            "bStart": (100, 320, 50, 50),
            "bStop": (170, 320, 50, 50),
        }
    )
    for i, x in enumerate((35, 85, 185, 235)):
        layout[f"bUp{i + 1}"] = (x, 95, 50, 50)
        layout[f"bDown{i + 1}"] = (x, 250, 50, 50)
    return layout


def _vacuum() -> dict[str, Rect]:
    layout = _header()
    for i, name in enumerate(("bFan", "bAction", "bHome", "bLocate")):
        layout[name] = ((12, 91, 170, 248)[i], 80, 60, 60)
    layout["tStatus"] = (12, 160, 296, 32)
    _entity_rows(layout, (250, 310))
    return layout


def _weather() -> dict[str, Rect]:
    layout = _header(title=False, bar=False)
    layout.update(
        {
            "tMainText": (10, 4, 300, 32),
            "tSubText": (10, 36, 300, 24),
            "tTime": (0, 64, WIDTH, 118),
            "tDate": (0, 182, WIDTH, 32),
            "tMainIcon": (40, 224, 72, 72),
            "d1Icon": (120, 236, 24, 24),
            "d1Val": (150, 235, 100, 24),
            "d2Icon": (120, 260, 24, 24),
            "d2Val": (150, 260, 100, 24),
        }
    )
    for i in range(5):
        x = 10 + 60 * i
        f = f"f{i + 1}"
        layout.update(
            {
                f"{f}Name": (x, 300, 58, 24),
                f"{f}Icon": (x, 324, 58, 48),
                f"{f}Val": (x, 372, 58, 24),
                f"{f}SubVal": (x, 396, 58, 24),
            }
        )
    return layout


PORTRAIT_LAYOUT: dict[str, dict[str, Rect]] = {
    "about": _about(),
    "alarm": _alarm(),
    "blank": _blank(),
    "climate": _climate(),
    "clock": _clock(),
    "clocktwo": _clocktwo(),
    "cover": _cover(),
    "grid": _grid(),
    "light": _light(),
    "media": _media(),
    "notify": _notify(),
    "qr": _qr(),
    "row": _row(),
    "select": _select(),
    "settings": _settings(),
    "system": _system(),
    "timer": _timer(),
    "vacuum": _vacuum(),
    "weather": _weather(),
}


# Attribute overrides: ``isbr`` enables word wrap and ``font`` picks a smaller
# embedded font where the narrower portrait widget would clip its text; the
# slider entries give every slider the same cursor as the landscape layout
# (small knob on settings/volume, plain fill bar elsewhere; see
# landscape_layout.py).
_H_SLIDER = {"wid": 25, "hig": 30, "pco": 15416}
_V_SLIDER = {"wid": 0, "hig": 0, "pco": 12678}
_ROW_SLIDER = {"wid": 0, "hig": 0, "pco": 19773}

PORTRAIT_ATTRS: dict[str, dict[str, dict[str, int]]] = {
    "about": {"tAbout1": {"isbr": 1}, "tAbout2": {"isbr": 1}},
    "settings": {"tBrghtTitle": {"font": 0}, "hBrght": _H_SLIDER, "hBrghtDim": _H_SLIDER},
    "light": {"hBrightness": _V_SLIDER, "hColorTemp": _V_SLIDER},
    "cover": {"hVertPos": _V_SLIDER},
    "media": {"hVolume": _H_SLIDER},
    "row": {f"r{i + 1}Slider": _ROW_SLIDER for i in range(5)},
    # The portrait weather time/date are full-width (0..320) but kept the
    # landscape ``xcen=2`` (right-aligned) attribute, pushing the text against
    # the screen edge.  Center them (#64).
    "weather": {"tTime": {"xcen": 1}, "tDate": {"xcen": 1}},
    # #60's clock font fix: the portrait clock time uses font 6 (larger) and
    # must survive HMI regeneration.
    "clock": {"tTime": {"font": 6}},
}


# Generic spec interface read by gen_portrait.py (``--spec portrait_layout``).
HMI_NAME = "nspanel_haui_portrait.HMI"
# Touch settings (Send Component ID) are copied from the landscape project: the
# hub addresses both TFTs by the same widget names and expects the same events.
SIBLING_HMI = "nspanel_haui.HMI"
LAYOUT = PORTRAIT_LAYOUT
# the page-background colour of every solid widget is shared with the landscape HMI
ATTRS = with_theme(PORTRAIT_ATTRS)
PARTIAL = False  # every visual widget of every page must be in LAYOUT


def check_bounds() -> list[str]:
    """Return a description of every widget that leaves the 320x480 canvas."""
    problems = []
    for page, widgets in PORTRAIT_LAYOUT.items():
        for name, (x, y, w, h) in widgets.items():
            if x < 0 or y < 0 or x + w > WIDTH or y + h > HEIGHT:
                problems.append(f"{page}.{name}: ({x}, {y}, {w}, {h}) leaves the canvas")
    return problems


if __name__ == "__main__":
    for page, widgets in PORTRAIT_LAYOUT.items():
        print(f"{page}: {len(widgets)} widgets")
    for problem in check_bounds():
        print("ERROR", problem)

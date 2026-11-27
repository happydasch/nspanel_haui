"""The theme code each solid-colour page runs in its Preinitialize event.

The hub sets the theme globals before every page switch and the page paints
itself from them before the display draws it; ``gen_virtual_layout.py --check``
(``test_virtual_layout.py``) fails when a page's code is missing from an HMI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(source: str) -> dict:
    """Run a snippet against the generator and return the JSON it prints.

    A subprocess, like ``_theme_code``: importing the generator replaces
    ``sys.modules['homeassistant']`` with its own minimal stubs, which would take the
    fixtures' stubs away from every test that runs afterwards.
    """
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _theme_code(*pages: str) -> subprocess.CompletedProcess:
    # A subprocess: the generator installs homeassistant stubs for itself.
    return subprocess.run(
        [sys.executable, "-m", "scripts.hmi_layout.gen_virtual_layout", "--theme-code", *pages],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _sections(output: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for block in output.strip().split("\n\n"):
        title, *lines = block.splitlines()
        sections[title.strip("= ")] = lines
    return sections


def test_solid_page_paints_page_header_and_widgets_from_the_theme_globals():
    result = _theme_code("grid", "settings")
    assert result.returncode == 0, result.stderr
    sections = _sections(result.stdout)

    grid = sections["grid"]
    assert grid[:2] == ["// theme colours: gen_virtual_layout.py --theme-code", "grid.bco=thmBg"]
    assert {
        "tHeader.bco=thmHdrBg",
        "tTitle.bco=thmHdrBg",
        "tTitle.pco=thmHdrTxt",
        "bFncLPri.bco2=thmPressed",
        "g1Btn.bco=thmBg",
        "g1Btn.bco2=thmPressed",
        "g1Name.bco=thmBg",
    } <= set(grid)
    # a slider's track is component_background, whatever the HMI compiles
    assert "hBrght.bco=thmCompBg" in sections["settings"]


_FOREGROUNDS = """
import json
from scripts.hmi_layout import gen_virtual_layout as g
from custom_components.nspanel_haui.haui.mapping.color import COLORS, FOREGROUND_GLOBALS
import copy
layout = g.build_layout("landscape")
page = next(p for p in layout["pages"].values() if p["name"] == "row")
plain = g.theme_code(page).splitlines()
baked = g.theme_code(page, foregrounds=True).splitlines()
legacy = copy.deepcopy(layout)
for name in FOREGROUND_GLOBALS.values():
    legacy["globals"].pop(name, None)
before = g.check_theme_code([legacy])
missing = copy.deepcopy(layout)
row = next(p for p in missing["pages"].values() if p["name"] == "row")
row_comp = next(c for c in row["components"] if c["type"] == g.TYPE_PAGE)
row_comp["events"]["load"] = "\\n".join(
    line
    for line in row_comp["events"]["load"].splitlines()
    if not any(line.strip().endswith(f".pco={name}") for name in FOREGROUND_GLOBALS.values())
)
print(json.dumps({
    "declares": g.declares_foregrounds(layout),
    "added": baked[len(plain):],
    "plain": plain,
    "foregrounds": len(g.theme_foregrounds(page)),
    "globals": sorted(FOREGROUND_GLOBALS.values()),
    "roles": sorted(FOREGROUND_GLOBALS),
    "table_roles": sorted(g.THEME_FOREGROUNDS),
    "before": before,
    "after": g.check_theme_code([missing]),
}))
"""


def _foregrounds() -> dict:
    return _run(_FOREGROUNDS)


def test_a_page_paints_its_body_foregrounds_when_program_declares_the_globals():
    """The body foregrounds are one assignment each, so the hub need not send them."""
    result = _foregrounds()
    globals_ = set(result["globals"])

    # Background-only code names no body foreground global.
    assert not any(line.rsplit("=", 1)[-1] in globals_ for line in result["plain"])
    # One line per body widget that has a foreground role, from a foreground global.
    assert len(result["added"]) == result["foregrounds"]
    for line in result["added"]:
        widget, _, global_name = line.partition(".pco=")
        assert widget and global_name in globals_, line


def test_the_check_switches_contract_with_the_globals_it_finds():
    """A page's code is only demanded in the form its own Program.s can paint."""
    result = _foregrounds()

    assert result["declares"]
    # With the foreground globals removed, the checker uses the legacy backgrounds-only
    # contract; the committed code still contains that generated block.
    assert not any("theme code" in problem for problem in result["before"])
    # Declared globals require each page to initialize its body foregrounds. Removing the
    # row page's assignments exercises the updated contract.
    assert any("Preinitialize event lacks its theme code" in problem for problem in result["after"])


def test_every_body_foreground_role_has_a_global():
    """Adding a role to the generated table must not silently skip its global."""
    result = _foregrounds()

    assert result["roles"] == result["table_roles"]


def test_picture_pages_have_no_theme_code():
    result = _theme_code("clock")

    assert result.returncode == 1
    assert "no solid-colour page named clock" in result.stderr

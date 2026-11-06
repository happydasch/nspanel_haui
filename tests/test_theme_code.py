"""The theme code each solid-colour page runs in its Preinitialize event.

The hub sets the theme globals before every page switch and the page paints
itself from them before the display draws it; ``gen_virtual_layout.py --check``
(``test_virtual_layout.py``) fails when a page's code is missing from an HMI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_virtual_layout" / "gen_virtual_layout.py"


def _theme_code(*pages: str) -> subprocess.CompletedProcess:
    # A subprocess: the generator installs homeassistant stubs for itself.
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--theme-code", *pages],
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


def test_picture_pages_have_no_theme_code():
    result = _theme_code("clock")

    assert result.returncode == 1
    assert "no solid-colour page named clock" in result.stderr

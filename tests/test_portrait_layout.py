"""Tests for the portrait layout spec and its HMI attribute verification.

The portrait HMI is generated from ``scripts/gen_portrait/portrait_layout.py``.
``gen_portrait.py --check`` now runs the attribute verifier as well as the
widget-coverage check, so a spec change (alignment, font, …) cannot pass while
the committed HMI still carries the old value (#64 alignment, #60 font).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "gen_portrait"))

import gen_portrait as gp  # noqa: E402
import portrait_layout as spec  # noqa: E402

HMI_PATH = ROOT / "nextion" / "nspanel_haui_portrait.HMI"
SIBLING_PATH = ROOT / "nextion" / "nspanel_haui.HMI"


def _pages(path: Path) -> dict:
    return gp.parse_pages(path.read_bytes())


def test_weather_time_and_date_are_centered():
    """#64: the portrait weather time/date are full-width and must be centered."""
    weather = spec.PORTRAIT_ATTRS["weather"]
    assert weather["tTime"]["xcen"] == 1
    assert weather["tDate"]["xcen"] == 1


def test_clock_time_uses_large_font():
    """#60: the portrait clock font fix must survive HMI regeneration."""
    assert spec.PORTRAIT_ATTRS["clock"]["tTime"]["font"] == 6


def test_committed_portrait_hmi_has_no_attribute_drift():
    """``gen_portrait.py --check`` verifies attributes, not only coverage."""
    raw = bytearray(HMI_PATH.read_bytes())
    problems = gp.verify(raw, spec, _pages(SIBLING_PATH))
    assert problems == [], "\n".join(problems)


def test_committed_portrait_hmi_covers_every_visual_widget():
    """Coverage (``check_coverage``) still passes on the committed HMI."""
    raw = bytearray(HMI_PATH.read_bytes())
    pages = gp.parse_pages(raw)
    problems = gp.check_coverage(pages, spec, _pages(SIBLING_PATH))
    assert problems == [], "\n".join(problems)

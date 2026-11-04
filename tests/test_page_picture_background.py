"""Pages drawn on a picture background must not clear it.

A page whose HMI background is a picture (``sta=2``) has to set
``PICTURE_BACKGROUND``: otherwise ``_apply_background`` sends ``cls`` and the
device (and every panel card, which replays the hub's commands) shows a flat
colour instead of the picture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nspanel_haui.haui.mapping.panel import PANEL_MAPPING

LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"
PAGE_CLASSES = sorted({cls for _, cls in PANEL_MAPPING.values()}, key=lambda cls: cls.__name__)


@pytest.mark.parametrize("orientation", ["landscape", "portrait"])
def test_picture_background_matches_the_hmi_page(orientation):
    layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
    mismatched = []
    for cls in PAGE_CLASSES:
        page = layout["pages"][str(cls.DESCRIPTOR.page_id)]["components"][0]["attrs"]
        if (page.get("sta") == 2) != cls.PICTURE_BACKGROUND:
            mismatched.append(cls.__name__)
    assert mismatched == []

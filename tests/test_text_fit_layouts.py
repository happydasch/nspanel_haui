"""Keep page text-fitting boxes aligned with the compiled Nextion layouts."""

import json
from pathlib import Path

from custom_components.nspanel_haui.haui.page.grid import _NAME_BOXES as GRID_NAME_BOXES
from custom_components.nspanel_haui.haui.page.media import _MEDIA_NAME_BOXES
from custom_components.nspanel_haui.haui.page.row import (
    _NAME_BOXES as ROW_NAME_BOXES,
)
from custom_components.nspanel_haui.haui.page.row import (
    _SLIDER_TEXT_BOXES,
    _VALUE_BOXES,
)
from custom_components.nspanel_haui.haui.page.select import _SELECTION_BOXES

_LAYOUTS = (
    Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"
)


def test_text_fitting_boxes_match_the_hmi_layouts():
    boxes = {
        "5": {
            "bSel1": lambda orientation: _SELECTION_BOXES[orientation]["regular"],
            "bSelFull1": lambda orientation: _SELECTION_BOXES[orientation]["full"],
        },
        "9": {"g1Name": lambda orientation: GRID_NAME_BOXES[orientation]},
        "10": {
            "r1Name": lambda orientation: ROW_NAME_BOXES[orientation],
            "r1BtnText": lambda orientation: _VALUE_BOXES[orientation],
            "r1SliderTxt": lambda orientation: _SLIDER_TEXT_BOXES[orientation],
        },
        "14": {"m1Name": lambda orientation: _MEDIA_NAME_BOXES[orientation]},
    }
    fonts = {
        "5": {"bSel1": 1, "bSelFull1": 1},
        "9": {"g1Name": 0},
        "10": {"r1Name": 1, "r1BtnText": 1, "r1SliderTxt": 0},
        "14": {"m1Name": 1},
    }
    for orientation in ("landscape", "portrait"):
        layout = json.loads((_LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
        for page_id, page_boxes in boxes.items():
            widgets = {
                widget["name"]: widget["attrs"] for widget in layout["pages"][page_id]["components"]
            }
            for name, get_box in page_boxes.items():
                box = get_box(orientation)
                attrs = widgets[name]
                assert (box.width, box.height, box.border, box.max_len) == (
                    attrs["w"],
                    attrs["h"],
                    attrs["borderw"],
                    attrs["txt_maxl"],
                ), f"{orientation} {name}"
                assert attrs["font"] == fonts[page_id][name], f"{orientation} {name} font"

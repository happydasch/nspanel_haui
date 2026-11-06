"""Title fitting: the universal page title helper and the HMI title widgets."""

import json
from pathlib import Path
from types import SimpleNamespace

from nspanel_haui.haui.abstract.component import Component
from nspanel_haui.haui.abstract.haui_page import HAUIPage
from nspanel_haui.haui.page.system import SystemPage
from nspanel_haui.haui.utils.text import TextBox, fits_line

LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"
_STANDARD_PAGE = "9"
_SYSTEM_PAGE = "0"


class _Page(HAUIPage):
    COMPONENTS = HAUIPage.COMPONENTS.merge(title=Component(3, "tTitle"))


def _page(portrait: bool = False) -> _Page:
    page = _Page.__new__(_Page)
    page.app = SimpleNamespace(device=SimpleNamespace(is_portrait=portrait))
    page.texts: dict[str, str] = {}
    page.set_component_text = lambda component, text: page.texts.__setitem__(component.name, text)
    page.log = lambda *args, **kwargs: None
    return page


def test_short_title_is_shown_unchanged():
    page = _page()

    page.set_title("Kitchen")

    assert page.texts["tTitle"] == "Kitchen"


def test_long_title_is_cut_to_the_title_widget():
    page = _page()

    page.set_title("Living Room Ceiling Light Group")

    shown = page.texts["tTitle"]
    assert shown.endswith("..")
    assert fits_line(shown, _Page.TITLE_FONT, _Page.TITLE_BOX["landscape"])


def test_portrait_title_has_more_room_than_landscape():
    title = "W" * 16

    landscape = _page()
    landscape.set_title(title)
    portrait = _page(portrait=True)
    portrait.set_title(title)

    assert landscape.texts["tTitle"] != title
    assert portrait.texts["tTitle"] == title


def test_reserved_suffix_is_never_cut():
    page = _page()

    page.set_title("W" * 30, reserve="(2/2)")

    shown = page.texts["tTitle"]
    assert shown.endswith("(2/2)")
    assert fits_line(shown, _Page.TITLE_FONT, _Page.TITLE_BOX["landscape"])


def test_title_boxes_match_the_hmi_layouts():
    """The fitting geometry must follow the HMIs (rerun gen_virtual_layout after changes)."""
    for orientation in ("landscape", "portrait"):
        layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))

        standard = {c["name"]: c["attrs"] for c in layout["pages"][_STANDARD_PAGE]["components"]}
        attrs = standard["tTitle"]
        assert HAUIPage.TITLE_BOX[orientation] == TextBox(
            attrs["w"], attrs["h"], attrs["borderw"], attrs["txt_maxl"]
        )
        assert HAUIPage.TITLE_FONT == attrs["font"]

        system = {c["name"]: c["attrs"] for c in layout["pages"][_SYSTEM_PAGE]["components"]}
        attrs = system["tTitle"]
        assert SystemPage.TITLE_BOX[orientation] == TextBox(
            attrs["w"], attrs["h"], attrs["borderw"], attrs["txt_maxl"]
        )
        assert SystemPage.TITLE_FONT == attrs["font"]

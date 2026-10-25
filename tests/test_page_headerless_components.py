"""Headerless pages must not declare header function buttons.

Clock, weather and clocktwo have no ``bFnc*`` widgets: the ids 3-6 belong to
other widgets on those Nextion pages, and the component list is served to the
editor.
"""

import pytest
from nspanel_haui.haui.mapping.panel import get_user_panel_type_descriptors


@pytest.mark.parametrize("type_key", ["clock", "weather", "clocktwo"])
def test_headerless_page_components_have_no_header_buttons(type_key):
    (descriptor,) = [d for d in get_user_panel_type_descriptors() if d["type_key"] == type_key]
    components = descriptor["components"]

    assert descriptor["has_header"] is False
    assert [c["name"] for c in components if c["name"].startswith("bFnc")] == []
    ids = [c["id"] for c in components]
    assert len(ids) == len(set(ids))


def test_blank_page_declares_only_its_own_widget():
    from nspanel_haui.haui.page.blank import BlankPage

    assert [c.name for c in BlankPage.COMPONENTS.values()] == ["hBlank"]


def test_grid_item_options_reach_the_editor_with_translated_labels():
    """The editor shows the grid's per-item options with labels in the user's language."""
    (grid,) = [d for d in get_user_panel_type_descriptors("pl") if d["type_key"] == "grid"]

    options = {o["key"]: o for o in grid["item_options"]}

    assert options["text_color"]["kind"] == "color"
    assert options["text_color"]["label"] == "Kolor tekstu"
    assert options["show_power_button"]["kind"] == "bool"

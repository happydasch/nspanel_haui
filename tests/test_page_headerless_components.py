"""Headerless pages must not declare header function buttons.

Clock, weather and clocktwo have no ``bFnc*`` widgets: the ids 3-6 belong to
other widgets on those Nextion pages, and the component list is served to the
editor.
"""

import pytest

from custom_components.nspanel_haui.haui.mapping.panel import get_user_panel_type_descriptors


@pytest.mark.parametrize("type_key", ["clock", "weather", "clocktwo"])
def test_headerless_page_components_have_no_header_buttons(type_key):
    (descriptor,) = [d for d in get_user_panel_type_descriptors() if d["type_key"] == type_key]
    components = descriptor["components"]

    assert descriptor["has_header"] is False
    assert [c["name"] for c in components if c["name"].startswith("bFnc")] == []
    ids = [c["id"] for c in components]
    assert len(ids) == len(set(ids))


def test_page_specific_color_options_are_exposed():
    """Pages that still support custom colors keep those controls in the editor."""
    descriptors = {
        descriptor["type_key"]: descriptor for descriptor in get_user_panel_type_descriptors("pl")
    }
    color_options = {
        "alarm": {
            "keypad_bg_color",
            "keypad_text_color",
            "arm_button_color",
            "arm_button_back_color",
            "disarm_button_color",
            "disarm_button_back_color",
        },
        "clocktwo": {"off_color", "letter_color", "special_color"},
    }

    for type_key, keys in color_options.items():
        options = {option["key"]: option for option in descriptors[type_key]["options"]}
        assert keys <= options.keys()
        assert all(options[key]["kind"] == "color" for key in keys)


def test_blank_page_declares_only_its_own_widget():
    from custom_components.nspanel_haui.haui.page.blank import BlankPage

    assert [c.name for c in BlankPage.COMPONENTS.values()] == ["hBlank"]


def test_grid_item_options_include_tile_theme_overrides():
    """Grid items can override tile colors while unspecified colors use the device theme."""
    (grid,) = [d for d in get_user_panel_type_descriptors("pl") if d["type_key"] == "grid"]

    options = {o["key"]: o for o in grid["item_options"]}

    assert options["show_power_button"]["kind"] == "bool"
    color_keys = {
        "text_color",
        "back_color",
        "color_pressed",
        "back_color_pressed",
        "power_color",
    }
    assert color_keys <= options.keys()
    assert all(options[key]["kind"] == "color" for key in color_keys)

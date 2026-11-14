"""Example data the Add panel catalog's keyless previews open with."""

from __future__ import annotations

from custom_components.nspanel_haui.web.preview.virtual_panel import preview_kwargs


def test_template_slots_get_examples_of_their_domain():
    panel = {
        "type": "grid",
        "key": "",
        "items": [
            {"item": "", "domain": "light", "icon": "mdi:lightbulb", "show_power_button": True},
            {"item": "", "domain": "cover", "icon": "mdi:blinds-horizontal"},
        ],
    }

    kwargs = preview_kwargs(None, panel)

    assert kwargs["items"] == [
        {"item": "light.haui_preview_lamp", "icon": "mdi:lightbulb", "show_power_button": True},
        {"item": "cover.haui_preview_blind", "icon": "mdi:blinds-horizontal"},
    ]


def test_repeated_slots_reuse_the_examples_of_their_domain():
    panel = {"type": "grid", "key": "", "items": [{"item": "", "domain": "switch"}] * 3}

    kwargs = preview_kwargs(None, panel)

    assert [entry["item"] for entry in kwargs["items"]] == [
        "switch.haui_preview_fan",
        "switch.haui_preview_radio",
        "switch.haui_preview_fan",
    ]


def test_a_list_with_chosen_entities_is_previewed_as_it_is():
    panel = {"type": "grid", "key": "", "items": [{"item": "light.real"}, {"item": ""}]}

    assert "items" not in preview_kwargs(None, panel)


def test_a_slot_without_a_hint_uses_the_default_examples():
    panel = {"type": "grid", "key": "", "items": [{"item": ""}]}

    kwargs = preview_kwargs(None, panel)

    assert kwargs["items"][0]["item"]

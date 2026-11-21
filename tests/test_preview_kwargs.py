"""Example data the Add panel catalog's keyless previews open with."""

from __future__ import annotations

from custom_components.nspanel_haui.web.preview.virtual_panel import preview_kwargs


def test_a_list_with_entries_is_previewed_as_it_is():
    panel = {"type": "grid", "key": "", "items": [{"item": "light.real"}, {"item": ""}]}

    assert "items" not in preview_kwargs(None, panel)


def test_an_empty_item_list_takes_example_entities():
    panel = {"type": "grid", "key": ""}

    kwargs = preview_kwargs(None, panel)

    assert kwargs["items"][0]["item"]

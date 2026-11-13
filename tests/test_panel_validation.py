"""Saving panels enforces the option rules on new and changed panels."""

from __future__ import annotations

import pytest

from custom_components.nspanel_haui.haui.config_models import (
    PanelValidationError,
    validate_panels,
)


def _store(*panels: dict) -> dict:
    return {"devices": {"kitchen": {"panels": list(panels)}}}


BROKEN_LIGHT = {"type": "light", "key": "light_0", "item": {"item": "sensor.x"}}
GRID = {"type": "grid", "key": "grid_0", "items": [{"item": "light.a"}]}


def test_changed_panel_with_wrong_domain_is_refused():
    with pytest.raises(PanelValidationError) as caught:
        validate_panels(_store(BROKEN_LIGHT), previous=_store())

    assert caught.value.errors == [
        {
            "device": "kitchen",
            "panel": "light_0",
            "field": "item",
            "kind": "domain",
            "message": "Use a light entity, not sensor.x",
        }
    ]


def test_unchanged_stored_panel_does_not_block_other_panels():
    validate_panels(_store(BROKEN_LIGHT, GRID), previous=_store(BROKEN_LIGHT))


def test_editing_the_invalid_panel_requires_a_fix():
    edited = {**BROKEN_LIGHT, "title": "Lamp"}

    with pytest.raises(PanelValidationError):
        validate_panels(_store(edited), previous=_store(BROKEN_LIGHT))


def test_popup_override_without_item_saves():
    popup = {"type": "light", "key": "popup_light", "show_in_navigation": False}

    validate_panels(_store(popup), previous=_store())


def test_popup_override_with_wrong_domain_is_refused():
    popup = {"type": "light", "key": "popup_light", "item": {"item": "sensor.x"}}

    with pytest.raises(PanelValidationError):
        validate_panels(_store(popup), previous=_store())


def test_yaml_import_checks_every_panel():
    with pytest.raises(PanelValidationError):
        validate_panels(_store(BROKEN_LIGHT))


def test_message_names_the_first_error():
    with pytest.raises(PanelValidationError) as caught:
        validate_panels(_store(BROKEN_LIGHT))

    assert "light_0" in str(caught.value)
    assert "sensor.x" in str(caught.value)


def test_unknown_type_is_not_checked_against_rules():
    validate_panels(_store({"type": "nonexistent", "key": "x"}))

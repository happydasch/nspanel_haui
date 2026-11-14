"""Starter templates for new panels (``haui/mapping/templates.py``)."""

from __future__ import annotations

import copy

import pytest

from custom_components.nspanel_haui.haui.config_models import (
    PanelValidationError,
    validate_panels,
)
from custom_components.nspanel_haui.haui.mapping import templates
from custom_components.nspanel_haui.haui.mapping.panel import PANEL_MAPPING
from custom_components.nspanel_haui.haui.mapping.templates import (
    PANEL_TEMPLATES,
    get_panel_templates,
)

EXAMPLES = {
    "alarm_control_panel": "alarm_control_panel.home",
    "climate": "climate.living",
    "cover": "cover.blind",
    "light": "light.lamp",
    "media_player": "media_player.tv",
    "scene": "scene.movie",
    "sensor": "sensor.outside",
    "switch": "switch.fan",
}


def _filled(panel: dict) -> dict:
    """The template with every empty entity slot chosen, as a user would save it."""
    panel = copy.deepcopy(panel)
    descriptor = PANEL_MAPPING[panel["type"]][1].DESCRIPTOR
    for option in descriptor.options:
        value = panel.get(option.key)
        if option.kind == "item" and isinstance(value, dict) and value.get("item") == "":
            value["item"] = EXAMPLES[option.domain]
        elif option.kind == "item_list" and isinstance(value, list):
            for entry in value:
                domain = entry.pop("domain", "sensor")
                if entry.get("item") == "":
                    entry["item"] = EXAMPLES[domain]
        elif option.kind == "str" and option.required and not value:
            panel[option.key] = "Guests"
    return panel


def _save(panel: dict) -> None:
    validate_panels({"devices": {"kitchen": {"panels": [{**panel, "key": "new_0"}]}}})


@pytest.mark.parametrize("template", PANEL_TEMPLATES, ids=lambda t: t.key)
def test_every_template_type_exists(template):
    assert template.panel["type"] in PANEL_MAPPING


@pytest.mark.parametrize("template", PANEL_TEMPLATES, ids=lambda t: t.key)
def test_templates_are_keyless(template):
    assert "key" not in template.panel


@pytest.mark.parametrize("template", PANEL_TEMPLATES, ids=lambda t: t.key)
def test_filled_template_validates(template):
    _save(_filled(template.panel))


@pytest.mark.parametrize("template", PANEL_TEMPLATES, ids=lambda t: t.key)
def test_empty_template_asks_only_for_entities_and_names(template):
    try:
        _save(template.panel)
    except PanelValidationError as error:
        assert {entry["kind"] for entry in error.errors} == {"required"}
    else:
        pytest.fail(f"{template.key} has no slot for the user to fill")


def test_templates_are_translated(monkeypatch):
    monkeypatch.setattr(templates, "get_translation", lambda text, language: f"{language}:{text}")

    served = get_panel_templates("de")

    first = served[0]
    assert first["label"] == f"de:{PANEL_TEMPLATES[0].label}"
    assert first["description"] == f"de:{PANEL_TEMPLATES[0].description}"
    assert first["panel"]["title"] == f"de:{PANEL_TEMPLATES[0].panel['title']}"
    assert PANEL_TEMPLATES[0].panel["title"] != first["panel"]["title"]


def test_served_templates_carry_their_card_fields():
    served = get_panel_templates("en")

    assert set(served[0]) == {"key", "label", "description", "icon", "panel"}

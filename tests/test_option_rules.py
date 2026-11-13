"""Field-level rules for panel options (``haui/option_rules.py``).

The cases live in ``tests/fixtures/option_rules_cases.json`` and run through the
editor's JS engine too (``tests/frontend/option-rules.test.mjs``), so the hub and
the editor cannot disagree about what a panel may save.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.nspanel_haui.haui.mapping.descriptor import PageOption
from custom_components.nspanel_haui.haui.mapping.panel import PANEL_MAPPING, _serialize_option
from custom_components.nspanel_haui.haui.option_rules import option_errors, panel_option_errors

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "option_rules_cases.json").read_text(encoding="utf-8")
)


def _option(spec: dict) -> PageOption:
    spec = dict(spec)
    if "choices" in spec:
        spec["choices"] = [tuple(choice) for choice in spec["choices"]]
    return PageOption(**spec)


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_fixture_cases(case):
    errors = option_errors(_option(case["option"]), case["value"], popup=case["popup"])

    assert [(error.field, error.kind) for error in errors] == [
        tuple(expected) for expected in case["errors"]
    ]


def test_every_error_has_a_message():
    for case in CASES:
        for error in option_errors(_option(case["option"]), case["value"], popup=case["popup"]):
            assert error.message, case["name"]


def test_serialized_option_carries_rule_fields():
    option = PageOption(key="n", kind="int", required=True, min=1, max=9)

    serialized = _serialize_option(option, "en")

    assert serialized["required"] is True
    assert serialized["min"] == 1
    assert serialized["max"] == 9


@pytest.mark.parametrize("type_key", ["alarm", "climate", "cover", "light", "media", "vacuum"])
def test_primary_items_are_required(type_key):
    options = {o.key: o for o in PANEL_MAPPING[type_key][1].DESCRIPTOR.options}

    assert options["item"].required is True


def test_qr_network_name_is_required():
    options = {o.key: o for o in PANEL_MAPPING["qr"][1].DESCRIPTOR.options}

    assert options["essid"].required is True


def test_int_options_have_bounds():
    for type_key, (_, cls) in PANEL_MAPPING.items():
        for option in cls.DESCRIPTOR.options:
            if option.kind == "int":
                assert option.min is not None, f"{type_key}.{option.key} has no minimum"


def test_panel_errors_cover_every_option():
    descriptor = PANEL_MAPPING["light"][1].DESCRIPTOR
    panel = {"type": "light", "key": "light_0", "item": {"item": "sensor.x"}, "show_kelvin": True}

    errors = panel_option_errors(panel, descriptor, popup=False)

    assert [(error.field, error.kind) for error in errors] == [("item", "domain")]


def test_panel_without_its_required_item():
    descriptor = PANEL_MAPPING["light"][1].DESCRIPTOR

    errors = panel_option_errors({"type": "light", "key": "l"}, descriptor, popup=False)

    assert [(error.field, error.kind) for error in errors] == [("item", "required")]

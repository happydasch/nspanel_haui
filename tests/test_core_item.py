"""HAUIItem internal item parsing."""

from __future__ import annotations

from nspanel_haui.haui.abstract import haui_item
from nspanel_haui.haui.abstract.haui_item import HAUIItem


class _App:
    pass


class _TemplateApp:
    def render_template(self, template: str) -> str:
        return template.replace("{{ 1 + 1 }}", "2")


def test_entity_value_defaults_to_entity_state(monkeypatch) -> None:
    monkeypatch.setattr(haui_item, "get_item_value", lambda item, default: "21.5 °C")
    item = HAUIItem(_App(), {"item": "sensor.temperature"})

    assert item.get_value() == "21.5 °C"


def test_numeric_value_override_is_shown() -> None:
    item = HAUIItem(_App(), {"item": "sensor.temperature", "value": 42})

    assert item.get_value() == "42"


def test_bare_jinja_template_is_rendered() -> None:
    item = HAUIItem(_TemplateApp(), {"item": "text:x", "value": "{{ 1 + 1 }} W"})

    assert item.get_value() == "2 W"


def test_text_item_keeps_colons() -> None:
    item = HAUIItem(_App(), {"item": "text:12:30"})

    assert item.get_value() == "12:30"


def test_navigate_item_data_is_panel_key() -> None:
    item = HAUIItem(_App(), {"item": "navigate:popup_timer"})

    assert item.get_internal_type() == "navigate"
    assert item.get_internal_data() == "popup_timer"


def test_zero_value_override_is_kept() -> None:
    item = HAUIItem(_App(), {"item": "sensor.temperature", "value": 0})

    assert item.get_value() == "0"

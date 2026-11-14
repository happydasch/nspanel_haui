"""HAUIItem internal item parsing."""

from __future__ import annotations

from typing import Any

import pytest
from support.page_app import Entity

from custom_components.nspanel_haui.haui.abstract import haui_item
from custom_components.nspanel_haui.haui.abstract.haui_item import HAUIItem
from custom_components.nspanel_haui.haui.device import HAUIDevice
from custom_components.nspanel_haui.haui.mapping.const import DEFAULT_CONFIG
from custom_components.nspanel_haui.haui.utils import item as item_utils


class _App:
    def log(self, msg: str, **kwargs) -> None:
        pass


class _TemplateApp:
    def log(self, msg: str, **kwargs) -> None:
        pass

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


def test_weather_value_shows_zero_degrees_and_whole_floats_plainly() -> None:
    class _Weather:
        def __init__(self, attrs: dict) -> None:
            self.attrs = attrs

        def get_item_attr(self, attr: str, default=None):
            return self.attrs.get(attr, default)

    value = item_utils._value_weather
    assert value(None, "sunny", _Weather({"temperature": 0.0})) == "0°C"
    assert value(None, "sunny", _Weather({"temperature": 21.0, "temperature_unit": "°F"})) == "21°F"
    assert value(None, "sunny", _Weather({"temperature": 21.5})) == "21.5°C"
    assert value(None, "sunny", _Weather({})) == ""


def test_zero_value_override_is_kept() -> None:
    item = HAUIItem(_App(), {"item": "sensor.temperature", "value": 0})

    assert item.get_value() == "0"


class _DeviceApp:
    """One entity on a device with its real format settings; Home Assistant runs in Berlin."""

    def __init__(self, entity: Entity, settings: dict[str, Any]) -> None:
        self.entity = entity
        self.device_config = DEFAULT_CONFIG
        self.device = HAUIDevice(self, settings)

    def log(self, msg: str, **kwargs) -> None:
        pass

    def item_exists(self, entity_id: str) -> bool:
        return True

    def get_item(self, entity_id: str) -> Entity:
        return self.entity

    def get_timezone(self) -> str:
        return "Europe/Berlin"


def _value(entity_id: str, state: str, attributes: dict | None = None, **settings) -> str:
    app = _DeviceApp(Entity(state, attributes or {}), {"locale": "en_US", **settings})
    return HAUIItem(app, {"item": entity_id}).get_value()


_US = {"time_format": "%I:%M %p", "date_format": "%m/%d/%Y"}


@pytest.mark.parametrize(
    ("entity_id", "state", "attributes", "shown"),
    [
        (
            "sensor.next_alarm",
            "2026-11-16T05:30:00+00:00",
            {"device_class": "timestamp"},
            "11/16/2026 06:30 AM",
        ),
        ("sensor.bin_day", "2026-11-16", {"device_class": "date"}, "11/16/2026"),
        ("date.holiday", "2026-12-24", {}, "12/24/2026"),
        ("time.wake_up", "18:45:00", {}, "06:45 PM"),
        ("datetime.departure", "2026-11-16T17:05:00+00:00", {}, "11/16/2026 06:05 PM"),
        ("input_datetime.reminder", "2026-11-16 18:45:00", {}, "11/16/2026 06:45 PM"),
        ("event.doorbell", "2026-11-16T21:41:00.123+00:00", {}, "11/16/2026 10:41 PM"),
    ],
)
def test_a_date_or_time_state_is_shown_in_the_device_formats(
    entity_id, state, attributes, shown
) -> None:
    assert _value(entity_id, state, attributes, **_US) == shown


def test_a_date_follows_the_language_while_the_formats_are_left_at_default() -> None:
    assert _value("date.holiday", "2026-12-24", locale="de_DE") == "Donnerstag, 24. Dezember 2026"
    assert _value("time.wake_up", "18:45:00") == "18:45"


def test_a_timestamp_sensor_without_a_date_shows_its_state_like_any_sensor() -> None:
    timestamp = _value("sensor.next_alarm", "unknown", {"device_class": "timestamp"}, **_US)

    assert timestamp == _value("sensor.next_alarm", "unknown", **_US)


def test_a_sensor_of_another_class_shows_its_state_unformatted() -> None:
    assert _value("sensor.build", "2026-11-16", {"device_class": "enum"}, **_US) == "2026-11-16"

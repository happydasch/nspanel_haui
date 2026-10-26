"""Tests for the current-page sensor platform."""

from __future__ import annotations

import asyncio
import sys
import types

from pytest import MonkeyPatch


class _App:
    def __init__(self):
        self._ha_device_id = "dev1"


def _import_sensor(monkeypatch: MonkeyPatch):
    sensor_mod = types.ModuleType("homeassistant.components.sensor")
    sensor_mod.SensorEntity = type("SensorEntity", (), {"_attr_has_entity_name": True})
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.DeviceInfo = dict
    entity_mod = types.ModuleType("homeassistant.helpers.entity")
    entity_mod.EntityCategory = type("EntityCategory", (), {"DIAGNOSTIC": "diagnostic"})
    monkeypatch.setitem(sys.modules, "homeassistant.components.sensor", sensor_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity", entity_mod)
    monkeypatch.delitem(sys.modules, "nspanel_haui.sensor", raising=False)
    from nspanel_haui import sensor

    return sensor


def _entity(sensor):
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = sensor.NSPanelPageSensor(_App(), "kitchen", entry)
    entity.async_write_ha_state = lambda: None
    return entity


def _event(data):
    return types.SimpleNamespace(data=data)


def test_page_event_updates_the_value(monkeypatch):
    sensor = _import_sensor(monkeypatch)
    entity = _entity(sensor)

    asyncio.run(
        entity._async_page_changed(
            _event(
                {
                    "device": "kitchen",
                    "page": "grid",
                    "panel": "grid_0",
                    "type": "grid",
                    "title": "Living",
                }
            )
        )
    )

    assert entity._attr_native_value == "grid"
    assert entity._attr_available is True
    assert entity._attr_extra_state_attributes["panel"] == "grid_0"
    assert entity._attr_extra_state_attributes["title"] == "Living"


def test_page_event_for_another_device_is_ignored(monkeypatch):
    sensor = _import_sensor(monkeypatch)
    entity = _entity(sensor)

    asyncio.run(entity._async_page_changed(_event({"device": "office", "page": "clock"})))

    assert entity._attr_native_value is None
    assert entity._attr_available is False


def test_connection_changed_toggles_availability(monkeypatch):
    sensor = _import_sensor(monkeypatch)
    entity = _entity(sensor)
    entity._attr_native_value = "clock"
    entity._attr_available = True

    asyncio.run(entity._async_connection_changed(_event({"device": "kitchen", "connected": False})))
    assert entity._attr_available is False
    assert entity._attr_native_value is None

    asyncio.run(entity._async_connection_changed(_event({"device": "kitchen", "connected": True})))
    assert entity._attr_available is True


def test_subscribes_to_bus_events(monkeypatch):
    sensor = _import_sensor(monkeypatch)
    entity = _entity(sensor)
    listened = []

    class _Bus:
        def async_listen(self, event_type, fn):
            listened.append(event_type)
            return lambda: None

    entity.hass = types.SimpleNamespace(bus=_Bus())

    asyncio.run(entity.async_added_to_hass())

    assert listened == ["nspanel_haui.page_changed", "nspanel_haui.connection_changed"]

    asyncio.run(entity.async_will_remove_from_hass())

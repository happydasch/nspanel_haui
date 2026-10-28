"""Tests for the shared integration helpers (ESPHome entry lookup, loop runner, store)."""

from __future__ import annotations

import asyncio
import sys
import threading
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

# storage.py imports Store at module level; test_api.py installs this stub
# for the whole suite, but this file must pass standalone too.
_storage_mod = types.ModuleType("homeassistant.helpers.storage")
_storage_mod.Store = object
sys.modules.setdefault("homeassistant.helpers.storage", _storage_mod)

from nspanel_haui import esphome_helpers, ha_adapter, storage  # noqa: E402


def _hass_with_esphome(*names: str):
    entries = [
        SimpleNamespace(entry_id=f"e{i}", data={"device_name": n}) for i, n in enumerate(names)
    ]
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = entries
    return hass, entries


def test_find_esphome_entry_matches_normalized_names():
    hass, entries = _hass_with_esphome("other-panel", "Living_Room-Panel")

    assert esphome_helpers.find_esphome_entry(hass, "living room panel") is entries[1]


def test_find_esphome_entry_returns_none_for_unknown_or_blank_name():
    hass, _ = _hass_with_esphome("kitchen")

    assert esphome_helpers.find_esphome_entry(hass, "office") is None
    assert esphome_helpers.find_esphome_entry(hass, "  ") is None


def _network_hass(monkeypatch, values, *, device_id="device-1"):
    registry_entries = {
        entity_id: SimpleNamespace(
            domain="sensor",
            platform="esphome",
            device_id=entity_device_id,
            original_name=name,
        )
        for entity_id, (entity_device_id, name) in values.items()
    }
    entity_registry = SimpleNamespace(entities=registry_entries)
    registry_module = types.ModuleType("homeassistant.helpers.entity_registry")
    registry_module.async_get = lambda hass: entity_registry
    helpers = sys.modules["homeassistant.helpers"]
    monkeypatch.setattr(helpers, "entity_registry", registry_module, raising=False)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", registry_module)
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: device_id)
    hass = MagicMock()
    return hass


def _state(entity_id, value):
    return SimpleNamespace(entity_id=entity_id, state=value)


def test_read_network_entities_resolves_prefixed_ids_by_device_and_original_name(monkeypatch):
    entities = {
        "sensor.lounge_panel_ip": ("device-1", "IP"),
        "sensor.lounge_panel_ssid": ("device-1", "SSID"),
        "sensor.lounge_panel_rssi": ("device-1", "RSSI"),
        "sensor.other_panel_ip": ("device-2", "IP"),
    }
    states = {
        "sensor.lounge_panel_ip": _state("sensor.lounge_panel_ip", "10.0.0.6"),
        "sensor.lounge_panel_ssid": _state("sensor.lounge_panel_ssid", "HomeNet"),
        "sensor.lounge_panel_rssi": _state("sensor.lounge_panel_rssi", "-55"),
    }
    hass = _network_hass(monkeypatch, entities)
    hass.states.get.side_effect = states.get

    nw = esphome_helpers.read_network_entities(hass, "nspanel-haui")

    assert nw == {"ip": "10.0.0.6", "ssid": "HomeNet", "rssi": -55.0}
    assert [args.args[0] for args in hass.states.get.call_args_list] == [
        "sensor.lounge_panel_ip",
        "sensor.lounge_panel_ssid",
        "sensor.lounge_panel_rssi",
    ]


def test_read_network_entities_handles_each_unavailable_field_independently(monkeypatch):
    entities = {
        "sensor.panel_ip": ("device-1", "IP"),
        "sensor.panel_ssid": ("device-1", "SSID"),
        "sensor.panel_rssi": ("device-1", "RSSI"),
    }
    hass = _network_hass(monkeypatch, entities)
    hass.states.get.side_effect = {
        "sensor.panel_ip": _state("sensor.panel_ip", "unavailable"),
        "sensor.panel_ssid": _state("sensor.panel_ssid", "HomeNet"),
        "sensor.panel_rssi": _state("sensor.panel_rssi", "not-a-number"),
    }.get

    assert esphome_helpers.read_network_entities(hass, "panel") == {
        "ip": "",
        "ssid": "HomeNet",
        "rssi": None,
    }


def test_read_network_entities_does_not_guess_an_entity_id(monkeypatch):
    hass = _network_hass(monkeypatch, {})

    assert esphome_helpers.read_network_entities(hass, "panel") == {
        "ip": "",
        "ssid": "",
        "rssi": None,
    }
    hass.states.get.assert_not_called()


def test_run_on_loop_returns_result_from_the_loop_thread():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    async def where() -> int:
        return threading.get_ident()

    try:
        assert ha_adapter._run_on_loop(loop, where()) == thread.ident
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()


def test_panel_store_uses_per_entry_key_and_fresh_empty_payloads(monkeypatch):
    created = []

    class _Store:
        def __init__(self, hass, version, key):
            created.append((version, key))

    monkeypatch.setattr(storage, "Store", _Store)

    storage.panel_store(object(), "abc")

    assert created == [(storage.PANEL_STORE_VERSION, "nspanel_haui.abc_panels")]
    assert storage.empty_store() == {"version": 1, "devices": {}}
    assert storage.empty_store() is not storage.empty_store()

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


def _state(entity_id, value):
    return SimpleNamespace(entity_id=entity_id, state=value)


def test_read_network_entities_falls_back_to_slug_ids():
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: {
        "sensor.nspanel_haui_ip": _state("sensor.nspanel_haui_ip", "10.0.0.5"),
        "sensor.nspanel_haui_ssid": _state("sensor.nspanel_haui_ssid", "HomeNet"),
        "sensor.nspanel_haui_rssi": _state("sensor.nspanel_haui_rssi", "-62"),
    }.get(eid)

    nw = esphome_helpers.read_network_entities(hass, "nspanel-haui")

    assert nw == {"ip": "10.0.0.5", "ssid": "HomeNet", "rssi": -62.0}


def test_read_network_entities_uses_the_registry_resolver_when_given():
    """Area/device-prefixed ids (fresh installs after a rename) resolve by name."""
    resolved = {
        "sensor.salon_nspanel_haui_ip": _state("sensor.salon_nspanel_haui_ip", "10.0.0.6"),
        "sensor.salon_nspanel_haui_ssid": _state("sensor.salon_nspanel_haui_ssid", "HomeNet"),
        "sensor.salon_nspanel_haui_rssi": _state("sensor.salon_nspanel_haui_rssi", "-55"),
    }
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: resolved.get(eid)

    def resolver(domain, original_name):
        return {
            "ip": "sensor.salon_nspanel_haui_ip",
            "ssid": "sensor.salon_nspanel_haui_ssid",
            "rssi": "sensor.salon_nspanel_haui_rssi",
        }.get(original_name)

    nw = esphome_helpers.read_network_entities(hass, "nspanel-haui", resolver)

    assert nw == {"ip": "10.0.0.6", "ssid": "HomeNet", "rssi": -55.0}


def test_read_network_entities_ignores_unavailable_states():
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: {
        "sensor.nspanel_haui_ip": _state("sensor.nspanel_haui_ip", "unknown"),
        "sensor.nspanel_haui_ssid": _state("sensor.nspanel_haui_ssid", "unavailable"),
        "sensor.nspanel_haui_rssi": None,
    }.get(eid)

    nw = esphome_helpers.read_network_entities(hass, "nspanel-haui")

    assert nw == {"ip": "", "ssid": "", "rssi": None}


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

"""Tests for the "HAUI Display" update entity platform."""

from __future__ import annotations

import asyncio
import enum
import sys
import types

import pytest
from pytest import MonkeyPatch


class _HomeAssistantError(Exception):
    pass


class _App:
    def __init__(self, install_result=None):
        self._ha_device_id = "dev1"
        self.install_result = install_result or {"state": "installing"}
        self.dispatched: list = []
        self.installs: list = []

    def dispatch(self, fn, *args):
        self.dispatched.append(fn)

    def publish_display_update(self):
        pass

    def install_tft(self, version=None):
        self.installs.append(version)
        return self.install_result

    async def async_run_on_worker(self, fn, *args):
        return fn(*args)


def _import_update(monkeypatch: MonkeyPatch):
    update_mod = types.ModuleType("homeassistant.components.update")
    update_mod.UpdateEntity = type("UpdateEntity", (), {})
    update_mod.UpdateDeviceClass = type("UpdateDeviceClass", (), {"FIRMWARE": "firmware"})
    update_mod.UpdateEntityFeature = enum.IntFlag(
        "UpdateEntityFeature", {"INSTALL": 1, "SPECIFIC_VERSION": 2, "PROGRESS": 4}
    )
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.HomeAssistantError = _HomeAssistantError
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.DeviceInfo = dict
    monkeypatch.setitem(sys.modules, "homeassistant.components.update", update_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.delitem(sys.modules, "nspanel_haui.update", raising=False)
    from nspanel_haui import update

    return update


def _entity(update, app=None):
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = update.NSPanelDisplayUpdate(app or _App(), "kitchen", entry)
    entity.async_write_ha_state = lambda: None
    return entity


def _event(**data):
    payload = {
        "device": "kitchen",
        "connected": True,
        "installed_version": "0.4.1",
        "latest_version": "0.4.2",
        "state": "idle",
        "last_error": None,
    }
    payload.update(data)
    return types.SimpleNamespace(data=payload)


def test_event_sets_installed_and_latest_version(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_display_update(_event()))

    assert entity._attr_installed_version == "0.4.1"
    assert entity._attr_latest_version == "0.4.2"
    assert entity._attr_available is True
    assert entity.in_progress is False


def test_event_for_another_device_is_ignored(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_display_update(_event(device="hallway")))

    assert entity._attr_available is False


def test_install_keeps_the_entity_available_while_the_device_is_offline(monkeypatch):
    """The upload blocks the device; the install outlives the API connection."""
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_display_update(_event(connected=False, state="installing")))

    assert entity._attr_available is True
    assert entity.in_progress is True


def test_offline_device_without_install_is_unavailable(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_display_update(_event(connected=False)))

    assert entity._attr_available is False


def test_install_runs_the_hub_tft_install(monkeypatch):
    update = _import_update(monkeypatch)
    app = _App()
    entity = _entity(update, app)

    asyncio.run(entity.async_install(None, False))

    assert app.installs == [None]


def test_install_with_a_version_installs_that_release(monkeypatch):
    """update.install with version installs another (e.g. older) release."""
    update = _import_update(monkeypatch)
    app = _App()
    entity = _entity(update, app)

    asyncio.run(entity.async_install("0.4.1", False))

    assert app.installs == ["0.4.1"]


def test_install_error_is_raised(monkeypatch):
    update = _import_update(monkeypatch)
    app = _App({"state": "error", "last_error": "No GitHub release 0.4.2"})
    entity = _entity(update, app)

    with pytest.raises(_HomeAssistantError, match="No GitHub release 0.4.2"):
        asyncio.run(entity.async_install(None, False))


def test_added_entity_requests_the_current_state(monkeypatch):
    """The device may have connected before the entity was added."""
    update = _import_update(monkeypatch)
    app = _App()
    entity = _entity(update, app)
    entity.hass = types.SimpleNamespace(
        bus=types.SimpleNamespace(async_listen=lambda event, cb: lambda: None)
    )

    asyncio.run(entity.async_added_to_hass())

    assert app.dispatched == [app.publish_display_update]


def test_setup_skips_devices_without_an_esphome_link(monkeypatch):
    update = _import_update(monkeypatch)
    linked = _App()
    unlinked = _App()
    unlinked._ha_device_id = None
    hass = types.SimpleNamespace(
        data={update.DOMAIN: {"entry1": {"kitchen": linked, "hallway": unlinked}}}
    )
    added: list = []

    asyncio.run(
        update.async_setup_entry(
            hass, types.SimpleNamespace(entry_id="entry1"), lambda entities: added.extend(entities)
        )
    )

    assert [entity._dev_name for entity in added] == ["kitchen"]

"""Tests for the "HAUI Firmware" and "HAUI Display" update entity platform."""

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
    def __init__(self, install_result=None, firmware_result=None):
        self._ha_device_id = "dev1"
        self.install_result = install_result or {"state": "installing"}
        self.firmware_result = firmware_result or {"firmware_installing": True}
        self.dispatched: list = []
        self.installs: list = []
        self.firmware_installs: list = []

    def dispatch(self, fn, *args):
        self.dispatched.append(fn)

    def publish_display_update(self):
        pass

    def publish_firmware_update(self):
        pass

    def install_tft(self, version=None):
        self.installs.append(version)
        return self.install_result

    def install_firmware(self, version=None, url=None):
        self.firmware_installs.append((version, url))
        return self.firmware_result

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
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.async_get = lambda hass: hass.entity_registry
    monkeypatch.setitem(sys.modules, "homeassistant.components.update", update_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", entity_registry)
    helpers = sys.modules.get("homeassistant.helpers")
    if helpers is not None:
        monkeypatch.setattr(helpers, "entity_registry", entity_registry, raising=False)
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

    asyncio.run(entity._async_update_event(_event()))

    assert entity._attr_installed_version == "0.4.1"
    assert entity._attr_latest_version == "0.4.2"
    assert entity._attr_available is True
    assert entity.in_progress is False


def test_event_for_another_device_is_ignored(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_update_event(_event(device="hallway")))

    assert entity._attr_available is False


def test_install_keeps_the_entity_available_while_the_device_is_offline(monkeypatch):
    """The upload blocks the device; the install outlives the API connection."""
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_update_event(_event(connected=False, state="installing")))

    assert entity._attr_available is True
    assert entity.in_progress is True


def test_offline_device_without_install_is_unavailable(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _entity(update)

    asyncio.run(entity._async_update_event(_event(connected=False)))

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


class _EntityRegistry:
    def __init__(self, entities=None):
        self.entities = dict(entities or {})  # entity_id -> unique_id of ours or None
        self.renamed: list = []

    def async_get_entity_id(self, domain, platform, unique_id):
        return next((eid for eid, uid in self.entities.items() if uid == unique_id), None)

    def async_is_registered(self, entity_id):
        return entity_id in self.entities

    def async_update_entity(self, entity_id, new_entity_id):
        self.renamed.append((entity_id, new_entity_id))
        self.entities[new_entity_id] = self.entities.pop(entity_id)


def _hass(update, apps, entities=None):
    return types.SimpleNamespace(
        data={update.DOMAIN: {"entry1": apps}},
        entity_registry=_EntityRegistry(entities),
        states=types.SimpleNamespace(get=lambda entity_id: None),
    )


def _setup(update, hass):
    added: list = []
    asyncio.run(
        update.async_setup_entry(
            hass, types.SimpleNamespace(entry_id="entry1"), lambda entities: added.extend(entities)
        )
    )
    return added


def test_setup_skips_devices_without_an_esphome_link(monkeypatch):
    update = _import_update(monkeypatch)
    unlinked = _App()
    unlinked._ha_device_id = None

    added = _setup(update, _hass(update, {"kitchen": _App(), "hallway": unlinked}))

    assert [(type(e).__name__, e._dev_name) for e in added] == [
        ("NSPanelFirmwareUpdate", "kitchen"),
        ("NSPanelDisplayUpdate", "kitchen"),
    ]


FIRMWARE_UID = "entry1_kitchen_firmware_update"


def test_setup_reclaims_the_firmware_entity_id_once_esphome_dropped_its_entity(monkeypatch):
    update = _import_update(monkeypatch)
    hass = _hass(
        update, {"kitchen": _App()}, {"update.kitchen_haui_firmware_2": FIRMWARE_UID}
    )

    _setup(update, hass)

    assert hass.entity_registry.renamed == [
        ("update.kitchen_haui_firmware_2", "update.kitchen_haui_firmware")
    ]


@pytest.mark.parametrize(
    "entities",
    [
        pytest.param(
            {"update.kitchen_haui_firmware_2": FIRMWARE_UID, "update.kitchen_haui_firmware": None},
            id="esphome-entity-still-there",
        ),
        pytest.param({"update.kitchen_firmware": FIRMWARE_UID}, id="renamed-by-the-user"),
        pytest.param({}, id="new-entity"),
    ],
)
def test_setup_keeps_the_firmware_entity_id(monkeypatch, entities):
    update = _import_update(monkeypatch)
    hass = _hass(update, {"kitchen": _App()}, entities)

    _setup(update, hass)

    assert hass.entity_registry.renamed == []


# --- HAUI Firmware ------------------------------------------------------------


def _firmware(update, app=None):
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = update.NSPanelFirmwareUpdate(app or _App(), "kitchen", entry)
    entity.async_write_ha_state = lambda: None
    return entity


def _firmware_event(**data):
    payload = {
        "device": "kitchen",
        "connected": True,
        "installed_version": "0.4.3",
        "latest_version": "0.4.4",
        "installing": False,
    }
    payload.update(data)
    return types.SimpleNamespace(data=payload)


def test_firmware_event_sets_installed_and_latest_version(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _firmware(update)

    asyncio.run(entity._async_update_event(_firmware_event()))

    assert entity._attr_unique_id == FIRMWARE_UID
    assert entity._attr_installed_version == "0.4.3"
    assert entity._attr_latest_version == "0.4.4"
    assert entity._attr_available is True
    assert entity.in_progress is False


def test_firmware_install_keeps_the_entity_available_while_the_panel_reboots(monkeypatch):
    update = _import_update(monkeypatch)
    entity = _firmware(update)

    asyncio.run(entity._async_update_event(_firmware_event(connected=False, installing=True)))

    assert entity._attr_available is True
    assert entity.in_progress is True


def test_firmware_install_runs_the_hub_firmware_install(monkeypatch):
    update = _import_update(monkeypatch)
    app = _App()

    asyncio.run(_firmware(update, app).async_install(None, False))
    asyncio.run(_firmware(update, app).async_install("0.4.2", False))

    assert app.firmware_installs == [(None, None), ("0.4.2", None)]


def test_firmware_install_error_is_raised(monkeypatch):
    update = _import_update(monkeypatch)
    app = _App(firmware_result={"firmware_install_error": "No firmware update is available"})

    with pytest.raises(_HomeAssistantError, match="No firmware update is available"):
        asyncio.run(_firmware(update, app).async_install(None, False))


def test_added_firmware_entity_requests_the_current_state(monkeypatch):
    update = _import_update(monkeypatch)
    app = _App()
    entity = _firmware(update, app)
    entity.hass = types.SimpleNamespace(
        bus=types.SimpleNamespace(async_listen=lambda event, cb: lambda: None)
    )

    asyncio.run(entity.async_added_to_hass())

    assert app.dispatched == [app.publish_firmware_update]

"""Tests for the notify entity platform."""

from __future__ import annotations

import asyncio
import sys
import types


class _App:
    def __init__(self):
        self.queued: list = []
        self.sent: list = []
        notification = types.SimpleNamespace(add_notification=lambda **kw: self.sent.append(kw))
        self.controller = {"notification": notification}

    def dispatch(self, fn, *args):
        self.queued.append((fn, args))


def _import_notify(monkeypatch):
    notify_mod = types.ModuleType("homeassistant.components.notify")
    notify_mod.NotifyEntity = type("NotifyEntity", (), {})
    notify_mod.NotifyEntityFeature = types.SimpleNamespace(TITLE=1)
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.DeviceInfo = dict
    registry.async_get = lambda hass: hass.device_registry
    registry.async_entries_for_config_entry = lambda dev_reg, entry_id: dev_reg[entry_id]
    monkeypatch.setitem(sys.modules, "homeassistant.components.notify", notify_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers"], "device_registry", registry, raising=False
    )
    monkeypatch.delitem(sys.modules, "custom_components.nspanel_haui.notify", raising=False)
    from custom_components.nspanel_haui import notify

    return notify


def test_setup_names_the_device_after_the_panel(monkeypatch):
    notify = _import_notify(monkeypatch)
    app = _App()
    app._ha_device_id = "dev1"
    esphome_entry = types.SimpleNamespace(entry_id="esphome1", data={"device_name": "kitchen"})
    hass = types.SimpleNamespace(
        data={notify.DOMAIN: {"entry1": {"kitchen": app}}},
        config_entries=types.SimpleNamespace(
            async_entries=lambda domain: [esphome_entry] if domain == "esphome" else []
        ),
        device_registry={
            "esphome1": [types.SimpleNamespace(name="Kitchen Panel", name_by_user=None)]
        },
    )
    added: list = []

    asyncio.run(
        notify.async_setup_entry(hass, types.SimpleNamespace(entry_id="entry1"), added.extend)
    )

    assert [e._attr_device_info for e in added] == [
        {"identifiers": {(notify.DOMAIN, "kitchen")}, "name": "Kitchen Panel"}
    ] * 2


def test_message_is_queued_on_the_app_worker(monkeypatch):
    notify = _import_notify(monkeypatch)
    app = _App()
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = notify.NSPanelNotifyEntity(app, "kitchen", entry, device_name="Kitchen")

    asyncio.run(entity.async_send_message("Door open", title="Front"))

    assert app.sent == []
    ((fn, args),) = app.queued
    fn(*args)
    assert app.sent == [{"title": "Front", "message": "Door open", "persistent": False}]


def test_persistent_entity_leaves_force_show_to_the_controller(monkeypatch):
    notify = _import_notify(monkeypatch)
    app = _App()
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = notify.NSPanelNotifyEntity(
        app, "kitchen", entry, device_name="Kitchen", persistent=True
    )

    asyncio.run(entity.async_send_message("Door open", title="Front"))

    ((fn, args),) = app.queued
    fn(*args)
    assert app.sent == [{"title": "Front", "message": "Door open", "persistent": True}]

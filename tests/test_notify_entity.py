"""Tests for the notify entity platform."""

from __future__ import annotations

import asyncio
import sys
import types


class _App:
    def __init__(self):
        self.queued: list = []
        self.sent: list = []
        notification = types.SimpleNamespace(send_notification=lambda **kw: self.sent.append(kw))
        self.controller = {"notification": notification}

    def dispatch(self, fn, *args):
        self.queued.append((fn, args))


def _import_notify(monkeypatch):
    notify_mod = types.ModuleType("homeassistant.components.notify")
    notify_mod.NotifyEntity = type("NotifyEntity", (), {})
    notify_mod.NotifyEntityFeature = types.SimpleNamespace(TITLE=1)
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.DeviceInfo = dict
    monkeypatch.setitem(sys.modules, "homeassistant.components.notify", notify_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.delitem(sys.modules, "nspanel_haui.notify", raising=False)
    from nspanel_haui import notify

    return notify


def test_message_is_queued_on_the_app_worker(monkeypatch):
    notify = _import_notify(monkeypatch)
    app = _App()
    entry = types.SimpleNamespace(entry_id="entry1")
    entity = notify.NSPanelNotifyEntity(app, "kitchen", entry)

    asyncio.run(entity.async_send_message("Door open", title="Front"))

    assert app.sent == []
    ((fn, args),) = app.queued
    fn(*args)
    assert app.sent == [{"title": "Front", "message": "Door open", "persistent": False}]

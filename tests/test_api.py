"""Tests for the editor REST API views and config entry reload flow.

The HA stubs mirror the upstream behaviour the views rely on:
``require_admin`` raises ``Unauthorized`` for non-admin users, and
``HomeAssistantView.json`` returns a response carrying a status code.
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from functools import wraps
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlsplit

import pytest


class _Unauthorized(Exception):
    pass


def _install_ha_stubs() -> None:
    http_mod = types.ModuleType("homeassistant.helpers.http")

    class HomeAssistantView:
        def json(self, result: Any, status_code: int = 200) -> dict:
            return {"status_code": status_code, "body": result}

    http_mod.HomeAssistantView = HomeAssistantView

    exceptions_mod = types.ModuleType("homeassistant.exceptions")
    exceptions_mod.Unauthorized = _Unauthorized

    decorators_mod = types.ModuleType("homeassistant.components.http.decorators")

    def require_admin(func):
        @wraps(func)
        async def with_admin(self, request, *args, **kwargs):
            if not request["hass_user"].is_admin:
                raise sys.modules["homeassistant.exceptions"].Unauthorized()
            return await func(self, request, *args, **kwargs)

        return with_admin

    decorators_mod.require_admin = require_admin

    storage_mod = types.ModuleType("homeassistant.helpers.storage")
    storage_mod.Store = object

    for name, mod in {
        "homeassistant.helpers.http": http_mod,
        "homeassistant.exceptions": exceptions_mod,
        "homeassistant.components.http.decorators": decorators_mod,
        "homeassistant.helpers.storage": storage_mod,
    }.items():
        sys.modules.setdefault(name, mod)


_install_ha_stubs()

from custom_components.nspanel_haui import (  # noqa: E402
    _auto_add_unconfigured_devices,
    api,
    async_reload_entry,
    async_remove_config_entry_device,
)
from custom_components.nspanel_haui.hub import esphome_helpers, storage  # noqa: E402

# --- fakes -----------------------------------------------------------------


class _User:
    def __init__(self, is_admin: bool) -> None:
        self.is_admin = is_admin


class _Request(dict):
    def __init__(self, hass, *, admin: bool, body: Any = None, query: dict | None = None):
        super().__init__(hass_user=_User(admin))
        self.app = {"hass": hass}
        self.query = query or {}
        self._body = body

    async def json(self):
        return self._body

    async def text(self):
        return self._body


class _UploadBody:
    def __init__(self, *chunks: bytes) -> None:
        self.chunks = chunks

    async def iter_chunked(self, _size: int):
        for chunk in self.chunks:
            yield chunk


class _Entry:
    def __init__(self, data: dict) -> None:
        self.entry_id = "entry1"
        self.title = "Hub"
        self.data = data
        self.options: dict = {}


class _ConfigEntries:
    def __init__(self, entry: _Entry, events: list) -> None:
        self._entry = entry
        self._events = events
        self.updates: list[dict] = []
        self.scheduled_reloads: list[str] = []
        self.reloads: list[str] = []

    async def async_reload(self, entry_id):
        self.reloads.append(entry_id)

    def async_get_entry(self, entry_id):
        return self._entry if entry_id == self._entry.entry_id else None

    def async_update_entry(self, entry, data):
        self._events.append("update_entry")
        self.updates.append(data)

    def async_schedule_reload(self, entry_id):
        self.scheduled_reloads.append(entry_id)


class _Hass:
    def __init__(self, entry: _Entry) -> None:
        self.events: list[str] = []
        self.config_entries = _ConfigEntries(entry, self.events)
        self.data: dict = {"nspanel_haui": {}}
        self.config = types.SimpleNamespace(internal_url="http://ha.local:8123")
        self.created_tasks: list = []

    def async_create_task(self, coro):
        self.created_tasks.append(coro)
        coro.close()

    async def async_add_executor_job(self, fn, *args):
        return fn(*args)


def _fake_store(events: list, stored: dict | None = None, saved: list | None = None):
    class _Store:
        def __init__(self, hass, version, key):
            pass

        async def async_load(self):
            return stored

        async def async_save(self, data):
            events.append("store_save")
            if saved is not None:
                saved.append(data)

    return _Store


def _entry_with(*devices: dict) -> _Entry:
    return _Entry({"name": "Hub", "devices": [dict(d) for d in devices]})


# --- admin checks ----------------------------------------------------------


_PROTECTED = [
    (api.DeviceStatusView, "get", {"entry_id": "entry1"}),
    (api.NotificationsView, "get", {"entry_id": "entry1"}),
    (api.NotificationsView, "delete", {"entry_id": "entry1"}),
    (api.PanelConfigView, "get", {"entry_id": "entry1"}),
    (api.DeviceOrderView, "put", {"entry_id": "entry1"}),
    (api.ThemesView, "get", {"entry_id": "entry1"}),
    (api.ThemesView, "post", {"entry_id": "entry1"}),
    (api.DeviceConfigView, "get", {"entry_id": "entry1"}),
    (api.DeviceConfigView, "post", {"entry_id": "entry1"}),
    (api.DeviceConfigView, "delete", {"entry_id": "entry1"}),
    (api.DeviceSettingsView, "get", {"entry_id": "entry1", "device": "kitchen"}),
    (api.DeviceSettingsView, "put", {"entry_id": "entry1", "device": "kitchen"}),
    (api.DevicePanelsView, "put", {"entry_id": "entry1", "device": "kitchen"}),
    (api.DeviceYamlView, "get", {"entry_id": "entry1"}),
    (api.DeviceYamlView, "post", {"entry_id": "entry1"}),
    (api.DeviceRefreshDisplayView, "post", {"entry_id": "entry1"}),
    (api.DeviceUpdateTftView, "post", {"entry_id": "entry1"}),
    (api.DeviceTftReleasesView, "get", {"entry_id": "entry1"}),
    (api.DeviceUpdateFirmwareView, "post", {"entry_id": "entry1"}),
    (api.DeviceFirmwareReleasesView, "get", {"entry_id": "entry1"}),
]


@pytest.mark.parametrize(("view_cls", "method", "url_kwargs"), _PROTECTED)
def test_config_endpoints_reject_non_admin_users(view_cls, method, url_kwargs):
    hass = MagicMock()
    request = _Request(hass, admin=False, body={}, query={"name": "panel"})

    with pytest.raises(_Unauthorized):
        asyncio.run(getattr(view_cls(), method)(request, **url_kwargs))

    assert hass.mock_calls == []


class _NotificationController:
    def __init__(self, notifications):
        self.notifications = notifications

    def get_notifications(self):
        return list(self.notifications)

    def remove_notification(self, notification):
        self.notifications.remove(notification)
        return True


class _NotificationApp:
    def __init__(self, name, notifications):
        self.device = types.SimpleNamespace(get_name=lambda: name)
        self.controller = {"notification": _NotificationController(notifications)}

    async def async_run_on_worker(self, function, *args):
        return function(*args)


def test_notifications_view_returns_queued_notifications():
    notification = types.SimpleNamespace(
        title="Doorbell",
        message="Someone is here",
        icon="mdi:bell",
        persistent=True,
        icon_color="#4aa5ee",
        sound="alert",
        force_show=True,
        text_size=2,
        timeout=30,
        notif_id="a1",
    )
    app = _NotificationApp("kitchen", [notification])
    hass = types.SimpleNamespace(data={"nspanel_haui": {"entry1": {"kitchen": app}}})
    request = _Request(hass, admin=True, query={})

    result = asyncio.run(api.NotificationsView().get(request, entry_id="entry1"))

    assert result["body"] == [
        {
            "id": "a1",
            "device": "kitchen",
            "title": "Doorbell",
            "message": "Someone is here",
            "icon": "mdi:bell",
            "icon_color": "#4aa5ee",
            "sound": "alert",
            "persistent": True,
            "force_show": True,
            "text_size": 2,
            "timeout": 30,
        }
    ]


def test_notifications_view_dismisses_notification_on_worker():
    notification = types.SimpleNamespace(
        title="Doorbell",
        message="Someone is here",
        icon="mdi:bell",
        persistent=False,
        notif_id="b2",
    )
    app = _NotificationApp("kitchen", [notification])
    hass = types.SimpleNamespace(data={"nspanel_haui": {"entry1": {"kitchen": app}}})
    request = _Request(
        hass,
        admin=True,
        query={"device": "kitchen", "id": "b2"},
    )

    result = asyncio.run(api.NotificationsView().delete(request, entry_id="entry1"))

    assert result["body"] == {"status": "ok"}
    assert app.controller["notification"].notifications == []


# --- device add / delete ---------------------------------------------------


def test_add_device_saves_entry_data_and_leaves_reload_to_update_listener(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events))
    request = _Request(hass, admin=True, body={"devices": [{"name": "office"}]})

    result = asyncio.run(api.DeviceConfigView().post(request, entry_id="entry1"))

    assert result["body"]["devices_added"] == ["office"]
    assert [d["name"] for d in entry.data["devices"]] == ["kitchen"]
    (saved,) = hass.config_entries.updates
    assert saved["devices"] == [{"name": "kitchen"}, {"name": "office"}]
    assert hass.events == ["store_save", "update_entry"]
    assert hass.created_tasks == []


def test_add_device_keeps_identity_in_the_entry_and_settings_in_the_store(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    stored = {"version": 1, "devices": {"office": {"config": {"locale": "de_DE"}, "panels": []}}}
    saved = _use_store(monkeypatch, hass, stored)
    body = {"devices": [{"name": "office", "esphome_device_id": "e2", "enabled": False}]}

    asyncio.run(api.DeviceConfigView().post(_Request(hass, admin=True, body=body), "entry1"))

    (entry_data,) = hass.config_entries.updates
    assert entry_data["devices"][-1] == {"name": "office", "esphome_device_id": "e2"}
    # A re-added device whose settings are still stored keeps them.
    assert saved[0]["devices"]["office"]["config"] == {"locale": "de_DE", "enabled": False}


def test_delete_device_saves_entry_data_and_leaves_reload_to_update_listener(monkeypatch):
    entry = _entry_with({"name": "kitchen"}, {"name": "office"})
    hass = _Hass(entry)
    stored = {"version": 1, "devices": {"kitchen": {}, "office": {}}}
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events, stored))
    request = _Request(hass, admin=True, body={}, query={"name": "office"})

    asyncio.run(api.DeviceConfigView().delete(request, entry_id="entry1"))

    (saved,) = hass.config_entries.updates
    assert [d["name"] for d in saved["devices"]] == ["kitchen"]
    assert hass.events == ["store_save", "update_entry"]
    assert hass.created_tasks == []


# --- reload flow -----------------------------------------------------------


def test_update_listener_schedules_ha_managed_reload():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)

    asyncio.run(async_reload_entry(hass, entry))

    assert hass.config_entries.scheduled_reloads == ["entry1"]


def test_auto_add_records_new_devices_by_identity_without_mutating_entry_data(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)

    async def discover(_hass):
        return [{"name": "kitchen"}, {"name": "office", "esphome_device_id": "e2"}]

    monkeypatch.setattr(esphome_helpers, "discover_esphome_devices", discover)

    asyncio.run(_auto_add_unconfigured_devices(hass, entry))

    assert entry.data["devices"] == [{"name": "kitchen"}]
    (saved,) = hass.config_entries.updates
    assert saved["devices"] == [{"name": "kitchen"}, {"name": "office", "esphome_device_id": "e2"}]
    assert hass.config_entries.scheduled_reloads == []


def test_auto_add_leaves_a_known_device_alone(monkeypatch):
    # Disabling is a store setting the user chose; auto-add must not undo it.
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)

    async def discover(_hass):
        return [{"name": "kitchen"}]

    monkeypatch.setattr(esphome_helpers, "discover_esphome_devices", discover)

    asyncio.run(_auto_add_unconfigured_devices(hass, entry))

    assert hass.config_entries.updates == []


# --- translations ----------------------------------------------------------


@pytest.mark.parametrize("language", ["/etc/hass/secrets", "..", "de/../../x"])
def test_translations_view_rejects_path_like_language(language):
    hass = MagicMock()

    async def run_in_executor(fn, *args):
        return fn(*args)

    hass.async_add_executor_job = run_in_executor
    request = _Request(hass, admin=False)

    result = asyncio.run(api.TranslationsView().get(request, language=language))

    assert result["status_code"] == 400


def test_translations_accept_region_suffixed_language():
    from custom_components.nspanel_haui.haui.utils.text import get_translations

    assert get_translations("de-DE") is get_translations("de")
    assert get_translations("de_DE") is get_translations("de")


# --- removed devices stay removed ------------------------------------------


def test_delete_device_remembers_it_as_removed(monkeypatch):
    entry = _entry_with({"name": "kitchen"}, {"name": "office"})
    hass = _Hass(entry)
    stored = {"version": 1, "devices": {"kitchen": {}, "office": {}}}
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events, stored))
    request = _Request(hass, admin=True, body={}, query={"name": "office"})

    asyncio.run(api.DeviceConfigView().delete(request, entry_id="entry1"))

    (saved,) = hass.config_entries.updates
    assert saved["removed_devices"] == ["office"]


def test_deleting_device_on_hub_page_removes_it_from_hub(monkeypatch):
    entry = _entry_with({"name": "kitchen"}, {"name": "office"})
    hass = _Hass(entry)
    stored = {"version": 1, "devices": {"kitchen": {}, "office": {}}}
    saved_store: list = []
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events, stored, saved_store))
    device = types.SimpleNamespace(identifiers={("nspanel_haui", "office")})

    assert asyncio.run(async_remove_config_entry_device(hass, entry, device)) is True

    (saved,) = hass.config_entries.updates
    assert saved["devices"] == [{"name": "kitchen"}]
    assert saved["removed_devices"] == ["office"]
    assert saved_store == [{"version": 1, "devices": {"kitchen": {}}, "device_order": ["kitchen"]}]


def test_deleting_stale_device_on_hub_page_leaves_hub_untouched(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    stored = {"version": 1, "devices": {"kitchen": {}}}
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events, stored))
    device = types.SimpleNamespace(identifiers={("nspanel_haui", "office")})

    assert asyncio.run(async_remove_config_entry_device(hass, entry, device)) is True

    assert hass.config_entries.updates == []
    assert hass.events == []


def test_auto_add_skips_removed_devices(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    entry.data["removed_devices"] = ["office"]
    hass = _Hass(entry)

    async def discover(_hass):
        return [{"name": "kitchen"}, {"name": "office"}]

    monkeypatch.setattr(esphome_helpers, "discover_esphome_devices", discover)

    asyncio.run(_auto_add_unconfigured_devices(hass, entry))

    assert hass.config_entries.updates == []


def test_adding_a_removed_device_again_clears_it_from_removed(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    entry.data["removed_devices"] = ["office", "garage"]
    hass = _Hass(entry)
    monkeypatch.setattr(storage, "Store", _fake_store(hass.events))
    request = _Request(hass, admin=True, body={"devices": [{"name": "office"}]})

    asyncio.run(api.DeviceConfigView().post(request, entry_id="entry1"))

    (saved,) = hass.config_entries.updates
    assert [d["name"] for d in saved["devices"]] == ["kitchen", "office"]
    assert saved["removed_devices"] == ["garage"]


# --- panel save ------------------------------------------------------------


def _use_store(monkeypatch, hass, stored=None):
    saved: list = []
    store = _fake_store(hass.events, stored, saved)
    monkeypatch.setattr(storage, "Store", store)
    return saved


def test_disabling_a_device_from_the_editor_reloads_the_entry(monkeypatch):
    entry = _entry_with({"name": "kitchen"}, {"name": "office"})
    hass = _Hass(entry)
    _use_store(
        monkeypatch,
        hass,
        {
            "version": 1,
            "devices": {
                "kitchen": {"config": {"enabled": True}, "panels": []},
                "office": {"config": {"enabled": True}, "panels": []},
            },
        },
    )
    kitchen_app = MagicMock()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": kitchen_app}

    result = asyncio.run(
        api.DeviceSettingsView().put(
            _Request(hass, admin=True, body={"config": {"enabled": False}}),
            "entry1",
            "kitchen",
        )
    )

    assert result["body"]["reloaded"] is True
    assert hass.config_entries.scheduled_reloads == ["entry1"]
    assert list(hass.data["nspanel_haui"]["entry1"]) == ["kitchen"]


def test_device_settings_get_migrates_legacy_keys_and_returns_one_device(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {"sleep_panel": "clock"}}}},
    )

    result = asyncio.run(
        api.DeviceSettingsView().get(_Request(hass, admin=True), "entry1", "kitchen")
    )

    assert result["body"] == {"device": "kitchen", "config": {"idle_panel": "clock"}}


def test_device_settings_get_returns_404_for_unknown_device(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)

    result = asyncio.run(
        api.DeviceSettingsView().get(_Request(hass, admin=True), "entry1", "missing")
    )

    assert result["status_code"] == 404


def test_device_settings_put_changes_only_the_addressed_config(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    old = {
        "version": 1,
        "device_order": ["kitchen", "office"],
        "devices": {
            "kitchen": {
                "config": {"locale": "en_US"},
                "panels": [{"type": "clock", "key": "k-clock"}],
                "last_panel_update": "2025-01-01T00:00:00+00:00",
            },
            "office": {
                "config": {"locale": "fr_FR"},
                "panels": [{"type": "grid", "key": "o-grid"}],
                "last_panel_update": "2025-02-01T00:00:00+00:00",
            },
        },
    }
    saved = _use_store(monkeypatch, hass, old)

    result = asyncio.run(
        api.DeviceSettingsView().put(
            _Request(hass, admin=True, body={"config": {"locale": "de_DE", "ignored": True}}),
            "entry1",
            "kitchen",
        )
    )

    assert result["status_code"] == 200
    (written,) = saved
    assert written["devices"]["kitchen"]["config"] == {"locale": "de_DE"}
    assert written["devices"]["kitchen"]["panels"] == old["devices"]["kitchen"]["panels"]
    assert (
        written["devices"]["kitchen"]["last_panel_update"]
        == old["devices"]["kitchen"]["last_panel_update"]
    )
    assert written["devices"]["office"] == old["devices"]["office"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"config": {"locale": None}},
        {"config": {"theme_id": "not-a-theme"}},
        {"config": {"brightness": 101}},
    ],
)
def test_device_settings_put_rejects_invalid_or_missing_config(monkeypatch, body):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )

    result = asyncio.run(
        api.DeviceSettingsView().put(_Request(hass, admin=True, body=body), "entry1", "kitchen")
    )

    assert result["status_code"] == 400
    assert saved == []


def test_device_panels_put_replaces_only_one_device_and_reloads_only_its_app(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    old = {
        "version": 1,
        "devices": {
            "kitchen": {
                "config": {"locale": "de_DE"},
                "panels": [],
                "last_panel_update": "old-kitchen",
            },
            "office": {
                "config": {"locale": "fr_FR"},
                "panels": [{"type": "clock", "key": "office"}],
                "last_panel_update": "old-office",
            },
        },
    }
    saved = _use_store(monkeypatch, hass, old)
    kitchen = _WorkerApp()
    office = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": kitchen, "office": office}
    panels = [{"type": "clock", "key": "new-kitchen"}]

    result = asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": panels}), "entry1", "kitchen"
        )
    )

    assert result["status_code"] == 200
    (written,) = saved
    assert written["devices"]["kitchen"]["panels"] == panels
    assert written["devices"]["kitchen"]["config"] == old["devices"]["kitchen"]["config"]
    assert written["devices"]["kitchen"]["last_panel_update"] != "old-kitchen"
    assert written["devices"]["office"] == old["devices"]["office"]
    assert kitchen.calls == ["worker", "reload_config"]
    assert office.calls == []


def test_device_panels_put_rejects_missing_panels_and_unknown_devices(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )

    missing = asyncio.run(
        api.DevicePanelsView().put(_Request(hass, admin=True, body={}), "entry1", "kitchen")
    )
    unknown = asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": []}), "entry1", "missing"
        )
    )

    assert missing["status_code"] == 400
    assert unknown["status_code"] == 404
    assert saved == []


def test_device_panels_put_names_the_field_that_breaks_a_rule(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )
    light = {"type": "light", "key": "light_0", "item": {"item": "sensor.x"}}

    result = asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": [light]}), "entry1", "kitchen"
        )
    )

    assert result["status_code"] == 400
    assert result["body"]["errors"][0]["panel"] == "light_0"
    assert result["body"]["errors"][0]["field"] == "item"
    assert saved == []


def test_device_panels_put_keeps_an_unchanged_stored_panel(monkeypatch):
    light = {"type": "light", "key": "light_0", "item": {"item": "sensor.x"}}
    hass = _Hass(_entry_with({"name": "kitchen"}))
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _WorkerApp()}
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": [light]}}},
    )
    panels = [light, {"type": "clock", "key": "clock_0"}]

    result = asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": panels}), "entry1", "kitchen"
        )
    )

    assert result["status_code"] == 200
    assert saved[0]["devices"]["kitchen"]["panels"] == panels


def test_device_panels_put_rejects_unknown_panel_theme(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )

    result = asyncio.run(
        api.DevicePanelsView().put(
            _Request(
                hass,
                admin=True,
                body={"panels": [{"type": "clock", "key": "clock", "theme_id": "missing"}]},
            ),
            "entry1",
            "kitchen",
        )
    )

    assert result["status_code"] == 400
    assert saved == []


def test_device_order_put_normalizes_without_pushing_or_reloading(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {
            "version": 1,
            "devices": {
                "kitchen": {"config": {}, "panels": []},
                "office": {"config": {}, "panels": []},
            },
        },
    )

    result = asyncio.run(
        api.DeviceOrderView().put(
            _Request(hass, admin=True, body={"device_order": ["office", "missing", "office"]}),
            "entry1",
        )
    )

    assert result["body"]["device_order"] == ["office", "kitchen"]
    assert saved[0]["device_order"] == ["office", "kitchen"]
    assert hass.events == ["store_save"]
    assert hass.config_entries.scheduled_reloads == []
    assert hass.config_entries.reloads == []


def _custom_theme(name="Evening"):
    from copy import deepcopy

    from custom_components.nspanel_haui.haui.mapping.color import BUILTIN_THEMES

    theme = deepcopy(BUILTIN_THEMES["dark"])
    theme["name"] = name
    return theme


def test_theme_library_round_trips_without_panel_push(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass, {"version": 1, "devices": {}})
    body = {"version": 1, "themes": {"evening": _custom_theme()}}

    result = asyncio.run(api.ThemesView().post(_Request(hass, admin=True, body=body), "entry1"))

    assert result["body"]["themes"] == body["themes"]
    assert saved[0]["themes"] == body["themes"]
    assert saved[0]["devices"] == {}
    assert hass.events == ["store_save"]


def test_theme_library_rejects_invalid_rgb565_values(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass)
    theme = _custom_theme()
    theme["colors"]["background"] = 65536
    result = asyncio.run(
        api.ThemesView().post(
            _Request(hass, admin=True, body={"version": 1, "themes": {"bad": theme}}),
            "entry1",
        )
    )
    assert result["status_code"] == 400
    assert saved == []


def test_theme_library_cannot_remove_a_theme_selected_by_a_device(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    stored = {
        "version": 1,
        "devices": {"kitchen": {"config": {"theme_id": "evening"}, "panels": []}},
        "themes": {"evening": _custom_theme()},
    }
    saved = _use_store(monkeypatch, hass, stored)

    result = asyncio.run(
        api.ThemesView().post(
            _Request(hass, admin=True, body={"version": 1, "themes": {}}), "entry1"
        )
    )

    assert result["status_code"] == 409
    assert saved == []


def test_theme_library_cannot_remove_a_theme_selected_only_by_a_panel(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    stored = {
        "version": 1,
        "devices": {
            "kitchen": {
                "config": {},
                "panels": [{"type": "clock", "key": "clock", "theme_id": "evening"}],
            }
        },
        "themes": {"evening": _custom_theme()},
    }
    saved = _use_store(monkeypatch, hass, stored)

    result = asyncio.run(
        api.ThemesView().post(
            _Request(hass, admin=True, body={"version": 1, "themes": {}}), "entry1"
        )
    )

    assert result["status_code"] == 409
    assert saved == []


def test_device_settings_put_rejects_empty_config_values(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(
        monkeypatch, hass, {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}}
    )

    result = asyncio.run(
        api.DeviceSettingsView().put(
            _Request(hass, admin=True, body={"config": {"locale": None}}),
            "entry1",
            "kitchen",
        )
    )

    assert result["status_code"] == 400
    assert saved == []


def test_panel_save_rejects_edits_of_fixed_system_panels(monkeypatch):
    """Only popups can be edited; a panel under the Settings key is refused."""
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )
    panels = [{"type": "system_settings", "key": "sys_settings", "show_in_navigation": False}]

    result = asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": panels}), "entry1", "kitchen"
        )
    )

    assert result["status_code"] == 400
    assert saved == []


def test_device_yaml_export_includes_the_selected_custom_theme_definition():
    from custom_components.nspanel_haui.api.config import _device_yaml_data

    custom = _custom_theme()
    device = {"config": {"theme_id": "evening"}, "panels": []}
    data = {"themes": {"evening": custom}}

    exported = _device_yaml_data(device, data)

    assert exported["theme_definition"] == {
        "id": "evening",
        **custom,
    }


def test_device_yaml_export_includes_panel_theme_definitions():
    from custom_components.nspanel_haui.api.config import _device_yaml_data

    custom = _custom_theme()
    exported = _device_yaml_data(
        {
            "config": {"theme_id": "dark"},
            "panels": [
                {"type": "clock", "key": "clock", "theme_id": "evening"},
                {"type": "grid", "key": "grid", "theme_id": ""},
            ],
        },
        {"themes": {"evening": custom}},
    )

    assert exported["theme_definitions"] == [{"id": "evening", **custom}]


def test_device_yaml_import_restores_custom_theme_definition(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass, {"version": 1, "devices": {}})
    import yaml

    theme = _custom_theme()
    body = yaml.safe_dump(
        {
            "config": {"theme_id": "evening"},
            "panels": [],
            "theme_definition": {"id": "evening", **theme},
        },
        sort_keys=False,
    )
    request = _Request(hass, admin=True, body=body, query={"device": "kitchen"})

    result = asyncio.run(api.DeviceYamlView().post(request, entry_id="entry1"))

    assert result["body"]["device"] == "kitchen"
    assert saved[0]["themes"]["evening"] == theme
    assert saved[0]["devices"]["kitchen"]["config"]["theme_id"] == "evening"


def test_device_yaml_import_restores_custom_themes_used_by_panels(monkeypatch):
    import yaml

    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(monkeypatch, hass, {"version": 1, "devices": {}})
    theme = _custom_theme()
    body = yaml.safe_dump(
        {
            "config": {"theme_id": "dark"},
            "panels": [{"type": "clock", "key": "clock", "theme_id": "evening"}],
            "theme_definitions": [{"id": "evening", **theme}],
        },
        sort_keys=False,
    )

    result = asyncio.run(
        api.DeviceYamlView().post(
            _Request(hass, admin=True, body=body, query={"device": "kitchen"}),
            entry_id="entry1",
        )
    )

    assert result["status_code"] == 200
    assert saved[0]["themes"]["evening"] == theme
    assert saved[0]["devices"]["kitchen"]["panels"][0]["theme_id"] == "evening"


def test_yaml_import_rejects_empty_config_values(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass)
    body = "config:\n  button_left_entity:\npanels: []\n"
    request = _Request(hass, admin=True, body=body, query={"device": "kitchen"})

    result = asyncio.run(api.DeviceYamlView().post(request, entry_id="entry1"))

    assert result["status_code"] == 400
    assert saved == []


def test_yaml_import_rejects_wrapped_device_yaml(monkeypatch):
    """YAML wrapped under the device name is no longer accepted."""
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    body = "kitchen:\n  config: {}\n  panels: []\n"
    request = _Request(hass, admin=True, body=body, query={"device": "kitchen"})

    result = asyncio.run(api.DeviceYamlView().post(request, entry_id="entry1"))

    assert result["status_code"] == 400
    assert result["body"]["message"].startswith("YAML must contain")


def test_push_panels_with_legacy_single_app_does_not_reload(monkeypatch):
    """A non-dict apps value (pre-multi-device format) is never reloaded."""
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    hass.data["nspanel_haui"]["entry1"] = _WorkerApp()

    result = asyncio.run(api.config.push_panels(hass, "entry1", {"version": 1, "devices": {}}))

    assert result == {"status": "ok"}
    assert hass.config_entries.reloads == []
    assert hass.config_entries.scheduled_reloads == []


def test_removing_the_hub_deletes_its_panel_store(monkeypatch):
    from custom_components.nspanel_haui import async_remove_entry

    removed: list[str] = []

    class _Store:
        def __init__(self, hass, version, key):
            self.key = key

        async def async_remove(self):
            removed.append(self.key)

    monkeypatch.setattr(storage, "Store", _Store)
    entry = _entry_with({"name": "kitchen"})

    asyncio.run(async_remove_entry(_Hass(entry), entry))

    assert removed == ["nspanel_haui.entry1_panels"]


# --- app work runs on the app's worker -------------------------------------


class _WorkerApp:
    device_config = {"device": {}}

    def __init__(self):
        self.calls: list[str] = []

    def reload_config(self, cfg):
        self.calls.append("reload_config")
        self.cfg = cfg

    def refresh_display(self):
        self.calls.append("refresh_display")

    def install_tft(self, version=None):
        self.calls.append(("install_tft", version))

    def install_tft_url(self, url):
        self.calls.append(("install_tft_url", url))

    def list_tft_releases(self):
        self.calls.append("list_tft_releases")
        return {"releases": ["v0.4.2", "v0.4.1"], "required": "0.4.2", "error": None}

    def install_firmware(self, version=None, url=None):
        self.calls.append(("install_firmware", version, url))
        return {"firmware_installing": True, "firmware_install_error": None}

    def list_firmware_releases(self):
        self.calls.append("list_firmware_releases")
        return {"releases": ["v0.4.3", "v0.4.2"], "error": None}

    async def async_run_on_worker(self, fn, *args):
        self.calls.append("worker")
        return fn(*args)

    async def async_list_tft_releases(self):
        self.calls.append("async_list_tft_releases")
        return self.list_tft_releases()

    async def async_list_firmware_releases(self):
        self.calls.append("async_list_firmware_releases")
        return self.list_firmware_releases()

    async def async_check_for_update(self):
        self.calls.append("async_check_for_update")
        return {"latest_release": "0.4.3", "check_error": None}

    async def async_install_tft(self, version=None, url=None):
        fn = self.install_tft_url if url is not None else self.install_tft
        args = (url,) if url is not None else (version,)
        return await self.async_run_on_worker(fn, *args)

    async def async_install_firmware(self, version=None, url=None):
        return await self.async_run_on_worker(self.install_firmware, version, url)

    def submit_off_worker(self, fn, *args, on_done=None):
        try:
            result = fn(*args)
        except BaseException as exc:
            on_done(None, exc)
        else:
            on_done(result, None)


def test_per_device_saves_reload_a_running_device_on_its_worker(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}},
    )
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": [{"type": "clock"}]}),
            "entry1",
            "kitchen",
        )
    )
    assert app.calls == ["worker", "reload_config"]
    assert app.cfg["device"]["locale"] == "en_US"

    asyncio.run(
        api.DeviceSettingsView().put(
            _Request(hass, admin=True, body={"config": {"locale": "de_DE"}}),
            "entry1",
            "kitchen",
        )
    )
    assert app.calls == ["worker", "reload_config", "worker", "reload_config"]
    assert app.cfg["device"]["locale"] == "de_DE"
    assert app.cfg["device"]["timeout_display_off"] == 120


def test_display_refresh_runs_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    asyncio.run(api.DeviceRefreshDisplayView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", "refresh_display"]


def _upload_request(hass, *, kind: str, filename: str, image: bytes, device: str = "kitchen"):
    request = _Request(
        hass,
        admin=True,
        query={"device": device, "filename": filename},
    )
    request.content = _UploadBody(image)
    request.content_length = len(image)
    request.headers = {}
    return request


def test_local_tft_upload_stages_a_range_readable_file_and_starts_install():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    image = b"\x00\x01DN2E" + bytes(range(20))

    result = asyncio.run(
        api.DeviceUpdateUploadView().post(
            _upload_request(hass, kind="tft", filename="panel.tft", image=image),
            entry_id="entry1",
            kind="tft",
        )
    )

    assert result["status_code"] == 200
    assert app.calls[0] == "worker"
    _, staged_url = app.calls[1]
    assert staged_url.startswith("http://ha.local:8123/api/nspanel_haui/update_artifact/")
    token = urlsplit(staged_url).path.rsplit("/", 1)[-1]
    artifacts = hass.data[api.updates._UPLOADS_KEY]
    assert artifacts[token].content == image

    request = types.SimpleNamespace(
        app={"hass": hass},
        match_info={"token": token},
        headers={"Range": "bytes=3-8"},
    )
    ranged = asyncio.run(api.DeviceUpdateArtifactView().get(request, token=token))
    repeated = asyncio.run(
        api.DeviceUpdateArtifactView().get(
            types.SimpleNamespace(app={"hass": hass}, match_info={"token": token}, headers={}),
            token=token,
        )
    )
    assert ranged.status == 206
    assert ranged.headers["Content-Range"] == f"bytes 3-8/{len(image)}"
    assert ranged.body == image[3:9]
    assert repeated.status == 200
    assert repeated.body == image


def test_local_firmware_upload_uses_existing_firmware_install_path():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    image = b"\xe9" + bytes(range(64))

    result = asyncio.run(
        api.DeviceUpdateUploadView().post(
            _upload_request(hass, kind="firmware", filename="ota.bin", image=image),
            entry_id="entry1",
            kind="firmware",
        )
    )

    assert result["status_code"] == 200
    assert app.calls[0] == "worker"
    assert app.calls[1][0:2] == ("install_firmware", None)
    assert app.calls[1][2].startswith("http://ha.local:8123/api/nspanel_haui/update_artifact/")
    token = urlsplit(app.calls[1][2]).path.rsplit("/", 1)[-1]
    assert hass.data[api.updates._UPLOADS_KEY][token].content == image


def test_local_tft_upload_ignores_the_error_of_an_earlier_attempt():
    """``last_error`` outlives a failed attempt; a started upload keeps its file."""
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()

    async def install_started(version=None, url=None):
        return {"state": "installing", "last_error": "previous attempt failed"}

    app.async_install_tft = install_started
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    image = b"\x00\x01DN2E" + bytes(range(20))

    result = asyncio.run(
        api.DeviceUpdateUploadView().post(
            _upload_request(hass, kind="tft", filename="panel.tft", image=image),
            entry_id="entry1",
            kind="tft",
        )
    )

    assert result["status_code"] == 200
    assert len(hass.data[api.updates._UPLOADS_KEY]) == 1


@pytest.mark.parametrize("view", [api.DeviceUpdateFirmwareView, api.DeviceUpdateTftView])
def test_an_unreadable_install_body_installs_nothing(view):
    """A malformed body must not fall back to "install on every device"."""

    class _BadJsonRequest(_Request):
        async def json(self):
            raise ValueError("not JSON")

    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = asyncio.run(view().post(_BadJsonRequest(hass, admin=True), entry_id="entry1"))

    assert result["status_code"] == 400
    assert app.calls == []


def test_register_views_registers_every_view():
    registered: list = []
    hass = types.SimpleNamespace(http=types.SimpleNamespace(register_view=registered.append))

    api.register_views(hass)

    assert [type(view) for view in registered] == list(api.VIEWS)
    assert len({view.url for view in registered}) == len(api.VIEWS)


@pytest.mark.parametrize(
    ("kind", "filename", "image", "device", "content_length", "status"),
    [
        ("other", "panel.tft", b"\x00\x01DN2E" + bytes(16), "kitchen", None, 400),
        ("tft", "panel.bin", b"\x00\x01DN2E" + bytes(16), "kitchen", None, 400),
        ("tft", "panel.tft", b"not a TFT image" + bytes(5), "kitchen", None, 400),
        ("firmware", "firmware.bin", b"not an image", "kitchen", None, 400),
        ("tft", "panel.tft", b"\x00\x01DN2E" + bytes(16), "*", None, 400),
        ("tft", "panel.tft", b"\x00\x01DN2E" + bytes(16), "missing", None, 404),
        ("firmware", "firmware.bin", b"\xe9", "kitchen", api.updates.FIRMWARE_MAX_BYTES + 1, 413),
    ],
    ids=[
        "unknown-kind",
        "wrong-extension",
        "bad-tft-signature",
        "bad-firmware-magic",
        "all-devices",
        "unknown-device",
        "too-large",
    ],
)
def test_local_update_upload_rejects_invalid_input(
    kind, filename, image, device, content_length, status
):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _upload_request(hass, kind=kind, filename=filename, image=image, device=device)
    if content_length is not None:
        request.content_length = content_length

    result = asyncio.run(api.DeviceUpdateUploadView().post(request, entry_id="entry1", kind=kind))

    assert result["status_code"] == status
    assert app.calls == []
    assert not hass.data.get(api.updates._UPLOADS_KEY)


def test_local_update_upload_requires_a_configured_internal_url():
    hass = _Hass(_entry_with({"name": "kitchen"}))
    hass.config.internal_url = None
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _upload_request(
        hass, kind="tft", filename="panel.tft", image=b"\x00\x01DN2E" + bytes(16)
    )

    result = asyncio.run(api.DeviceUpdateUploadView().post(request, entry_id="entry1", kind="tft"))

    assert result["status_code"] == 400
    assert "internal URL" in result["body"]["message"]
    assert app.calls == []


def test_staged_update_download_supports_head_and_expires():
    hass = _Hass(_entry_with({"name": "kitchen"}))
    token = "secret"
    hass.data[api.updates._UPLOADS_KEY] = {
        token: api.updates._StagedUpdate(b"\xe9image", time.monotonic() + 60)
    }
    request = types.SimpleNamespace(app={"hass": hass}, match_info={"token": token}, headers={})

    head = asyncio.run(api.DeviceUpdateArtifactView().head(request, token=token))
    request.headers = {"Range": "bytes=100-"}
    invalid_range = asyncio.run(api.DeviceUpdateArtifactView().get(request, token=token))
    hass.data[api.updates._UPLOADS_KEY][token].expires_at = 0
    expired = asyncio.run(api.DeviceUpdateArtifactView().get(request, token=token))

    assert head.status == 200
    assert head.body == b""
    assert head.headers["Content-Length"] == "6"
    assert invalid_range.status == 416
    assert expired.status == 404


def test_local_update_upload_requires_admin():
    request = _Request(MagicMock(), admin=False, query={})
    with pytest.raises(_Unauthorized):
        asyncio.run(api.DeviceUpdateUploadView().post(request, entry_id="entry1", kind="tft"))


def test_firmware_install_runs_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = asyncio.run(
        api.DeviceUpdateFirmwareView().post(
            _Request(hass, admin=True, body={"device": "kitchen"}), entry_id="entry1"
        )
    )

    assert app.calls == ["worker", ("install_firmware", None, None)]
    assert result["status_code"] == 200
    assert result["body"]["devices_updated"] == ["kitchen"]


def test_firmware_install_reports_controller_errors():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    app.install_firmware = lambda version, url: {
        "firmware_installing": False,
        "firmware_install_error": "No firmware update is available",
    }
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = asyncio.run(
        api.DeviceUpdateFirmwareView().post(
            _Request(hass, admin=True, body={"device": "kitchen"}), entry_id="entry1"
        )
    )

    assert result["status_code"] == 502
    assert result["body"]["message"] == "No firmware update is available"


@pytest.mark.parametrize(
    ("body", "call"),
    [
        pytest.param(
            {"device": "kitchen", "version": "v0.4.2"},
            ("install_firmware", "v0.4.2", None),
            id="release",
        ),
        pytest.param(
            {"device": "kitchen", "url": "http://ha.local/firmware.ota.bin"},
            ("install_firmware", None, "http://ha.local/firmware.ota.bin"),
            id="url",
        ),
    ],
)
def test_firmware_install_passes_the_chosen_release_or_url(body, call):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    asyncio.run(
        api.DeviceUpdateFirmwareView().post(
            _Request(hass, admin=True, body=body), entry_id="entry1"
        )
    )

    assert app.calls == ["worker", call]


@pytest.mark.parametrize(
    "body",
    [
        {"device": "*", "url": "http://ha.local/firmware.ota.bin"},
        {"device": "kitchen", "url": "file:///firmware.ota.bin"},
        {"device": "kitchen", "url": "http://ha.local/firmware.ota.bin", "version": "v0.4.2"},
    ],
    ids=["all-devices", "not-http", "with-version"],
)
def test_firmware_install_rejects_an_unusable_url(body):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = asyncio.run(
        api.DeviceUpdateFirmwareView().post(
            _Request(hass, admin=True, body=body), entry_id="entry1"
        )
    )

    assert result["status_code"] == 400
    assert app.calls == []


def test_firmware_releases_are_listed_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, query={"device": "kitchen"})

    result = asyncio.run(api.DeviceFirmwareReleasesView().get(request, entry_id="entry1"))

    assert app.calls == ["async_list_firmware_releases", "list_firmware_releases"]
    assert result["body"]["releases"] == ["v0.4.3", "v0.4.2"]


def test_manual_update_check_uses_the_staged_async_api():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    result = asyncio.run(api.DeviceUpdateCheckView().post(request, entry_id="entry1"))

    assert app.calls == ["async_check_for_update"]
    assert result["body"]["results"]["kitchen"]["latest_release"] == "0.4.3"


def test_tft_install_runs_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    # A missing version is passed as None; the controller replaces it with the
    # firmware's yaml_version when the install runs.
    assert app.calls == ["worker", ("install_tft", None)]


def test_tft_install_rejects_invalid_json():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True)

    async def invalid_json():
        raise ValueError("malformed")

    request.json = invalid_json
    result = asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert result["status_code"] == 400
    assert result["body"]["message"] == "Invalid JSON request body"
    assert app.calls == []


def test_tft_install_passes_the_requested_version():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen", "version": "0.4.0"})

    asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", ("install_tft", "0.4.0")]


def test_tft_install_passes_the_requested_url():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen", "url": "http://ha.local/x.tft"})

    asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", ("install_tft_url", "http://ha.local/x.tft")]


@pytest.mark.parametrize(
    "body",
    [
        {"device": "*", "url": "http://ha.local/x.tft"},
        {"device": "kitchen", "url": "ftp://ha.local/x.tft"},
        {"device": "kitchen", "url": "http://ha.local/x.tft", "version": "0.4.1"},
    ],
    ids=["all-devices", "not-http", "with-version"],
)
def test_tft_install_rejects_an_unusable_url(body):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = asyncio.run(
        api.DeviceUpdateTftView().post(_Request(hass, admin=True, body=body), entry_id="entry1")
    )

    assert result["status_code"] == 400
    assert app.calls == []


def test_tft_releases_are_listed_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, query={"device": "kitchen"})

    result = asyncio.run(api.DeviceTftReleasesView().get(request, entry_id="entry1"))

    assert app.calls == ["async_list_tft_releases", "list_tft_releases"]
    assert result["body"]["releases"] == ["v0.4.2", "v0.4.1"]


def test_tft_install_includes_the_update_state_in_the_response():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    state = {"state": "installing", "version": "0.4.1", "started_at": "t", "last_error": None}
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _StatefulTftApp(state)}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    result = asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert result["status_code"] == 200
    assert result["body"]["devices_updated"] == ["kitchen"]
    assert result["body"]["update"] == state


class _StatefulTftApp(_WorkerApp):
    """A worker app whose install_tft reports the controller's update state."""

    def __init__(self, state: dict):
        super().__init__()
        self._state = state

    def install_tft(self, version=None):
        self.calls.append(("install_tft", version))
        return self._state


def test_tft_install_reports_why_it_could_not_start():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    state = {
        "state": "error",
        "version": "0.4.1",
        "started_at": None,
        "last_error": "device disconnected",
    }
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _StatefulTftApp(state)}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    result = asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    # A failed TFT install must surface the reason instead of pretending the
    # install started (the success path used to be shown unconditionally).
    assert result["status_code"] == 502
    assert result["body"]["status"] == "error"
    assert result["body"]["message"] == "device disconnected"


def test_tft_install_reports_a_publish_failure():
    """A publish that could not reach the device is a 502, not a silent success.

    The upload command must reach the ESP32 for the install to happen; when
    the ESPHome publish call fails the controller records an error state that
    the API must surface exactly like the other install failures.
    """
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    state = {
        "state": "error",
        "version": "0.4.1",
        "started_at": None,
        "last_error": "Could not send the TFT upload command; check the ESPHome connection",
    }
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _StatefulTftApp(state)}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    result = asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert result["status_code"] == 502
    assert "could not send" in (result["body"]["message"] or "").lower()


def test_tft_install_all_devices_reports_failures_separately():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    hass.data["nspanel_haui"]["entry1"] = {
        "kitchen": _WorkerApp(),
        "office": _StatefulTftApp(
            {
                "state": "error",
                "version": None,
                "started_at": None,
                "last_error": "no yaml_version reported",
            }
        ),
    }
    request = _Request(hass, admin=True, body={"device": "*"})

    result = asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert result["status_code"] == 200
    assert result["body"]["devices_updated"] == ["kitchen"]
    assert result["body"]["failed"] == [{"name": "office", "error": "no yaml_version reported"}]


# --- YAML import pushes like a panel save ----------------------------------

_YAML = "config:\n  enabled: {enabled}\npanels: []\n"


def _import_yaml(hass, device="kitchen", enabled="true"):
    request = _Request(
        hass, admin=True, body=_YAML.format(enabled=enabled), query={"device": device}
    )
    return asyncio.run(api.DeviceYamlView().post(request, entry_id="entry1"))


def test_yaml_import_pushes_to_running_apps_in_place(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = _import_yaml(hass)

    assert result["body"] == {"status": "ok", "device": "kitchen"}
    assert app.calls == ["worker", "reload_config"]
    assert hass.config_entries.scheduled_reloads == []


def test_yaml_import_that_disables_a_running_device_reloads_the_entry(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = _import_yaml(hass, enabled="false")

    assert result["body"]["reloaded"] is True
    assert hass.config_entries.scheduled_reloads == ["entry1"]
    assert app.calls == []


def test_yaml_import_that_enables_a_new_device_reloads_the_entry(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    _use_store(monkeypatch, hass)
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _WorkerApp()}
    stored = {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}}
    _use_store(monkeypatch, hass, stored)

    _import_yaml(hass, device="office")

    assert hass.config_entries.scheduled_reloads == ["entry1"]


def test_yaml_import_without_running_apps_reloads_the_entry(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    hass.data["nspanel_haui"]["entry1"] = {}

    result = _import_yaml(hass)

    assert result["body"]["reloaded"] is True
    assert hass.config_entries.reloads == ["entry1"]


def test_yaml_import_before_entry_setup_only_saves(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(monkeypatch, hass)

    result = _import_yaml(hass)

    assert result["body"] == {"status": "ok", "device": "kitchen"}
    assert saved[0]["devices"]["kitchen"]["last_panel_update"]


# --- device add accepts only the batch body --------------------------------


@pytest.mark.parametrize("body", [{"name": "office"}, {}, {"devices": "office"}, None])
def test_add_device_rejects_a_body_without_a_devices_list(monkeypatch, body):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)

    result = asyncio.run(
        api.DeviceConfigView().post(_Request(hass, admin=True, body=body), entry_id="entry1")
    )

    assert result["status_code"] == 400
    assert "devices" in result["body"]["message"]
    assert hass.config_entries.updates == []


def test_panel_save_with_a_store_only_device_does_not_reload(monkeypatch):
    # "office" has settings in the store but no config-entry record.
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(
        monkeypatch,
        hass,
        {
            "version": 1,
            "devices": {
                "kitchen": {"config": {}, "panels": []},
                "office": {"config": {}, "panels": []},
            },
        },
    )
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    asyncio.run(
        api.DevicePanelsView().put(
            _Request(hass, admin=True, body={"panels": []}), "entry1", "kitchen"
        )
    )

    assert hass.config_entries.scheduled_reloads == []
    assert app.calls == ["worker", "reload_config"]


@pytest.mark.parametrize("active", [False, True], ids=["disabled-device", "running-device"])
def test_device_status_reads_wifi_fields_from_the_device_registry(monkeypatch, active):
    device_id = "ha-device-1"
    entity_ids = {
        "IP": "sensor.upstairs_panel_ip",
        "SSID": "sensor.upstairs_panel_ssid",
        "RSSI": "sensor.upstairs_panel_rssi",
        "Temperature": "sensor.upstairs_panel_temperature",
        "Brightness Full": "number.upstairs_panel_brightness_full",
        "Brightness Dimmed": "number.upstairs_panel_brightness_dimmed",
    }
    domains = {
        "Brightness Full": "number",
        "Brightness Dimmed": "number",
    }
    registry = types.SimpleNamespace(
        entities={
            entity_id: types.SimpleNamespace(
                domain=domains.get(original_name, "sensor"),
                platform="esphome",
                device_id=device_id,
                original_name=original_name,
            )
            for original_name, entity_id in entity_ids.items()
        }
    )

    def get_registry(hass):
        asyncio.get_running_loop()
        return registry

    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.async_get = get_registry
    helpers = sys.modules["homeassistant.helpers"]
    monkeypatch.setattr(helpers, "entity_registry", entity_registry, raising=False)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", entity_registry)
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: device_id)

    hass = _Hass(_entry_with({"name": "panel"}))
    hass.states = MagicMock()
    states = {
        entity_ids["IP"]: types.SimpleNamespace(state="unavailable"),
        entity_ids["SSID"]: types.SimpleNamespace(state="HomeNet"),
        entity_ids["RSSI"]: types.SimpleNamespace(state="-54"),
    }

    def get_state(entity_id):
        asyncio.get_running_loop()
        return states.get(entity_id)

    hass.states.get.side_effect = get_state

    if active:

        class RunningApp:
            worker_calls = 0

            def get_device_status(self):
                return {
                    "integration_version": "1.2.3",
                    "integration_version_mismatch": True,
                    "device_info": {
                        "ip": "stale",
                        "ssid": "stale",
                        "rssi": 0,
                        "yaml_version": "0.9.0",
                        "tft_version": "0.4.2",
                        "tft_required_version": "0.4.3",
                    },
                }

            async def async_run_on_worker(self, callback):
                self.worker_calls += 1
                return callback()

        running_app = RunningApp()
        hass.data["nspanel_haui"]["entry1"] = {"panel": running_app}

    request = _Request(hass, admin=True, query={"device": "panel"})
    result = asyncio.run(api.DeviceStatusView().get(request, "entry1"))

    assert result["status_code"] == 200
    assert {key: result["body"]["device_info"][key] for key in ("ip", "ssid", "rssi")} == {
        "ip": "",
        "ssid": "HomeNet",
        "rssi": -54.0,
    }
    # The editor preview shows this sensor as the clock/weather inside temperature.
    assert result["body"]["device_info"]["temperature_entity_id"] == entity_ids["Temperature"]
    # The schedule card reads the panel's own brightness numbers from these.
    assert result["body"]["device_info"]["brightness_entity_id"] == entity_ids["Brightness Full"]
    assert (
        result["body"]["device_info"]["brightness_dim_entity_id"] == entity_ids["Brightness Dimmed"]
    )
    if active:
        assert running_app.worker_calls == 1
        assert result["body"]["integration_version"] == "1.2.3"
        assert result["body"]["integration_version_mismatch"] is True
        assert result["body"]["device_info"]["yaml_version"] == "0.9.0"
        # Running-device status carries the firmware-declared TFT requirement,
        # distinct from the installed TFT and the firmware ``yaml_version``.
        assert result["body"]["device_info"]["tft_version"] == "0.4.2"
        assert result["body"]["device_info"]["tft_required_version"] == "0.4.3"


@pytest.mark.parametrize("state", ["unknown", "unavailable", "not-a-number", "NaN"])
def test_disabled_device_status_keeps_unavailable_wifi_fields_unknown(monkeypatch, state):
    device_id = "ha-device-1"
    entity_ids = {
        "IP": "sensor.room_ip",
        "SSID": "sensor.room_ssid",
        "RSSI": "sensor.room_rssi",
    }
    registry = types.SimpleNamespace(
        entities={
            entity_id: types.SimpleNamespace(
                domain="sensor",
                platform="esphome",
                device_id=device_id,
                original_name=original_name,
            )
            for original_name, entity_id in entity_ids.items()
        }
    )
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.async_get = lambda hass: registry
    helpers = sys.modules["homeassistant.helpers"]
    monkeypatch.setattr(helpers, "entity_registry", entity_registry, raising=False)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", entity_registry)
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: device_id)

    hass = _Hass(_entry_with({"name": "room"}))
    hass.states = MagicMock()
    hass.states.get.side_effect = {
        entity_ids["IP"]: types.SimpleNamespace(state="10.0.0.8"),
        entity_ids["SSID"]: types.SimpleNamespace(state="unavailable"),
        entity_ids["RSSI"]: types.SimpleNamespace(state=state),
    }.get

    result = asyncio.run(
        api.DeviceStatusView().get(_Request(hass, admin=True, query={"device": "room"}), "entry1")
    )

    assert result["status_code"] == 200
    assert result["body"]["device_info"]["ip"] == "10.0.0.8"
    assert result["body"]["device_info"]["ssid"] == ""
    assert result["body"]["device_info"]["rssi"] is None


def test_disabled_device_status_returns_unknown_readings_when_registry_lookup_fails(monkeypatch):
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: None)
    hass = _Hass(_entry_with({"name": "room"}))

    result = asyncio.run(
        api.DeviceStatusView().get(_Request(hass, admin=True, query={"device": "room"}), "entry1")
    )

    assert result["status_code"] == 200
    assert result["body"]["device_info"]["ip"] == ""
    assert result["body"]["device_info"]["ssid"] == ""
    assert result["body"]["device_info"]["rssi"] is None


def test_panel_templates_are_served_in_the_language_asked_for(monkeypatch):
    from custom_components.nspanel_haui.haui.mapping import templates

    asked = []
    monkeypatch.setattr(
        templates, "get_panel_templates", lambda language: asked.append(language) or ["t"]
    )
    hass = _Hass(_entry_with({"name": "kitchen"}))

    result = asyncio.run(
        api.PanelTemplatesView().get(_Request(hass, admin=False, query={"language": "de"}))
    )

    assert result == {"status_code": 200, "body": ["t"]}
    assert asked == ["de"]


def test_update_policy_get_answers_the_defaults_on_an_empty_store(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass, None)

    result = asyncio.run(api.UpdatePolicyView().get(_Request(hass, admin=False), "entry1"))

    assert result["status_code"] == 200
    assert result["body"]["policy"]["max_attempts"] == 3
    assert result["body"]["policy"]["install_delay"] == 600


def test_update_policy_put_stores_it_and_reloads_every_device(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}}, "office": {"config": {}}}},
    )
    kitchen = _WorkerApp()
    office = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": kitchen, "office": office}

    result = asyncio.run(
        api.UpdatePolicyView().put(
            _Request(hass, admin=True, body={"policy": {"max_attempts": 5}}), "entry1"
        )
    )

    assert result["status_code"] == 200
    assert saved[0]["update_policy"]["max_attempts"] == 5
    assert result["body"]["policy"]["max_attempts"] == 5
    assert "reload_config" in kitchen.calls
    assert "reload_config" in office.calls
    assert kitchen.cfg["update"]["max_attempts"] == 5


def test_update_policy_put_refuses_an_invalid_policy(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(monkeypatch, hass, {"version": 1, "devices": {}})

    result = asyncio.run(
        api.UpdatePolicyView().put(
            _Request(hass, admin=True, body={"policy": {"max_attempts": 0}}), "entry1"
        )
    )

    assert result["status_code"] == 400
    assert saved == []


class _ControlApp(_WorkerApp):
    """A running app whose update controller has a firmware install scheduled."""

    def __init__(self, offered="0.5.1"):
        super().__init__()
        self.offered = offered

    async def async_update_state(self):
        return {
            "firmware_update_available": bool(self.offered),
            "firmware_update_version": self.offered,
        }

    async def async_update_control(self, action, seconds=None):
        if action == "defer" and seconds not in (3600, 86400):
            raise ValueError("Defer by 3600 or 86400 seconds")
        self.calls.append((action, seconds))
        return {"firmware_scheduled": None}


def _control(hass, body):
    return asyncio.run(
        api.UpdateControlView().post(_Request(hass, admin=True, body=body), "entry1")
    )


def test_update_control_defers_the_scheduled_install(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    app = _ControlApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}

    result = _control(hass, {"device": "kitchen", "action": "defer", "seconds": 3600})

    assert result["status_code"] == 200
    assert app.calls == [("defer", 3600)]


def test_update_control_refuses_a_bad_defer(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _ControlApp()}

    result = _control(hass, {"device": "kitchen", "action": "defer", "seconds": 60})

    assert result["status_code"] == 400


def test_update_control_skip_stores_the_offered_version_and_reloads_that_device(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}, {"name": "office"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {"version": 1, "devices": {"kitchen": {"config": {}}, "office": {"config": {}}}},
    )
    kitchen = _ControlApp()
    office = _ControlApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": kitchen, "office": office}

    result = _control(hass, {"device": "kitchen", "action": "skip"})

    assert result["status_code"] == 200
    assert saved[0]["devices"]["kitchen"]["config"]["update"]["skipped_firmware_version"] == "0.5.1"
    assert "reload_config" in kitchen.calls
    assert office.calls == []


def test_update_control_skip_needs_an_offered_update(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(monkeypatch, hass, {"version": 1, "devices": {"kitchen": {"config": {}}}})
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _ControlApp(offered=None)}

    result = _control(hass, {"device": "kitchen", "action": "skip"})

    assert result["status_code"] == 400
    assert saved == []


def test_update_control_refuses_an_unknown_action(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _ControlApp()}

    assert _control(hass, {"device": "kitchen", "action": "explode"})["status_code"] == 400


class _RolloutApp(_WorkerApp):
    """A running device whose update state the rollout reads."""

    def __init__(self, firmware=False, tft=False, connected=True):
        super().__init__()
        self.snapshot = {
            "connected": connected,
            "display": {
                "installed_version": "0.5.0",
                "available": tft,
                "state": "idle",
                "last_error": None,
            },
            "firmware": {"available": firmware, "installing": False, "last_error": None},
        }

    async def async_update_snapshot(self):
        return self.snapshot

    async def async_set_rollout_hold(self, hold):
        self.calls.append(("hold", hold))


def _rollout_hass(monkeypatch, apps, order):
    hass = _Hass(_entry_with(*({"name": name} for name in apps)))
    hass.async_create_background_task = lambda coro, name: (coro.close(), None)[1]
    _use_store(monkeypatch, hass, {"version": 1, "device_order": order, "devices": {}})
    hass.data["nspanel_haui"]["entry1"] = apps
    return hass


def test_status_of_every_device_carries_the_rollout(monkeypatch):
    hass = _Hass(_entry_with())

    result = asyncio.run(api.DeviceStatusView().get(_Request(hass, admin=True), "entry1"))

    assert result["body"]["rollout"]["state"] == "idle"


def test_rollout_starts_with_the_devices_that_have_an_offered_update(monkeypatch):
    apps = {
        "kitchen": _RolloutApp(firmware=True),
        "hall": _RolloutApp(),
        "office": _RolloutApp(tft=True),
        "attic": _RolloutApp(firmware=True, connected=False),
    }
    hass = _rollout_hass(monkeypatch, apps, ["office", "hall", "kitchen", "attic"])

    result = asyncio.run(api.RolloutView().post(_Request(hass, admin=True, body={}), "entry1"))

    assert result["status_code"] == 200
    rollout = result["body"]["rollout"]
    assert [(entry["name"], entry["kind"]) for entry in rollout["devices"]] == [
        ("office", "tft"),
        ("kitchen", "firmware"),
    ]
    assert ("hold", True) in apps["kitchen"].calls


def test_rollout_without_an_offered_update_is_refused(monkeypatch):
    hass = _rollout_hass(monkeypatch, {"hall": _RolloutApp()}, ["hall"])

    result = asyncio.run(api.RolloutView().post(_Request(hass, admin=True, body={}), "entry1"))

    assert result["status_code"] == 400


def test_rollout_cancels_one_queued_device(monkeypatch):
    apps = {"kitchen": _RolloutApp(firmware=True), "office": _RolloutApp(firmware=True)}
    hass = _rollout_hass(monkeypatch, apps, ["kitchen", "office"])

    async def run():
        await api.RolloutView().post(_Request(hass, admin=True, body={}), "entry1")
        return await api.RolloutDeviceView().delete(_Request(hass, admin=True), "entry1", "office")

    result = asyncio.run(run())

    states = {entry["name"]: entry["state"] for entry in result["body"]["rollout"]["devices"]}
    assert states["office"] == "cancelled"
    assert ("hold", False) in apps["office"].calls


@pytest.mark.parametrize(
    "sent_update",
    [{"enabled": True}, {"enabled": True, "skipped_firmware_version": "0.5.0"}, None],
)
def test_a_settings_save_keeps_the_skipped_firmware_version(monkeypatch, sent_update):
    """Only Skip this version writes the skip; a settings save from a stale editor keeps it."""
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch,
        hass,
        {
            "version": 1,
            "devices": {
                "kitchen": {
                    "config": {"update": {"enabled": True, "skipped_firmware_version": "0.5.1"}},
                    "panels": [],
                }
            },
        },
    )
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": _WorkerApp()}
    config = {"locale": "de_DE"} if sent_update is None else {"update": sent_update}

    result = asyncio.run(
        api.DeviceSettingsView().put(
            _Request(hass, admin=True, body={"config": config}), "entry1", "kitchen"
        )
    )

    assert result["status_code"] == 200
    stored = saved[0]["devices"]["kitchen"]["config"]
    assert stored["update"]["skipped_firmware_version"] == "0.5.1"


def test_a_settings_save_refuses_a_bad_device_policy(monkeypatch):
    hass = _Hass(_entry_with({"name": "kitchen"}))
    saved = _use_store(
        monkeypatch, hass, {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}}
    )

    result = asyncio.run(
        api.DeviceSettingsView().put(
            _Request(
                hass,
                admin=True,
                body={"config": {"update": {"policy_override": True, "retry_interval": 0}}},
            ),
            "entry1",
            "kitchen",
        )
    )

    assert result["status_code"] == 400
    assert saved == []

"""Tests for the editor REST API views and config entry reload flow.

The HA stubs mirror the upstream behaviour the views rely on:
``require_admin`` raises ``Unauthorized`` for non-admin users, and
``HomeAssistantView.json`` returns a response carrying a status code.
"""

from __future__ import annotations

import asyncio
import sys
import types
from functools import wraps
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests


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

from nspanel_haui import (  # noqa: E402
    _auto_add_unconfigured_devices,
    api,
    async_reload_entry,
    esphome_helpers,
    storage,
)

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
    (api.DeviceStatusView, "get"),
    (api.PanelConfigView, "get"),
    (api.PanelConfigView, "post"),
    (api.DeviceConfigView, "get"),
    (api.DeviceConfigView, "post"),
    (api.DeviceConfigView, "delete"),
    (api.DeviceYamlView, "get"),
    (api.DeviceYamlView, "post"),
    (api.DeviceUpdateDisplayView, "post"),
    (api.DeviceUpdateTftView, "post"),
]


@pytest.mark.parametrize(("view_cls", "method"), _PROTECTED)
def test_config_endpoints_reject_non_admin_users(view_cls, method):
    hass = MagicMock()
    request = _Request(hass, admin=False, body={}, query={"name": "panel"})

    with pytest.raises(_Unauthorized):
        asyncio.run(getattr(view_cls(), method)(request, entry_id="entry1"))

    assert hass.mock_calls == []


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
    # A device re-added after a keep-config removal keeps its stored settings.
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
    from nspanel_haui.haui.utils.text import get_translations

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


def test_enabling_a_device_from_the_editor_reloads_the_entry(monkeypatch):
    entry = _entry_with({"name": "kitchen"}, {"name": "office"})
    hass = _Hass(entry)
    _use_store(monkeypatch, hass)
    kitchen_app = MagicMock()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": kitchen_app}
    body = {
        "version": 1,
        "devices": {
            "kitchen": {"config": {}, "panels": []},
            "office": {"config": {"enabled": True}, "panels": []},
        },
    }

    asyncio.run(api.PanelConfigView().post(_Request(hass, admin=True, body=body), "entry1"))

    assert hass.config_entries.scheduled_reloads == ["entry1"]
    assert list(hass.data["nspanel_haui"]["entry1"]) == ["kitchen"]


def test_panel_save_drops_response_only_fields(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass)
    body = {
        "version": 1,
        "system_panels": [{"key": "sys_about"}],
        "devices": {"kitchen": {"friendly_name": "Kitchen", "config": {}, "panels": []}},
    }

    asyncio.run(api.PanelConfigView().post(_Request(hass, admin=True, body=body), "entry1"))

    (stored,) = saved
    assert "system_panels" not in stored
    assert "friendly_name" not in stored["devices"]["kitchen"]


def test_panel_save_rejects_empty_device_config_values(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    saved = _use_store(monkeypatch, hass)
    body = {"version": 1, "devices": {"kitchen": {"config": {"locale": None}, "panels": []}}}

    result = asyncio.run(
        api.PanelConfigView().post(_Request(hass, admin=True, body=body), "entry1")
    )

    assert result["status_code"] == 400
    assert saved == []


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

    result = asyncio.run(api._push_panels(hass, "entry1", {"version": 1, "devices": {}}))

    assert result == {"status": "ok"}
    assert hass.config_entries.reloads == []
    assert hass.config_entries.scheduled_reloads == []


def test_removing_the_hub_deletes_its_panel_store(monkeypatch):
    from nspanel_haui import async_remove_entry

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

    def update_display(self):
        self.calls.append("update_display")

    def install_tft(self, version=None):
        self.calls.append(("install_tft", version))

    async def async_run_on_worker(self, fn, *args):
        self.calls.append("worker")
        return fn(*args)


def test_panel_save_reloads_a_running_device_on_its_worker(monkeypatch):
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    _use_store(monkeypatch, hass)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    body = {"version": 1, "devices": {"kitchen": {"config": {"locale": "de_DE"}, "panels": []}}}

    asyncio.run(api.PanelConfigView().post(_Request(hass, admin=True, body=body), "entry1"))

    assert app.calls == ["worker", "reload_config"]
    # Rebuilt the way setup builds it: store settings over defaults.
    assert app.cfg["device"]["locale"] == "de_DE"
    assert app.cfg["device"]["timeout_display_off"] == 120


def test_display_refresh_runs_on_the_device_worker():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    asyncio.run(api.DeviceUpdateDisplayView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", "update_display"]


def test_firmware_download_rejects_non_admin_users():
    hass = MagicMock()
    request = _Request(hass, admin=False)

    with pytest.raises(_Unauthorized):
        asyncio.run(api.FirmwareDownloadView().get(request))

    assert hass.mock_calls == []


class _BinResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_firmware_download_resolves_the_latest_binary_asset(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "get",
        lambda url, timeout: _BinResponse(
            [
                {
                    "tag_name": "v0.4.0",
                    "assets": [{"name": "nspanel_haui.tft", "browser_download_url": "/tft"}],
                },
                {
                    "tag_name": "v0.3.3",
                    "assets": [
                        {"name": "nspanel_haui.tft", "browser_download_url": "/tft-0.3.3"},
                        {
                            "name": "nspanel_haui.bin",
                            "browser_download_url": "/esp/nspanel_haui.bin",
                        },
                    ],
                },
            ]
        ),
    )
    hass = MagicMock()

    result = asyncio.run(api.FirmwareDownloadView().get(_Request(hass, admin=True)))

    assert result["status_code"] == 200
    assert result["body"] == {"url": "/esp/nspanel_haui.bin", "version": "v0.3.3"}


def test_firmware_download_without_a_binary_returns_no_url(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "get",
        lambda url, timeout: _BinResponse(
            [
                {
                    "tag_name": "v0.4.0",
                    "assets": [{"name": "nspanel_haui.tft", "browser_download_url": "/tft"}],
                }
            ]
        ),
    )
    hass = MagicMock()

    result = asyncio.run(api.FirmwareDownloadView().get(_Request(hass, admin=True)))

    assert result["status_code"] == 200
    assert result["body"] == {"url": None, "version": None}


def test_firmware_download_unreachable_github_returns_error(monkeypatch):
    def raise_timeout(url, timeout):
        raise requests.exceptions.ConnectTimeout("no route to host")

    monkeypatch.setattr(api.requests, "get", raise_timeout)
    hass = MagicMock()

    result = asyncio.run(api.FirmwareDownloadView().get(_Request(hass, admin=True)))

    # A network problem must not be reported as "the release has no binary".
    assert result["status_code"] == 502
    assert result["body"]["status"] == "error"
    assert "GitHub" in result["body"]["message"]


def test_firmware_download_empty_release_list_returns_error(monkeypatch):
    monkeypatch.setattr(api.requests, "get", lambda url, timeout: _BinResponse([]))
    hass = MagicMock()

    result = asyncio.run(api.FirmwareDownloadView().get(_Request(hass, admin=True)))

    assert result["status_code"] == 502
    assert result["body"]["status"] == "error"

    # --- YAML import pushes like a panel save ----------------------------------
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen"})

    asyncio.run(api.DeviceUpdateDisplayView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", "update_display"]


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


def test_tft_install_passes_the_requested_version():
    entry = _entry_with({"name": "kitchen"})
    hass = _Hass(entry)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    request = _Request(hass, admin=True, body={"device": "kitchen", "version": "0.4.0"})

    asyncio.run(api.DeviceUpdateTftView().post(request, entry_id="entry1"))

    assert app.calls == ["worker", ("install_tft", "0.4.0")]


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
    state = {"state": "error", "version": "0.4.1", "started_at": None,
             "last_error": "device disconnected"}
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
            {"state": "error", "version": None, "started_at": None,
             "last_error": "no yaml_version reported"}
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


def test_panel_save_with_a_kept_config_of_a_removed_device_does_not_reload(monkeypatch):
    # "office" was removed with keep_config: its settings stay in the store only.
    hass = _Hass(_entry_with({"name": "kitchen"}))
    _use_store(monkeypatch, hass)
    app = _WorkerApp()
    hass.data["nspanel_haui"]["entry1"] = {"kitchen": app}
    body = {
        "version": 1,
        "devices": {
            "kitchen": {"config": {}, "panels": []},
            "office": {"config": {}, "panels": []},
        },
    }

    asyncio.run(api.PanelConfigView().post(_Request(hass, admin=True, body=body), "entry1"))

    assert hass.config_entries.scheduled_reloads == []
    assert app.calls == ["worker", "reload_config"]

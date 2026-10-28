"""Tests for config entry setup, panel storage loading and device event routing."""

from __future__ import annotations

import asyncio
import importlib
import sys
import threading
import types

_storage_stub = types.ModuleType("homeassistant.helpers.storage")
_storage_stub.Store = object
sys.modules.setdefault("homeassistant.helpers.storage", _storage_stub)

import nspanel_haui  # noqa: E402
from nspanel_haui import esphome_helpers, storage  # noqa: E402
from nspanel_haui.ha_adapter import ESPHomeProxy  # noqa: E402
from nspanel_haui.nspanel_haui import NSPanelHAUI  # noqa: E402

# --- setup ----------------------------------------------------------------


class _Entry:
    def __init__(self, devices: list[dict]) -> None:
        self.entry_id = "entry1"
        self.title = "Hub"
        self.data = {"name": "Hub", "devices": devices}
        self.options: dict = {}
        self.on_unload: list = []

    def async_on_unload(self, cb):
        self.on_unload.append(cb)

    def add_update_listener(self, listener):
        return lambda: None


class _Bus:
    def __init__(self) -> None:
        self.cancel_calls = 0
        self.listeners: list = []

    def async_listen(self, event_type, cb):
        self.listeners.append(cb)

        def cancel():
            self.cancel_calls += 1

        return cancel


class _ConfigEntries:
    def __init__(self) -> None:
        self.forwarded: list = []
        self.entries: dict = {}
        self.reloaded: list = []

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded.append(list(platforms))

    def async_get_entry(self, entry_id):
        return self.entries.get(entry_id)

    def async_schedule_reload(self, entry_id):
        self.reloaded.append(entry_id)

    def async_entries(self, domain):
        return [e for e in self.entries.values() if getattr(e, "domain", None) == domain]


class _Hass:
    def __init__(self) -> None:
        self.data: dict = {}
        self.bus = _Bus()
        self.config_entries = _ConfigEntries()

    def async_create_task(self, coro):
        coro.close()


class _App:
    def __init__(self) -> None:
        self._ha_device_id = None
        self._plugin_proxies: dict = {}


def _setup(monkeypatch, devices: list[dict], stored: dict | None = None):
    class _PanelStorage:
        def __init__(self, hass, entry_id, entry):
            pass

        async def load(self):
            return stored or {"version": 1, "devices": {}}

    async def create_app(hass, entry, name, data, panels, device_name):
        return _App()

    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.EVENT_DEVICE_REGISTRY_UPDATED = "device_registry_updated"
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers"], "device_registry", registry, raising=False
    )
    monkeypatch.setattr(storage, "PanelStorage", _PanelStorage)
    monkeypatch.setattr(nspanel_haui, "_create_app", create_app)

    hass = _Hass()
    entry = _Entry(devices)
    assert asyncio.run(nspanel_haui.async_setup_entry(hass, entry)) is True
    return hass, entry


def test_setup_with_unresolved_device_registers_no_listener_of_its_own(monkeypatch):
    hass, _entry = _setup(monkeypatch, [{"name": "kitchen"}])

    assert set(hass.data[nspanel_haui.DOMAIN]) == {"entry1"}
    assert hass.bus.listeners == []


def test_idle_hub_still_sets_up_platforms(monkeypatch):
    hass, _entry = _setup(monkeypatch, [])

    assert hass.data[nspanel_haui.DOMAIN]["entry1"] == {}
    assert hass.config_entries.forwarded == [nspanel_haui.PLATFORMS]


def _registry_update(monkeypatch, app):
    """Run the session-wide registry listener for a HAUI ESPHome device update."""
    # The stubbed core module may be a restricted/wrapping mock that does not
    # expose ``callback``; raising=False lets the patch create it either way.
    monkeypatch.setattr(
        sys.modules["homeassistant.core"], "callback", lambda f: f, raising=False
    )
    monkeypatch.setattr(nspanel_haui, "_DISCOVERY_INITIALIZED", False)
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: "dev1")
    monkeypatch.setattr(esphome_helpers, "is_haui_device", lambda hass, entry: True)
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.EVENT_DEVICE_REGISTRY_UPDATED = "device_registry_updated"
    registry.async_get = lambda hass: types.SimpleNamespace(
        async_get=lambda device_id: types.SimpleNamespace(config_entry_id="esp1")
    )
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers"], "device_registry", registry, raising=False
    )
    hass = _Hass()
    hub = _Entry([{"name": "kitchen"}])
    hub.domain = nspanel_haui.DOMAIN
    hass.config_entries.entries = {
        "esp1": types.SimpleNamespace(domain="esphome", entry_id="esp1"),
        "entry1": hub,
    }
    hass.data[nspanel_haui.DOMAIN] = {"entry1": {"kitchen": app}}
    asyncio.run(nspanel_haui._register_discovery(hass))
    (on_registry_update,) = hass.bus.listeners

    on_registry_update(types.SimpleNamespace(data={"action": "create", "device_id": "dev1"}))
    return hass


def test_registry_update_reloads_hub_whose_device_resolves_late(monkeypatch):
    """The reload re-creates the app, which links the device and adds its notify entities."""
    hass = _registry_update(monkeypatch, _App())

    assert hass.config_entries.reloaded == ["entry1"]


def test_registry_update_leaves_hub_with_resolved_devices_alone(monkeypatch):
    resolved = _App()
    resolved._ha_device_id = "dev1"

    hass = _registry_update(monkeypatch, resolved)

    assert hass.config_entries.reloaded == []


# --- notify platform ------------------------------------------------------


def test_notify_entities_skip_devices_not_linked_to_esphome(monkeypatch):
    """An unlinked device's DeviceInfo would create a bare device whose identifier
    later collides when the ESPHome device gets linked."""
    notify_stub = types.ModuleType("homeassistant.components.notify")
    notify_stub.NotifyEntity = object
    notify_stub.NotifyEntityFeature = types.SimpleNamespace(TITLE=1)
    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.DeviceInfo = dict
    monkeypatch.setitem(sys.modules, "homeassistant.components.notify", notify_stub)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.delitem(sys.modules, "nspanel_haui.notify", raising=False)
    notify = importlib.import_module("nspanel_haui.notify")
    linked = _App()
    linked._ha_device_id = "esphome-device"
    hass = _Hass()
    hass.data[nspanel_haui.DOMAIN] = {"entry1": {"kitchen": linked, "office": _App()}}
    added: list = []

    asyncio.run(notify.async_setup_entry(hass, _Entry([]), added.extend))

    assert {e._attr_unique_id for e in added} == {
        "entry1_kitchen_notify",
        "entry1_kitchen_notify_persistent",
    }


def test_setup_starts_only_enabled_devices_listed_in_the_entry(monkeypatch):
    stored = {
        "version": 1,
        "devices": {
            "kitchen": {"config": {}, "panels": []},
            "office": {"config": {"enabled": False}, "panels": []},
            # Removed with "keep config": settings stay, the device stays removed.
            "garage": {"config": {}, "panels": []},
        },
    }

    hass, _entry = _setup(monkeypatch, [{"name": "kitchen"}, {"name": "office"}], stored)

    assert list(hass.data["nspanel_haui"]["entry1"]) == ["kitchen"]


# --- config reload -----------------------------------------------------------


def test_store_device_name_matches_case_insensitively():
    clock = {"type": "clock", "key": "clock_0"}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "nspanel-kitchen"}]},
        {"devices": {"NSPanel-Kitchen": {"config": {}, "panels": [clock]}}},
        device_name="nspanel-kitchen",
    )

    assert cfg["panels"] == [clock]


# --- panel storage ---------------------------------------------------------


def test_panel_storage_load_preserves_stored_config_values(monkeypatch):
    stored = {
        "version": 1,
        "devices": {
            "kitchen": {"config": {"locale": "de_DE", "button_left_entity": None}, "panels": []},
        },
    }

    class _Store:
        def __init__(self, hass, version, key):
            pass

        async def async_load(self):
            return stored

        async def async_save(self, data):
            pass

    monkeypatch.setattr(storage, "Store", _Store)
    entry = _Entry([{"name": "kitchen"}, {"name": "office", "enabled": True}])

    result = asyncio.run(storage.PanelStorage(object(), "entry1", entry).load())

    # The store is no longer a migration layer: stored config passes through
    # untouched (bad values are the editor/import validation's job to reject).
    assert result["devices"]["kitchen"]["config"] == {
        "locale": "de_DE",
        "button_left_entity": None,
    }
    # A device only listed in the entry gets an empty store entry (defaults apply).
    assert result["devices"]["office"] == {"config": {}, "panels": []}


# --- device event routing --------------------------------------------------


class _Event:
    event_type = "esphome.nspanel_event"

    def __init__(self, device_id: str) -> None:
        self.data = {"device_id": device_id, "name": "esphome.touch_end", "value": "1"}


def test_unresolved_device_ignores_events_from_other_devices(monkeypatch):
    monkeypatch.setattr(
        sys.modules["homeassistant.core"], "callback", lambda f: f, raising=False
    )
    listeners: list = []
    jobs: list = []
    hass = types.SimpleNamespace(
        bus=types.SimpleNamespace(async_listen=lambda et, cb: listeners.append(cb) or (lambda: 0)),
        async_add_executor_job=lambda *args: jobs.append(args),
    )
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        proxy = ESPHomeProxy(
            hass, loop, device_name="kitchen", device_id=None, dispatch=lambda *a: jobs.append(a)
        )
        proxy.listen_event(lambda *a: None, "esphome.nspanel_event")
        (on_event,) = listeners

        on_event(_Event("office-device-id"))
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()

    assert jobs == []


class _Device:
    def __init__(self) -> None:
        self.config: dict = {}
        self.synced = 0

    def _cancel_callbacks(self):
        pass

    def _register_callbacks(self):
        pass

    def sync_config_to_device(self):
        self.synced += 1


class _DeviceConfig:
    """The app's current HAUIConfig; reload_config swaps its panel lists."""

    _panels: list = []


def _reload(saved_config: dict):
    app = NSPanelHAUI.__new__(NSPanelHAUI)
    app.device_config = _DeviceConfig()
    app.device = _Device()
    app.controller = {}
    app._runtime_device_name = "kitchen"
    app.log = lambda *a, **kw: None
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": saved_config, "panels": []}}},
        device_name="kitchen",
    )
    app.reload_config(cfg)
    return app


def test_reload_config_clamps_saved_color_overrides_like_startup():
    saved = {"color_overrides": {"background": 70000, "text": "123", "not_a_color": 5}}

    app = _reload(saved)

    assert app.device.config["color_overrides"] == {"background": 65535, "text": 123}
    assert app._color_theme.get("background") == 65535


def test_reload_config_resets_a_setting_removed_from_the_store_to_its_default():
    app = _reload({})

    assert app.device.config["timeout_display_off"] == 120
    assert app.device.config["locale"] == "en_US"


def test_reload_config_pushes_all_device_settings_to_the_firmware():
    # Relay mode and button interaction too, not only the auto-* behaviour.
    app = _reload({"use_relay_left": False})

    assert app.device.synced == 1


# --- app lifecycle on the app's worker --------------------------------------


class _LifecycleApp:
    _runtime_device_name = "kitchen"
    _ha_device_id = None

    def __init__(self, *args, **kwargs):
        self.calls: list[str] = []

    def initialize(self):
        self.calls.append("initialize")

    def stop(self):
        self.calls.append("stop")

    async def async_run_on_worker(self, fn, *args):
        self.calls.append("worker")
        return fn(*args)


def test_new_app_initializes_on_its_worker(monkeypatch):
    from nspanel_haui import esphome_helpers

    monkeypatch.setattr(sys.modules["nspanel_haui.nspanel_haui"], "NSPanelHAUI", _LifecycleApp)
    monkeypatch.setattr(nspanel_haui, "_build_config_dict", lambda *a, **kw: {})
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: None)

    app = asyncio.run(nspanel_haui._create_app(_Hass(), _Entry([]), "Hub", {}, None, "kitchen"))

    assert app.calls == ["worker", "initialize"]


def test_stopping_an_app_runs_stop_on_its_worker():
    app = _LifecycleApp()

    assert asyncio.run(nspanel_haui._stop_app(app)) is True
    assert app.calls == ["worker", "stop"]

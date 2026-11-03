"""Tests for the virtual panel's WebSocket commands."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types

import pytest
import voluptuous as vol

_storage_stub = types.ModuleType("homeassistant.helpers.storage")
_storage_stub.Store = object
sys.modules.setdefault("homeassistant.helpers.storage", _storage_stub)


def _websocket_stub():
    module = types.ModuleType("homeassistant.components.websocket_api")
    module.registered = []

    def websocket_command(schema):
        def decorator(fn):
            fn.schema = schema
            return fn

        return decorator

    module.websocket_command = websocket_command
    module.require_admin = lambda fn: fn
    module.async_response = lambda fn: fn
    module.event_message = lambda msg_id, data: {"id": msg_id, "type": "event", "event": data}
    module.async_register_command = lambda hass, fn: module.registered.append(fn)
    return module


class _Connection:
    def __init__(self):
        self.subscriptions = {}
        self.results = []
        self.errors = []
        self.events = []

    def send_result(self, msg_id, result=None):
        self.results.append(msg_id)

    def send_error(self, msg_id, code, message):
        self.errors.append((msg_id, code))

    def send_message(self, message):
        self.events.append(message["event"])


class _FakeSession:
    instances: list = []
    fail_start = False

    def __init__(self, hass, device, cfg, sink, **kwargs):
        self.id = f"s{len(_FakeSession.instances)}"
        self.device = device
        self.kwargs = kwargs
        self.sink = sink
        self.started = self.stopped = False
        self.events = []
        self.live = kwargs["live"]
        _FakeSession.instances.append(self)

    async def async_start(self):
        if _FakeSession.fail_start:
            raise RuntimeError("boom")
        self.started = True

    async def async_stop(self):
        self.stopped = True

    def send_event(self, name, value):
        if name != "esphome.component":
            raise ValueError("not allowed")
        self.events.append((name, value))

    def set_live(self, live):
        self.live = live

    def reset_sandbox(self):
        self.reset_count = getattr(self, "reset_count", 0) + 1


@pytest.fixture
def ws(monkeypatch):
    stub = _websocket_stub()
    monkeypatch.setitem(sys.modules, "homeassistant.components.websocket_api", stub)
    monkeypatch.setattr(sys.modules["homeassistant.components"], "websocket_api", stub, False)
    import nspanel_haui.websocket_api as module

    module = importlib.reload(module)
    from nspanel_haui import esphome_helpers, storage, virtual_panel

    class _Store:
        async def async_load(self):
            return {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}}

    monkeypatch.setattr(storage, "panel_store", lambda hass, entry_id: _Store())
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: None)
    monkeypatch.setattr(virtual_panel, "VirtualPanelSession", _FakeSession)
    _FakeSession.instances = []
    _FakeSession.fail_start = False
    return module


class _Hass:
    def __init__(self, loop):
        self.loop = loop
        self.data = {}
        self.tasks = []
        entry = types.SimpleNamespace(
            entry_id="entry1", data={"name": "Hub", "devices": [{"name": "kitchen"}]}
        )
        self.config_entries = types.SimpleNamespace(
            async_get_entry=lambda entry_id: entry if entry_id == "entry1" else None
        )

    def async_create_task(self, coro):
        self.tasks.append(self.loop.create_task(coro))


def _subscribe(
    ws, hass, conn, msg_id=1, device="kitchen", entry_id="entry1", protocol_version=None
):
    msg = {"id": msg_id, "entry_id": entry_id, "device": device, "live": False}
    if protocol_version is not None:
        msg["protocol_version"] = protocol_version
    return ws.ws_subscribe(hass, conn, msg)


def _run(coro_fn):
    async def _main():
        loop = asyncio.get_running_loop()
        hass = _Hass(loop)
        await coro_fn(hass)
        await asyncio.gather(*hass.tasks)
        await asyncio.sleep(0)  # let call_soon_threadsafe sends run

    asyncio.run(_main())


def test_all_commands_are_registered(ws):
    hass = types.SimpleNamespace()
    ws.async_register_websocket_commands(hass)
    registered = sys.modules["homeassistant.components.websocket_api"].registered
    assert [fn.schema["type"] for fn in registered] == [
        "nspanel_haui/virtual_panel/subscribe",
        "nspanel_haui/virtual_panel/event",
        "nspanel_haui/virtual_panel/configure",
    ]


@pytest.mark.parametrize(("entry_id", "device"), [("nope", "kitchen"), ("entry1", "garage")])
def test_subscribe_rejects_unknown_hub_or_device(ws, entry_id, device):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn, device=device, entry_id=entry_id)

    _run(body)
    assert conn.errors == [(1, "not_found")]
    assert _FakeSession.instances == []


def test_subscribe_starts_a_session_and_unsubscribe_stops_it(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        session = _FakeSession.instances[0]
        assert session.started
        assert session.kwargs["protocol_version"] == 1
        assert ws._sessions(hass) == {session.id: session}
        session.sink({"type": "page", "page": 9})
        await asyncio.sleep(0)
        conn.subscriptions[1]()
        assert ws._sessions(hass) == {}

    _run(body)
    session = _FakeSession.instances[0]
    assert session.stopped
    assert conn.results == [1]
    assert conn.events[0] == {
        "type": "started",
        "session_id": session.id,
        "portrait": False,
        "live": False,
    }
    assert {"type": "page", "page": 9} in conn.events


def test_subscribe_passes_current_protocol_version_to_session(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn, protocol_version=2)
        assert _FakeSession.instances[0].kwargs["protocol_version"] == 2

    _run(body)


def test_subscribe_limits_concurrent_sessions(ws):
    conn = _Connection()

    async def body(hass):
        for msg_id in range(ws.MAX_SESSIONS + 1):
            await _subscribe(ws, hass, conn, msg_id=msg_id)

    _run(body)
    assert len(_FakeSession.instances) == ws.MAX_SESSIONS
    assert conn.errors == [(ws.MAX_SESSIONS, "too_many_sessions")]


def test_a_session_that_fails_to_start_is_dropped(ws):
    _FakeSession.fail_start = True
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        assert ws._sessions(hass) == {}

    _run(body)
    assert {"type": "error", "message": "start_failed"} in conn.events


def test_event_forwards_allowed_events_and_rejects_others(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        sid = _FakeSession.instances[0].id
        await ws.ws_event(
            hass, conn, {"id": 2, "session_id": sid, "name": "esphome.component", "value": "9,12,0"}
        )
        await ws.ws_event(
            hass, conn, {"id": 3, "session_id": sid, "name": "esphome.connected", "value": ""}
        )
        await ws.ws_event(hass, conn, {"id": 4, "session_id": "gone", "name": "x", "value": ""})

    _run(body)
    assert _FakeSession.instances[0].events == [("esphome.component", "9,12,0")]
    assert conn.errors == [(3, "invalid_event"), (4, "not_found")]


def test_configure_switches_the_mode(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        sid = _FakeSession.instances[0].id
        await ws.ws_configure(hass, conn, {"id": 2, "session_id": sid, "live": True})

    _run(body)
    session = _FakeSession.instances[0]
    assert session.live is True
    assert conn.results == [1, 2]


def test_configure_accepts_reset_without_a_live_field(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        session = _FakeSession.instances[0]
        msg = vol.Schema(ws.ws_configure.schema)(
            {
                "type": "nspanel_haui/virtual_panel/configure",
                "session_id": session.id,
                "reset_sandbox": True,
            }
        )
        msg["id"] = 2
        await ws.ws_configure(hass, conn, msg)

    _run(body)
    session = _FakeSession.instances[0]
    assert session.live is False
    assert session.reset_count == 1
    assert conn.results == [1, 2]


def test_protected_entities_are_the_real_devices_own(ws, monkeypatch):
    registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entry = types.SimpleNamespace
    entries = {
        "dev1": [
            entry(entity_id="switch.kitchen_use_auto_dim", original_name="Use Auto-Dimming"),
            entry(entity_id="switch.kitchen_relay_left", original_name="Relay Left"),
            entry(entity_id="switch.kitchen_relay_right", original_name="Relay Right"),
        ]
    }
    registry.async_get = lambda hass: "registry"
    registry.async_entries_for_device = lambda reg, device_id, include_disabled_entities: entries[
        device_id
    ]
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", registry)
    monkeypatch.setattr(sys.modules["homeassistant.helpers"], "entity_registry", registry, False)

    async def body(hass):
        assert await ws._protected_entities(hass, None) == frozenset()
        # The relays are left out: live mode switches them for real.
        assert await ws._protected_entities(hass, "dev1") == {"switch.kitchen_use_auto_dim"}

    _run(body)

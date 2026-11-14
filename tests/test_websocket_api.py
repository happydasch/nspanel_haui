"""Tests for the virtual panel's WebSocket commands."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types

import pytest

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


class _FakeHost:
    instances: list = []
    fail_start = False
    # Runs while the host starts (the subscriber may close meanwhile).
    on_start = None

    def __init__(self, hass, device, cfg, **kwargs):
        self.device = device
        self.cfg = cfg
        self.kwargs = kwargs
        self.started = self.stopped = False
        self.viewers = {}
        self.events = []
        self.renders = []
        self.notifications_from = None
        self.reloads = []
        self.idle_count = 0
        self.home_count = 0
        self.reset_count = 0
        self.opened = []
        self.followed = None
        self.app = types.SimpleNamespace(device=types.SimpleNamespace(get=lambda key: None))
        _FakeHost.instances.append(self)

    @property
    def viewer_count(self):
        return len(self.viewers)

    async def async_start(self):
        if _FakeHost.fail_start:
            raise RuntimeError("boom")
        if _FakeHost.on_start is not None:
            _FakeHost.on_start()
        self.started = True

    async def async_stop(self):
        self.stopped = True

    async def async_follow_device(self, running):
        self.followed = running

    async def async_reload(self, cfg):
        self.reloads.append(cfg)

    def attach(self, viewer_id, sink):
        self.viewers[viewer_id] = sink

    def detach(self, viewer_id):
        return self.viewers.pop(viewer_id, None) is not None

    def send_event(self, name, value):
        if name != "esphome.component":
            raise ValueError("not allowed")
        self.events.append((name, value))

    def show_home(self):
        self.home_count += 1

    async def async_follow_notifications(self, running):
        self.notifications_from = running

    def show_idle(self):
        self.idle_count += 1

    async def async_show_panel(self, key, *, idle=False):
        if key == "missing":
            raise ValueError(f"Unknown panel key: {key!r}")
        self.opened.append((key, idle))

    def reset_sandbox(self):
        self.reset_count += 1

    async def async_configured_panel(self, key):
        if key != "popup_notify":
            raise ValueError(f"Unknown panel key: {key!r}")
        return {"type": "notify", "key": key, "show_in_navigation": False}

    async def async_render(self, panel, kwargs=None):
        if panel.get("type") == "bogus":
            raise ValueError("Unknown panel type: 'bogus'")
        self.renders.append((panel, kwargs))
        return {"page": 9, "before": [], "commands": ["cls 4226"]}


@pytest.fixture
def ws(monkeypatch):
    stub = _websocket_stub()
    monkeypatch.setitem(sys.modules, "homeassistant.components.websocket_api", stub)
    monkeypatch.setattr(sys.modules["homeassistant.components"], "websocket_api", stub, False)
    import custom_components.nspanel_haui.web.websocket as module

    module = importlib.reload(module)
    from custom_components.nspanel_haui.hub import esphome_helpers, storage
    from custom_components.nspanel_haui.web.preview import virtual_panel

    class _Store:
        async def async_load(self):
            return {"version": 1, "devices": {"kitchen": {"config": {}, "panels": []}}}

    monkeypatch.setattr(storage, "panel_store", lambda hass, entry_id: _Store())
    monkeypatch.setattr(esphome_helpers, "resolve_ha_device_id", lambda hass, name: None)
    monkeypatch.setattr(virtual_panel, "VirtualPanelHost", _FakeHost)
    _FakeHost.instances = []
    _FakeHost.fail_start = False
    _FakeHost.on_start = None
    return module


class _Hass:
    def __init__(self, loop):
        self.loop = loop
        self.data = {}
        self.tasks = []
        self.entry = types.SimpleNamespace(
            entry_id="entry1", data={"name": "Hub", "devices": [{"name": "kitchen"}]}
        )
        self.config_entries = types.SimpleNamespace(
            async_get_entry=lambda entry_id: self.entry if entry_id == "entry1" else None
        )

    def async_create_task(self, coro):
        self.tasks.append(self.loop.create_task(coro))


def _subscribe(ws, hass, conn, msg_id=1, device="kitchen", entry_id="entry1"):
    return ws.ws_subscribe(hass, conn, {"id": msg_id, "entry_id": entry_id, "device": device})


def _render(ws, hass, conn, panel, msg_id=1, device="kitchen", entry_id="entry1", **target):
    msg = {"id": msg_id, "entry_id": entry_id, "device": device, **target}
    if panel is not None:
        msg["panel"] = panel
    return ws.ws_render(hass, conn, msg)


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
        "nspanel_haui/virtual_panel/home",
        "nspanel_haui/virtual_panel/open",
        "nspanel_haui/virtual_panel/idle",
        "nspanel_haui/virtual_panel/reset_sandbox",
        "nspanel_haui/virtual_panel/render",
    ]


@pytest.mark.parametrize(("entry_id", "device"), [("nope", "kitchen"), ("entry1", "garage")])
def test_subscribe_and_render_reject_unknown_hub_or_device(ws, entry_id, device):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn, device=device, entry_id=entry_id)
        await _render(ws, hass, conn, {"type": "grid"}, msg_id=2, device=device, entry_id=entry_id)

    _run(body)
    assert conn.errors == [(1, "not_found"), (2, "not_found")]
    assert _FakeHost.instances == []


def test_subscription_follows_the_running_physical_apps_info_and_notifications(ws):
    conn = _Connection()
    running = types.SimpleNamespace(
        device=types.SimpleNamespace(device_info={"tft_version": "1.2"})
    )

    async def _run_on_worker(fn):
        return fn()

    running.async_run_on_worker = _run_on_worker

    async def body(hass):
        hass.data[ws.DOMAIN] = {"entry1": {"kitchen": running}}
        await _subscribe(ws, hass, conn)
        host = _FakeHost.instances[0]
        assert host.followed is running
        assert host.notifications_from is running

    _run(body)


def test_subscribe_attaches_a_viewer_and_unsubscribe_detaches_it(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        host = _FakeHost.instances[0]
        assert host.started
        [(viewer_id, sink)] = host.viewers.items()
        sink({"type": "page", "page": 9})
        await asyncio.sleep(0)
        conn.subscriptions[1]()
        assert host.viewers == {}
        # The app outlives the viewer: panel cards and the next preview use it.
        assert not host.stopped
        assert conn.events[0] == {"type": "started", "session_id": viewer_id, "portrait": False}

    _run(body)
    assert conn.results == [1]
    assert {"type": "page", "page": 9} in conn.events


def test_a_subscription_closed_while_the_app_starts_attaches_no_viewer(ws):
    conn = _Connection()

    async def body(hass):
        _FakeHost.on_start = lambda: conn.subscriptions[1]()
        await _subscribe(ws, hass, conn)

    _run(body)
    [host] = _FakeHost.instances
    assert host.viewers == {}
    assert not any(event["type"] == "started" for event in conn.events)


def test_previews_and_cards_of_a_device_share_one_app(ws):
    conn = _Connection()

    async def body(hass):
        await asyncio.gather(
            _subscribe(ws, hass, conn, msg_id=1),
            _subscribe(ws, hass, conn, msg_id=2),
            _render(ws, hass, conn, {"type": "grid", "key": "rooms"}, msg_id=3),
        )

    _run(body)
    [host] = _FakeHost.instances
    assert host.viewer_count == 2
    assert host.renders == [({"type": "grid", "key": "rooms"}, None)]


def test_an_app_that_fails_to_start_is_retried_by_the_next_use(ws):
    _FakeHost.fail_start = True
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        _FakeHost.fail_start = False
        await _subscribe(ws, hass, conn, msg_id=2)

    _run(body)
    assert {"type": "error", "message": "start_failed"} in conn.events
    assert [host.started for host in _FakeHost.instances] == [False, True]


def test_an_idle_app_without_viewers_stops(ws):
    conn = _Connection()

    async def body(hass):
        await _render(ws, hass, conn, {"type": "grid", "key": "rooms"})
        await _subscribe(ws, hass, conn, msg_id=2)
        hosts = ws._hosts(hass)
        hosts._idle_check(("entry1", "kitchen"))
        assert not _FakeHost.instances[0].stopped  # a viewer is attached
        conn.subscriptions[2]()
        hosts._idle_check(("entry1", "kitchen"))

    _run(body)
    assert _FakeHost.instances[0].stopped


def test_a_use_right_after_an_idle_stop_starts_a_new_app(ws):
    conn = _Connection()

    async def body(hass):
        await _render(ws, hass, conn, {"type": "grid", "key": "rooms"})
        # No viewer: the stop is scheduled, and a preview opens before it runs.
        ws._hosts(hass)._idle_check(("entry1", "kitchen"))
        await _subscribe(ws, hass, conn, msg_id=2)

    _run(body)
    first, second = _FakeHost.instances
    assert first.stopped
    assert not second.stopped
    assert second.viewer_count == 1


def test_render_returns_the_hub_output_and_reports_a_bad_panel(ws):
    conn = _Connection()
    results = []
    conn.send_result = lambda msg_id, result=None: results.append((msg_id, result))

    async def body(hass):
        await _render(ws, hass, conn, {"type": "grid", "key": "rooms"})
        await _render(ws, hass, conn, {"type": "bogus", "key": "x"}, msg_id=2)

    _run(body)
    assert results == [(1, {"page": 9, "before": [], "commands": ["cls 4226"]})]
    assert conn.errors == [(2, "invalid_panel")]


def test_render_by_key_uses_the_devices_configured_panel(ws):
    conn = _Connection()

    async def body(hass):
        await _render(ws, hass, conn, None, key="popup_notify")
        await _render(ws, hass, conn, None, msg_id=2, key="nope")
        await _render(ws, hass, conn, None, msg_id=3)

    _run(body)
    assert _FakeHost.instances[0].renders == [
        ({"type": "notify", "key": "popup_notify", "show_in_navigation": False}, None)
    ]
    assert conn.errors == [(2, "invalid_panel"), (3, "invalid_format")]


def test_a_save_reloads_the_hubs_apps_and_unload_stops_them(ws):
    conn = _Connection()
    store = {"devices": {"kitchen": {"config": {"home_panel": "rooms"}, "panels": []}}}

    async def body(hass):
        await _render(ws, hass, conn, {"type": "grid", "key": "rooms"})
        await ws.async_reload_hosts(hass, "entry1", store)
        host = _FakeHost.instances[0]
        assert host.reloads[0]["device"]["home_panel"] == "rooms"
        await ws.async_stop_hosts(hass, "entry1")
        assert host.stopped

    _run(body)


def test_event_forwards_allowed_events_and_rejects_others(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        [sid] = _FakeHost.instances[0].viewers
        await ws.ws_event(
            hass, conn, {"id": 2, "session_id": sid, "name": "esphome.component", "value": "9,12,0"}
        )
        await ws.ws_event(
            hass, conn, {"id": 3, "session_id": sid, "name": "esphome.connected", "value": ""}
        )
        await ws.ws_event(hass, conn, {"id": 4, "session_id": "gone", "name": "x", "value": ""})

    _run(body)
    assert _FakeHost.instances[0].events == [("esphome.component", "9,12,0")]
    assert conn.errors == [(3, "invalid_event"), (4, "not_found")]


def test_home_opens_the_home_panel_for_the_preview_session(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        [session_id] = _FakeHost.instances[0].viewers
        await ws.ws_home(hass, conn, {"id": 2, "session_id": session_id})

    _run(body)
    assert _FakeHost.instances[0].home_count == 1
    assert conn.results == [1, 2]


def test_open_shows_a_panel_of_the_device_and_reports_an_unknown_key(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        [sid] = _FakeHost.instances[0].viewers
        await ws.ws_open(hass, conn, {"id": 2, "session_id": sid, "key": "sleep", "idle": True})
        await ws.ws_open(hass, conn, {"id": 3, "session_id": sid, "key": "missing", "idle": False})
        await ws.ws_open(hass, conn, {"id": 4, "session_id": "gone", "key": "sleep", "idle": False})

    _run(body)
    assert _FakeHost.instances[0].opened == [("sleep", True)]
    assert conn.results == [1, 2]
    assert conn.errors == [(3, "invalid_panel"), (4, "not_found")]


def test_idle_opens_the_idle_page_for_the_preview_session(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        [session_id] = _FakeHost.instances[0].viewers
        await ws.ws_idle(hass, conn, {"id": 2, "session_id": session_id})

    _run(body)
    assert _FakeHost.instances[0].idle_count == 1
    assert conn.results == [1, 2]


def test_reset_sandbox_clears_simulated_states_for_the_preview_session(ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(ws, hass, conn)
        [session_id] = _FakeHost.instances[0].viewers
        await ws.ws_reset_sandbox(hass, conn, {"id": 2, "session_id": session_id})

    _run(body)
    assert _FakeHost.instances[0].reset_count == 1
    assert conn.results == [1, 2]

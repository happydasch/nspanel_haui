"""Tests for the dashboard card's WebSocket commands (``web/card.py``)."""

from __future__ import annotations

import importlib
import sys
import types

import pytest
from test_live_panel import _FakeLive
from test_websocket_api import (
    _Connection,
    _FakeHost,
    _run,
    ws,  # noqa: F401
)


@pytest.fixture
def card(request, monkeypatch):
    """The card module, with ``require_admin`` marking the commands it guards."""
    ws_module = request.getfixturevalue("ws")
    stub = sys.modules["homeassistant.components.websocket_api"]

    def require_admin(fn):
        fn.admin_only = True
        return fn

    stub.require_admin = require_admin
    importlib.reload(ws_module)
    import custom_components.nspanel_haui.web.card as module
    import custom_components.nspanel_haui.web.preview.live_panel as live_panel

    importlib.reload(live_panel)
    module = importlib.reload(module)
    monkeypatch.setattr(module, "LivePanel", _FakeLive)
    _FakeLive.instances = []
    module.live_panel = live_panel
    module.ws = ws_module
    return module


class _App:
    def __init__(self, portrait=False):
        self.device = types.SimpleNamespace(is_portrait=portrait, device_info={})

    async def async_run_on_worker(self, fn):
        return fn()


def _with_apps(card, hass, apps):
    hass.data[card.DOMAIN] = {"entry1": apps}


def _with_devices(card, hass, *names):
    """The hub's devices, as its config entry lists them."""
    hass.entry.data["devices"] = [{"name": name} for name in names]


def _store(card, monkeypatch, devices):
    """What the panel store holds: each device's settings, ``enabled`` included."""
    from custom_components.nspanel_haui.hub import storage

    class _PanelStore:
        async def async_load(self):
            return {"version": 1, "devices": devices}

    monkeypatch.setattr(storage, "panel_store", lambda hass, entry_id: _PanelStore())


def _subscribe(card, kind, hass, conn, msg_id=1, device="kitchen", **target):
    command = card.ws_home_subscribe if kind == "home" else card.ws_live_subscribe
    return command(hass, conn, {"id": msg_id, "entry_id": "entry1", "device": device, **target})


def _device_ids(card, monkeypatch, mapping):
    """Resolve the panel's Home Assistant device id from this test's map."""
    monkeypatch.setattr(card, "resolve_ha_device_id", lambda hass, name: mapping.get(name))


def test_card_commands_are_open_to_every_user_and_the_editors_stay_admin_only(card):
    hass = types.SimpleNamespace()
    card.ws.async_register_websocket_commands(hass)
    card.live_panel.async_register_commands(hass)
    card.async_register_commands(hass)

    registered = sys.modules["homeassistant.components.websocket_api"].registered
    open_types = [fn.schema["type"] for fn in registered if not getattr(fn, "admin_only", False)]
    assert open_types == [
        "nspanel_haui/card/devices",
        "nspanel_haui/card/home/subscribe",
        "nspanel_haui/card/live/subscribe",
    ]
    assert len(registered) > len(open_types)


def test_devices_lists_the_hubs_devices_disabled_ones_included(card, monkeypatch):
    """A disabled device is still selectable; its card says why it shows nothing."""
    conn = _Connection()
    _device_ids(card, monkeypatch, {"kitchen": "ha-device-1"})
    _store(card, monkeypatch, {"hall": {"config": {"enabled": False}}})

    async def body(hass):
        _with_devices(card, hass, "kitchen", "hall", "attic")
        _with_apps(card, hass, {"kitchen": _App()})
        await card.ws_devices(hass, conn, {"id": 1})

    _run(body)
    assert conn.payloads[1] == [
        {"entry_id": "entry1", "name": "kitchen", "device_id": "ha-device-1", "enabled": True},
        {"entry_id": "entry1", "name": "hall", "device_id": None, "enabled": False},
        {"entry_id": "entry1", "name": "attic", "device_id": None, "enabled": True},
    ]


@pytest.mark.parametrize("kind", ["home", "live"])
def test_a_card_of_a_disabled_device_is_told_apart_from_one_that_is_starting(
    card, kind, monkeypatch
):
    """A disabled device has no live screen; its home render needs no app."""
    conn = _Connection()
    _store(card, monkeypatch, {"kitchen": {"config": {"enabled": False}}})

    async def body(hass):
        _with_apps(card, hass, {})
        await _subscribe(card, kind, hass, conn)

    _run(body)
    if kind == "home":
        # The hub renders the panels from the store: the card keeps its screen.
        assert conn.results == [1]
        [host] = _FakeHost.instances
        assert host.followed is None, "a device that does not run reports no metadata"
        assert host.panel_from is None, "and no state of its own"
        assert len(host.home.viewers) == 1
    else:
        assert conn.errors == [(1, "disabled")]
        assert _FakeHost.instances == []
    assert _FakeLive.instances == []


@pytest.mark.parametrize("kind", ["home", "live"])
def test_a_card_finds_its_device_by_its_home_assistant_device_id(card, kind, monkeypatch):
    """The card editor stores the panel's own device id, so a rename keeps the dashboard working."""
    conn = _Connection()
    running = _App()
    _device_ids(card, monkeypatch, {"kitchen": "ha-device-1"})

    async def body(hass):
        _with_apps(card, hass, {"kitchen": running})
        # The name is the one the card was set up with; the id is what wins.
        await _subscribe(card, kind, hass, conn, device="old-name", device_id="ha-device-1")

    _run(body)
    assert conn.results == [1]
    if kind == "home":
        assert _FakeHost.instances[0].panel_from is running
    else:
        assert _FakeLive.instances[0].source is running


@pytest.mark.parametrize("kind", ["home", "live"])
def test_a_card_with_an_unknown_device_id_is_refused_like_an_unknown_name(card, kind, monkeypatch):
    conn = _Connection()
    _device_ids(card, monkeypatch, {"kitchen": "ha-device-1"})

    async def body(hass):
        _with_apps(card, hass, {"kitchen": _App()})
        await _subscribe(card, kind, hass, conn, device_id="ha-device-2")

    _run(body)
    assert conn.errors == [(1, "not_found")]
    assert _FakeHost.instances == []
    assert _FakeLive.instances == []


@pytest.mark.parametrize("kind", ["home", "live"])
def test_a_card_subscription_needs_a_device_id_or_an_entry_and_device(card, kind):
    conn = _Connection()

    async def body(hass):
        _with_apps(card, hass, {"kitchen": _App()})
        command = card.ws_home_subscribe if kind == "home" else card.ws_live_subscribe
        await command(hass, conn, {"id": 1})

    _run(body)
    assert conn.errors == [(1, "invalid_format")]


@pytest.mark.parametrize("kind", ["home", "live"])
def test_a_card_needs_the_devices_running_app(card, kind):
    conn = _Connection()

    async def body(hass):
        await _subscribe(card, kind, hass, conn)

    _run(body)
    assert conn.errors == [(1, "not_found")]
    assert _FakeHost.instances == []
    assert _FakeLive.instances == []


def test_a_home_card_watches_the_devices_home_stream_until_it_unsubscribes(card):
    conn = _Connection()
    running = _App()

    async def body(hass):
        _with_apps(card, hass, {"kitchen": running})
        await _subscribe(card, "home", hass, conn)
        [host] = _FakeHost.instances
        assert host.followed is running
        assert host.panel_from is running
        [(viewer_id, sink)] = host.home.viewers.items()
        sink({"type": "page", "page": 9})
        conn.subscriptions[1]()
        assert host.home.viewers == {}
        assert host.viewers == {}

    _run(body)
    assert conn.results == [1]
    assert conn.events == [{"type": "page", "page": 9}]


def test_a_live_card_mirrors_the_running_app_without_an_input_session(card):
    conn = _Connection()

    async def body(hass):
        _with_apps(card, hass, {"kitchen": _App()})
        await _subscribe(card, "live", hass, conn)
        [viewer] = _FakeLive.instances
        assert viewer.source is hass.data[card.DOMAIN]["entry1"]["kitchen"]
        event = {"session_id": viewer.session_id, "name": "esphome.component", "value": "9,12,0"}
        await card.live_panel.ws_event(hass, conn, {"id": 2, **event})
        await card.live_panel.ws_action(
            hass, conn, {"id": 3, "session_id": viewer.session_id, "action": "idle"}
        )
        conn.subscriptions[1]()
        assert viewer.stopped

    _run(body)
    [viewer] = _FakeLive.instances
    assert viewer.calls == []
    assert conn.errors == [(2, "not_found"), (3, "not_found")]


def test_an_unloading_hub_ends_its_live_cards(card):
    conn = _Connection()

    async def body(hass):
        _with_apps(card, hass, {"kitchen": _App()})
        await _subscribe(card, "live", hass, conn)
        await card.async_end_live_viewers(hass, "other")
        assert not _FakeLive.instances[0].stopped
        await card.async_end_live_viewers(hass, "entry1")
        # The card unsubscribes once it is told; that finds nothing left to stop.
        conn.subscriptions[1]()

    _run(body)
    assert _FakeLive.instances[0].stopped
    assert conn.events[-1] == {"type": "ended"}

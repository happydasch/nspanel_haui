"""Tests for the home stream: a device's home panel, running for dashboard cards.

The stream runs on a real virtual app (``VirtualPanelHost``), so the page,
its state listeners and its output are the hub's own.
"""

from __future__ import annotations

import sys
import types

import pytest
from test_virtual_panel import (
    GRID_PAGE_ID,
    _commands,
    _config,
    _run,
    _State,
    _tap_power,
    _wait,
)
from test_virtual_panel import env as _env_fixture  # noqa: F401

import custom_components.nspanel_haui as nspanel_haui
from custom_components.nspanel_haui.haui.controller.esphome import command_target
from custom_components.nspanel_haui.web.preview.virtual_panel import VirtualPanelHost

LIGHT_PAGE_ID = 13
GRID = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
STARTED = {"type": "started", "portrait": False}


@pytest.fixture
def states(env, monkeypatch):
    """Real state changes, delivered to the hub's listeners as Home Assistant does."""
    listeners: dict[str, list] = {}
    event = sys.modules["homeassistant.helpers.event"]

    def track(hass, entity_ids, cb):
        ids = [entity_ids] if isinstance(entity_ids, str) else list(entity_ids)
        for entity_id in ids:
            listeners.setdefault(entity_id, []).append(cb)

        def remove():
            for entity_id in ids:
                listeners[entity_id].remove(cb)

        return remove

    monkeypatch.setattr(event, "async_track_state_change_event", track)

    def change(entity_id, state, attributes):
        old = env._states.get(entity_id)
        new = _State(state, attributes)
        env._states[entity_id] = new
        data = {"entity_id": entity_id, "old_state": old, "new_state": new}

        def fire():
            for cb in list(listeners.get(entity_id, [])):
                cb(types.SimpleNamespace(data=data))

        env.loop.call_soon_threadsafe(fire)

    return types.SimpleNamespace(listeners=listeners, change=change)


def _host(env, config):
    host = VirtualPanelHost(env, "kitchen", config)
    _run(env, host.async_start())
    return host


def _watch(env, host, viewer_id="card"):
    messages: list[dict] = []
    env.loop.call_soon_threadsafe(lambda: host.home.attach(viewer_id, messages.append))
    return messages


def _last(commands, target):
    return next(c for c in reversed(commands) if command_target(c) == target)


def _drawn(messages):
    return 'g1Name.txt="Lamp"' in _commands(messages)


def test_a_card_sees_the_home_panel_without_moving_the_sandbox(env):
    host = _host(env, _config())
    sandbox: list[dict] = []
    env.loop.call_soon_threadsafe(lambda: host.attach("sandbox", sandbox.append))
    _wait(lambda: _drawn(sandbox))
    navigation = host.app.controller["navigation"]
    sandbox_panel = navigation.panel
    sandbox_pages = [m for m in sandbox if m["type"] == "page"]

    cards = _watch(env, host)

    _wait(lambda: _drawn(cards))
    assert cards[0] == STARTED
    assert {"type": "page", "page": GRID_PAGE_ID} in cards
    assert navigation.panel is sandbox_panel
    assert [m for m in sandbox if m["type"] == "page"] == sandbox_pages
    _run(env, host.async_stop())


def test_the_home_panel_follows_a_real_state_change(env, states):
    host = _host(env, _config())
    cards = _watch(env, host)
    _wait(lambda: _drawn(cards))
    off = _last(_commands(cards), "g1Icon.txt")

    states.change("light.lamp", "on", {"friendly_name": "Lamp", "brightness": 200})

    _wait(lambda: _last(_commands(cards), "g1Icon.txt") != off)
    on = _run(env, host.async_render(GRID))
    assert _last(_commands(cards), "g1Icon.txt") == _last(on["commands"], "g1Icon.txt")
    _run(env, host.async_stop())


def test_the_home_panel_never_shows_simulated_states(env):
    host = _host(env, _config())
    sandbox: list[dict] = []
    host.messages = sandbox
    env.loop.call_soon_threadsafe(lambda: host.attach("sandbox", sandbox.append))
    cards = _watch(env, host)
    _wait(lambda: _drawn(sandbox) and _drawn(cards))
    off = _last(_commands(cards), "g1Icon.txt")

    _tap_power(host)

    _wait(lambda: host.app.sandbox.is_simulated("light.lamp"))
    _wait(lambda: any(c.startswith("g1Icon.txt=") and c != off for c in _commands(sandbox)))
    late = _watch(env, host, "late")
    _wait(lambda: _drawn(late))
    assert _last(_commands(late), "g1Icon.txt") == off
    assert all(c == off for c in _commands(cards) if c.startswith("g1Icon.txt="))
    _run(env, host.async_stop())


def test_a_late_card_gets_the_running_page_one_write_per_target(env):
    host = _host(env, _config())
    first = _watch(env, host, "first")
    _wait(lambda: _drawn(first))

    late = _watch(env, host, "late")

    _wait(lambda: _drawn(late))
    assert late[0] == STARTED
    page = late.index({"type": "page", "page": GRID_PAGE_ID})
    drawn = _commands(late[page + 1 :])
    assert len({command_target(c) for c in drawn}) == len(drawn)
    _run(env, host.async_stop())


def test_the_last_card_stops_the_home_panel(env, states):
    host = _host(env, _config())
    cards = _watch(env, host)
    _wait(lambda: _drawn(cards))
    assert states.listeners["light.lamp"]

    env.loop.call_soon_threadsafe(lambda: host.home.detach("card"))

    _wait(lambda: not states.listeners["light.lamp"])
    assert host.home.viewer_count == 0
    _run(env, host.async_stop())


def test_a_save_shows_the_new_home_panel(env):
    light = {"type": "light", "key": "light_0", "item": {"item": "light.lamp"}}
    host = _host(env, _config([light]))
    cards = _watch(env, host)
    _wait(lambda: _drawn(cards))
    cards.clear()

    _run(env, host.async_reload(_config([light], home_panel="light_0")))

    _wait(lambda: {"type": "page", "page": LIGHT_PAGE_ID} in cards)
    assert cards[0] == STARTED
    _run(env, host.async_stop())


def test_a_device_without_panels_shows_what_the_panel_shows_until_a_save_adds_one(env):
    def config(panels):
        return nspanel_haui._build_config_dict(
            {"name": "Hub", "devices": [{"name": "kitchen"}]},
            {"devices": {"kitchen": {"config": {}, "panels": panels}}},
            device_name="kitchen",
        )

    host = _host(env, config([]))
    home = host.app.controller["navigation"].home_panel
    cards = _watch(env, host)
    _wait(lambda: any(m["type"] == "page" for m in cards))
    assert cards[0] == STARTED
    assert {
        "type": "page",
        "page": _run(env, host.async_render(home.get_default_config()))["page"],
    } in cards
    cards.clear()

    _run(env, host.async_reload(config([GRID])))

    _wait(lambda: _drawn(cards))
    assert cards[0] == STARTED
    _run(env, host.async_stop())


def test_a_stopping_host_ends_its_cards(env):
    host = _host(env, _config())
    cards = _watch(env, host)
    _wait(lambda: _drawn(cards))

    _run(env, host.async_stop())

    assert cards[-1] == {"type": "ended"}


def test_the_home_panel_asks_home_assistant_for_its_weather_forecast(env):
    env._states["weather.home"] = _State("rainy", {"temperature": 14.6})
    weather = {
        "type": "weather",
        "key": "weather_0",
        "item": {"item": "weather.home"},
        "forecast_type": "daily",
    }
    host = _host(env, _config([weather], home_panel="weather_0"))

    cards = _watch(env, host)

    _wait(lambda: any(call[:2] == ("weather", "get_forecasts") for call in env.services.calls))
    assert cards[0] == STARTED
    _run(env, host.async_stop())

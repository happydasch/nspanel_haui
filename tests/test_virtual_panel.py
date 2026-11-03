"""End-to-end tests for the editor's virtual panel.

A real event loop runs in a background thread, as in Home Assistant, and the
full ``NSPanelHAUI`` boots against a virtual device: the handshake, page
switches, rendering and touch handling are the real hub code paths.
"""

from __future__ import annotations

import asyncio
import datetime
import sys
import threading
import time
import types

import nspanel_haui
import pytest
from nspanel_haui.haui.mapping.const import ESPEvent
from nspanel_haui.virtual_panel import InertUpdateController, VirtualPanelSession

GRID_PAGE_ID = 9
G1_POWER = 12


class _State:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes
        self.last_updated = None


class _Services:
    def __init__(self):
        self.calls = []

    async def async_call(self, domain, service, service_data=None, target=None, **kwargs):
        self.calls.append((domain, service, service_data, target))


class _Hass:
    def __init__(self, loop, states):
        self.loop = loop
        self._states = states
        self.states = types.SimpleNamespace(get=self._states.get)
        self.services = _Services()
        self.fired = []
        self.bus = types.SimpleNamespace(
            async_listen=lambda *a: lambda: None,
            async_fire=lambda event_type, data: self.fired.append(event_type),
        )
        self.config = types.SimpleNamespace(
            units=types.SimpleNamespace(temperature_unit="°C"), time_zone="UTC"
        )
        self.data = {}

    def async_add_executor_job(self, fn, *args):
        return self.loop.run_in_executor(None, fn, *args)


@pytest.fixture
def env(monkeypatch):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = lambda hass, entity_id, cb: lambda: None
    # Timers run for real (page settle delays are 0.1 s); intervals never fire.
    event.async_call_later = lambda hass, delay, cb: loop.call_later(delay, cb, None).cancel
    event.async_track_time_interval = lambda hass, cb, interval: lambda: None
    registry = types.ModuleType("homeassistant.helpers.entity_registry")
    registry.async_get = lambda hass: None
    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.now = lambda: datetime.datetime.now(datetime.UTC)
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt_util)
    monkeypatch.setattr(sys.modules["homeassistant.util"], "dt", dt_util, False)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.event", event)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", registry)
    monkeypatch.setattr(sys.modules["homeassistant.helpers"], "entity_registry", registry, False)
    core = types.ModuleType("homeassistant.core")
    core.callback = lambda fn: fn
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)

    hass = _Hass(loop, {"light.lamp": _State("off", {"friendly_name": "Lamp"})})
    yield hass
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)


def _config():
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    return nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "grid_0"}, "panels": [grid]}}},
        device_name="kitchen",
    )


def _wait(cond, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


def _run(hass, coro):
    return asyncio.run_coroutine_threadsafe(coro, hass.loop).result(timeout=5)


def _commands(messages):
    return [c for m in messages if m["type"] == "commands" for c in m["commands"]]


@pytest.fixture
def session(env):
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", _config(), messages.append)
    sess.messages = messages
    _run(env, sess.async_start())
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: any(c.startswith("g1Name.txt=") for c in _commands(messages)))
    yield sess
    _run(env, sess.async_stop())


def _tap_power(session):
    session.messages.clear()
    session.send_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},1")
    session.send_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},0")


def test_boots_through_the_handshake_to_the_home_panel(session, env):
    assert session.app.controller["connection"].is_connected
    assert 'g1Name.txt="Lamp"' in _commands(session.messages)


def test_sandbox_tap_changes_only_simulated_state(session, env):
    _tap_power(session)

    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))
    assert session.app.sandbox.get("light.lamp").state == "on"
    assert env.services.calls == []
    assert env.states.get("light.lamp").state == "off"
    _wait(lambda: {"type": "sandbox", "entities": ["light.lamp"]} in session.messages)
    # The tile re-renders from the simulated state change.
    _wait(lambda: any(c.startswith("g1") for c in _commands(session.messages)))



def test_reset_sandbox_restores_real_state_without_changing_mode(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.get("light.lamp").state == "on")
    session.app.live = True

    session.app.reset_sandbox()

    _wait(lambda: not session.app.sandbox.is_simulated("light.lamp"))
    assert session.app.sandbox.get("light.lamp").state == "off"
    assert session.app.live is True
    assert env.services.calls == []


def test_old_protocol_does_not_receive_entity_or_idle_metadata(env):
    messages: list[dict] = []
    session = VirtualPanelSession(env, "kitchen", _config(), messages.append, protocol_version=1)
    _run(env, session.async_start())
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)

    proxy = session.app.virtual_esphome
    proxy._sink({"type": "entities", "map": {"g1Overlay": "light.lamp"}})
    proxy._sink({"type": "idle", "active": True})
    proxy._sink({"type": "page", "page": GRID_PAGE_ID})

    assert {"type": "page", "page": GRID_PAGE_ID} in messages
    assert not any(message["type"] in {"entities", "idle"} for message in messages)
    _run(env, session.async_stop())


def test_live_mode_calls_home_assistant(session, env):
    session.set_live(True)
    _tap_power(session)

    _wait(lambda: env.services.calls)
    domain, service, _data, target = env.services.calls[0]
    assert (domain, service, target) == ("light", "turn_on", {"entity_id": "light.lamp"})
    assert not session.app.sandbox.is_simulated("light.lamp")



@pytest.mark.parametrize("selector", ["area_id", "device_id", "floor_id", "label_id"])
@pytest.mark.parametrize("return_response", [False, True])
def test_live_mode_refuses_unresolved_service_target_selectors(
    session, env, selector, return_response
):
    session.app.live = True
    session.app._protected = frozenset({"switch.kitchen_use_auto_dim"})

    session.app.call_service(
        "switch.turn_off", target={selector: "panel-target"}, return_response=return_response
    )

    assert env.services.calls == []
    assert session.app.sandbox.simulated_ids() == []

def test_live_mode_still_sandboxes_the_real_devices_own_entities(env):
    messages: list[dict] = []
    sess = VirtualPanelSession(
        env,
        "kitchen",
        _config(),
        messages.append,
        protected_entities=frozenset({"light.lamp"}),
        live=True,
    )
    _run(env, sess.async_start())
    _wait(lambda: any(c.startswith("g1Name.txt=") for c in _commands(messages)))
    sess.messages = messages
    _tap_power(sess)

    _wait(lambda: sess.app.sandbox.is_simulated("light.lamp"))
    assert env.services.calls == []
    _run(env, sess.async_stop())


def test_going_live_drops_the_simulated_states(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))

    session.set_live(True)

    _wait(lambda: {"type": "sandbox", "entities": []} in session.messages)
    assert session.app.sandbox.get("light.lamp").state == "off"


def test_no_bus_events_reach_automations(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))
    assert env.fired == []


def test_updates_are_never_checked_or_installed(session):
    update = session.app.controller["update"]
    assert isinstance(update, InertUpdateController)
    assert update.install_tft()["state"] == "error"
    assert session.app.virtual_esphome.publish("upload_tft_url", "http://x/y.tft") is False
    assert session.app.virtual_esphome.publish("install_firmware_url", "http://x/y.bin") is False


def test_only_events_a_person_can_cause_are_accepted(session):
    with pytest.raises(ValueError):
        session.send_event(ESPEvent.CONNECTED, "")
    with pytest.raises(ValueError):
        session.send_event("esphome.res_device_state", "{}")


def test_read_requests_go_to_the_browser_and_its_answer_is_accepted(session):
    session.messages.clear()
    assert session.app.virtual_esphome.publish("req_val", "hBrightness") is True
    assert {"type": "request", "kind": "val", "name": "hBrightness"} in session.messages

    session.send_event(
        "esphome.read_response", '{"name": "hBrightness", "type": "number", "value": 42}'
    )


def test_a_slider_release_reads_the_value_from_the_browser_and_applies_it(env):
    env._states["light.lamp"] = _State(
        "on", {"friendly_name": "Lamp", "brightness": 50, "supported_color_modes": ["brightness"]}
    )
    light = {"type": "light", "key": "light_0", "item": {"item": "light.lamp"}}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "light_0"}, "panels": [light]}}},
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", cfg, messages.append)
    _run(env, sess.async_start())
    _wait(lambda: {"type": "page", "page": 13} in messages)
    _wait(lambda: any(c.startswith("hBrightness.val=") for c in _commands(messages)))
    slider = sess.app.controller["navigation"].page.COMPONENTS.h_brightness

    # What the browser sends for a press-drag-release on the slider ...
    sess.send_event(ESPEvent.COMPONENT, f"13,{slider.id},1")
    sess.send_event(ESPEvent.COMPONENT, f"13,{slider.id},0")
    request = {"type": "request", "kind": "val", "name": slider.name}
    _wait(lambda: request in messages)
    # ... and its answer to the hub's read request.
    sess.send_event(
        "esphome.read_response", f'{{"name": "{slider.name}", "type": "number", "value": 100}}'
    )

    _wait(lambda: (sess.app.sandbox.get("light.lamp").attributes.get("brightness")) == 255)
    assert env.services.calls == []
    _run(env, sess.async_stop())


def test_a_long_press_on_a_clock_goes_back_home(env):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    clock = {"type": "clock", "key": "clock_0", "long_press_back": True}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "grid_0"}, "panels": [grid, clock]}}},
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", cfg, messages.append)
    _run(env, sess.async_start())
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)

    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    _wait(lambda: {"type": "page", "page": 7} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)
    messages.clear()

    sess.send_event(ESPEvent.TOUCH_START, "")
    time.sleep(1.0)
    sess.send_event(ESPEvent.TOUCH_END, "200,150,202,151")

    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _run(env, sess.async_stop())


def test_the_browser_is_told_when_the_idle_page_starts_and_ends(env):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    clock = {"type": "clock", "key": "clock_0", "show_in_navigation": False}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {
                    "config": {"home_panel": "grid_0", "idle_panel": "clock_0"},
                    "panels": [grid, clock],
                }
            }
        },
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", cfg, messages.append)
    _run(env, sess.async_start())
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)
    assert not any(m["type"] == "idle" for m in messages)

    sess.send_event(ESPEvent.TIMEOUT, "page")
    _wait(lambda: {"type": "idle", "active": True} in messages)
    _wait(lambda: {"type": "page", "page": 7} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)

    # Past the idle-touch grace window: a touch leaves the idle page.
    time.sleep(1.2)
    sess.send_event(ESPEvent.TOUCH_START, "")
    _wait(lambda: {"type": "idle", "active": False} in messages)
    _run(env, sess.async_stop())


def _relay_session(env, live, use_relay=True):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {"config": {"use_relay_left": use_relay}, "panels": [grid]}
            }
        },
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", cfg, messages.append, live=live)
    _run(env, sess.async_start())
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    relays = {"Relay Left": "switch.kitchen_relay_left"}
    sess.app.device.find_esphome_entity_id = lambda domain, name: relays.get(name)
    return sess


def test_a_hardware_button_toggles_its_relay_in_the_sandbox(env):
    sess = _relay_session(env, live=False)
    sess.send_event(ESPEvent.BUTTON_LEFT, "1")
    sess.send_event(ESPEvent.BUTTON_LEFT, "0")
    _wait(lambda: sess.app.sandbox.is_simulated("switch.kitchen_relay_left"))
    assert sess.app.sandbox.get("switch.kitchen_relay_left").state == "on"
    assert env.services.calls == []
    _run(env, sess.async_stop())


def test_a_hardware_button_switches_the_real_relay_in_live_mode(env):
    sess = _relay_session(env, live=True)
    sess.send_event(ESPEvent.BUTTON_LEFT, "1")
    sess.send_event(ESPEvent.BUTTON_LEFT, "0")
    _wait(lambda: env.services.calls)
    domain, service, _data, target = env.services.calls[0]
    assert (domain, service, target) == (
        "switch",
        "toggle",
        {"entity_id": "switch.kitchen_relay_left"},
    )
    _run(env, sess.async_stop())


def test_without_relay_mode_the_button_leaves_the_relay_alone(env):
    sess = _relay_session(env, live=False, use_relay=False)
    sess.send_event(ESPEvent.BUTTON_LEFT, "1")
    sess.send_event(ESPEvent.BUTTON_LEFT, "0")
    time.sleep(0.3)
    assert not sess.app.sandbox.is_simulated("switch.kitchen_relay_left")
    _run(env, sess.async_stop())


def test_the_browser_learns_which_widgets_show_which_entity(env):
    env._states["weather.home"] = _State("rainy", {"temperature": 14.6})
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    clock = {
        "type": "clock",
        "key": "clock_0",
        "item": {"item": "weather.home"},
        "items": [{"item": "light.lamp"}],
    }
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "grid_0"}, "panels": [grid, clock]}}},
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", cfg, messages.append)
    _run(env, sess.async_start())
    _wait(lambda: {"type": "entities", "map": {"g1Overlay": "light.lamp"}} in messages)

    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    clock_map = {"#page": "weather.home", "bEntity1": "light.lamp"}
    _wait(lambda: {"type": "entities", "map": clock_map} in messages)
    _run(env, sess.async_stop())


def test_stop_cancels_every_listener_and_timer(env):
    messages: list[dict] = []
    sess = VirtualPanelSession(env, "kitchen", _config(), messages.append)
    _run(env, sess.async_start())
    _wait(lambda: any(c.startswith("g1Name.txt=") for c in _commands(messages)))

    _run(env, sess.async_stop())

    assert sess.app._state_handles == {}
    assert sess.app._timer_handles == {}

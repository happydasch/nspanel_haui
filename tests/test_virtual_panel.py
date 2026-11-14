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

import pytest

import custom_components.nspanel_haui as nspanel_haui
from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent
from custom_components.nspanel_haui.haui.mapping.icons import ICO_PASSWORD
from custom_components.nspanel_haui.haui.mapping.panel import get_user_panel_type_descriptors
from custom_components.nspanel_haui.haui.page.alarm import AlarmPage
from custom_components.nspanel_haui.web.preview.virtual_panel import (
    InertUpdateController,
    VirtualPanelHost,
)

GRID_PAGE_ID = 9
UNLOCK_PAGE_ID = 17
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
        self.states = types.SimpleNamespace(
            get=self._states.get,
            async_entity_ids=lambda domain: [e for e in self._states if e.startswith(f"{domain}.")],
        )
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


@pytest.fixture(name="env")
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


def _config(extra_panels=(), *, idle_panel=None):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    device_config = {"home_panel": "grid_0"}
    if idle_panel:
        device_config.update(idle_panel=idle_panel, use_auto_page=True)
    return nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {
                    "config": device_config,
                    "panels": [grid, *extra_panels],
                }
            }
        },
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


def _open(env, config, sink, **kwargs):
    """Start the device's virtual app and attach one sandbox viewer to it."""
    host = VirtualPanelHost(env, "kitchen", config, **kwargs)
    _run(env, host.async_start())
    env.loop.call_soon_threadsafe(lambda: host.attach("viewer", sink))
    return host


def _commands(messages):
    return [c for m in messages if m["type"] == "commands" for c in m["commands"]]


@pytest.fixture
def session(env):
    messages: list[dict] = []
    sess = _open(env, _config(), messages.append)
    sess.messages = messages
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: any(c.startswith("g1Name.txt=") for c in _commands(messages)))
    yield sess
    _run(env, sess.async_stop())


def _tap_power(session):
    session.messages.clear()
    session.send_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},1")
    session.send_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},0")


def _process_virtual_event(env, session, name, value):
    _run(env, session.app.async_run_on_worker(session.app.callback_event, HAUIEvent(name, value)))


@pytest.mark.parametrize("initial_state", ["idle", "paused"])
def test_grid_power_button_simulates_inactive_media_player_as_playing(env, initial_state):
    media = {
        "type": "grid",
        "key": "grid_0",
        "items": [{"item": "media_player.tv", "show_power_button": True}],
    }
    config = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "grid_0"}, "panels": [media]}}},
        device_name="kitchen",
    )
    env._states["media_player.tv"] = _State(initial_state, {"friendly_name": "TV"})
    messages: list[dict] = []
    session = _open(env, config, messages.append)
    session.messages = messages
    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        _wait(lambda: any('g1Name.txt="TV"' in cmd for cmd in _commands(messages)))
        _tap_power(session)

        _wait(lambda: session.app.sandbox.is_simulated("media_player.tv"))
        assert session.app.sandbox.get("media_player.tv").state == "playing"

        _tap_power(session)
        _wait(lambda: session.app.sandbox.get("media_player.tv").state == "idle")
    finally:
        _run(env, session.async_stop())


def test_boots_through_the_handshake_to_the_home_panel(session, env):
    assert session.app.controller["connection"].is_connected
    assert 'g1Name.txt="Lamp"' in _commands(session.messages)


def test_live_preview_publishes_relay_states_and_tracks_sandbox_toggles(session, env):
    relay_entities = {"Relay Left": "switch.relay_left", "Relay Right": "switch.relay_right"}
    env._states.update(
        {
            "switch.relay_left": _State("off", {}),
            "switch.relay_right": _State("on", {}),
        }
    )
    session.app.find_entity_id = lambda domain, name: (
        relay_entities.get(name) if domain == "switch" else None
    )

    _run(env, session.app.async_run_on_worker(session.app.start_relay_state_tracking))
    no_entities = {"left": None, "right": None}
    expected = {"type": "relays", "left": "off", "right": "on", "entities": no_entities}
    _wait(lambda: expected in session.messages)

    _run(
        env,
        session.app.async_run_on_worker(
            lambda: session.app.call_service(
                "switch/toggle", target={"entity_id": "switch.relay_left"}
            )
        ),
    )
    _wait(
        lambda: (
            {"type": "relays", "left": "on", "right": "on", "entities": no_entities}
            in session.messages
        )
    )


def test_live_preview_button_light_shows_its_entity_without_relay_mode(session, env):
    """With relay mode off, a button's light shows the entity it switches."""
    env._states.update({"switch.relay_left": _State("off", {}), "light.lamp": _State("on", {})})
    session.app.find_entity_id = lambda domain, name: (
        "switch.relay_left" if (domain, name) == ("switch", "Relay Left") else None
    )

    def entity_mode():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = "light.lamp"
        session.app.start_relay_state_tracking()

    _run(env, session.app.async_run_on_worker(entity_mode))
    _wait(
        lambda: (
            {
                "type": "relays",
                "left": "off",
                "right": "unknown",
                "entities": {"left": "on", "right": None},
            }
            in session.messages
        )
    )

    _run(
        env,
        session.app.async_run_on_worker(
            lambda: session.app.call_service("light/toggle", target={"entity_id": "light.lamp"})
        ),
    )
    _wait(
        lambda: (
            {
                "type": "relays",
                "left": "off",
                "right": "unknown",
                "entities": {"left": "off", "right": None},
            }
            in session.messages
        )
    )


def test_live_preview_button_indicator_shows_any_entity_kind(session, env):
    """A hardware button indicator reflects its configured entity's domain-specific state."""
    env._states["switch.relay_left"] = _State("off", {})
    session.app.find_entity_id = lambda domain, name: (
        "switch.relay_left" if (domain, name) == ("switch", "Relay Left") else None
    )
    cases = [
        ("switch.pump", "on", "on"),
        ("binary_sensor.window", "off", "off"),
        ("media_player.tv", "playing", "on"),
        ("media_player.tv", "paused", "off"),
        ("climate.ac", "heat", "on"),
        ("climate.ac", "off", "off"),
        ("vacuum.robot", "cleaning", "on"),
        ("vacuum.robot", "docked", "off"),
        ("lock.door", "unlocked", "on"),
        ("lock.door", "locked", "off"),
        ("alarm_control_panel.home", "armed_away", "on"),
        ("alarm_control_panel.home", "disarmed", "off"),
        ("timer.egg", "active", "on"),
        ("scene.morning", "2026-11-08T10:00:00+00:00", "unknown"),
        ("binary_sensor.window", "unavailable", "unknown"),
    ]

    for entity_id, state, expected in cases:
        env._states[entity_id] = _State(state, {})

        def configure(entity_id=entity_id):
            session.app.device.config["use_relay_left"] = False
            session.app.device.config["button_left_entity"] = entity_id
            session.app.start_relay_state_tracking()

        session.messages.clear()
        _run(env, session.app.async_run_on_worker(configure))
        message = {
            "type": "relays",
            "left": "off",
            "right": "unknown",
            "entities": {"left": expected, "right": None},
        }
        _wait(lambda message=message: message in session.messages)


def _press_button(session, side: str) -> None:
    event = ESPEvent.BUTTON_LEFT if side == "left" else ESPEvent.BUTTON_RIGHT
    session.send_event(event, "1")
    session.send_event(event, "0")


def test_hardware_button_simulates_relay_at_press_in_relay_mode(session, env):
    relay_id = "switch.relay_left"
    env._states[relay_id] = _State("off", {})
    session.app.find_entity_id = lambda domain, name: (
        relay_id if (domain, name) == ("switch", "Relay Left") else None
    )
    _run(env, session.app.async_run_on_worker(session.app.start_relay_state_tracking))

    session.send_event(ESPEvent.BUTTON_LEFT, "1")

    _wait(lambda: session.app.sandbox.is_simulated(relay_id))
    assert session.app.sandbox.get(relay_id).state == "on"
    assert session.app.sandbox.get("light.lamp").state == "off"
    assert env.services.calls == []

    session.send_event(ESPEvent.BUTTON_LEFT, "0")
    _wait(
        lambda: (
            {
                "type": "relays",
                "left": "on",
                "right": "unknown",
                "entities": {"left": None, "right": None},
            }
            in session.messages
        )
    )
    time.sleep(0.05)
    assert session.app.sandbox.get(relay_id).state == "on"


def test_hardware_button_simulates_configured_entity_on_release(session, env):
    relay_id = "switch.relay_left"
    entity_id = "light.lamp"
    env._states[relay_id] = _State("off", {})
    env._states[entity_id] = _State("off", {"friendly_name": "Lamp"})
    session.app.find_entity_id = lambda domain, name: (
        relay_id if (domain, name) == ("switch", "Relay Left") else None
    )

    def configure_entity_button():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = entity_id
        session.app.device._register_callbacks()
        session.app.start_relay_state_tracking()

    _run(env, session.app.async_run_on_worker(configure_entity_button))

    session.send_event(ESPEvent.BUTTON_LEFT, "1")
    _wait(lambda: session.app.device.device_info.get("button_left") == "1")
    assert not session.app.sandbox.is_simulated(entity_id)

    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: session.app.sandbox.is_simulated(entity_id))
    assert session.app.sandbox.get(entity_id).state == "on"
    assert not session.app.sandbox.is_simulated(relay_id)
    assert env.services.calls == []
    _wait(
        lambda: (
            {
                "type": "relays",
                "left": "off",
                "right": "unknown",
                "entities": {"left": "on", "right": None},
            }
            in session.messages
        )
    )


def test_hardware_button_simulates_configured_cover_and_tracks_position(session, env):
    relay_id = "switch.relay_left"
    cover_id = "cover.window"
    env._states[relay_id] = _State("off", {})
    env._states[cover_id] = _State("closed", {"current_position": 0})
    session.app.find_entity_id = lambda domain, name: (
        relay_id if (domain, name) == ("switch", "Relay Left") else None
    )

    def configure_cover_button():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = cover_id
        session.app.device._register_callbacks()
        session.app.start_relay_state_tracking()

    _run(env, session.app.async_run_on_worker(configure_cover_button))
    off = {
        "type": "relays",
        "left": "off",
        "right": "unknown",
        "entities": {"left": "off", "right": None},
    }
    _wait(lambda: off in session.messages)

    session.send_event(ESPEvent.BUTTON_LEFT, "1")
    _wait(lambda: session.app.device.device_info.get("button_left") == "1")
    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: session.app.sandbox.is_simulated(cover_id))
    opened = session.app.sandbox.get(cover_id)
    assert opened.state == "open"
    assert opened.attributes["current_position"] == 100
    on = {**off, "entities": {"left": "on", "right": None}}
    _wait(lambda: on in session.messages)

    session.send_event(ESPEvent.BUTTON_LEFT, "1")
    _wait(lambda: session.app.device.device_info.get("button_left") == "1")
    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: session.app.sandbox.get(cover_id).attributes["current_position"] == 0)
    closed = session.app.sandbox.get(cover_id)
    assert closed.state == "closed"
    assert closed.attributes["current_position"] == 0
    _wait(lambda: off in session.messages)


def test_sandbox_tap_changes_only_simulated_state(session, env):
    _tap_power(session)

    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))
    assert session.app.sandbox.get("light.lamp").state == "on"
    assert env.services.calls == []
    assert env.states.get("light.lamp").state == "off"
    # The tile re-renders from the simulated state change.
    _wait(lambda: any(c.startswith("g1") for c in _commands(session.messages)))


def test_reset_sandbox_drops_simulated_states(session, env):
    _wait(lambda: any(m == {"type": "sandbox", "changed": False} for m in session.messages))
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))
    _wait(lambda: any(m == {"type": "sandbox", "changed": True} for m in session.messages))

    session.reset_sandbox()

    _wait(lambda: not session.app.sandbox.is_simulated("light.lamp"))
    _wait(lambda: any(m == {"type": "sandbox", "changed": False} for m in session.messages))
    assert session.app.sandbox.get("light.lamp").state == "off"


def test_no_bus_events_reach_automations(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))
    assert env.fired == []


def test_updates_are_never_checked_or_installed(session):
    update = session.app.controller["update"]
    assert isinstance(update, InertUpdateController)
    assert update.install_tft()["state"] == "error"
    submitted: list = []
    session.app.submit_off_worker = lambda fn, *args, **kwargs: submitted.append(fn)
    results: list = []
    # A saved config, the display-model switch and the update endpoints
    # must not reach GitHub from a preview app.
    update.reload_options({**update.config, "enabled": True})
    update.start_async_check(on_complete=results.append)
    update.start_async_tft_install(None, None, results.append)
    update.start_async_firmware_install(None, None, results.append)
    update.start_async_list_tft_releases(results.append)
    update.start_async_list_firmware_releases(results.append)
    assert submitted == []
    assert len(results) == 5
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
    sess = _open(env, cfg, messages.append)
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
    sess = _open(env, cfg, messages.append)
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


def test_the_unlock_popup_takes_the_code_and_opens_the_locked_panel(env):
    clock = {"type": "clock", "key": "clock_0", "unlock_code": "1234"}
    messages: list[dict] = []
    sess = _open(env, _config([clock]), messages.append)
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)

    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    _wait(lambda: {"type": "page", "page": UNLOCK_PAGE_ID} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)

    def tap(component):
        sess.send_event(ESPEvent.COMPONENT, f"{UNLOCK_PAGE_ID},{component.id},1")
        sess.send_event(ESPEvent.COMPONENT, f"{UNLOCK_PAGE_ID},{component.id},0")

    keys = AlarmPage.COMPONENTS
    code = (keys.btn_key_1, keys.btn_key_2, keys.btn_key_3, keys.btn_key_4)
    for digits, component in enumerate(code, start=1):
        tap(component)
        # a release is buffered (tap or swipe), and the next one would replace it
        entered = f'tTitle.txt="{ICO_PASSWORD * digits}"'
        _wait(lambda entered=entered: entered in _commands(messages))
    tap(keys.b1_fnc)

    _wait(lambda: {"type": "page", "page": 7} in messages)
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
    sess = _open(env, cfg, messages.append)
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)
    assert not any(m["type"] == "idle" for m in messages)

    sess.show_idle()
    _wait(lambda: {"type": "idle", "active": True} in messages)
    _wait(lambda: {"type": "page", "page": 7} in messages)
    _wait(lambda: sess.app.controller["navigation"].page.started)

    # Past the idle-touch grace window: a touch leaves the idle page.
    time.sleep(1.2)
    sess.send_event(ESPEvent.TOUCH_START, "")
    _wait(lambda: {"type": "idle", "active": False} in messages)
    _run(env, sess.async_stop())


def test_the_idle_control_toggles_the_idle_page(env):
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
    sess = _open(env, cfg, messages.append)
    navigation = sess.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        sess.show_idle()
        _wait(lambda: {"type": "idle", "active": True} in messages)
        _wait(lambda: navigation.panel.get("key") == "clock_0")
        messages.clear()

        sess.show_idle()

        _wait(lambda: {"type": "idle", "active": False} in messages)
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        assert navigation.panel.get("key") == "grid_0"
        # A wake is an interaction: the idle page is not due again at once.
        assert time.monotonic() - navigation._activity_ts < 60
    finally:
        _run(env, sess.async_stop())


def _relay_session(env, use_relay=True):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"use_relay_left": use_relay}, "panels": [grid]}}},
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = _open(env, cfg, messages.append)
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    relays = {"Relay Left": "switch.kitchen_relay_left"}
    sess.app.device.find_esphome_entity_id = lambda domain, name: relays.get(name)
    return sess


def test_a_hardware_button_toggles_its_relay_in_the_sandbox(env):
    sess = _relay_session(env)
    sess.send_event(ESPEvent.BUTTON_LEFT, "1")
    sess.send_event(ESPEvent.BUTTON_LEFT, "0")
    _wait(lambda: sess.app.sandbox.is_simulated("switch.kitchen_relay_left"))
    assert sess.app.sandbox.get("switch.kitchen_relay_left").state == "on"
    assert env.services.calls == []
    _run(env, sess.async_stop())


def test_without_relay_mode_the_button_leaves_the_relay_alone(env):
    sess = _relay_session(env, use_relay=False)
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
    weather = {
        "type": "weather",
        "key": "weather_0",
        "item": {"item": "weather.home"},
        "info_items": [{"item": "light.lamp"}],
    }
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {
                    "config": {"home_panel": "grid_0"},
                    "panels": [grid, clock, weather],
                }
            }
        },
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = _open(env, cfg, messages.append)
    _wait(lambda: {"type": "entities", "map": {"g1Overlay": "light.lamp"}} in messages)

    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    clock_map = {"#page": "weather.home", "bEntity1": "light.lamp"}
    _wait(lambda: {"type": "entities", "map": clock_map} in messages)
    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    weather_map = {
        "#page": "weather.home",
        "d1Icon": "light.lamp",
        "d1Val": "light.lamp",
    }
    _wait(lambda: {"type": "entities", "map": weather_map} in messages)
    _run(env, sess.async_stop())


def test_the_browser_maps_an_entity_popup_from_its_opening_item_id(env):
    messages: list[dict] = []
    sess = _open(env, _config(), messages.append)
    _wait(lambda: any(message.get("type") == "entities" for message in messages))

    navigation = sess.app.controller["navigation"]
    _run(
        env,
        sess.app.async_run_on_worker(
            lambda: navigation.open_panel("popup_light", item_id="light.lamp")
        ),
    )

    _wait(
        lambda: any(
            message.get("type") == "entities" and message["map"].get("#page") == "light.lamp"
            for message in messages
        )
    )
    _run(env, sess.async_stop())


def test_the_browser_maps_a_vacuum_battery_sensor_to_its_header_widget(env):
    env._states["vacuum.robot"] = _State("docked", {"friendly_name": "Robot"})
    env._states["sensor.robot_battery"] = _State("82", {"friendly_name": "Battery"})
    vacuum = {
        "type": "vacuum",
        "key": "vacuum_0",
        "item": {"item": "vacuum.robot"},
        "battery_sensor": {"item": "sensor.robot_battery"},
    }
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {
                    "config": {"home_panel": "vacuum_0"},
                    "panels": [vacuum],
                }
            }
        },
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = _open(env, cfg, messages.append)

    _wait(
        lambda: any(
            message.get("type") == "entities"
            and message["map"].get("#page") == "vacuum.robot"
            and message["map"].get("bFncRSec") == "sensor.robot_battery"
            for message in messages
        )
    )
    _run(env, sess.async_stop())


def test_stop_cancels_every_listener_and_timer(env):
    messages: list[dict] = []
    sess = _open(env, _config(), messages.append)
    _wait(lambda: any(c.startswith("g1Name.txt=") for c in _commands(messages)))

    _run(env, sess.async_stop())

    assert sess.app._state_handles == {}
    assert sess.app._timer_handles == {}


# one app per device: late viewers and panel cards


def test_show_home_leaves_the_idle_page_for_the_home_panel(env):
    clock = {"type": "clock", "key": "clock_0", "show_in_navigation": False}
    messages: list[dict] = []
    host = _open(env, _config([clock], idle_panel="clock_0"), messages.append)
    navigation = host.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        host.show_idle()
        _wait(lambda: {"type": "idle", "active": True} in messages)
        _wait(lambda: navigation.panel.get("key") == "clock_0")
        messages.clear()

        host.show_home()

        _wait(lambda: {"type": "idle", "active": False} in messages)
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        assert navigation.panel.get("key") == "grid_0"
    finally:
        _run(env, host.async_stop())


def test_show_panel_opens_the_devices_panel_and_leaves_the_idle_page(env):
    clock = {"type": "clock", "key": "clock_0", "show_in_navigation": False}
    light = {"type": "light", "key": "light_0", "item": "light.lamp"}
    messages: list[dict] = []
    host = _open(env, _config([clock, light], idle_panel="clock_0"), messages.append)
    navigation = host.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        host.show_idle()
        _wait(lambda: navigation.panel.get("key") == "clock_0")
        _run(env, host.app.async_run_on_worker(lambda: setattr(navigation, "_activity_ts", 0)))

        _run(env, host.async_show_panel("light_0"))

        assert navigation.panel.get("key") == "light_0"
        assert not navigation.idle_panel_active
        # A fresh inactivity clock: the idle page is not due right away again.
        assert time.monotonic() - navigation._activity_ts < 60
    finally:
        _run(env, host.async_stop())


def test_show_panel_opens_the_idle_page_the_device_shows(env):
    clock = {"type": "clock", "key": "clock_0", "show_in_navigation": False}
    messages: list[dict] = []
    host = _open(env, _config([clock], idle_panel="clock_0"), messages.append)
    navigation = host.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)

        _run(env, host.async_show_panel("clock_0", idle=True))

        assert navigation.panel.get("key") == "clock_0"
        assert navigation.idle_panel_active
        _wait(lambda: {"type": "idle", "active": True} in messages)
    finally:
        _run(env, host.async_stop())


def test_show_panel_opens_a_popup_with_its_sample_context(env):
    messages: list[dict] = []
    host = _open(env, _config(), messages.append)
    navigation = host.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)

        _run(env, host.async_show_panel("popup_notify"))

        assert navigation.panel.get("key") == "popup_notify"
        assert navigation.panel_kwargs["notification"].startswith("Example notification")
    finally:
        _run(env, host.async_stop())


def test_show_panel_refuses_a_key_the_device_cannot_open(session, env):
    navigation = session.app.controller["navigation"]

    with pytest.raises(ValueError, match="Unknown panel key"):
        _run(env, session.async_show_panel("missing"))
    with pytest.raises(ValueError, match="Not an idle panel"):
        _run(env, session.async_show_panel("grid_0", idle=True))

    assert navigation.panel.get("key") == "grid_0"


def test_back_from_live_the_sandbox_starts_over(env):
    # Live drives the device's own app: the virtual app gets no touches while
    # it is shown, so its idle page comes due in the background.
    clock = {"type": "clock", "key": "clock_0", "show_in_navigation": False}
    messages: list[dict] = []
    host = _open(env, _config([clock], idle_panel="clock_0"), messages.append)
    navigation = host.app.controller["navigation"]

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)

        def left_alone_while_live():
            host.app.simulate_service("light", "turn_on", ["light.lamp"], {})
            navigation._activity_ts -= 3600
            navigation.open_idle_panel(True)

        _run(env, host.app.async_run_on_worker(left_alone_while_live))
        _wait(lambda: navigation.panel.get("key") == "clock_0")
        assert host.app.sandbox.has_changes

        host.show_home()

        _wait(lambda: navigation.panel.get("key") == "grid_0")
        assert not navigation.idle_panel_active
        assert not host.app.sandbox.has_changes
        # A fresh inactivity clock: the idle page is not due right away again.
        assert time.monotonic() - navigation._activity_ts < 60
    finally:
        _run(env, host.async_stop())


def test_a_late_viewer_gets_the_current_panel_drawn(session, env):
    late: list[dict] = []
    env.loop.call_soon_threadsafe(lambda: session.attach("late", late.append))

    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in late)
    _wait(lambda: 'g1Name.txt="Lamp"' in _commands(late))


def test_a_card_render_never_moves_the_live_display(session, env):
    navigation = session.app.controller["navigation"]
    live_panel = navigation.panel
    session.messages.clear()
    card = {"type": "light", "key": "desk", "title": "Desk", "item": {"item": "light.lamp"}}

    result = _run(env, session.async_render(card))

    assert result["page"] == 13
    # The light page titles itself with the entity's name, as on the panel.
    assert 'tTitle.txt="Lamp"' in result["commands"]
    assert navigation.panel is live_panel
    assert session.messages == []


def test_a_card_render_changes_no_state(session, env):
    card = {"type": "grid", "key": "rooms", "items": [{"item": "light.lamp"}]}

    _run(env, session.async_render(card))

    assert env.services.calls == []
    assert not session.app.sandbox.is_simulated("light.lamp")


def test_a_slow_weather_forecast_does_not_block_the_virtual_app_worker(session, env):
    env._states["weather.home"] = _State("rainy", {"temperature": 14.6})
    started = threading.Event()
    release = asyncio.Event()

    async def slow_forecast(domain, service, service_data=None, target=None, **kwargs):
        started.set()
        await release.wait()
        return {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": "2026-11-12T12:00:00+00:00",
                        "temperature": 22,
                        "templow": 11,
                        "condition": "sunny",
                    }
                ]
            }
        }

    env.services.async_call = slow_forecast
    card = {
        "type": "weather",
        "key": "weather_card",
        "item": {"item": "weather.home"},
        "forecast_type": "daily",
    }
    render = asyncio.run_coroutine_threadsafe(session.async_render(card), env.loop)

    try:
        assert started.wait(timeout=2)
        worker_task = asyncio.run_coroutine_threadsafe(
            session.app.async_run_on_worker(lambda: "worker responsive"), env.loop
        )
        assert worker_task.result(timeout=1) == "worker responsive"
    finally:
        env.loop.call_soon_threadsafe(release.set)

    result = render.result(timeout=5)
    assert result["page"] == 6
    assert 'f1Val.txt="22°C"' in result["commands"]


def test_an_entity_popup_card_opens_for_an_entity_of_its_domain(session, env):
    result = _run(env, session.async_render({"type": "popup_light", "key": "popup_light"}))

    assert result["page"] == 13
    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_an_edited_entity_popup_card_still_opens_for_an_entity_of_its_domain(session, env):
    # The editor saves an edited entity popup with the user type (popup_light → light).
    result = _run(env, session.async_render({"type": "light", "key": "popup_light"}))

    assert result["page"] == 13
    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_an_edited_entity_popup_with_an_empty_item_still_opens_for_an_entity(session, env):
    # A saved popup override keeps the editor's empty single-item field.
    card = {"type": "light", "key": "popup_light", "item": {"item": None}}

    result = _run(env, session.async_render(card))

    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_an_entity_popup_card_prefers_an_entity_that_is_on(session, env):
    env._states["light.attic"] = _State("unavailable", {"friendly_name": "Attic"})
    env._states["light.porch"] = _State("on", {"friendly_name": "Porch"})

    result = _run(env, session.async_render({"type": "popup_light", "key": "popup_light"}))

    assert 'tTitle.txt="Porch"' in result["commands"]


def test_an_entity_popup_card_prefers_an_off_entity_to_an_unavailable_one(session, env):
    env._states["light.attic"] = _State("unavailable", {"friendly_name": "Attic"})

    result = _run(env, session.async_render({"type": "popup_light", "key": "popup_light"}))

    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_the_virtual_queue_mirrors_the_physical_notifications(session, env):
    source = _open(env, _config(), lambda _message: None)
    physical = source.app.controller["notification"]
    controller = session.app.controller["notification"]

    try:
        queued = _run(
            env,
            source.app.async_run_on_worker(
                lambda: physical.add_notification(
                    title="Doorbell", message="Someone is here", force_show=True
                )
            ),
        )
        _run(env, session.async_follow_notifications(source.app))
        # The queue as it is when the preview starts following it...
        _wait(lambda: len(controller.get_notifications()) == 1)
        mirrored = controller.get_notifications()[0]
        assert mirrored.notif_id != queued.notif_id
        assert (mirrored.title, mirrored.message) == ("Doorbell", "Someone is here")
        _wait(lambda: any("Someone is here" in command for command in _commands(session.messages)))

        # ...and every change after it.
        _run(
            env,
            source.app.async_run_on_worker(
                lambda: physical.add_notification(title="Mail", message="A letter")
            ),
        )
        _wait(lambda: len(controller.get_notifications()) == 2)
        _run(env, source.app.async_run_on_worker(physical.clear_notifications))
        _wait(lambda: not controller.get_notifications())
    finally:
        _run(env, source.async_stop())


def test_a_popup_card_shows_its_descriptor_sample(session, env):
    result = _run(env, session.async_render({"type": "notify", "key": "popup_notify"}))

    assert any("Example notification" in command for command in result["commands"])


def test_add_panel_previews_include_a_sample_entity(session, env):
    result = _run(env, session.async_render({"type": "light", "key": ""}))

    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_add_panel_list_previews_include_sample_entities(session, env):
    result = _run(env, session.async_render({"type": "grid", "key": ""}))

    assert any("Lamp" in command for command in result["commands"])


def test_every_add_panel_preview_renders_with_sample_data(session, env):
    env._states.clear()

    expected_text = {
        "alarm": "Disarmed",
        "climate": "Living Room",
        "clock": "18°C",
        "cover": "Blind",
        "grid": "Lamp",
        "light": "Lamp",
        "media": "Morning Coffee",
        "row": "Lamp",
        "vacuum": "Robot Vacuum",
    }
    for descriptor in get_user_panel_type_descriptors():
        panel_type = descriptor["type_key"]
        result = _run(
            env,
            session.async_render({"type": panel_type, "key": ""}, settle=0.1),
        )
        assert result["page"] == descriptor["page_id"], panel_type
        assert result["commands"], panel_type
        if panel_type in expected_text:
            assert any(expected_text[panel_type] in command for command in result["commands"])


def test_add_weather_preview_includes_a_sample_forecast(session, env):
    env._states.clear()
    result = _run(env, session.async_render({"type": "weather", "key": ""}))

    assert 'f1Val.txt="24°C"' in result["commands"]


def test_add_qr_preview_includes_example_network_details(session, env):
    result = _run(env, session.async_render({"type": "qr", "key": ""}))

    assert any("WIFI:S:NSPanel;T:WPA;P:12345678;;" in command for command in result["commands"])


def test_add_timer_preview_shows_example_time(session, env):
    result = _run(env, session.async_render({"type": "timer", "key": ""}))

    assert 'tMin.txt="12"' in result["commands"]
    assert 'tSec.txt="34"' in result["commands"]


def test_saved_panel_previews_do_not_fill_in_missing_entities(session, env):
    result = _run(env, session.async_render({"type": "light", "key": "my_light"}))

    assert 'tTitle.txt="Light"' in result["commands"]


def test_a_system_panel_renders_with_its_configured_defaults(session, env):
    config = _run(env, session.async_configured_panel("popup_notify"))

    assert config["key"] == "popup_notify"
    assert config["show_in_navigation"] is False
    with pytest.raises(ValueError):
        _run(env, session.async_configured_panel("nope"))


def test_about_card_uses_current_device_versions_without_a_viewer(env):
    host = VirtualPanelHost(
        env,
        "kitchen",
        _config(),
        device_info={"yaml_version": "yaml-initial", "tft_version": "tft-initial"},
    )
    _run(env, host.async_start())
    try:
        panel = _run(env, host.async_configured_panel("sys_about"))
        initial = _run(env, host.async_render(panel))

        assert 'tTftVersVal.txt="tft-initial"' in initial["commands"]
        assert 'tYamlVersVal.txt="yaml-initial"' in initial["commands"]

        _run(
            env,
            host.async_set_device_info(
                {"yaml_version": "yaml-updated", "tft_version": "tft-updated"}
            ),
        )
        updated = _run(env, host.async_render(panel))

        assert 'tTftVersVal.txt="tft-updated"' in updated["commands"]
        assert 'tYamlVersVal.txt="yaml-updated"' in updated["commands"]
    finally:
        _run(env, host.async_stop())


def test_device_info_sync_does_not_copy_display_state_or_page(session, env):
    # Display state travels through the explicit event subscription, not metadata sync.
    assert session.app.device.display_state == "on"

    _run(
        env,
        session.async_set_device_info(
            {"tft_version": "tft-real", "display_state": "off", "page": "3"}
        ),
    )

    assert session.app.device.display_state == "on"
    assert session.app.device.device_info["tft_version"] == "tft-real"


def test_a_burst_of_card_renders_reads_the_real_device_once(session, env):
    reads = []

    class _Running:
        device = types.SimpleNamespace(device_info={"tft_version": "tft-real"})

        async def async_run_on_worker(self, fn):
            reads.append(fn)
            await asyncio.sleep(0.05)
            return fn()

    async def burst():
        running = _Running()
        await asyncio.gather(*(session.async_follow_device(running) for _ in range(10)))

    _run(env, burst())

    assert len(reads) == 1
    assert session.app.device.device_info["tft_version"] == "tft-real"

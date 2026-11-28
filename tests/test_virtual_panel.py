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
from io import BytesIO

import pytest
from PIL import Image

import custom_components.nspanel_haui as nspanel_haui
from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent
from custom_components.nspanel_haui.haui.mapping.icons import ICO_PASSWORD
from custom_components.nspanel_haui.haui.mapping.panel import get_user_panel_type_descriptors
from custom_components.nspanel_haui.haui.page.alarm import AlarmPage
from custom_components.nspanel_haui.haui.page.camera import CameraPage, picture_rect
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.grid import GridPage
from custom_components.nspanel_haui.haui.page.light import LightPage
from custom_components.nspanel_haui.haui.page.unlock import UnlockPage
from custom_components.nspanel_haui.haui.page.weather import WeatherPage
from custom_components.nspanel_haui.haui.utils.image_stream import DEFAULT_QUALITY, QUALITY
from custom_components.nspanel_haui.hub import camera_stream
from custom_components.nspanel_haui.web.preview.sample_data import sample_snapshot
from custom_components.nspanel_haui.web.preview.virtual_panel import (
    InertUpdateController,
    VirtualPanelHost,
)

GRID_PAGE_ID = GridPage.DESCRIPTOR.page_id
CLOCK_PAGE_ID = ClockPage.DESCRIPTOR.page_id
LIGHT_PAGE_ID = LightPage.DESCRIPTOR.page_id
UNLOCK_PAGE_ID = UnlockPage.DESCRIPTOR.page_id
WEATHER_PAGE_ID = WeatherPage.DESCRIPTOR.page_id
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


def _config(extra_panels=(), *, idle_panel=None, home_panel="grid_0"):
    grid = {"type": "grid", "key": "grid_0", "items": [{"item": "light.lamp"}]}
    device_config = {"home_panel": home_panel}
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


def _button(messages, side):
    """One hardware button as last reported, or None before the first report.

    The hub sends the two buttons together (``buttons``): the entity each one
    switches, the light's ``state`` and the relay's own ``relay_state``.
    """
    message = next((m for m in reversed(messages) if m["type"] == "buttons"), None)
    return message[side] if message else None


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

    _run(env, session.app.async_run_on_worker(session.app.start_button_state_tracking))
    _wait(
        lambda: (
            _button(session.messages, "left")
            == {
                "relay": "switch.relay_left",
                "entity": None,
                "state": "off",
                "relay_state": "off",
            }
        )
    )
    assert _button(session.messages, "right")["state"] == "on"

    _run(
        env,
        session.app.async_run_on_worker(
            lambda: session.app.call_service(
                "switch/toggle", target={"entity_id": "switch.relay_left"}
            )
        ),
    )
    _wait(lambda: _button(session.messages, "left")["state"] == "on")
    assert _button(session.messages, "right")["state"] == "on"


def test_live_preview_button_light_shows_its_entity_without_relay_mode(session, env):
    """With relay mode off, a button's light shows the entity it switches."""
    env._states.update({"switch.relay_left": _State("off", {}), "light.lamp": _State("on", {})})
    session.app.find_entity_id = lambda domain, name: (
        "switch.relay_left" if (domain, name) == ("switch", "Relay Left") else None
    )

    def entity_mode():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = "light.lamp"
        session.app.start_button_state_tracking()

    _run(env, session.app.async_run_on_worker(entity_mode))
    _wait(
        lambda: (
            _button(session.messages, "left")
            == {
                "relay": "switch.relay_left",
                "entity": "light.lamp",
                "state": "on",
                "relay_state": "off",
            }
        )
    )

    _run(
        env,
        session.app.async_run_on_worker(
            lambda: session.app.call_service("light/toggle", target={"entity_id": "light.lamp"})
        ),
    )
    # The light follows the entity; the relay's own state keeps its dot.
    _wait(lambda: _button(session.messages, "left")["state"] == "off")
    assert _button(session.messages, "left")["relay_state"] == "off"


def test_live_preview_names_the_entity_each_hardware_button_switches(session, env):
    """A button names what a press switches: its relay, or its entity without relay mode."""
    env._states.update({"switch.relay_left": _State("off", {}), "light.lamp": _State("on", {})})
    session.app.find_entity_id = lambda domain, name: (
        "switch.relay_left" if (domain, name) == ("switch", "Relay Left") else None
    )

    _run(env, session.app.async_run_on_worker(session.app.start_button_state_tracking))
    _wait(lambda: _button(session.messages, "left") is not None)
    assert _button(session.messages, "left")["entity"] is None
    assert _button(session.messages, "left")["relay"] == "switch.relay_left"
    assert _button(session.messages, "right")["relay"] is None

    def entity_mode():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = "light.lamp"
        session.app.start_button_state_tracking()

    _run(env, session.app.async_run_on_worker(entity_mode))
    _wait(lambda: _button(session.messages, "left")["entity"] == "light.lamp")


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
            session.app.start_button_state_tracking()

        session.messages.clear()
        _run(env, session.app.async_run_on_worker(configure))
        message = {
            "relay": "switch.relay_left",
            "entity": entity_id,
            "state": expected,
            "relay_state": "off",
        }
        _wait(lambda message=message: _button(session.messages, "left") == message)


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
    _run(env, session.app.async_run_on_worker(session.app.start_button_state_tracking))

    session.send_event(ESPEvent.BUTTON_LEFT, "1")

    _wait(lambda: session.app.sandbox.is_simulated(relay_id))
    assert session.app.sandbox.get(relay_id).state == "on"
    assert session.app.sandbox.get("light.lamp").state == "off"
    assert env.services.calls == []

    session.send_event(ESPEvent.BUTTON_LEFT, "0")
    _wait(
        lambda: (
            _button(session.messages, "left")
            == {"relay": relay_id, "entity": None, "state": "on", "relay_state": "on"}
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
        session.app.start_button_state_tracking()

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
            _button(session.messages, "left")
            == {"relay": relay_id, "entity": entity_id, "state": "on", "relay_state": "off"}
        )
    )


def test_hardware_button_simulates_a_scene_by_activating_it(session, env):
    """A scene has no toggle: the release runs scene.turn_on, which the sandbox simulates."""
    relay_id = "switch.relay_left"
    scene_id = "scene.morning"
    env._states[relay_id] = _State("off", {})
    env._states[scene_id] = _State("unknown", {"friendly_name": "Morning"})
    session.app.find_entity_id = lambda domain, name: (
        relay_id if (domain, name) == ("switch", "Relay Left") else None
    )
    applied: list[tuple[str, str]] = []
    apply = session.app.sandbox.apply

    def record_apply(domain, service, entity_ids, data):
        applied.append((domain, service))
        return apply(domain, service, entity_ids, data)

    session.app.sandbox.apply = record_apply

    def configure_scene_button():
        session.app.device.config["use_relay_left"] = False
        session.app.device.config["button_left_entity"] = scene_id
        # The sandbox reports an unhandled service at DEBUG level.
        session.app.device.config["log_level"] = "DEBUG"
        session.app.device._register_callbacks()
        session.app.start_button_state_tracking()

    _run(env, session.app.async_run_on_worker(configure_scene_button))

    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: applied)
    assert applied == [("scene", "turn_on")]
    # Activating a scene changes nothing to simulate; it is not "unsimulated" either.
    assert not session.app.sandbox.is_simulated(scene_id)
    assert session.app.sandbox.get(scene_id).state == "unknown"
    assert env.services.calls == []
    assert not any("not simulated" in line for line in session.app.get_status_logs())


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
        session.app.start_button_state_tracking()

    _run(env, session.app.async_run_on_worker(configure_cover_button))
    closed = {"relay": relay_id, "entity": cover_id, "state": "off", "relay_state": "off"}
    _wait(lambda: _button(session.messages, "left") == closed)

    session.send_event(ESPEvent.BUTTON_LEFT, "1")
    _wait(lambda: session.app.device.device_info.get("button_left") == "1")
    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: session.app.sandbox.is_simulated(cover_id))
    opened = session.app.sandbox.get(cover_id)
    assert opened.state == "open"
    assert opened.attributes["current_position"] == 100
    _wait(lambda: _button(session.messages, "left") == {**closed, "state": "on"})

    session.send_event(ESPEvent.BUTTON_LEFT, "1")
    _wait(lambda: session.app.device.device_info.get("button_left") == "1")
    session.send_event(ESPEvent.BUTTON_LEFT, "0")

    _wait(lambda: session.app.sandbox.get(cover_id).attributes["current_position"] == 0)
    closed_again = session.app.sandbox.get(cover_id)
    assert closed_again.state == "closed"
    assert closed_again.attributes["current_position"] == 0
    _wait(lambda: _button(session.messages, "left") == closed)


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


def test_the_last_preview_closing_drops_the_simulated_states(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))

    env.loop.call_soon_threadsafe(lambda: session.detach("viewer"))

    # Nothing shows the sandbox any more, and a card render reading the shared
    # app would show the simulated state as the panel's own.
    _wait(lambda: not session.app.sandbox.has_changes)
    assert session.app.sandbox.get("light.lamp").state == "off"


def test_a_preview_closing_keeps_the_states_another_one_shows(session, env):
    _tap_power(session)
    _wait(lambda: session.app.sandbox.is_simulated("light.lamp"))

    late: list[dict] = []
    env.loop.call_soon_threadsafe(lambda: session.attach("late", late.append))
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in late)

    assert session.detach("late")
    # The device's previews share one sandbox: it goes with the last one only.
    _run(env, session.app.async_run_on_worker(lambda: None))
    assert session.app.sandbox.is_simulated("light.lamp")


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
    _wait(lambda: {"type": "page", "page": LIGHT_PAGE_ID} in messages)
    _wait(lambda: any(c.startswith("hBrightness.val=") for c in _commands(messages)))
    slider = sess.app.controller["navigation"].page.COMPONENTS.h_brightness

    # What the browser sends for a press-drag-release on the slider ...
    sess.send_event(ESPEvent.COMPONENT, f"{LIGHT_PAGE_ID},{slider.id},1")
    sess.send_event(ESPEvent.COMPONENT, f"{LIGHT_PAGE_ID},{slider.id},0")
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
    _wait(lambda: {"type": "page", "page": CLOCK_PAGE_ID} in messages)
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

    _wait(lambda: {"type": "page", "page": CLOCK_PAGE_ID} in messages)
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
    _wait(lambda: {"type": "page", "page": CLOCK_PAGE_ID} in messages)
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


def test_the_browser_learns_widgets_of_entities_home_assistant_does_not_know(env):
    """A missing entity shows as unavailable on the panel; the hover still names it."""
    grid = {
        "type": "grid",
        "key": "grid_0",
        "items": [{"item": "light.lamp"}, {"item": "light.gone"}],
    }
    light = {"type": "light", "key": "light_0", "item": {"item": "light.gone"}}
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {
            "devices": {
                "kitchen": {"config": {"home_panel": "grid_0"}, "panels": [grid, light]},
            }
        },
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = _open(env, cfg, messages.append)
    grid_map = {"g1Overlay": "light.lamp", "g2Overlay": "light.gone"}
    _wait(lambda: {"type": "entities", "map": grid_map} in messages)

    sess.send_event(ESPEvent.GESTURE, "swipe_left")
    _wait(
        lambda: any(
            message["type"] == "entities" and message["map"].get("#page") == "light.gone"
            for message in messages
        )
    )
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


def test_the_browser_maps_a_rows_controls_to_its_entity(env):
    env._states["cover.blind"] = _State("open", {"friendly_name": "Blind"})
    row = {
        "type": "row",
        "key": "row_0",
        "items": [{"item": "light.lamp"}, {"item": "cover.blind"}],
    }
    cfg = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]},
        {"devices": {"kitchen": {"config": {"home_panel": "row_0"}, "panels": [row]}}},
        device_name="kitchen",
    )
    messages: list[dict] = []
    sess = _open(env, cfg, messages.append)

    _wait(
        lambda: any(
            message.get("type") == "entities"
            and message["map"].get("r1Toggle") == "light.lamp"
            and message["map"].get("r2BtnUp") == "cover.blind"
            and message["map"].get("r2BtnDown") == "cover.blind"
            and "r3BtnUp" not in message["map"]
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

    assert result["page"] == LIGHT_PAGE_ID
    # The light page titles itself with the entity's name, as on the panel.
    assert 'tTitle.txt="Lamp"' in result["commands"]
    assert navigation.panel is live_panel
    assert session.messages == []


def test_a_card_render_changes_no_state(session, env):
    card = {"type": "grid", "key": "rooms", "items": [{"item": "light.lamp"}]}

    _run(env, session.async_render(card))

    assert env.services.calls == []
    assert not session.app.sandbox.is_simulated("light.lamp")


def test_a_card_render_interrupted_by_the_apps_stop_ends_with_what_was_drawn(
    session, env, monkeypatch
):
    """An app stopped under a render (an unload, Home Assistant stopping) is no error."""
    from custom_components.nspanel_haui.web.preview import virtual_panel

    # The render's own page start is the signal that it is under way.
    page_started = threading.Event()
    start = virtual_panel._PanelRender.start

    def recording_start(render):
        start(render)
        page_started.set()

    monkeypatch.setattr(virtual_panel._PanelRender, "start", recording_start)
    card = {"type": "light", "key": "desk", "title": "Desk", "item": {"item": "light.lamp"}}
    # A settle no quiet period reaches: only the app's stop ends this render.
    render = asyncio.run_coroutine_threadsafe(session.async_render(card, settle=30.0), env.loop)

    assert page_started.wait(timeout=5)
    _run(env, session.app.async_run_on_worker(session.app.stop))
    result = render.result(timeout=5)

    assert result["page"] == LIGHT_PAGE_ID
    assert 'tTitle.txt="Lamp"' in result["commands"]


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
    assert result["page"] == WEATHER_PAGE_ID
    assert 'f1Val.txt="22°C"' in result["commands"]


def test_an_entity_popup_card_opens_for_an_entity_of_its_domain(session, env):
    result = _run(env, session.async_render({"type": "popup_light", "key": "popup_light"}))

    assert result["page"] == LIGHT_PAGE_ID
    assert 'tTitle.txt="Lamp"' in result["commands"]


def test_an_edited_entity_popup_card_still_opens_for_an_entity_of_its_domain(session, env):
    # The editor saves an edited entity popup with the user type (popup_light → light).
    result = _run(env, session.async_render({"type": "light", "key": "popup_light"}))

    assert result["page"] == LIGHT_PAGE_ID
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
        _run(env, session.async_follow_panel(source.app))
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


def _page_id(env, app) -> str | None:
    """The page an app shows, read on its own worker."""
    page = _run(env, app.async_run_on_worker(lambda: app.controller["navigation"].page))
    return None if page is None else page.page_id


def _replay(env, app) -> list[str]:
    """The commands the app's shown page was sent, as a viewer is seeded with them."""
    return list(_run(env, app.async_run_on_worker(app.controller["esphome"].page_commands)))


def test_a_simulated_camera_page_draws_with_no_physical_panel(env, monkeypatch):
    """The camera page, planner, packed transport and browser feed are all real."""
    panel = {"type": "camera", "key": "front", "item": {"item": "camera.front"}}
    env._states["camera.front"] = _State("idle", {"friendly_name": "Front"})
    env.async_create_task = env.loop.create_task
    image = BytesIO()
    Image.new("RGB", (64, 48), (255, 0, 0)).save(image, format="PNG")

    async def snapshot(_stream):
        return image.getvalue()

    monkeypatch.setattr(camera_stream.CameraStream, "_snapshot", snapshot)
    messages: list[dict] = []
    host = _open(env, _config([panel], home_panel="front"), messages.append)
    try:
        _wait(lambda: any(command.startswith("fill ") for command in _commands(messages)))
        page_index = messages.index({"type": "page", "page": CameraPage.DESCRIPTOR.page_id})
        commands = _commands(messages[page_index + 1 :])
        first = next(i for i, cmd in enumerate(commands) if cmd.startswith("fill "))
        assert commands[first].endswith(",63488")
        assert "vis tText,0" in commands[:first], "the placeholder is hidden before the paint"
        late: list[dict] = []
        env.loop.call_soon_threadsafe(lambda: host.attach("camera-late", late.append))
        _wait(lambda: commands[first] in _commands(late))
    finally:
        _run(env, camera_stream.stop_stream(host.app))
        _run(env, host.async_stop())


def test_a_card_render_asks_for_the_picture_it_has_none_of(env):
    """A replay that cannot describe the area leaves the card on the placeholder.

    A running stream trims its oldest fills within a minute, after which
    ``camera_page_frame`` is empty for ever and the card showed "Waiting for the
    camera" while the panel showed the picture. The render asks the stream for a
    whole paint, so the next one carries it - and asks nothing when it has one.
    """
    asked: list[str] = []

    class _Source:
        """The followed device, as the host reads it: worker calls run inline."""

        def __init__(self, frame: list[str]) -> None:
            self.frames = frame
            self.controller = {
                "navigation": types.SimpleNamespace(
                    page=types.SimpleNamespace(panel={"key": "front"})
                )
            }

        async def async_run_on_worker(self, fn, *args):
            return fn(*args)

        def camera_page_frame(self) -> list[str]:
            return self.frames

        def request_camera_page_picture(self) -> None:
            asked.append("asked")

    panel = {"type": "camera", "key": "front"}

    host = object.__new__(VirtualPanelHost)
    host._panel_source = _Source([])

    assert _run(env, host._async_camera_frame(panel)) == []
    assert asked == ["asked"], "no picture, so the stream is asked for one"

    host._panel_source = _Source(["fill 12,70,426,170,1024"])

    assert _run(env, host._async_camera_frame(panel)) == ["fill 12,70,426,170,1024"]
    assert asked == ["asked"], "and a render that has one asks for nothing"


def _card_host(env, source=None, *, portrait: bool = False):
    """The host as its camera prefetch reads it: one app, maybe a followed device."""
    host = object.__new__(VirtualPanelHost)
    host._panel_source = source
    host.app = types.SimpleNamespace(
        device=types.SimpleNamespace(is_portrait=portrait),
        hass=env,
    )
    return host


class _CameraSource:
    """The followed device showing a camera page, as the host reads it."""

    def __init__(self, frame: list[str], *, key: str = "front", entity: str = "") -> None:
        self.frames = frame
        self.controller = {
            "navigation": types.SimpleNamespace(
                page=types.SimpleNamespace(panel={"key": key}, entity_id=entity)
            )
        }
        self.asked = 0

    async def async_run_on_worker(self, fn, *args):
        return fn(*args)

    def camera_page_frame(self) -> list[str]:
        return self.frames

    def request_camera_page_picture(self) -> None:
        self.asked += 1


def _stub_camera(monkeypatch, *, content: bytes = b"", error: Exception | None = None):
    """Stand in for Home Assistant's camera component and record what it was asked."""
    calls: list[tuple[str, int | None, int | None]] = []
    components = types.ModuleType("homeassistant.components")
    components.__path__ = []
    module = types.ModuleType("homeassistant.components.camera")

    async def async_get_image(hass, entity_id, *, timeout=None, width=None, height=None):
        calls.append((entity_id, width, height))
        if error is not None:
            raise error
        return types.SimpleNamespace(content=content)

    module.async_get_image = async_get_image
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.camera", module)
    return calls


def _instance_camera(env, entity_id: str = "camera.driveway", state: str = "idle") -> None:
    """Give the instance a camera of its own, as a real Home Assistant would have."""
    env._states[entity_id] = _State(state, {"friendly_name": "Driveway"})


def test_a_card_of_a_camera_no_device_shows_paints_a_planned_picture(env):
    """A card has no display stream behind it, so the hub plans the picture itself.

    The panel list, the panel editor and the catalog render a camera panel like
    any other card - there is no device on that page and often no device at all -
    so a card that asked only for the device's fills showed *Waiting for the
    camera* for ever.
    """
    item = "camera.haui_preview_front_door"
    host = _card_host(env)

    runs = _run(env, host._async_camera_frame({"type": "camera", "item": {"item": item}}))

    rect = picture_rect(False)
    assert runs == camera_stream.plan_still_frame(
        sample_snapshot(item), rect, QUALITY[DEFAULT_QUALITY]
    ), "the card shows the panel's own picture, planned at the panel's quality"
    assert runs[0].startswith(f"fill {rect.x},{rect.y},{rect.w},{rect.h},")


def test_a_card_picture_follows_the_panel_s_quality(env):
    """The density of a card's picture is the setting the panel draws with."""
    item = "camera.haui_preview_front_door"
    host = _card_host(env)
    panel = {"type": "camera", "item": {"item": item}}

    fine = _run(env, host._async_camera_frame({**panel, "quality": "high"}))
    coarse = _run(env, host._async_camera_frame({**panel, "quality": "low"}))

    assert coarse != fine
    assert len(coarse) < len(fine), "low is the coarser picture"


def test_a_card_fetches_the_snapshot_of_a_camera_no_device_shows(env, monkeypatch):
    """A real camera's picture comes from Home Assistant, sized for the panel."""
    picture = BytesIO()
    Image.new("RGB", (64, 48), (200, 40, 40)).save(picture, format="PNG")
    calls = _stub_camera(monkeypatch, content=picture.getvalue())
    host = _card_host(env)
    panel = {"type": "camera", "key": "front", "item": {"item": "camera.driveway"}}

    runs = _run(env, host._async_camera_frame(panel))

    rect = picture_rect(False)
    assert calls == [("camera.driveway", rect.w, rect.h)], "one snapshot, at the picture area"
    assert runs == camera_stream.plan_still_frame(
        picture.getvalue(), rect, QUALITY[DEFAULT_QUALITY]
    )


def test_a_portrait_device_plans_the_picture_in_its_own_area(env, monkeypatch):
    """A card draws into the picture area of the display it will be shown on."""
    picture = BytesIO()
    Image.new("RGB", (64, 48), (40, 120, 200)).save(picture, format="PNG")
    calls = _stub_camera(monkeypatch, content=picture.getvalue())
    host = _card_host(env, portrait=True)

    _run(
        env,
        host._async_camera_frame({"type": "camera", "item": {"item": "camera.driveway"}}),
    )

    assert calls == [("camera.driveway", picture_rect(True).w, picture_rect(True).h)]


def test_a_card_keeps_the_placeholder_when_the_camera_gives_nothing(env, monkeypatch):
    """A camera that does not answer is a card with no picture, not a stale one."""
    _stub_camera(monkeypatch, error=TimeoutError("no answer"))
    host = _card_host(env)

    runs = _run(
        env,
        host._async_camera_frame({"type": "camera", "item": {"item": "camera.driveway"}}),
    )

    assert runs == []


def test_a_sample_camera_previews_the_instance_s_own_camera(env, monkeypatch):
    """The Add panel catalog previews the user's own picture, not a drawing.

    A new camera panel's preview names one of the sample world's cameras, because
    that is what the panel will be pointed at: on an instance that has a camera,
    that camera holds the picture the user is about to see on their wall.
    """
    picture = BytesIO()
    Image.new("RGB", (64, 48), (30, 90, 200)).save(picture, format="PNG")
    calls = _stub_camera(monkeypatch, content=picture.getvalue())
    _instance_camera(env)
    host = _card_host(env)
    item = "camera.haui_preview_front_door"

    runs = _run(env, host._async_camera_frame({"type": "camera", "item": {"item": item}}))

    rect = picture_rect(False)
    assert calls == [("camera.driveway", rect.w, rect.h)]
    assert runs == camera_stream.plan_still_frame(
        picture.getvalue(), rect, QUALITY[DEFAULT_QUALITY]
    )


def test_the_sample_world_s_cameras_are_not_the_instance_s(env):
    """A preview-only entity is not a camera anyone can fetch, so nothing is asked."""
    _instance_camera(env, "camera.haui_preview_front_door")
    host = _card_host(env)
    item = "camera.haui_preview_front_door"

    runs = _run(env, host._async_camera_frame({"type": "camera", "item": {"item": item}}))

    assert runs == camera_stream.plan_still_frame(
        sample_snapshot(item), picture_rect(False), QUALITY[DEFAULT_QUALITY]
    )


def test_a_card_previews_the_camera_that_answers_over_a_dead_one(env, monkeypatch):
    """Two cameras of its own, one unavailable: the card takes the one that can show."""
    picture = BytesIO()
    Image.new("RGB", (64, 48), (200, 120, 40)).save(picture, format="PNG")
    calls = _stub_camera(monkeypatch, content=picture.getvalue())
    _instance_camera(env, "camera.alley", state="unavailable")
    _instance_camera(env)
    host = _card_host(env)

    _run(
        env,
        host._async_camera_frame(
            {"type": "camera", "item": {"item": "camera.haui_preview_front_door"}}
        ),
    )

    assert [call[0] for call in calls] == ["camera.driveway"]


def test_a_sample_camera_whose_real_camera_fails_keeps_the_placeholder(env, monkeypatch):
    """The drawing is for an instance without a camera, not for one that will not answer."""
    _stub_camera(monkeypatch, error=TimeoutError("no answer"))
    _instance_camera(env)
    host = _card_host(env)

    runs = _run(
        env,
        host._async_camera_frame(
            {"type": "camera", "item": {"item": "camera.haui_preview_front_door"}}
        ),
    )

    assert runs == []


def test_a_card_of_another_camera_does_not_take_the_device_s_picture(env):
    """The device's fills are this panel's only while both name the same camera.

    A card is rendered from the editor's config, unsaved edits included, so its
    camera may be another one than the device is showing.
    """
    source = _CameraSource(["fill 0,0,480,268,1024"], key="front", entity="camera.driveway")
    host = _card_host(env, source)
    item = "camera.haui_preview_front_door"

    runs = _run(
        env,
        host._async_camera_frame({"type": "camera", "key": "front", "item": {"item": item}}),
    )

    assert runs == camera_stream.plan_still_frame(
        sample_snapshot(item), picture_rect(False), QUALITY[DEFAULT_QUALITY]
    )


def test_a_card_render_of_a_camera_page_carries_the_planned_picture(env):
    """The whole way round: what the editor's simulator replays is that picture."""
    item = "camera.haui_preview_front_door"
    host = _open(env, _config(), lambda _message: None)
    try:
        render = _run(env, host.async_render({"type": "camera", "item": {"item": item}}))

        expected = camera_stream.plan_still_frame(
            sample_snapshot(item), picture_rect(False), QUALITY[DEFAULT_QUALITY]
        )
        commands = render["commands"]
        start = next(i for i, command in enumerate(commands) if command == expected[0])
        assert commands[start : start + len(expected)] == expected, (
            "the whole picture reaches the card, in the order it paints"
        )
        assert "vis tText,0" in commands, "the placeholder is gone from under it"
    finally:
        _run(env, host.async_stop())


def test_an_image_the_panel_draws_shows_in_the_simulated_preview(session, env):
    """``show_image`` is display output, not state: it must reach the preview too."""
    source = _open(env, _config(), lambda _message: None)
    program = ["fill 10,10,20,20,63488", "fill 30,10,20,20,2016"]

    try:
        _run(env, session.async_follow_panel(source.app))
        # Both boot to the same page; the panel's image belongs to it.
        _wait(lambda: _page_id(env, source.app) == _page_id(env, session.app) is not None)
        _run(
            env,
            source.app.async_run_on_worker(
                lambda: source.app.controller["esphome"].draw_overlay(program)
            ),
        )

        _wait(lambda: all(run in _commands(session.messages) for run in program))
        # A late viewer is seeded from the replay, not from the stream: the panel
        # confirms a slice with a fence, and only then does the picture belong to it.
        _wait(lambda: all(run in _replay(env, session.app) for run in program))
        # A second viewer gets the drawn image without forcing a redraw for the first.
        late: list[dict] = []
        marker = len(session.messages)
        env.loop.call_soon_threadsafe(lambda: session.attach("late", late.append))
        _wait(lambda: all(run in _commands(late) for run in program))
        assert not any(m["type"] == "page" for m in session.messages[marker:])
    finally:
        _run(env, source.async_stop())


def test_an_image_drawn_on_another_panel_with_the_same_layout_stays_out(session, env):
    """Two grid panels share an HMI page but have independent drawn content."""
    other = {"type": "grid", "key": "other_grid", "items": [{"item": "light.lamp"}]}
    source = _open(env, _config([other], home_panel="other_grid"), lambda _message: None)
    program = ["fill 10,10,20,20,63488"]

    try:
        _run(env, session.async_follow_panel(source.app))
        _wait(lambda: _page_id(env, source.app) == _page_id(env, session.app) == GRID_PAGE_ID)
        _run(
            env,
            source.app.async_run_on_worker(source.app.controller["esphome"].draw_overlay, program),
        )
        _run(env, session.app.async_run_on_worker(lambda: None))

        assert program[0] not in _commands(session.messages)
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

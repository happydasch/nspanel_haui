"""Tests for the live preview: a viewer of a device's running hub app.

The app a viewer mirrors is a virtual panel's app here (``VirtualPanelHost``):
it runs the real hub code, so its display output and event handling are the
code paths a live viewer follows on a real device.
"""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
from test_virtual_panel import (
    G1_POWER,
    GRID_PAGE_ID,
    _commands,
    _config,
    _open,
    _run,
    _State,
    _wait,
)
from test_virtual_panel import env as _env_fixture  # noqa: F401
from test_websocket_api import _Connection, _websocket_stub
from test_websocket_api import _run as _run_ws

from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent, PopupPanelKey
from custom_components.nspanel_haui.web.preview.live_panel import LivePanel

_ROOT = Path(__file__).resolve().parent.parent
_REPLAY = _ROOT / "tests" / "frontend" / "replay-renders.mjs"


def _replay_live_attach(messages, page_id, tmp_path, expected):
    """Replay a real live attach command stream in the editor's Nextion simulator.

    ``expected`` lists ``{"component", "visible", "textIncludes"}`` checks of the
    replayed screen (``tests/frontend/replay-renders.mjs``).
    """
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node 22+ is required to replay live-preview output")

    page_index = next(
        i for i, message in enumerate(messages) if message == {"type": "page", "page": page_id}
    )
    end = next(
        (
            i
            for i, message in enumerate(messages[page_index + 1 :], start=page_index + 1)
            if message["type"] == "page"
        ),
        len(messages),
    )
    renders = {
        "live-attach": {
            "page": page_id,
            "before": _commands(messages[:page_index]),
            "commands": _commands(messages[page_index + 1 : end]),
            "expected": expected,
        }
    }
    renders_path = tmp_path / "live-attach.json"
    renders_path.write_text(json.dumps(renders), encoding="utf-8")
    orientation = "portrait" if messages[0]["portrait"] else "landscape"
    result = subprocess.run(
        [node, str(_REPLAY), orientation, str(renders_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _source(env, config):
    """Start an app to mirror and wait until it shows its home panel."""
    source = _open(env, config, lambda _message: None)
    navigation = source.app.controller["navigation"]
    _wait(lambda: navigation.page is not None and navigation.page.panel is not None)
    return source


def _live(env, source):
    messages: list[dict] = []
    viewer = LivePanel(env, source.app, messages.append)
    _run(env, viewer.async_start("live"))
    return viewer, messages


def _stop(env, viewer):
    async def stop():
        viewer.stop()

    _run(env, stop())


def test_a_live_viewer_replays_the_apps_commands_and_routes_input(env):
    light_panel = {"type": "light", "key": "light_0", "item": {"item": "light.lamp"}}
    source = _source(env, _config([light_panel]))
    viewer, messages = _live(env, source)

    try:
        assert messages[0] == {"type": "started", "session_id": "live", "portrait": False}
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        _wait(lambda: any(command.startswith("g1Name.txt=") for command in _commands(messages)))

        marker = len(messages)
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},11,1"))
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},11,0"))
        navigation = source.app.controller["navigation"]
        _wait(lambda: navigation.panel.get("key") == "popup_light")
        _wait(lambda: {"type": "page", "page": 13} in messages[marker:])
        _wait(
            lambda: any('tTitle.txt="Lamp"' in command for command in _commands(messages[marker:]))
        )

        _run(
            env,
            source.app.async_run_on_worker(
                source.app.callback_event, HAUIEvent(ESPEvent.DISPLAY_STATE, "off")
            ),
        )
        _wait(
            lambda: any(
                message.get("type") == "physical" and message.get("display_state") == "off"
                for message in messages
            )
        )
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_live_attach_sets_system_background_before_loading_the_current_page(env):
    clock = {"type": "clock", "key": "clock_0", "background": "modern"}
    config = _config([clock])
    config["device"]["home_panel"] = "clock_0"
    source = _source(env, config)
    viewer, messages = _live(env, source)
    page_id = source.app.controller["navigation"].page.page_id

    try:
        background_index = next(
            i
            for i, message in enumerate(messages)
            if message["type"] == "commands" and "system.vBackground.val=3" in message["commands"]
        )
        page_index = next(
            i for i, message in enumerate(messages) if message == {"type": "page", "page": page_id}
        )
        assert background_index < page_index
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_attaching_a_live_viewer_sends_nothing_to_the_panel(env):
    # A viewer gets what the page was sent; the panel itself does not change.
    clock = {"type": "clock", "key": "home"}
    config = _config([clock])
    config["device"]["home_panel"] = "home"
    panel_output: list[dict] = []
    source = _open(env, config, panel_output.append)
    navigation = source.app.controller["navigation"]
    _wait(lambda: navigation.page is not None and navigation.page.panel is not None)
    _wait(lambda: any(command.startswith("tTime.txt=") for command in _commands(panel_output)))
    marker = len(panel_output)

    viewer, messages = _live(env, source)

    try:
        _run(env, source.app.async_run_on_worker(lambda: None))
        assert any(command.startswith("tTime.txt=") for command in _commands(messages))
        assert [m for m in panel_output[marker:] if m["type"] in ("commands", "page")] == []
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


@pytest.mark.parametrize(
    ("panel", "widgets"),
    [
        (
            {"type": "clock", "key": "home", "items": [{"item": "light.lamp"}]},
            ("tTime.txt=", "tDate.txt=", "bEntity1.txt="),
        ),
        ({"type": "weather", "key": "home"}, ("tTime.txt=", "tDate.txt=")),
        ({"type": "clocktwo", "key": "home"}, ("l1.txt=", "s1.txt=")),
    ],
)
def test_attaching_a_live_viewer_draws_the_whole_current_page(env, panel, widgets):
    # The viewer loads the page afresh: every widget the page drew must come
    # again, not only what changed since.
    config = _config([panel])
    config["device"]["home_panel"] = "home"
    source = _source(env, config)
    page_id = source.app.controller["navigation"].page.page_id
    viewer, messages = _live(env, source)

    try:
        page_index = messages.index({"type": "page", "page": page_id})
        drawn = _commands(messages[page_index:])
        for widget in widgets:
            assert any(command.startswith(widget) for command in drawn), widget
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


@pytest.mark.parametrize("display_model", ["eu", "us"])
@pytest.mark.parametrize("page_type", ["clock", "weather"])
def test_live_attach_replays_current_weather_below_the_clock(
    env, page_type, display_model, tmp_path
):
    env._states["weather.home"] = _State(
        "rainy",
        {
            "temperature": 14.6,
            "temperature_unit": "°C",
            "pressure": 1003,
            "pressure_unit": "hPa",
        },
    )
    panel = {"type": page_type, "key": "home", "item": {"item": "weather.home"}}
    config = _config([panel])
    config["device"]["home_panel"] = "home"
    config["device"]["display_model"] = display_model
    source = _source(env, config)
    page_id = source.app.controller["navigation"].page.page_id
    viewer, messages = _live(env, source)

    try:
        page_index = messages.index({"type": "page", "page": page_id})
        drawn = _commands(messages[page_index:])
        assert any(command.startswith("tMainIcon.txt=") for command in drawn)
        assert any(command.startswith("tMainText.txt=") and "15°C" in command for command in drawn)
        assert any(
            command.startswith("tSubText.txt=") and "1003hPa" in command for command in drawn
        )
        _replay_live_attach(
            messages,
            page_id,
            tmp_path,
            [
                {"component": "tMainIcon", "visible": True},
                {"component": "tMainText", "visible": True, "textIncludes": "15°C"},
                {"component": "tSubText", "visible": True, "textIncludes": "1003hPa"},
            ],
        )
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_live_attach_shows_the_forecast_the_app_drew(env, tmp_path):
    # The weather page's load code hides the forecast row and start_panel shows
    # it: a viewer that attaches later must get that too, not only what
    # render_panel draws.
    env._states["weather.home"] = _State(
        "rainy",
        {
            "temperature": 14.6,
            "temperature_unit": "°C",
            "pressure": 1003,
            "pressure_unit": "hPa",
        },
    )
    panel = {
        "type": "weather",
        "key": "home",
        "item": {"item": "weather.home"},
        "forecast_type": "daily",
    }
    config = _config([panel])
    config["device"]["home_panel"] = "home"
    source = _source(env, config)
    forecast = [
        {
            "datetime": "2026-01-01T00:00:00+00:00",
            "condition": "sunny",
            "temperature": 11,
            "templow": 1,
        }
    ]
    page = source.app.controller["navigation"].page

    def draw_forecast():
        # The test hub answers get_forecasts with nothing: the page draws the last one.
        page._previous_forecast = forecast
        with page.rec_cmd:
            page.render_forecast()

    _run(env, source.app.async_run_on_worker(draw_forecast))
    viewer, messages = _live(env, source)

    try:
        _replay_live_attach(
            messages,
            page.page_id,
            tmp_path,
            [
                {"component": "f1Val", "visible": True, "textIncludes": "11°C"},
                {"component": "f1SubVal", "visible": True, "textIncludes": "1°C"},
                {"component": "f1Icon", "visible": True},
                {"component": "f1Name", "visible": True},
            ],
        )
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_a_live_viewer_tracks_page_sensor_events(env):
    source = _source(env, _config())
    viewer, messages = _live(env, source)
    page_id = source.app.controller["navigation"].page.page_id

    try:
        messages.clear()
        _run(
            env,
            source.app.async_run_on_worker(
                source.app.callback_event, HAUIEvent(ESPEvent.PAGE, str(page_id))
            ),
        )
        _wait(lambda: {"type": "page", "page": page_id} in messages)
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_live_slider_values_use_the_current_pages_registered_handler(env):
    light_panel = {"type": "light", "key": "light_0", "item": {"item": "light.lamp"}}
    config = _config([light_panel])
    config["device"]["home_panel"] = "light_0"
    source = _source(env, config)
    viewer, _messages = _live(env, source)
    page = source.app.controller["navigation"].page
    component = page.COMPONENTS.h_brightness
    values = []
    _run(
        env,
        source.app.async_run_on_worker(
            lambda: page._read_callbacks.__setitem__(component.name, values.append)
        ),
    )

    try:
        _run(env, viewer.async_slider(page.page_id, component.id, 72))
        assert values == [72]
        with pytest.raises(ValueError, match="current page"):
            _run(env, viewer.async_slider(9, component.id, 20))
        with pytest.raises(ValueError, match="not a slider"):
            _run(env, viewer.async_slider(page.page_id, page.COMPONENTS.btn_power.id, 20))
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_a_live_viewer_streams_page_local_changes_from_the_app(env):
    source = _source(env, _config())
    viewer, messages = _live(env, source)
    notification = "A long notification message. " * 80
    _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
    _wait(lambda: any(command.startswith("g1Name.txt=") for command in _commands(messages)))

    try:
        navigation = source.app.controller["navigation"]
        _run(
            env,
            source.app.async_run_on_worker(
                lambda: navigation.open_panel(
                    PopupPanelKey.POPUP_NOTIFY,
                    notification=notification,
                    title="Alert",
                    text_size=1,
                )
            ),
        )
        _wait(lambda: navigation.panel.get("key") == "popup_notify")
        page = navigation.page
        _wait(lambda: page._total_pages > 1)
        next_id = page.COMPONENTS.fnc_right_sec.id
        marker = len(messages)
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"4,{next_id},1"))
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"4,{next_id},0"))

        _wait(lambda: page._current_page == 1)
        _wait(
            lambda: any(
                command.startswith("tTextFull.txt=") and "notification" in command
                for command in _commands(messages[marker:])
            )
        )
        # A viewer that attaches now gets the page the panel shows.
        late, late_messages = _live(env, source)
        second_page = page._chunks[1].replace("\n", "\\r")
        assert any(second_page in command for command in _commands(late_messages))
        assert page._current_page == 1
        _stop(env, late)
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_attaching_a_live_viewer_keeps_the_qr_zoom(env):
    qr_panel = {
        "type": "qr",
        "key": "qr_0",
        "essid": "Network",
        "password": "secret",
        "start_big_qr": False,
    }
    config = _config([qr_panel])
    config["device"]["home_panel"] = "qr_0"
    source = _open(env, config, lambda _message: None)
    navigation = source.app.controller["navigation"]
    _wait(lambda: navigation.page is not None and navigation.page.page_id == 11)
    page = navigation.page
    _run(env, source.app.async_run_on_worker(page._set_big, True))

    viewer, _messages = _live(env, source)

    try:
        _run(env, source.app.async_run_on_worker(lambda: None))
        assert page._is_big
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_live_interactions_run_on_the_app_and_are_checked(env):
    source = _source(env, _config())
    calls = []
    _run(
        env,
        source.app.async_run_on_worker(
            lambda: setattr(
                source.app,
                "call_service",
                lambda service, **kwargs: calls.append((service, kwargs)),
            )
        ),
    )
    page = source.app.controller["navigation"].page
    assert G1_POWER in {component.id for component in page.COMPONENTS.values()}
    viewer, _messages = _live(env, source)

    try:
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},1"))
        _run(env, viewer.async_event(ESPEvent.COMPONENT, f"{GRID_PAGE_ID},{G1_POWER},0"))
        _wait(lambda: calls)
        assert calls == [
            ("light.turn_on", {"target": {"entity_id": "light.lamp"}, "service_data": {}})
        ]
        assert env.services.calls == []

        with pytest.raises(ValueError, match="not allowed"):
            _run(env, viewer.async_event("esphome.res_device_state", "{}"))
        with pytest.raises(ValueError, match="current page"):
            _run(env, viewer.async_event(ESPEvent.COMPONENT, "9,999,0"))
        with pytest.raises(ValueError, match="outside"):
            _run(env, viewer.async_event(ESPEvent.TOUCH_END, "10,10,480,20"))
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_a_live_hardware_button_switches_the_real_relay_as_the_firmware_does(env):
    source = _source(env, _config())
    calls, events = [], []
    relays = {"Relay Left": "switch.kitchen_relay_left"}

    def patch():
        source.app.device.find_esphome_entity_id = lambda domain, name: relays.get(name)
        source.app.call_service = lambda service, **kwargs: calls.append((service, kwargs))
        source.app.callback_event = lambda event: events.append((event.name, event.value))

    _run(env, source.app.async_run_on_worker(patch))
    viewer, _messages = _live(env, source)

    try:
        _run(env, viewer.async_event(ESPEvent.BUTTON_LEFT, "1"))
        _run(env, viewer.async_event(ESPEvent.BUTTON_LEFT, "0"))
        assert calls == [("switch.toggle", {"target": {"entity_id": "switch.kitchen_relay_left"}})]
        assert events == [(ESPEvent.BUTTON_LEFT, "1"), (ESPEvent.BUTTON_LEFT, "0")]
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_the_live_idle_action_switches_the_app_to_its_idle_page(env):
    idle_panel = {"type": "grid", "key": "grid_1", "items": [{"item": "light.lamp"}]}
    source = _source(env, _config([idle_panel], idle_panel="grid_1"))
    viewer, messages = _live(env, source)

    try:
        _wait(lambda: {"type": "page", "page": GRID_PAGE_ID} in messages)
        _run(env, viewer.async_action("idle"))
        _wait(lambda: source.app.controller["navigation"].idle_panel_active)
        _wait(
            lambda: any(
                message.get("type") == "physical" and message.get("idle") is True
                for message in messages
            )
        )
        with pytest.raises(ValueError, match="not allowed"):
            _run(env, viewer.async_action("reboot"))
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_a_live_viewer_shows_the_real_button_lights(env):
    env._states["switch.kitchen_relay_left"] = _State("on", {})
    source = _source(env, _config())
    relays = {"Relay Left": "switch.kitchen_relay_left"}
    source.app.device.find_esphome_entity_id = lambda domain, name: relays.get(name)
    # A simulated state of the app it mirrors does not reach the live lights.
    source.app.sandbox.apply("switch", "turn_off", ["switch.kitchen_relay_left"], {})

    viewer, messages = _live(env, source)

    try:
        assert {
            "type": "relays",
            "left": "on",
            "right": "unknown",
            "entities": {"left": None, "right": None},
        } in messages
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_live_button_lights_follow_a_save(env):
    env._states["switch.kitchen_relay_left"] = _State("on", {})
    source = _source(env, _config())
    relays = {"Relay Left": "switch.kitchen_relay_left"}
    source.app.device.find_esphome_entity_id = lambda domain, name: relays.get(name)
    viewer, messages = _live(env, source)

    def save_left_button_for_the_lamp():
        source.app.device.config["use_relay_left"] = False
        source.app.device.config["button_left_entity"] = "light.lamp"

    try:
        _run(env, source.app.async_run_on_worker(save_left_button_for_the_lamp))
        marker = len(messages)
        _run(env, viewer.async_reload_lights())
        assert {
            "type": "relays",
            "left": "on",
            "right": "unknown",
            "entities": {"left": "off", "right": None},
        } in messages[marker:]
    finally:
        _stop(env, viewer)
        _run(env, source.async_stop())


def test_a_stopped_live_viewer_gets_no_more_output(env):
    source = _source(env, _config())
    viewer, messages = _live(env, source)
    _wait(lambda: any(command.startswith("g1Name.txt=") for command in _commands(messages)))

    _stop(env, viewer)
    marker = len(messages)
    _run(env, source.app.async_run_on_worker(source.app.controller["navigation"].refresh_panel))

    try:
        assert messages[marker:] == []
    finally:
        _run(env, source.async_stop())


def test_a_live_viewer_stopped_before_its_start_finished_follows_nothing(env):
    source = _source(env, _config())
    messages: list[dict] = []
    viewer = LivePanel(env, source.app, messages.append)
    _stop(env, viewer)

    _run(env, viewer.async_start("live"))
    marker = len(messages)
    _run(env, source.app.async_run_on_worker(source.app.controller["navigation"].refresh_panel))

    try:
        assert messages[marker:] == []
        assert not any(message["type"] == "relays" for message in messages)
    finally:
        _run(env, source.async_stop())


# WebSocket commands


class _FakeLive:
    instances: list = []

    def __init__(self, hass, source, sink):
        self.source = source
        self.sink = sink
        self.session_id = None
        self.stopped = False
        self.calls = []
        self.fail = None
        self.reloads = 0
        _FakeLive.instances.append(self)

    async def async_start(self, session_id):
        self.session_id = session_id
        self.sink({"type": "started", "session_id": session_id, "portrait": False})

    def stop(self):
        self.stopped = True

    async def async_reload_lights(self):
        if self.fail is not None:
            raise self.fail
        self.reloads += 1

    async def async_event(self, name, value):
        if self.fail is not None:
            raise self.fail
        self.calls.append((name, value))

    async def async_slider(self, page_id, component_id, value):
        if self.fail is not None:
            raise self.fail
        self.calls.append(("slider", page_id, component_id, value))

    async def async_action(self, action):
        if self.fail is not None:
            raise self.fail
        self.calls.append((action,))


@pytest.fixture
def live_ws(monkeypatch):
    stub = _websocket_stub()
    monkeypatch.setitem(sys.modules, "homeassistant.components.websocket_api", stub)
    monkeypatch.setattr(sys.modules["homeassistant.components"], "websocket_api", stub, False)
    import custom_components.nspanel_haui.web.preview.live_panel as module

    module = importlib.reload(module)
    monkeypatch.setattr(module, "LivePanel", _FakeLive)
    _FakeLive.instances = []
    return module


def _subscribe(live_ws, hass, conn, msg_id=1):
    return live_ws.ws_subscribe(
        hass, conn, {"id": msg_id, "entry_id": "entry1", "device": "kitchen"}
    )


def _with_running_app(live_ws, hass):
    hass.data[live_ws.DOMAIN] = {"entry1": {"kitchen": object()}}


def test_the_live_commands_are_registered(live_ws):
    live_ws.async_register_commands(types.SimpleNamespace())
    registered = sys.modules["homeassistant.components.websocket_api"].registered
    assert [fn.schema["type"] for fn in registered] == [
        "nspanel_haui/live_panel/subscribe",
        "nspanel_haui/live_panel/event",
        "nspanel_haui/live_panel/slider",
        "nspanel_haui/live_panel/action",
    ]


def test_a_live_subscription_needs_the_devices_running_app(live_ws):
    conn = _Connection()

    async def body(hass):
        await _subscribe(live_ws, hass, conn)

    _run_ws(body)
    assert conn.errors == [(1, "not_found")]
    assert _FakeLive.instances == []


def test_a_live_subscription_starts_a_viewer_and_unsubscribing_stops_it(live_ws):
    conn = _Connection()

    async def body(hass):
        _with_running_app(live_ws, hass)
        await _subscribe(live_ws, hass, conn)
        [viewer] = _FakeLive.instances
        assert viewer.source is hass.data[live_ws.DOMAIN]["entry1"]["kitchen"]
        assert not viewer.stopped
        conn.subscriptions[1]()
        assert viewer.stopped

    _run_ws(body)
    [viewer] = _FakeLive.instances
    assert conn.results == [1]
    assert conn.events == [{"type": "started", "session_id": viewer.session_id, "portrait": False}]


def test_live_events_and_actions_need_the_owning_connection(live_ws):
    conn = _Connection()
    other = _Connection()

    async def body(hass):
        _with_running_app(live_ws, hass)
        await _subscribe(live_ws, hass, conn)
        sid = _FakeLive.instances[0].session_id
        event = {"session_id": sid, "name": "esphome.component", "value": "9,12,0"}
        await live_ws.ws_event(hass, conn, {"id": 2, **event})
        await live_ws.ws_slider(
            hass,
            conn,
            {
                "id": 6,
                "session_id": sid,
                "page_id": 13,
                "component_id": 14,
                "value": 61,
            },
        )
        await live_ws.ws_action(hass, conn, {"id": 3, "session_id": sid, "action": "idle"})
        await live_ws.ws_event(hass, other, {"id": 4, **event})
        await live_ws.ws_action(hass, conn, {"id": 5, "session_id": "gone", "action": "idle"})

    _run_ws(body)
    assert _FakeLive.instances[0].calls == [
        ("esphome.component", "9,12,0"),
        ("slider", 13, 14, 61),
        ("idle",),
    ]
    assert conn.results == [1, 2, 6, 3]
    assert conn.errors == [(5, "not_found")]
    assert other.errors == [(4, "not_found")]


@pytest.mark.parametrize(
    ("command", "error", "code"),
    [
        ("event", ValueError("bad"), "invalid_event"),
        ("event", KeyError("missing display model"), "live_event_failed"),
        ("slider", ValueError("bad"), "invalid_slider"),
        ("slider", RuntimeError("exploded"), "live_slider_failed"),
        ("action", ValueError("disconnected"), "invalid_action"),
        ("action", RuntimeError("exploded"), "live_action_failed"),
    ],
)
def test_a_failed_live_interaction_names_its_cause(live_ws, command, error, code):
    conn = _Connection()

    async def body(hass):
        _with_running_app(live_ws, hass)
        await _subscribe(live_ws, hass, conn)
        viewer = _FakeLive.instances[0]
        viewer.fail = error
        msg = {"id": 2, "session_id": viewer.session_id}
        if command == "event":
            await live_ws.ws_event(hass, conn, {**msg, "name": "esphome.gesture", "value": "x"})
        elif command == "slider":
            await live_ws.ws_slider(
                hass,
                conn,
                {**msg, "page_id": 13, "component_id": 14, "value": 50},
            )
        else:
            await live_ws.ws_action(hass, conn, {**msg, "action": "idle"})

    _run_ws(body)
    assert conn.errors == [(2, code)]
    assert conn.results == [1]


def test_unloading_an_entry_stops_and_unregisters_its_live_viewers(live_ws):
    conn = _Connection()

    async def body(hass):
        _with_running_app(live_ws, hass)
        await _subscribe(live_ws, hass, conn, msg_id=1)
        await _subscribe(live_ws, hass, conn, msg_id=2)
        first, other_entry = _FakeLive.instances
        viewers = hass.data[live_ws.VIEWERS_KEY]
        other_session = other_entry.session_id
        viewers[other_session] = (*viewers[other_session][:2], "entry2", 2)

        await live_ws.async_stop_viewers(hass, "entry1")

        assert first.stopped
        assert not other_entry.stopped
        assert first.session_id not in viewers
        assert other_session in viewers
        assert set(conn.subscriptions) == {2}

    _run_ws(body)


def test_a_save_reloads_the_lights_of_the_hubs_live_viewers(live_ws):
    conn = _Connection()

    async def body(hass):
        _with_running_app(live_ws, hass)
        await _subscribe(live_ws, hass, conn, msg_id=1)
        await _subscribe(live_ws, hass, conn, msg_id=2)
        await _subscribe(live_ws, hass, conn, msg_id=3)
        dead, kept, _other = _FakeLive.instances
        # A viewer of a stopped app does not keep the others from following.
        dead.fail = RuntimeError("worker stopped")
        session_id = _other.session_id
        viewers = hass.data[live_ws.VIEWERS_KEY]
        viewers[session_id] = (*viewers[session_id][:2], "entry2", viewers[session_id][3])

        await live_ws.async_reload_viewers(hass, "entry1")

    _run_ws(body)
    _dead, kept, other = _FakeLive.instances
    assert kept.reloads == 1
    assert other.reloads == 0

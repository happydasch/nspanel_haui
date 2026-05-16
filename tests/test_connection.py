"""Test the HAUIConnectionController state machine."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from nspanel_haui.haui.abstract.event import HAUIEvent
from nspanel_haui.haui.controller.connection import (
    ConnectionState,
    HAUIConnectionController,
)
from nspanel_haui.haui.mapping.const import ESPResponse, ServerRequest, ServerResponse

# ── test helpers ──────────────────────────────────────────────────────────────


class DummyESPHomeController:
    def __init__(self, parent_app=None):
        self.sent_cmds: list = []
        self._parent = parent_app

    def send_cmd(self, name: str, value: str = "", force: bool = False) -> None:
        self.sent_cmds.append((name, value, force))
        if self._parent is not None:
            self._parent.sent_esphome.append((name, value, force))


class DummyDevice:
    def __init__(self):
        self.device_info = {}
        self.connected = False
        self._initial_connect_done = False
        self._config: dict = {}

    def set_device_info(self, info: dict, append: bool = True) -> None:
        if append:
            self.device_info = {**self.device_info, **info}
        else:
            self.device_info = info

    def set_connected(self, connected: bool) -> None:
        self.connected = connected

    def get(self, key: str, default=0):
        """Minimal get() stub - HAUIBase.debug_log calls self.app.device.get()."""
        return default


class DummyApp:
    def __init__(self):
        self.timers: dict[str, callable] = {}
        self.meta: dict[str, dict] = {}
        self.controller = {"esphome": DummyESPHomeController(parent_app=self)}
        self.device = DummyDevice()
        self.logged: list = []
        self.sent_esphome: list = []

    def log(self, msg: str, **kwargs) -> None:
        self.logged.append((msg, kwargs))

    def debug_log(self, msg: str, **kwargs) -> None:
        pass  # suppress in tests

    def get(self, key: str, default=None):
        return default

    def run_every(self, cb: callable, start: str, interval: float) -> str:
        handle = f"t{len(self.timers)}"
        self.timers[handle] = cb
        return handle

    def run_in(self, cb: callable, delay: float) -> str:
        handle = f"t{len(self.timers)}"
        self.timers[handle] = cb
        return handle

    def cancel_timer(self, handle: str) -> None:
        self.timers.pop(handle, None)

    def send_esphome(self, name: str, value: str = "", retain: bool = False) -> None:
        self.sent_esphome.append((name, value, retain))


# ── fixtures ─────────────────────────────────────────────────────────────────


def make_controller(app=None):
    if app is None:
        app = DummyApp()
    cb = MagicMock()
    ctrl = HAUIConnectionController(app, {"heartbeat_interval": 5.0}, cb)
    ctrl.start_part()
    return app, cb, ctrl


# ── tests ────────────────────────────────────────────────────────────────────


class TestConnectionStateMachine:
    def test_initial_state_is_disconnected(self):
        _, _, ctrl = make_controller()
        assert ctrl._state == ConnectionState.DISCONNECTED
        assert ctrl.is_connected is False
        assert ctrl.connected is False
        assert ctrl.connection_state == ConnectionState.DISCONNECTED

    def test_req_connection_transitions_to_handshaking(self):
        app, cb, ctrl = make_controller()
        event = HAUIEvent(ServerRequest.REQ_CONNECTION, '{"name":"test"}')

        ctrl.process_event(event)

        assert ctrl._state == ConnectionState.HANDSHAKING
        assert ctrl.is_connected is False
        # Should have sent hub_connection_response
        expected = ServerResponse.HUB_CONNECTION_RESPONSE
        assert any(name == expected for name, _, _ in app.sent_esphome), (
            f"Expected {expected} in sent commands: {[n for n, _, _ in app.sent_esphome]}"
        )
        # Callback should NOT have been called (not yet connected)
        cb.assert_not_called()

    def test_res_connection_during_handshaking_sends_req_device_state(self):
        app, cb, ctrl = make_controller()
        event = HAUIEvent(ServerRequest.REQ_CONNECTION, '{"name":"test"}')
        ctrl.process_event(event)
        app.sent_esphome.clear()

        event2 = HAUIEvent(
            ServerRequest.RES_CONNECTION,
            '{"heartbeat_interval":5.0}',
        )
        ctrl.process_event(event2)

        assert ctrl._state == ConnectionState.HANDSHAKING
        expected = "esphome.req_device_state"
        assert any(name == expected for name, _, _ in app.sent_esphome), (
            f"Expected {expected}: {[n for n, _, _ in app.sent_esphome]}"
        )
        cb.assert_not_called()

    def test_res_device_state_during_handshaking_transitions_to_connected(self):
        app, cb, ctrl = make_controller()

        # Drive through handshake steps 1 and 2
        ctrl.process_event(HAUIEvent(ServerRequest.REQ_CONNECTION, '{"name":"test"}'))
        ctrl.process_event(HAUIEvent(ServerRequest.RES_CONNECTION, '{"heartbeat_interval":5.0}'))

        # Step 3: res_device_state
        event3 = HAUIEvent(ESPResponse.RES_DEVICE_STATE, '{"page":"5","brightness":"80"}')
        ctrl.process_event(event3)

        assert ctrl._state == ConnectionState.CONNECTED
        assert ctrl.is_connected is True
        cb.assert_called_once_with(True)
        # Should have sent hub_connection_initialized
        expected = ServerResponse.HUB_CONNECTION_INITIALIZED
        assert any(name == expected for name, _, _ in app.sent_esphome)

    def test_timeout_when_connected_transitions_to_disconnected(self):
        _, cb, ctrl = make_controller()

        # Force CONNECTED state
        ctrl._set_state(ConnectionState.CONNECTED)
        cb.reset_mock()

        # Manually set last_time far in the past
        ctrl._last_time = time.monotonic() - 20
        ctrl._heartbeat_interval = 5.0
        ctrl._overdue_factor = 2.0

        ctrl._check_timeout()

        assert ctrl._state == ConnectionState.DISCONNECTED
        assert ctrl.is_connected is False
        cb.assert_called_once_with(False)

    def test_heartbeat_event_updates_last_time(self):
        _, _, ctrl = make_controller()

        old_time = ctrl._last_time
        # Heartbeat while CONNECTED
        ctrl._set_state(ConnectionState.CONNECTED)

        event = HAUIEvent(ServerRequest.HEARTBEAT, "alive")
        ctrl.process_event(event)

        # last_time should have advanced
        assert ctrl._last_time > old_time
        assert ctrl._state == ConnectionState.CONNECTED  # unchanged

    def test_heartbeat_event_while_disconnected_triggers_livesign(self):
        """Heartbeat while DISCONNECTED triggers livesign handshake.
        Heartbeats from a device that lost sync are legitimate livesigns."""
        app, _, ctrl = make_controller()
        assert ctrl._state == ConnectionState.DISCONNECTED

        event = HAUIEvent(ServerRequest.HEARTBEAT, "alive")
        ctrl.process_event(event)

        # Should transition to HANDSHAKING (heartbeat is a livesign)
        assert ctrl._state == ConnectionState.HANDSHAKING
        expected = ServerResponse.HUB_CONNECTION_RESPONSE
        assert any(name == expected for name, _, _ in app.sent_esphome)

    def test_livesign_event_while_disconnected_triggers_handshake(self):
        app, _, ctrl = make_controller()
        assert ctrl._state == ConnectionState.DISCONNECTED

        # A non-handshake event should trigger livesign handshake
        event = HAUIEvent("esphome.page", "5")
        ctrl.process_event(event)

        assert ctrl._state == ConnectionState.HANDSHAKING
        expected = ServerResponse.HUB_CONNECTION_RESPONSE
        assert any(name == expected for name, _, _ in app.sent_esphome)

    def test_livesign_does_not_fall_through(self):
        """Livesign must return early - the same event must not be processed
        as a regular event."""
        app, _, ctrl = make_controller()
        assert ctrl._state == ConnectionState.DISCONNECTED

        # A page event while disconnected triggers livesign
        event = HAUIEvent("esphome.page", "5")
        ctrl.process_event(event)

        # After livesign, state is HANDSHAKING. The page event should NOT
        # have been processed further (no extra side effects).
        # Count how many hub_connection_response were sent - should be exactly 1
        expected = ServerResponse.HUB_CONNECTION_RESPONSE
        count = sum(1 for name, _, _ in app.sent_esphome if name == expected)
        assert count == 1, f"Expected exactly 1 {expected}, got {count}"

    def test_unexpected_event_in_wrong_state_is_logged(self):
        app, _, ctrl = make_controller()

        # res_connection while DISCONNECTED is unexpected
        event = HAUIEvent(ServerRequest.RES_CONNECTION, '{"heartbeat_interval":5.0}')
        ctrl.process_event(event)

        # Should log a warning and remain DISCONNECTED
        assert ctrl._state == ConnectionState.DISCONNECTED

    def test_full_handshake_cycle(self):
        """Complete DISCONNECTED → CONNECTED handshake through all steps."""
        app, cb, ctrl = make_controller()
        assert ctrl._state == ConnectionState.DISCONNECTED

        # Step 1: req_connection
        ctrl.process_event(HAUIEvent(ServerRequest.REQ_CONNECTION, '{"name":"test"}'))
        assert ctrl._state == ConnectionState.HANDSHAKING

        # Step 2: res_connection
        ctrl.process_event(HAUIEvent(ServerRequest.RES_CONNECTION, '{"heartbeat_interval":5.0}'))
        assert ctrl._state == ConnectionState.HANDSHAKING

        # Step 3: res_device_state
        ctrl.process_event(HAUIEvent(ESPResponse.RES_DEVICE_STATE, '{"page":"1"}'))
        assert ctrl._state == ConnectionState.CONNECTED
        cb.assert_called_once_with(True)

    def test_reconnect_cycle(self):
        """CONNECTED → timeout → reconnection."""
        _, cb, ctrl = make_controller()

        # First: CONNECTED
        ctrl._set_state(ConnectionState.CONNECTED)
        cb.reset_mock()

        # Timeout → DISCONNECTED
        ctrl._last_time = time.monotonic() - 20
        ctrl._check_timeout()
        assert ctrl._state == ConnectionState.DISCONNECTED
        cb.assert_called_once_with(False)

        # Reconnect via full handshake
        cb.reset_mock()
        ctrl.process_event(HAUIEvent(ServerRequest.REQ_CONNECTION, '{"name":"test"}'))
        assert ctrl._state == ConnectionState.HANDSHAKING
        ctrl.process_event(HAUIEvent(ServerRequest.RES_CONNECTION, '{"heartbeat_interval":5.0}'))
        assert ctrl._state == ConnectionState.HANDSHAKING
        ctrl.process_event(HAUIEvent(ESPResponse.RES_DEVICE_STATE, '{"page":"1"}'))
        assert ctrl._state == ConnectionState.CONNECTED
        cb.assert_called_once_with(True)

    def test_res_device_state_while_connected_is_replay(self):
        """res_device_state while already CONNECTED should be logged as replay,
        not trigger another callback."""
        _, cb, ctrl = make_controller()

        # Drive to CONNECTED
        ctrl._set_state(ConnectionState.CONNECTED)
        cb.reset_mock()

        event = HAUIEvent(ESPResponse.RES_DEVICE_STATE, '{"page":"5"}')
        ctrl.process_event(event)

        # State unchanged, callback not called again
        assert ctrl._state == ConnectionState.CONNECTED
        cb.assert_not_called()

    def test_connected_property_returns_expected_values(self):
        _, _, ctrl = make_controller()

        assert ctrl.connected is False
        assert ctrl.is_connected is False

        ctrl._set_state(ConnectionState.CONNECTED)
        assert ctrl.connected is True
        assert ctrl.is_connected is True

        ctrl._set_state(ConnectionState.DISCONNECTED)
        assert ctrl.connected is False
        assert ctrl.is_connected is False

"""Connection Controller - state-machine handshake with bidirectional heartbeats."""

from __future__ import annotations

import json
import time
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPAction, ESPRequest, ESPResponse, ServerRequest, ServerResponse
from ..version import get_version


class ConnectionState(StrEnum):
    """Three-state connection model for the handshake state machine."""

    DISCONNECTED = "disconnected"
    HANDSHAKING = "handshaking"
    CONNECTED = "connected"


class HAUIConnectionController(HAUIBase):
    """Connection controller with 3-state handshake and bidirectional heartbeats.

    State machine:
      DISCONNECTED ──req_connection──▶ HANDSHAKING ──res_device_state──▶ CONNECTED
           ▲                                                               │
           └───────────────────── timeout ─────────────────────────────────┘

    Timeouts:
      - HEARTBEAT: CONNECTED → DISCONNECTED when no device heartbeat
        within heartbeat_interval x overdue_factor (min 10s).
      - HANDSHAKE: HANDSHAKING → DISCONNECTED when the 3-step handshake
        does not complete within 15 s (device retries req_connection
        every 10 s).

    Bidirectional heartbeats:
      - Hub→Device: periodic ``hub_heartbeat`` at the device-declared interval
      - Device→Hub: monitor ``esphome.heartbeat`` events
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any], connection_callback: Any) -> None:
        """Initialise the Connection Controller.

        Args:
            app: The owning NSPanelHAUI instance.
            config: Controller configuration dictionary.
            connection_callback: Callable invoked on connection-state
                changes with a single ``bool`` argument.
        """
        super().__init__(app, config)
        self.debug_log(f"Creating Connection Controller with config: {config}")

        # State - replaces the old ``self.connected`` boolean
        self._state: ConnectionState = ConnectionState.DISCONNECTED

        # Heartbeat parameters (populated in start_part / handshake)
        self._heartbeat_interval: float = 5.0
        self._overdue_factor: float = 2.0
        self._last_time: float = time.monotonic()

        # Timers
        self._timer: Any = None
        self._hub_heartbeat_timer: Any = None
        self._disconnect_warn_timer: Any = None
        self._handshake_timer: Any = None

        # Track when we entered DISCONNECTED so we can warn on extended downtime
        self._last_connection_time: float = 0.0
        self._disconnected_since: float | None = None

        # Callback
        self._connection_callback = connection_callback

    @property
    def connection_state(self) -> ConnectionState:
        """Expose the raw connection state enum for debug/monitoring."""
        return self._state

    @property
    def last_connection_time(self) -> float:
        """Return wall-clock timestamp of the most recent CONNECTED transition."""
        return self._last_connection_time

    @property
    def is_connected(self) -> bool:
        """Preferred predicate for connection status (read-only)."""
        return self._state == ConnectionState.CONNECTED

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_state(self, new_state: ConnectionState) -> None:
        """Atomically transition to *new_state*, running side-effects once."""
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self.log(f"Connection state: {old.value} → {new_state.value}")

        if new_state == ConnectionState.CONNECTED:
            self._on_entering_connected()
        elif new_state == ConnectionState.DISCONNECTED:
            self._on_entering_disconnected(old)
        elif new_state == ConnectionState.HANDSHAKING:
            self._on_entering_handshaking()

    # ------------------------------------------------------------------
    # State-transition side-effects
    # ------------------------------------------------------------------

    def _on_entering_connected(self) -> None:
        """Run side-effects when transitioning to CONNECTED."""
        self._update_last_time()
        self._last_connection_time = time.time()

        self._stop_handshake_timer()
        self.send_esphome(ServerResponse.HUB_CONNECTION_INITIALIZED, "", True)
        # Explicitly reset the device's inactivity timer so that display
        # timeouts (dim/sleep/page) start fresh after every connection
        # (including reconnections during a fast hub restart).
        self.send_esphome(ESPAction.RESET_LAST_INTERACTION, "0", True)
        self._start_heartbeat_timer()
        self._start_timer()
        self._disconnected_since = None
        self._connection_callback(True)

    def _on_entering_disconnected(self, old: ConnectionState) -> None:
        """Run side-effects when transitioning to DISCONNECTED."""
        if old == ConnectionState.CONNECTED:
            self.send_esphome(ServerResponse.HUB_CONNECTION_CLOSED, "", True)
            self._connection_callback(False)
        self._stop_heartbeat_timer()
        self._stop_handshake_timer()
        if self._disconnected_since is None:
            self._disconnected_since = time.monotonic()

    def _on_entering_handshaking(self) -> None:
        """Run side-effects when transitioning to HANDSHAKING.

        Start a timer so a stalled handshake (e.g. service calls failing
        silently) does not leave us in HANDSHAKING forever.
        The device retries req_connection every ~10 s, so 15 s gives
        one full retry cycle.
        """
        self._start_handshake_timer()

    # ------------------------------------------------------------------
    # Hub→Device heartbeat timer
    # ------------------------------------------------------------------

    def _initiate_handshake(self, context: str = "livesign") -> None:
        """Transition to HANDSHAKING and send connection response to device.

        Args:
            context: Description of why the handshake is being initiated
                (e.g. "livesign" or "req_connection").
        """
        self.log(f"Initiating handshake ({context})")
        self._set_state(ConnectionState.HANDSHAKING)
        self.send_esphome(
            ServerResponse.HUB_CONNECTION_RESPONSE,
            {"version": get_version()},
            True,
        )

    def _start_heartbeat_timer(self) -> None:
        """Start sending periodic ``hub_heartbeat`` messages to the device.

        First heartbeat fires immediately (``now+0``), then every interval.
        """
        self._stop_heartbeat_timer()
        self._hub_heartbeat_timer = self.app.run_every(
            self._send_hub_heartbeat,
            "now+0",
            self._heartbeat_interval,
        )

    def _stop_heartbeat_timer(self) -> None:
        """Cancel the hub→device heartbeat timer."""
        if self._hub_heartbeat_timer:
            self.app.cancel_timer(self._hub_heartbeat_timer)
            self._hub_heartbeat_timer = None

    def _send_hub_heartbeat(self, kwargs: dict[str, Any]) -> None:
        """Callback: send a single ``hub_heartbeat`` to the device."""
        self.send_esphome(ServerResponse.HUB_HEARTBEAT, "", True)

    # ------------------------------------------------------------------
    # Handshake timeout timer
    # ------------------------------------------------------------------

    _HANDSHAKE_TIMEOUT: float = 15.0  # seconds before stalled handshake → DISCONNECTED

    def _start_handshake_timer(self) -> None:
        """Start a one-shot timer that transitions to DISCONNECTED if the
        handshake does not complete within ``_HANDSHAKE_TIMEOUT`` seconds."""
        self._stop_handshake_timer()
        self._handshake_timer = self.app.run_in(
            self._on_handshake_timeout,
            self._HANDSHAKE_TIMEOUT,
        )

    def _stop_handshake_timer(self) -> None:
        """Cancel the handshake timeout timer if running."""
        if self._handshake_timer:
            self.app.cancel_timer(self._handshake_timer)
            self._handshake_timer = None

    def _on_handshake_timeout(self, kwargs: dict[str, Any]) -> None:
        """Callback: handshake did not complete in time → DISCONNECTED."""
        if self._state == ConnectionState.HANDSHAKING:
            self.log(
                f"Handshake timed out after {self._HANDSHAKE_TIMEOUT}s",
                level="WARNING",
            )
            self._set_state(ConnectionState.DISCONNECTED)

    # ------------------------------------------------------------------
    # Timeout monitoring (Device→Hub)
    # ------------------------------------------------------------------

    def _check_timeout(self, _kwargs: dict | None = None) -> None:
        """Check whether the device heartbeat has timed out.

        Only active in CONNECTED state. Transitions to DISCONNECTED
        when ``last_time + max(interval × factor, 10.0)`` is exceeded.

        Args:
            _kwargs: Unused - accepts the scheduler kwargs dict that
                ``run_every`` passes to callbacks.
        """
        if self._state != ConnectionState.CONNECTED:
            return

        time_max = self._last_time + max(self._heartbeat_interval * self._overdue_factor, 10.0)
        if time.monotonic() > time_max:
            self.log("Device connection timeout - no heartbeat received")
            self._set_state(ConnectionState.DISCONNECTED)

    def _log_extended_disconnect(self) -> None:
        """Log a warning if the device has been disconnected for >60s.

        Resets the timer on each fire so the warning appears at most
        once per minute.
        """
        if self._state == ConnectionState.DISCONNECTED and self._disconnected_since is not None:
            elapsed = time.monotonic() - self._disconnected_since
            if elapsed > 60:
                self.log(
                    f"Device disconnected for >{int(elapsed)}s",
                    level="WARNING",
                )
                self._disconnected_since = time.monotonic()

    def _start_timer(self) -> None:
        """Start (or restart) the timeout-check timer.

        The first timeout check fires after one full ``heartbeat_interval``
        (so the device has time to establish heartbeats), then every interval.
        """
        self._stop_timer()
        self._timer = self.app.run_every(
            self._check_timeout,
            f"now+{int(self._heartbeat_interval)}",
            self._heartbeat_interval,
        )

    def _stop_timer(self) -> None:
        """Stop the timeout-check timer."""
        if self._timer:
            self.app.cancel_timer(self._timer)
            self._timer = None

    def _update_last_time(self) -> None:
        """Record that device activity was seen (resets the timeout clock)."""
        self._last_time = time.monotonic()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_part(self) -> None:
        """Read heartbeat parameters from config and begin monitoring."""
        raw = self.get("heartbeat_interval")
        self._heartbeat_interval = max(float(raw) if raw else 5.0, 0.5)
        self._overdue_factor = float(self.get("overdue_factor", 2.0))
        self.log(
            f"Using heartbeat interval: {self._heartbeat_interval}s, "
            f"overdue factor: {self._overdue_factor}"
        )
        self._start_timer()
        # Extended-disconnect warning fires at most once per minute
        self._disconnect_warn_timer = self.app.run_every(
            lambda _: self._log_extended_disconnect(),
            "now+30",
            60,
        )

    def stop_part(self) -> None:
        """Stop all timers."""
        self._stop_timer()
        self._stop_heartbeat_timer()
        self._stop_handshake_timer()
        if self._disconnect_warn_timer:
            self.app.cancel_timer(self._disconnect_warn_timer)
            self._disconnect_warn_timer = None

    # ------------------------------------------------------------------
    # Event handling - 3-step handshake + heartbeat
    # ------------------------------------------------------------------

    # Events that are excluded from livesign detection (they are part of
    # the handshake protocol itself, not external signs of life).
    _LIVESIGN_EXCLUDED: frozenset = frozenset(
        {
            ServerRequest.REQ_CONNECTION,
            ServerRequest.RES_CONNECTION,
            ESPResponse.RES_DEVICE_STATE,
        }
    )

    def process_event(self, event: HAUIEvent) -> None:
        """Process a single event.

        Handles:
        * Livesign detection - any event while DISCONNECTED triggers
          handshake re-initiation (except handshake messages themselves).
        * Device→Hub heartbeats (``esphome.heartbeat``) - update
          ``_last_time`` to prevent timeout while connected.
        * 3-step connection handshake:
            1. ``req_connection`` - hub replies ``hub_connection_response``
            2. ``res_connection`` - hub reads heartbeat interval, sends
               ``req_device_state``
            3. ``res_device_state`` - hub sends ``hub_connection_initialized``
               and marks the connection as CONNECTED
        """
        name = event.name

        # --- Livesign detection: any event when disconnected → handshake ---
        # Heartbeats that arrive while DISCONNECTED are NOT filtered out -
        # they ARE legitimate livesigns from a device that still runs but
        # lost connection sync with the hub.  Only handshake protocol
        # messages (res_connection, res_device_state) are excluded since
        # they are part of the handshake itself.
        if self._state == ConnectionState.DISCONNECTED:
            if name not in self._LIVESIGN_EXCLUDED:
                self._handle_livesign(event)
                return

        if name == ServerRequest.HEARTBEAT:
            self._handle_heartbeat(event)
        elif name == ServerRequest.REQ_CONNECTION:
            self._handle_req_connection(event)
        elif name == ServerRequest.RES_CONNECTION:
            self._handle_res_connection(event)
        elif name == ESPResponse.RES_DEVICE_STATE:
            self._handle_res_device_state(event)

    def _handle_livesign(self, event: HAUIEvent) -> None:
        """Handle any event while DISCONNECTED — treat as livesign → handshake."""
        self.log(f"Livesign received while disconnected: {event.name}, initiating handshake")
        self._initiate_handshake("livesign")

    def _handle_heartbeat(self, event: HAUIEvent) -> None:
        """Handle device→hub heartbeat.

        Updates ``_last_time`` and responds so the device's hub_heartbeat
        timestamp stays fresh.
        """
        self._update_last_time()
        # Bidirectional heartbeat: respond so the device's hub_heartbeat
        # timestamp stays fresh.  The periodic timer (run_every) is a
        # fallback; this event-driven response ensures the device never
        # times out even if the timer callback fails silently.
        self._send_hub_heartbeat({})

    def _handle_req_connection(self, event: HAUIEvent) -> None:
        """Handle handshake step 1: device requests connection."""
        device = self.app.device
        if self._state == ConnectionState.HANDSHAKING:
            # Device is retrying while we wait for res_connection --
            # our response is already in-flight, so just ignore.
            return
        if isinstance(event.value, str):
            connection_request = json.loads(event.value)
            device.set_device_info(connection_request, append=False)
            self.debug_log(f"Connection request from device: {connection_request}")
        self._initiate_handshake("req_connection")

    def _handle_res_connection(self, event: HAUIEvent) -> None:
        """Handle handshake step 2: device responds with capabilities."""
        device = self.app.device
        if self._state != ConnectionState.HANDSHAKING:
            if self._state == ConnectionState.CONNECTED:
                # Duplicate/retry res_connection after handshake — device
                # is alive, treat as heartbeat refresh.
                self._update_last_time()
                self.debug_log(f"res_connection received in state {self._state.value} (ignored)")
            else:
                self.log(
                    f"Unexpected res_connection in state {self._state.value}",
                    level="WARNING",
                )
            return
        if isinstance(event.value, str):
            connection_response = json.loads(event.value)
            # Adopt the device's heartbeat_interval if declared
            try:
                dev_interval = float(connection_response.get("heartbeat_interval", 5.0))
                if dev_interval > 0.5:
                    self._heartbeat_interval = dev_interval
                    self.log(f"Device heartbeat interval: {self._heartbeat_interval}s")
            except (TypeError, ValueError):
                self.log(
                    "Invalid heartbeat_interval from device, using default",
                    level="WARNING",
                )
            device.set_device_info(connection_response, append=True)
            self.debug_log(f"Connection response from device: {connection_response}")
        self.send_esphome(ESPRequest.REQ_DEVICE_STATE)

    def _handle_res_device_state(self, event: HAUIEvent) -> None:
        """Handle handshake step 3 or reconnect replay: device state."""
        device = self.app.device
        if isinstance(event.value, str):
            try:
                device_state = json.loads(event.value)
                device.set_device_info(device_state, append=True)
            except json.JSONDecodeError:
                self.log("Invalid device state JSON", level="WARNING")
        if self._state == ConnectionState.HANDSHAKING:
            self.debug_log(f"Device state received {event.value}")
            self._set_state(ConnectionState.CONNECTED)
            # Emit a compact INFO summary of key device info
            info = device.device_info
            parts = [f"name={info.get('name', '?')}"]
            if info.get("ip"):
                parts.append(f"ip={info['ip']}")
            if info.get("tft_version"):
                parts.append(f"tft={info['tft_version']}")
            if info.get("page"):
                parts.append(f"page={info['page']}")
            self.log(f"Device connected | {' | '.join(parts)}")
        elif self._state == ConnectionState.CONNECTED:
            self.debug_log(f"Device state received (replay) {event.value}")
        else:
            self.log(
                f"Unexpected res_device_state in state {self._state.value}",
                level="WARNING",
            )

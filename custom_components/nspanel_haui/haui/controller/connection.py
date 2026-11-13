"""Connection Controller - state-machine handshake with bidirectional heartbeats."""

from __future__ import annotations

import datetime
import json
import time
from collections import deque
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPRequest, ESPResponse, ServerRequest, ServerResponse
from ..version import get_integration_version

# How far back the connection health looks, and when a device heartbeat counts
# as late: more than this many heartbeat intervals after the previous one.
HEALTH_WINDOW = 86_400.0
LATE_HEARTBEAT_FACTOR = 1.5
RECENT_DROPS = 5


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
        self.log(f"Creating Connection Controller with config: {config}", level="DEBUG")

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
        # Human-readable reason for the last disconnect (heartbeat timeout,
        # handshake timeout, app stopped, ...).  None while connected.
        self._last_disconnect_reason: str | None = None
        # Connection health for the editor: drops of an established connection
        # as (wall time, reason) and late device heartbeats as (wall time, gap).
        # Bounded so a flapping device cannot grow them without limit.
        self._drops: deque[tuple[float, str]] = deque(maxlen=200)
        self._late_heartbeats: deque[tuple[float, float]] = deque(maxlen=1000)
        self._last_heartbeat: float | None = None

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

    @property
    def last_disconnect_reason(self) -> str | None:
        """Human-readable reason of the most recent disconnect (None while connected)."""
        return self._last_disconnect_reason

    @property
    def disconnected_since(self) -> float | None:
        """Wall-clock timestamp of when the device went offline (None while connected)."""
        if self._disconnected_since is None:
            return None
        return time.time() - (time.monotonic() - self._disconnected_since)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_state(self, new_state: ConnectionState, reason: str | None = None) -> None:
        """Atomically transition to *new_state*, running side-effects once.

        Args:
            new_state: Target state.
            reason: Optional human-readable reason for the transition, stored
                as ``last_disconnect_reason`` when leaving CONNECTED/HANDSHAKING
                and recorded as a drop when leaving CONNECTED.
        """
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self.log(f"Connection state: {old.value} → {new_state.value}")
        if old == ConnectionState.CONNECTED:
            self._drops.append((time.time(), reason or "lost connection"))

        if new_state == ConnectionState.CONNECTED:
            self._last_disconnect_reason = None
            self._on_entering_connected()
        elif new_state == ConnectionState.DISCONNECTED:
            self._last_disconnect_reason = reason or "lost connection"
            self._on_entering_disconnected(old)
        elif new_state == ConnectionState.HANDSHAKING:
            self._on_entering_handshaking(old)

    # ------------------------------------------------------------------
    # State-transition side-effects
    # ------------------------------------------------------------------

    def _on_entering_connected(self) -> None:
        """Run side-effects when transitioning to CONNECTED."""
        self._update_last_time()
        self._last_connection_time = time.time()
        # Gaps are measured within one connection. A device that reconnects
        # without the hub timing out first (a reboot) sends no heartbeats while
        # it is handshaking; that outage is a drop, not a late heartbeat.
        self._last_heartbeat = None

        self._stop_handshake_timer()
        self.send_esphome(ServerResponse.HUB_CONNECTION_INITIALIZED, "", True)
        # Reconnection restores transport, not user activity; keep the
        # firmware's existing inactivity age.
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

    def _on_entering_handshaking(self, old: ConnectionState) -> None:
        """Run side-effects when transitioning to HANDSHAKING.

        Start a timer so a stalled handshake (e.g. service calls failing
        silently) does not leave us in HANDSHAKING forever.
        The device retries req_connection every ~10 s, so 15 s gives
        one full retry cycle.

        From CONNECTED the device rebooted or gave up on the hub without the
        hub timing out first: the connection is reported lost now, as a
        heartbeat timeout would, so the reconnect that follows (or the
        handshake timeout) is reported like any other.
        """
        if old == ConnectionState.CONNECTED:
            self._connection_callback(False)
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
        # From CONNECTED this is a drop: the device rebooted or gave up on the
        # hub's heartbeats and asks for a new connection.
        self._set_state(ConnectionState.HANDSHAKING, reason="device reconnected")
        self.send_esphome(
            ServerResponse.HUB_CONNECTION_RESPONSE,
            {"version": get_integration_version()},
            True,
        )

    def _start_heartbeat_timer(self) -> None:
        """Start sending periodic ``hub_heartbeat`` messages to the device.

        First heartbeat fires immediately (``now+0``), then every interval.

        The timer runs on the event loop (``on_loop``) and its publish is
        fire-and-forget: every other path to the device is queued on the
        app's single worker thread, which render bursts, update checks or a
        blocked publish can stall for seconds.  The device force-disconnects
        the hub after two missed heartbeats — and wakes the display when it
        does — so the heartbeat must not depend on the worker at all.
        """
        self._stop_heartbeat_timer()
        self._hub_heartbeat_timer = self.app.run_every(
            self._send_hub_heartbeat,
            "now+0",
            self._heartbeat_interval,
            on_loop=True,
        )

    def _stop_heartbeat_timer(self) -> None:
        """Cancel the hub→device heartbeat timer."""
        self._cancel_timer("_hub_heartbeat_timer")

    def _send_hub_heartbeat(self, kwargs: dict[str, Any]) -> None:
        """Send a single ``hub_heartbeat``, fire-and-forget.

        Uses the ESPHome controller's detached publish (which strips the
        ``esphome.`` prefix like ``send_cmd``), bypassing the worker-side
        dedup and batching: the heartbeat is sent straight from the event
        loop and never queues behind other work.
        """
        esp_ctrl = self.app.controller.get("esphome")
        if esp_ctrl is not None:
            esp_ctrl.publish_detached(ServerResponse.HUB_HEARTBEAT)

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
        self._cancel_timer("_handshake_timer")

    def _on_handshake_timeout(self, kwargs: dict[str, Any]) -> None:
        """Callback: handshake did not complete in time → DISCONNECTED."""
        if self._state == ConnectionState.HANDSHAKING:
            self.log(
                f"Handshake timed out after {self._HANDSHAKE_TIMEOUT}s",
                level="WARNING",
            )
            self._set_state(ConnectionState.DISCONNECTED, reason="handshake timeout")

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
            self._set_state(ConnectionState.DISCONNECTED, reason="heartbeat timeout")

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
        self._cancel_timer("_timer")

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
        self._cancel_timer("_disconnect_warn_timer")

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
        self._record_heartbeat()
        # Bidirectional heartbeat: respond so the device's hub_heartbeat
        # timestamp stays fresh.  The periodic loop-side timer is the
        # primary sender; this event-driven reply is a fallback for a lost
        # timer (and re-anchors the device right after a jittery interval).
        self._send_hub_heartbeat({})

    def _record_heartbeat(self) -> None:
        """Note a device heartbeat that came late, measured from the previous one."""
        now = time.monotonic()
        if self._state != ConnectionState.CONNECTED:
            self._last_heartbeat = None
            return
        if self._last_heartbeat is not None:
            gap = now - self._last_heartbeat
            if gap > self._heartbeat_interval * LATE_HEARTBEAT_FACTOR:
                self._late_heartbeats.append((time.time(), gap))
        self._last_heartbeat = now

    def health(self) -> dict[str, Any]:
        """Drops and late heartbeats of the last 24 hours, for the editor's diagnostics.

        The history lives in memory: it starts empty when the hub starts.
        """
        cutoff = time.time() - HEALTH_WINDOW
        drops = [drop for drop in self._drops if drop[0] >= cutoff]
        gaps = [gap for stamp, gap in self._late_heartbeats if stamp >= cutoff]
        return {
            "drops_24h": len(drops),
            "recent_drops": [
                {
                    "time": datetime.datetime.fromtimestamp(stamp, tz=datetime.UTC).isoformat(),
                    "reason": reason,
                }
                for stamp, reason in reversed(drops[-RECENT_DROPS:])
            ],
            "late_heartbeats_24h": len(gaps),
            "longest_heartbeat_gap": round(max(gaps), 1) if gaps else None,
            "heartbeat_interval": self._heartbeat_interval,
        }

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
            self.log(f"Connection request from device: {connection_request}", level="DEBUG")
        self._initiate_handshake("req_connection")

    def _handle_res_connection(self, event: HAUIEvent) -> None:
        """Handle handshake step 2: device responds with capabilities."""
        device = self.app.device
        if self._state != ConnectionState.HANDSHAKING:
            if self._state == ConnectionState.CONNECTED:
                # Duplicate/retry res_connection after handshake — device
                # is alive, treat as heartbeat refresh.
                self._update_last_time()
                self.log(
                    f"res_connection received in state {self._state.value} (ignored)",
                    level="DEBUG",
                )
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
            except TypeError, ValueError:
                self.log(
                    "Invalid heartbeat_interval from device, using default",
                    level="WARNING",
                )
            device.set_device_info(connection_response, append=True)
            self.log(f"Connection response from device: {connection_response}", level="DEBUG")
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
            self.log(f"Device state received {event.value}", level="DEBUG")
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
            self.log(f"Device state received (replay) {event.value}", level="DEBUG")
        else:
            self.log(
                f"Unexpected res_device_state in state {self._state.value}",
                level="WARNING",
            )

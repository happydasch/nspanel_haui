"""Tests that each app's callbacks run on one worker, in order, and honour cancellation.

A real event loop runs in a background thread, as in Home Assistant. The fake
``hass.async_add_executor_job`` uses a multi-thread pool, like HA's shared
executor, so code that dispatches there runs callbacks concurrently.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor

import pytest
from nspanel_haui.ha_adapter import HAAdapter


class _Hass:
    def __init__(self, loop, pool):
        self.loop = loop
        self._pool = pool
        self.bus_listeners: list = []
        self.bus = types.SimpleNamespace(async_listen=self._async_listen)

    def _async_listen(self, event_type, cb):
        self.bus_listeners.append(cb)
        return lambda: None

    def async_add_executor_job(self, fn, *args):
        return self.loop.run_in_executor(self._pool, fn, *args)

    def async_create_task(self, coro):
        return self.loop.create_task(coro)


class _HelpersEvent:
    """Fake homeassistant.helpers.event: records callbacks instead of scheduling them."""

    def __init__(self):
        self.state_cbs: dict = {}
        self.later: list = []
        self.intervals: list = []

    def async_track_state_change_event(self, hass, entity_id, cb):
        self.state_cbs[entity_id] = cb
        return lambda: self.state_cbs.pop(entity_id, None)

    def async_call_later(self, hass, delay, cb):
        self.later.append(cb)
        return lambda: None

    def async_track_time_interval(self, hass, cb, interval):
        self.intervals.append(cb)
        return lambda: None


def _state_event(new):
    state = types.SimpleNamespace
    old_state = state(state="old", attributes={})
    return types.SimpleNamespace(
        data={"old_state": old_state, "new_state": state(state=new, attributes={})}
    )


@pytest.fixture
def env(monkeypatch):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    pool = ThreadPoolExecutor(max_workers=4)
    helpers = _HelpersEvent()
    module = types.ModuleType("homeassistant.helpers.event")
    module.async_track_state_change_event = helpers.async_track_state_change_event
    module.async_call_later = helpers.async_call_later
    module.async_track_time_interval = helpers.async_track_time_interval
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.event", module)
    # The stubbed core module may be a restricted/wrapping mock that does not
    # expose ``callback``; raising=False lets the patch create it either way.
    monkeypatch.setattr(sys.modules["homeassistant.core"], "callback", lambda f: f, raising=False)
    adapter = HAAdapter(_Hass(loop, pool), "hub")
    yield adapter, loop, helpers
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    loop.close()
    pool.shutdown(wait=False)


def _on_loop(loop, fn, *args):
    """Run an HA-side callback on the event loop and wait until it returned."""
    done = threading.Event()

    def run():
        fn(*args)
        done.set()

    loop.call_soon_threadsafe(run)
    assert done.wait(5)


def _occupy_worker(adapter, loop, helpers):
    """Start a state callback that blocks until the returned event is set."""
    release = threading.Event()
    started = threading.Event()

    def busy(*_args):
        started.set()
        release.wait(5)

    adapter.listen_state(busy, "sensor.busy")
    _on_loop(loop, helpers.state_cbs["sensor.busy"], _state_event("busy"))
    assert started.wait(5)
    return release


def _settle(adapter, loop, helpers):
    """Wait until callbacks queued so far have run (a marker queued last has run)."""
    reached = threading.Event()
    adapter.listen_state(lambda *_a: reached.set(), "sensor.marker")
    _on_loop(loop, helpers.state_cbs["sensor.marker"], _state_event("mark"))
    assert reached.wait(5)


def test_state_callbacks_of_one_app_run_one_at_a_time_in_order(env):
    adapter, loop, helpers = env
    runs = []
    done = threading.Event()

    def on_change(entity_id, attribute, old, new, kwargs):
        start = time.monotonic()
        time.sleep(0.05)
        runs.append((new, start, time.monotonic(), threading.get_ident()))
        if len(runs) == 3:
            done.set()

    adapter.listen_state(on_change, "light.desk")
    for value in ("1", "2", "3"):
        _on_loop(loop, helpers.state_cbs["light.desk"], _state_event(value))

    assert done.wait(5)
    assert [r[0] for r in runs] == ["1", "2", "3"]
    assert all(later[1] >= earlier[2] for earlier, later in zip(runs, runs[1:], strict=False))
    assert len({r[3] for r in runs}) == 1


def test_device_event_waits_for_the_running_callback(env):
    adapter, loop, helpers = env
    proxy = adapter.get_plugin_api("ESPHome", device_name="kitchen", device_id="dev1")
    received = []
    proxy.listen_event(lambda *a: received.append(a), "esphome.nspanel_event")
    (on_event,) = adapter.hass.bus_listeners
    release = _occupy_worker(adapter, loop, helpers)

    event = types.SimpleNamespace(
        event_type="esphome.nspanel_event",
        data={"device_id": "dev1", "name": "esphome.touch_end", "value": "1"},
    )
    _on_loop(loop, on_event, event)
    time.sleep(0.05)
    seen_while_busy = list(received)
    release.set()
    _settle(adapter, loop, helpers)

    assert seen_while_busy == []
    assert len(received) == 1


def test_state_callback_cancelled_while_queued_does_not_run(env):
    adapter, loop, helpers = env
    calls = []
    handle = adapter.listen_state(lambda *a: calls.append(a), "light.desk")
    release = _occupy_worker(adapter, loop, helpers)

    _on_loop(loop, helpers.state_cbs["light.desk"], _state_event("on"))
    adapter.cancel_listen_state(handle)
    release.set()
    _settle(adapter, loop, helpers)

    assert calls == []


def test_timer_cancelled_after_firing_but_before_running_does_not_run(env):
    adapter, loop, helpers = env
    calls = []
    handle = adapter.run_in(lambda kwargs: calls.append(kwargs), 1)
    release = _occupy_worker(adapter, loop, helpers)

    _on_loop(loop, helpers.later[-1], None)
    adapter.cancel_timer(handle)
    release.set()
    _settle(adapter, loop, helpers)

    assert calls == []


def test_fired_one_shot_timer_leaves_no_bookkeeping(env):
    adapter, loop, helpers = env
    fired = threading.Event()
    adapter.run_in(lambda kwargs: fired.set(), 1)

    _on_loop(loop, helpers.later[-1], None)

    assert fired.wait(5)
    _settle(adapter, loop, helpers)
    assert adapter._timer_handles == {}
    assert adapter._timer_meta == {}


def test_interval_cancelled_before_its_first_fire_never_starts(env):
    adapter, loop, helpers = env
    calls = []
    handle = adapter.run_every(lambda kwargs: calls.append(kwargs), "now+5", 10)
    adapter.cancel_timer(handle)

    _on_loop(loop, helpers.later[-1], None)
    _settle(adapter, loop, helpers)

    assert helpers.intervals == []
    assert calls == []


def test_loop_side_timer_fires_while_worker_busy(env):
    """A timer registered with ``on_loop=True`` (the hub heartbeat) fires on
    the event loop even while the worker is blocked — it must never queue
    behind a render burst or a slow update check."""
    adapter, loop, helpers = env
    release = threading.Event()
    started = threading.Event()
    worker_thread: dict = {}

    def busy(*_args):
        worker_thread["id"] = threading.get_ident()
        started.set()
        release.wait(5)

    adapter.listen_state(busy, "sensor.busy")
    _on_loop(loop, helpers.state_cbs["sensor.busy"], _state_event("busy"))
    assert started.wait(5)

    fired = threading.Event()
    cb_info: dict = {}

    def heartbeat(kwargs):
        cb_info["id"] = threading.get_ident()
        cb_info["worker_still_busy"] = not release.is_set()
        fired.set()

    adapter.run_every(heartbeat, "now+0", 10, on_loop=True)
    _on_loop(loop, helpers.later[-1], None)

    assert fired.wait(5)
    assert cb_info["worker_still_busy"] is True
    assert cb_info["id"] != worker_thread["id"]
    release.set()
    _settle(adapter, loop, helpers)


def test_detached_publish_returns_immediately_while_worker_busy(env):
    """``publish_detached`` never waits for the app worker: the heartbeat calls
    it from the event loop and must return at once even when the worker sits
    in a long render."""
    adapter, loop, helpers = env
    proxy = adapter.get_plugin_api("ESPHome", device_name="kitchen", device_id="dev1")
    release = _occupy_worker(adapter, loop, helpers)

    start = time.monotonic()
    proxy.publish_detached("send_command", "x")
    elapsed = time.monotonic() - start

    release.set()
    _settle(adapter, loop, helpers)

    assert elapsed < 1.0


def test_run_off_worker_runs_the_callable_on_another_thread(env):
    """Blocking work (HTTP, disk) must never execute on the app's worker."""
    adapter, loop, helpers = env
    seen: dict = {}

    def blocking():
        seen["thread"] = threading.get_ident()
        return "done"

    worker_thread: dict = {}
    result: dict = {}

    def on_worker():
        worker_thread["id"] = threading.get_ident()
        result["value"] = adapter.run_off_worker(blocking, timeout=5)

    adapter._worker.submit(on_worker).result(10)

    assert result["value"] == "done"
    assert seen["thread"] != worker_thread["id"]


def test_run_off_worker_times_out_and_logs(env):
    """A hung request cannot hold the worker past the call's own timeout."""
    adapter, loop, helpers = env
    release = threading.Event()
    logged: list = []
    adapter.log = lambda msg, **kw: logged.append((msg, kw))

    def hung():
        release.wait(5)

    def on_worker():
        with pytest.raises(TimeoutError):
            adapter.run_off_worker(hung, timeout=0.05)

    try:
        adapter._worker.submit(on_worker).result(10)
    finally:
        release.set()

    assert any("timed out" in msg for msg, _kw in logged)


def test_submit_off_worker_delivers_the_result_on_the_worker(env):
    """Fire-and-forget I/O hands its result back on the worker, so the caller
    keeps app state single-threaded while the request runs off-thread."""
    adapter, loop, helpers = env
    io_thread: dict = {}
    delivered = threading.Event()
    seen: dict = {}

    def fetch():
        io_thread["id"] = threading.get_ident()
        return "payload"

    def apply(result, error):
        seen["result"] = result
        seen["error"] = error
        seen["thread"] = threading.get_ident()
        delivered.set()

    adapter.submit_off_worker(fetch, on_done=apply)

    assert delivered.wait(5)
    assert seen["result"] == "payload" and seen["error"] is None
    # Applied on the worker, produced on the I/O pool.
    assert seen["thread"] != io_thread["id"]


def test_submit_off_worker_reports_an_error_to_the_callback(env):
    adapter, loop, helpers = env
    delivered = threading.Event()
    seen: dict = {}

    def boom():
        raise RuntimeError("network down")

    def apply(result, error):
        seen["result"] = result
        seen["error"] = error
        delivered.set()

    adapter.submit_off_worker(boom, on_done=apply)

    assert delivered.wait(5)
    assert seen["result"] is None
    assert isinstance(seen["error"], RuntimeError)


def test_stop_shuts_the_io_pool_down(env):
    """A stopped app leaves no I/O threads behind to apply stale results."""
    adapter, loop, helpers = env
    adapter.stop()

    with pytest.raises(RuntimeError):
        adapter.run_off_worker(lambda: None, timeout=1)


def test_update_check_http_runs_off_the_worker(env, monkeypatch):
    """The hourly GitHub read must not execute on the worker's thread.

    It used to: a slow response blocked the worker, which then starved the
    hub→device heartbeat and the panel disconnected and woke its display.
    """
    adapter, loop, helpers = env
    from nspanel_haui.haui.controller import update as update_module
    from nspanel_haui.haui.controller.update import HAUIUpdateController

    seen: dict = {}

    class _Response:
        def json(self):
            return []

    def fake_get(url, timeout):
        seen["thread"] = threading.get_ident()
        seen["thread_name"] = threading.current_thread().name
        return _Response()

    monkeypatch.setattr(update_module.requests, "get", fake_get)
    monkeypatch.setattr(update_module, "_release_cache", None, raising=False)

    ctrl = HAUIUpdateController.__new__(HAUIUpdateController)
    ctrl.app = adapter
    ctrl._req_fetch = False
    ctrl._release_infos = []
    ctrl.log = lambda *a, **kw: None

    caller: dict = {}

    def on_worker():
        caller["id"] = threading.get_ident()
        ctrl._update_release_infos()

    adapter._worker.submit(on_worker).result(10)

    assert "thread" in seen, "the release list was never fetched"
    assert seen["thread"] != caller["id"]
    # It ran on the app's I/O pool, not just on some other thread.
    assert "_io" in seen["thread_name"]


def test_slow_update_fetch_keeps_the_heartbeat_beating(env):
    """End-to-end encoding of the reported bug.

    While the update check waits for a slow GitHub response the hub→device
    heartbeat must keep firing; it used to sit behind that same work, the
    device timed the hub out and woke its display at full brightness.
    """
    adapter, loop, helpers = env
    beats: list = []
    adapter.run_every(lambda kwargs: beats.append(1), "now+0", 0.05, on_loop=True)
    _on_loop(loop, helpers.later[-1], None)
    interval_cb = helpers.intervals[-1]
    first_beats = len(beats)

    release = threading.Event()
    started = threading.Event()

    def slow_fetch():
        started.set()
        release.wait(5)

    def on_worker():
        adapter.run_off_worker(slow_fetch, timeout=5)

    worker = adapter._worker.submit(on_worker)
    try:
        assert started.wait(5)
        # Fire the interval the way HA's scheduler would while the worker is
        # still waiting for the fetch; each fire returns immediately.
        for _ in range(3):
            _on_loop(loop, interval_cb, None)
    finally:
        release.set()
    worker.result(10)

    assert len(beats) - first_beats == 3


def test_callbacks_still_queued_when_the_app_stops_are_dropped(env):
    adapter, loop, helpers = env
    calls = []
    adapter.listen_state(lambda *a: calls.append(a), "light.desk")
    release = _occupy_worker(adapter, loop, helpers)

    _on_loop(loop, helpers.state_cbs["light.desk"], _state_event("on"))
    adapter.stop()
    release.set()
    time.sleep(0.1)

    assert calls == []


def test_listen_state_with_attribute_all_reports_state_pair(env):
    """attribute="all" listeners receive the primary state as the old/new pair."""
    adapter, loop, helpers = env
    calls = []
    adapter.listen_state(lambda *a: calls.append(a), "light.desk", attribute="all")
    _on_loop(loop, helpers.state_cbs["light.desk"], _state_event("on"))
    _settle(adapter, loop, helpers)

    assert calls == [("light.desk", "all", "old", "on", {})]


def test_solar_profile_state_rejects_locations_without_solar_events(env, monkeypatch):
    from datetime import UTC, datetime

    adapter, _, _ = env
    const_module = types.ModuleType("homeassistant.const")
    const_module.SUN_EVENT_SUNRISE = "sunrise"
    const_module.SUN_EVENT_SUNSET = "sunset"
    monkeypatch.setitem(sys.modules, "homeassistant.const", const_module)

    sun_module = types.ModuleType("homeassistant.helpers.sun")
    sun_module.get_astral_event_date = lambda hass, event, date: None
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.sun", sun_module)

    util_module = sys.modules.get("homeassistant.util") or types.ModuleType("homeassistant.util")
    util_module.dt = types.SimpleNamespace(now=lambda: datetime(2026, 6, 21, 12, 0, tzinfo=UTC))
    monkeypatch.setitem(sys.modules, "homeassistant.util", util_module)
    monkeypatch.setattr(sys.modules["homeassistant"], "util", util_module, raising=False)

    with pytest.raises(ValueError, match="cannot calculate both sunrise and sunset"):
        adapter.get_solar_profile_state(0, 0)


class _ThresholdDevice:
    """Device stub whose get() resolves the configured log_level."""

    def __init__(self, level):
        self._level = level

    def get(self, key, default=None):
        return self._level if key == "log_level" else default


def _capture_logger(monkeypatch):
    """Replace the module logger with a recorder; return the record list."""
    logs = []
    monkeypatch.setattr(
        sys.modules["nspanel_haui.ha_adapter"],
        "_LOGGER",
        type(
            "_FakeLogger",
            (),
            {"log": lambda self, level, msg, exc_info=None: logs.append((level, msg))},
        )(),
    )
    return logs


def test_log_threshold_info_drops_debug_before_device_config(env, monkeypatch):
    """Without a device config the INFO threshold applies, so DEBUG is dropped."""
    adapter, loop, helpers = env
    logs = _capture_logger(monkeypatch)

    adapter.log("debug detail", level="DEBUG")
    adapter.log("lifecycle", level="INFO")

    assert [(level, msg) for level, msg in logs] == [(logging.INFO, "lifecycle")]
    status = adapter.get_status_logs()
    assert len(status) == 1
    assert status[0].endswith("INFO lifecycle")


def test_log_threshold_info_filters_debug_for_the_device(env, monkeypatch):
    """The configured log_level is the per-device emission threshold."""
    adapter, loop, helpers = env
    adapter.device = _ThresholdDevice("INFO")
    logs = _capture_logger(monkeypatch)

    adapter.log("debug detail", level="DEBUG")
    adapter.log("warning", level="WARNING")

    assert [(level, msg) for level, msg in logs] == [(logging.WARNING, "warning")]
    assert len(adapter.get_status_logs()) == 1


def test_log_threshold_debug_emits_debug_records(env, monkeypatch):
    """DEBUG threshold lets detailed diagnostics through."""
    adapter, loop, helpers = env
    adapter.device = _ThresholdDevice("DEBUG")
    logs = _capture_logger(monkeypatch)

    adapter.log("debug detail", level="DEBUG")
    adapter.log("lifecycle", level="INFO")

    assert [(level, msg) for level, msg in logs] == [
        (logging.DEBUG, "debug detail"),
        (logging.INFO, "lifecycle"),
    ]
    assert len(adapter.get_status_logs()) == 2

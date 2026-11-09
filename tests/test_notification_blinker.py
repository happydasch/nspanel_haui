"""Tests for the shared notification indicator blinker."""

from __future__ import annotations

from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.mapping.const import NotifEvent
from custom_components.nspanel_haui.haui.utils.notification_blinker import NotificationBlinker


class _Scheduler:
    """App timer fake: records armed intervals, like HAAdapter.run_every/cancel_timer."""

    def __init__(self):
        self.timers: dict[str, tuple] = {}
        self.cancelled: list[str] = []

    def run_every(self, cb, start, interval):
        handle = f"timer_{len(self.timers) + len(self.cancelled)}"
        self.timers[handle] = (cb, interval)
        return handle

    def cancel_timer(self, handle):
        self.timers.pop(handle, None)
        self.cancelled.append(handle)


def _blinker(visible=True):
    scheduler = _Scheduler()
    refreshes = []
    blinker = NotificationBlinker(
        scheduler, lambda: refreshes.append(True), visible_fn=lambda: visible
    )
    return blinker, scheduler, refreshes


def test_notif_add_event_starts_blinking():
    blinker, scheduler, refreshes = _blinker()

    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))

    assert blinker.new_notifications is True
    assert refreshes == [True]
    assert len(scheduler.timers) == 1


def test_blink_ticks_run_on_app_timers():
    """Ticks come from the app's timers (worker thread), never from a thread of their own."""
    blinker, scheduler, refreshes = _blinker()
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))
    ((tick, interval),) = scheduler.timers.values()

    tick({})
    tick({})

    assert interval == 1.0
    assert len(refreshes) == 3


def test_blink_ticks_skip_a_dark_display():
    blinker, scheduler, refreshes = _blinker(visible=False)
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))
    ((tick, _),) = scheduler.timers.values()
    refreshes.clear()

    tick({})

    assert refreshes == []
    # Event-driven renders still happen, so the indicator is right on wake.
    blinker.refresh()
    assert refreshes == [True]


def test_notif_clear_event_stops_blinking():
    blinker, scheduler, _ = _blinker()
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))

    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_CLEAR, value=None))

    assert blinker.new_notifications is False
    assert scheduler.timers == {}


def test_repeated_events_keep_a_single_timer_and_stop_cancels_it():
    blinker, scheduler, _ = _blinker()
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("a", "1")))
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("b", "2")))
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_REMOVE, value=("a", "1")))
    assert len(scheduler.timers) == 1

    blinker.stop()

    assert scheduler.timers == {}


def test_controller_stop_cancels_running_blink_timer():
    from custom_components.nspanel_haui.haui.controller.notification import (
        HAUINotificationController,
    )

    class _Device:
        def get(self, key, default=0):
            return default

    class _App(_Scheduler):
        controller: dict = {}
        device = _Device()

        def log(self, msg, **kwargs):
            pass

        def callback_event(self, event):
            pass

    app = _App()
    controller = HAUINotificationController(app, {})
    controller.start()
    controller.blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))
    assert len(app.timers) == 1

    controller.stop()

    assert app.timers == {}

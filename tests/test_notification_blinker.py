"""Tests for the shared notification indicator blinker."""

from __future__ import annotations

from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.mapping.const import NotifEvent
from nspanel_haui.haui.utils import notification_blinker
from nspanel_haui.haui.utils.notification_blinker import NotificationBlinker


class _FakeTimer:
    created: list[_FakeTimer] = []

    def __init__(self, interval, fn):
        self.cancelled = False
        self.daemon = False
        _FakeTimer.created.append(self)

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True


def _blinker(monkeypatch):
    _FakeTimer.created = []
    monkeypatch.setattr(notification_blinker.threading, "Timer", _FakeTimer)
    refreshes = []
    blinker = NotificationBlinker(lambda: refreshes.append(True))
    return blinker, refreshes


def test_notif_add_event_starts_blinking(monkeypatch):
    blinker, refreshes = _blinker(monkeypatch)

    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))

    assert blinker.new_notifications is True
    assert refreshes == [True]
    assert len(_FakeTimer.created) == 1


def test_notif_clear_event_stops_blinking(monkeypatch):
    blinker, _ = _blinker(monkeypatch)
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))

    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_CLEAR, value=None))

    assert blinker.new_notifications is False
    assert all(t.cancelled for t in _FakeTimer.created)


def test_repeated_events_leave_no_running_timer_after_stop(monkeypatch):
    blinker, _ = _blinker(monkeypatch)
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("a", "1")))
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("b", "2")))
    blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_REMOVE, value=("a", "1")))

    blinker.stop()

    assert len(_FakeTimer.created) == 3
    assert all(t.cancelled for t in _FakeTimer.created)


def test_controller_stop_cancels_running_blink_timer(monkeypatch):
    from nspanel_haui.haui.controller.notification import HAUINotificationController

    class _Device:
        def get(self, key, default=0):
            return default

    class _App:
        controller: dict = {}
        device = _Device()

        def callback_event(self, event):
            pass

    _FakeTimer.created = []
    monkeypatch.setattr(notification_blinker.threading, "Timer", _FakeTimer)
    controller = HAUINotificationController(_App(), {})
    controller.start()
    controller.blinker.handle_event(HAUIEvent(NotifEvent.NOTIF_ADD, value=("t", "m")))
    assert len(_FakeTimer.created) == 1 and not _FakeTimer.created[0].cancelled

    controller.stop()

    assert all(t.cancelled for t in _FakeTimer.created)

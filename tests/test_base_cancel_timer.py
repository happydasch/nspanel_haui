"""Tests for HAUIBase._cancel_timer, the shared cancel-and-clear for timer handles."""

from nspanel_haui.haui.abstract.haui_base import HAUIBase


class _App:
    def __init__(self):
        self.cancelled: list[str] = []

    def cancel_timer(self, handle):
        self.cancelled.append(handle)


def _base():
    base = HAUIBase.__new__(HAUIBase)
    base.app = _App()
    return base


def test_cancel_timer_cancels_the_handle_and_clears_the_attribute():
    base = _base()
    base._refresh_timer = "handle-1"

    base._cancel_timer("_refresh_timer")

    assert base.app.cancelled == ["handle-1"]
    assert base._refresh_timer is None


def test_cancel_timer_without_a_running_timer_does_nothing():
    base = _base()
    base._refresh_timer = None

    base._cancel_timer("_refresh_timer")

    assert base.app.cancelled == []
    assert base._refresh_timer is None

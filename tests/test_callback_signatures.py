"""Tests that page callbacks accept the arguments their dispatchers pass.

Dispatcher contracts:
- ``HAAdapter.run_in`` invokes ``cb({})``.
- ``HAAdapter.listen_state`` invokes ``cb(entity_id, attribute, old, new, {})``.
- ``HAUIPage._flush_buffer_callback`` invokes on_release handlers as
  ``callback(event, component)``.
"""

from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.page.clock import ClockPage
from nspanel_haui.haui.page.select import SelectPage
from nspanel_haui.haui.page.settings import SettingsPage
from nspanel_haui.haui.page.timer import TimerPage


class _TimerApp:
    def __init__(self):
        self.timers = []
        self.device = type("Device", (), {"get": lambda s, k, d=None: False})()

    def run_in(self, cb, delay, **kwargs):
        self.timers.append(cb)
        return f"handle-{len(self.timers)}"

    def cancel_timer(self, handle):
        pass


def test_timer_ended_callback_accepts_run_in_args():
    page = TimerPage.__new__(TimerPage)
    page.app = _TimerApp()
    page._show_notification = False
    stopped = []
    page.stop_timer = lambda: stopped.append(True)

    page.callback_timer_ended({})

    assert stopped == [True]


def test_select_multiple_timer_commits_selection():
    page = SelectPage.__new__(SelectPage)
    page.app = _TimerApp()
    page._handle_multiple_timer = None
    page._multiple_delay = 1.5
    page._selected = ["kitchen", "office"]
    page._close_on_select = False
    committed = []
    page._selection_callback_fnc = committed.append

    page._start_selection_timer()
    (timer_cb,) = page.app.timers
    timer_cb({})

    assert committed == [["kitchen", "office"]]


def test_settings_brightness_callback_accepts_listen_state_args():
    page = SettingsPage.__new__(SettingsPage)
    page.log = lambda *a, **kw: None
    page.brightness_full_entity = type("E", (), {"entity_id": "number.panel_brightness_full"})()
    page.brightness_dimmed_entity = type("E", (), {"entity_id": "number.panel_brightness_dim"})()
    page._full_brightness = 10
    slider_values = []
    page.set_brightness_full_slider = slider_values.append

    page.callback_brightness("number.panel_brightness_full", "state", "10", "42.0", {})

    assert slider_values == [42]
    assert page._full_brightness == 42


def test_clock_tap_on_time_advances_card():
    page = ClockPage.__new__(ClockPage)
    page._callback_map = {}
    page._drag_components = set()
    page._cycle_state = "cycling"
    page._cycle_cards = ["time", "date", "weather"]
    page._current_card_index = 0
    page._card_timer = 5
    page._render_cycle_card = lambda: None
    page.on_release({ClockPage.COMPONENTS.t_time: page._advance_card})

    event = HAUIEvent("button", "")
    page._queued_callback = (ClockPage.COMPONENTS.t_time.id, 0, event)
    page._buffer_timer = None
    page._flush_buffer_callback()

    assert page._current_card_index == 1
    assert page._card_timer == 0

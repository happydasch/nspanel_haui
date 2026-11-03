"""Long press to go back (panel option ``long_press_back``).

Pages without header buttons (clock, clocktwo, weather) can only be left by a
swipe. With ``long_press_back`` a touch held still for about a second goes
back: to the panel this one was opened from, else to the home panel. Touch
start and end come from the firmware's 200 ms touch poll, so the duration is
measured between those events.
"""

from __future__ import annotations

from unittest.mock import patch

import nspanel_haui.haui.abstract.haui_page as page_module
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.controller.navigation import HAUINavigationController
from nspanel_haui.haui.mapping.const import PANEL_CONFIG, ESPEvent
from test_gesture_suppression import _bare_page
from test_navigation import FakeApp, FakeDevice, OpenPanel


class _Panel:
    def __init__(self, **cfg):
        self._cfg = cfg

    def get(self, key, default=None):
        return self._cfg.get(key, default)


class _Navigation:
    def __init__(self):
        self.back = 0

    def go_back(self):
        self.back += 1


def _page(**panel_cfg):
    page = _bare_page()
    page.panel = _Panel(**panel_cfg)
    page.app.controller["navigation"] = _Navigation()
    return page


def _touch(page, held, start=(100, 100), end=(105, 102)):
    """Feed a touch held for ``held`` seconds through process_event."""
    times = iter([1000.0, 1000.0 + held])
    with patch.object(page_module.time, "monotonic", lambda: next(times)):
        page.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
        coords = f"{start[0]},{start[1]},{end[0]},{end[1]}"
        page.process_event(HAUIEvent(ESPEvent.TOUCH_END, coords))


def test_the_option_is_off_by_default():
    assert PANEL_CONFIG["long_press_back"] is False
    page = _page()
    _touch(page, held=2.0)
    assert page.app.controller["navigation"].back == 0


def test_a_long_press_goes_back():
    page = _page(long_press_back=True)
    _touch(page, held=1.0)
    assert page.app.controller["navigation"].back == 1


def test_a_short_tap_does_not():
    page = _page(long_press_back=True)
    _touch(page, held=0.3)
    assert page.app.controller["navigation"].back == 0


def test_a_long_drag_does_not():
    page = _page(long_press_back=True)
    _touch(page, held=1.5, start=(100, 100), end=(300, 110))
    assert page.app.controller["navigation"].back == 0


def test_the_first_touch_start_of_a_touch_counts():
    """A widget that sends its id reports touch_start twice per touch."""
    page = _page(long_press_back=True)
    times = iter([1000.0, 1000.7, 1001.0])
    with patch.object(page_module.time, "monotonic", lambda: next(times)):
        page.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))
        page.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
        page.process_event(HAUIEvent(ESPEvent.TOUCH_END, "100,100,100,100"))
    assert page.app.controller["navigation"].back == 1


def test_a_touch_end_without_its_start_is_ignored():
    """E.g. the touch that left the idle page started on the previous page."""
    page = _page(long_press_back=True)
    page.process_event(HAUIEvent(ESPEvent.TOUCH_END, "100,100,100,100"))
    assert page.app.controller["navigation"].back == 0


# --- navigation.go_back -----------------------------------------------------


def _nav(current, home, stack=()):
    app = FakeApp(FakeDevice())
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav.panel = current
    nav._home_panel = home
    nav._stack = [(p, {}) for p in stack]
    nav.calls = []
    nav.close_panel = lambda: nav.calls.append("close")
    nav.open_home_panel = lambda: nav.calls.append("home")
    return nav


def test_go_back_closes_a_panel_opened_from_another():
    popup = OpenPanel("clock", nav_panel=False)
    nav = _nav(current=popup, home=OpenPanel("grid"), stack=[popup])
    nav.go_back()
    assert nav.calls == ["close"]


def test_go_back_from_a_navigation_panel_opens_home():
    nav = _nav(current=OpenPanel("weather"), home=OpenPanel("grid"))
    nav.go_back()
    assert nav.calls == ["home"]


def test_go_back_on_the_home_panel_stays():
    home = OpenPanel("weather")
    nav = _nav(current=home, home=home)
    nav.go_back()
    assert nav.calls == []

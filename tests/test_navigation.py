"""Characterization tests for HAUINavigationController.process_event.

These lock the *current* event-dispatch behaviour (branch by branch) so the
state machine can be refactored without silent regressions. They spy on the
high-level navigation methods rather than exercising the full display stack.
"""

from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.controller.navigation import HAUINavigationController
from nspanel_haui.haui.mapping.const import ESPEvent


class DummyPanel:
    def __init__(self, panel_id, key=""):
        self.id = panel_id
        self._key = key

    def get(self, key, default=None):
        return self._key if key == "key" else default


class FakePage:
    def __init__(self, page_id, started=False):
        self.page_id = page_id
        self.page_id_recv = None
        self._started = started
        self.events = []

    def is_started(self):
        return self._started

    def stop(self):
        self._started = False

    def process_event(self, event):
        self.events.append(event)


class FakeDevice:
    def __init__(self, **cfg):
        self.connected = cfg.pop("connected", True)
        self.sleeping = False
        self.device_info = {}
        self.config = {}
        self._cfg = {"debug_level": 0, **cfg}
        self.check_wakeup_calls = 0

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def check_wakeup(self, from_button=False):
        self.check_wakeup_calls += 1


class FakeApp:
    def __init__(self, device):
        self.hass = None  # skip debouncer executor wiring in HAUIBase
        self.device = device
        self.controller = {}
        self.cancel_calls = []

    def log(self, msg, *a, **k):
        pass

    def cancel_timer(self, handle):
        self.cancel_calls.append(handle)

    def run_in(self, cb, delay, **kwargs):
        if delay == 0:
            cb(kwargs)
        return "handle"


def _make_nav(**device_cfg):
    device = FakeDevice(**device_cfg)
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    # Spy on the high-level branch outcomes.
    nav.calls = {
        "idle": 0,
        "nav_home": 0,
        "open_sleep": [],
        "open_wakeup": 0,
        "exit_sleep": 0,
        "display_panel": [],
        "unset_page": 0,
    }
    nav._start_idle_timer = lambda: nav.calls.__setitem__("idle", nav.calls["idle"] + 1)
    nav._start_nav_home_timer = lambda: nav.calls.__setitem__("nav_home", nav.calls["nav_home"] + 1)
    nav.open_sleep_panel = lambda **kw: nav.calls["open_sleep"].append(kw)
    nav.open_wakeup_panel = lambda **kw: nav.calls.__setitem__(
        "open_wakeup", nav.calls["open_wakeup"] + 1
    )
    nav.exit_sleep_to_prev_or_home = lambda cfg: nav.calls.__setitem__(
        "exit_sleep", nav.calls["exit_sleep"] + 1
    )
    nav.display_panel = lambda panel: nav.calls["display_panel"].append(panel)
    nav.unset_page = lambda: nav.calls.__setitem__("unset_page", nav.calls["unset_page"] + 1)
    return nav


# --- interaction events reset the hub-side idle / nav-home timers ----------


def test_touch_start_resets_hub_timers():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert nav.calls["idle"] == 1
    assert nav.calls["nav_home"] == 1


def test_gesture_resets_hub_timers():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_left"))
    assert nav.calls["idle"] == 1
    assert nav.calls["nav_home"] == 1


def test_button_resets_timers_when_interaction_enabled():
    nav = _make_nav(reset_interaction_on_button=True)
    nav.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    assert nav.calls["idle"] == 1
    assert nav.calls["nav_home"] == 1


def test_button_skips_timers_when_interaction_disabled():
    nav = _make_nav(reset_interaction_on_button=False)
    nav.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    assert nav.calls["idle"] == 0
    assert nav.calls["nav_home"] == 0


# --- PAGE event ------------------------------------------------------------


def test_page_event_cancels_pending_timeout():
    nav = _make_nav()
    nav._page_timeout = "pending-handle"
    nav.process_event(HAUIEvent(ESPEvent.PAGE, "3"))
    assert "pending-handle" in nav.app.cancel_calls
    assert nav._page_timeout is None


def test_page_event_displays_panel_when_match_and_not_started():
    nav = _make_nav(page_settle_delay=0)
    panel = DummyPanel("p1")
    nav.panel = panel
    nav.page = FakePage(page_id=3, started=False)
    nav.process_event(HAUIEvent(ESPEvent.PAGE, "3"))
    assert nav.calls["display_panel"] == [panel]
    assert nav.page.page_id_recv == 3


def test_page_event_stale_echo_ignored():
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=False)
    nav.process_event(HAUIEvent(ESPEvent.PAGE, "5"))  # mismatch
    assert nav.calls["display_panel"] == []


def test_page_event_no_display_when_already_started():
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav.process_event(HAUIEvent(ESPEvent.PAGE, "3"))
    assert nav.calls["display_panel"] == []


# --- TIMEOUT (sleep / page) -> open sleep panel ----------------------------


def test_timeout_sleep_opens_sleep_panel():
    nav = _make_nav()
    nav._sleep_panel = DummyPanel("sleep")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "sleep"))
    assert nav._sleep_panel_active is True
    assert nav.calls["open_sleep"] == [{"autostart": True}]


def test_timeout_page_opens_sleep_panel():
    nav = _make_nav()
    nav._sleep_panel = DummyPanel("sleep")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "page"))
    assert nav.calls["open_sleep"] == [{"autostart": True}]


def test_timeout_skips_when_already_on_sleep_panel():
    nav = _make_nav()
    sleep_panel = DummyPanel("sleep")
    nav._sleep_panel = sleep_panel
    nav.panel = sleep_panel  # already showing the sleep panel
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "sleep"))
    assert nav.calls["open_sleep"] == []


def test_timeout_other_value_ignored():
    nav = _make_nav()
    nav._sleep_panel = DummyPanel("sleep")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "dim"))
    assert nav.calls["open_sleep"] == []


# --- DISPLAY_STATE ---------------------------------------------------------


def test_display_state_prev_off_opens_wakeup_panel():
    nav = _make_nav()
    nav.app.device.connected = True
    nav.app.device.sleeping = True
    nav.app.device.device_info = {"display_state": "off"}
    nav._sleep_panel_active = False
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    assert nav.calls["open_wakeup"] == 1


def test_display_state_on_with_sleep_panel_active_does_not_exit():
    # The sleep-screen exit decision is owned by the touch (Device.check_wakeup),
    # NOT the display_state event — so display_state="on" must not drive an exit
    # or wake panel here (avoids event-order double exits).
    nav = _make_nav()
    nav.app.device.connected = True
    nav.app.device.device_info = {"display_state": "dim"}
    nav._sleep_panel_active = True
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    assert nav.app.device.check_wakeup_calls == 0
    assert nav.calls["open_wakeup"] == 0


def test_display_state_skipped_when_not_connected():
    nav = _make_nav()
    nav.app.device.connected = False
    nav.app.device.device_info = {"display_state": "off"}
    nav._sleep_panel_active = True
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    assert nav.calls["open_wakeup"] == 0
    assert nav.app.device.check_wakeup_calls == 0


# --- WAKEUP ----------------------------------------------------------------


def test_wakeup_with_wakeup_panel_opens_it():
    nav = _make_nav()
    nav._wakeup_panel = DummyPanel("wake")
    nav.process_event(HAUIEvent(ESPEvent.WAKEUP, ""))
    assert nav.calls["open_wakeup"] == 1
    assert nav.calls["exit_sleep"] == 0


def test_wakeup_without_wakeup_panel_exits_to_prev_or_home():
    nav = _make_nav()
    nav._wakeup_panel = None
    nav.process_event(HAUIEvent(ESPEvent.WAKEUP, ""))
    assert nav.calls["exit_sleep"] == 1
    assert nav.calls["open_wakeup"] == 0


# --- SLEEP -----------------------------------------------------------------


def test_sleep_unsets_page():
    nav = _make_nav()
    nav.page = FakePage(page_id=1)
    nav.process_event(HAUIEvent(ESPEvent.SLEEP, ""))
    assert nav.calls["unset_page"] == 1


# --- page event forwarding -------------------------------------------------


def test_event_forwarded_to_active_page():
    nav = _make_nav()
    page = FakePage(page_id=1, started=True)
    nav.page = page
    event = HAUIEvent(ESPEvent.GESTURE, "swipe_up")
    nav.process_event(event)
    assert event in page.events


# --- _open_panel_impl: same-page vs different-page rendering ---------------


from unittest.mock import patch  # noqa: E402

import nspanel_haui.haui.controller.navigation as nav_module  # noqa: E402


class OpenPanel:
    """Fake panel with enough surface for _open_panel_impl."""

    def __init__(self, panel_id, panel_type="grid", nav_panel=True):
        self.id = panel_id
        self._type = panel_type
        self._nav = nav_panel
        self._state = {}
        self._cfg = {"unlock_code": "", "close_timeout": 0, "key": "test"}

    def get_type(self):
        return self._type

    def show_in_navigation(self):
        return self._nav

    def apply_kwargs(self, kwargs):
        pass

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def get_state(self, key, default=None):
        return self._state.get(key, default)

    def set_state(self, key, value):
        self._state[key] = value


class OpenPage:
    """Fake page created by the patched page_class."""

    def __init__(self, app, config):
        self.page_id = config.get("page_id")
        self.page_id_recv = None
        self._started = False
        self.create_called = False

    def create_panel(self, panel):
        self.create_called = True

    def stop(self):
        self._started = False

    def is_started(self):
        return self._started


class FakeDeviceConfig:
    def __init__(self, panel):
        self._panel = panel

    def get_panel(self, panel_id):
        return self._panel


def _make_nav_for_open(panel, page_id):
    """Build a nav controller wired for _open_panel_impl tests."""
    device = FakeDevice()
    app = FakeApp(device)
    app.device_config = FakeDeviceConfig(panel)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav.calls = {"display_panel": [], "goto_page": []}
    nav.display_panel = lambda p: nav.calls["display_panel"].append(p)
    nav.goto_page = lambda pid, force=False: nav.calls["goto_page"].append(
        {"page_id": pid, "force": force}
    )
    return nav


def test_open_panel_same_page_waits_for_event():
    """Same page_id: display_panel NOT called, _page_timeout is set.

    The Nextion fires 0x66 even for same-page ``page N`` (full refresh),
    so we always wait for the page event before rendering.
    """
    panel = OpenPanel("p1", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=3)
    # current page is already on page_id 3
    nav.page = FakePage(page_id=3, started=True)
    nav.panel = OpenPanel("old")

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=3),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl("p1")

    assert nav.calls["display_panel"] == []
    assert nav._page_timeout is not None  # run_in returns "handle"


def test_open_panel_different_page_waits_for_event():
    """Different page_id: display_panel NOT called, _page_timeout is set."""
    panel = OpenPanel("p1", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=5)
    # current page is on page_id 3, new page is 5
    nav.page = FakePage(page_id=3, started=True)
    nav.panel = OpenPanel("old")

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=5),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl("p1")

    assert nav.calls["display_panel"] == []
    assert nav._page_timeout is not None  # run_in returns "handle"


def test_page_timeout_callback_forces_goto_and_displays():
    """_page_timeout_callback re-sends goto_page (force=True) and displays."""
    panel = OpenPanel("p1", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=5)
    nav.page = FakePage(page_id=5, started=False)
    nav.panel = panel

    nav._page_timeout_callback({})

    assert nav.calls["goto_page"] == [{"page_id": 5, "force": True}]
    assert len(nav.calls["display_panel"]) == 1


# --- BUFFER_OVERFLOW -------------------------------------------------------


def test_buffer_overflow_schedules_re_render():
    """Buffer overflow event schedules a debounced re-render timer."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    assert nav._buffer_overflow_timer is not None  # run_in returns "handle"


def test_buffer_overflow_recover_renders_panel():
    """_buffer_overflow_recover calls display_panel with the current panel."""
    nav = _make_nav()
    panel = DummyPanel("p1")
    nav.panel = panel
    nav.page = FakePage(page_id=3, started=True)
    nav._buffer_overflow_recover({})
    assert nav.calls["display_panel"] == [panel]
    assert nav._buffer_overflow_timer is None


def test_buffer_overflow_recover_skips_when_no_panel():
    """_buffer_overflow_recover does nothing when no panel/page is active."""
    nav = _make_nav()
    nav.panel = None
    nav.page = None
    nav._buffer_overflow_recover({})
    assert nav.calls["display_panel"] == []


def test_buffer_overflow_debounces_repeated_events():
    """Repeated overflow events cancel the previous timer before scheduling."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    first_timer = nav._buffer_overflow_timer
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    # First timer was cancelled
    assert first_timer in nav.app.cancel_calls

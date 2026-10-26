"""Characterization tests for HAUINavigationController.process_event.

These lock the *current* event-dispatch behaviour (branch by branch) so the
state machine can be refactored without silent regressions. They spy on the
high-level navigation methods rather than exercising the full display stack.
"""

import time

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
        self.device_info = {}
        self.config = {}
        self._cfg = {"debug_level": 0, **cfg}
        self.check_wakeup_calls = 0
        self._first_touch_consumed = False

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def get_name(self):
        return "Fake Panel"

    def check_wakeup(self):
        self.check_wakeup_calls += 1


class FakeApp:
    def __init__(self, device):
        self.hass = None  # skip debouncer executor wiring in HAUIBase
        self.device = device
        self.controller = {}
        self.cancel_calls = []
        self.fire_event_calls = []
        self.run_in_delays = []

    def log(self, msg, *a, **k):
        pass

    def fire_event(self, event_type, data=None):
        self.fire_event_calls.append((event_type, data))

    def cancel_timer(self, handle):
        self.cancel_calls.append(handle)

    def run_in(self, cb, delay, **kwargs):
        self.run_in_delays.append(delay)
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
        "open_idle": [],
        "exit_idle": 0,
        "leave_restore": 0,
        "display_panel": [],
        "refresh_panel": 0,
        "unset_page": 0,
    }
    nav._start_idle_timer = lambda: nav.calls.__setitem__("idle", nav.calls["idle"] + 1)
    nav._start_nav_home_timer = lambda: nav.calls.__setitem__("nav_home", nav.calls["nav_home"] + 1)
    nav.open_idle_panel = lambda **kw: nav.calls["open_idle"].append(kw)
    nav.exit_idle_to_prev_or_home = lambda cfg: nav.calls.__setitem__(
        "exit_idle", nav.calls["exit_idle"] + 1
    )
    nav._leave_idle_restoring_or_home = lambda cfg: nav.calls.__setitem__(
        "leave_restore", nav.calls["leave_restore"] + 1
    )
    nav.display_panel = lambda panel: nav.calls["display_panel"].append(panel)
    nav.refresh_panel = lambda: nav.calls.__setitem__(
        "refresh_panel", nav.calls["refresh_panel"] + 1
    )
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


# --- TIMEOUT -> automatic page switching ------------------------------------

# The firmware publishes "dim" / "off" / "page" idle milestones.  Only
# "page" concerns the hub (automatic page switching); dim and off are
# display-brightness milestones that must not trigger a page switch.


def test_timeout_page_opens_idle_panel():
    nav = _make_nav()
    nav._idle_panel = DummyPanel("idle")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "page"))
    assert nav.calls["open_idle"] == [{"autostart": True}]


def test_timeout_off_is_ignored():
    """Display-off (esphome.timeout 'off') never switches pages."""
    nav = _make_nav()
    nav._idle_panel = DummyPanel("idle")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "off"))
    assert nav.calls["open_idle"] == []


def test_timeout_dim_is_ignored():
    nav = _make_nav()
    nav._idle_panel = DummyPanel("idle")
    nav.panel = DummyPanel("home")
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "dim"))
    assert nav.calls["open_idle"] == []


def test_timeout_skips_when_already_on_idle_panel():
    nav = _make_nav()
    idle_panel = DummyPanel("idle")
    nav._idle_panel = idle_panel
    nav.panel = idle_panel  # already showing the idle page
    nav.process_event(HAUIEvent(ESPEvent.TIMEOUT, "page"))
    assert nav.calls["open_idle"] == []


# --- DISPLAY_STATE ----------------------------------------------------------

# The nav controller has no display_state handler: brightness transitions are
# the firmware's job and the idle-page exit decision belongs to the touch.


def test_display_state_does_not_drive_navigation():
    nav = _make_nav()
    nav.app.device.connected = True
    nav.app.device.device_info = {"display_state": "off"}
    nav._idle_panel_active = True
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    assert nav.app.device.check_wakeup_calls == 0
    assert nav.calls["open_idle"] == []
    assert nav.calls["exit_idle"] == 0


# --- WAKEUP ----------------------------------------------------------------


def test_wakeup_while_idle_active_defers_to_touch():
    nav = _make_nav()
    nav._idle_panel_active = True
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_ON, ""))
    assert nav.calls["leave_restore"] == 0


def test_wakeup_restores_context_when_not_idle():
    nav = _make_nav()
    nav._idle_panel_active = False
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_ON, ""))
    assert nav.calls["leave_restore"] == 1


# --- DISPLAY_OFF -----------------------------------------------------------


def test_display_off_unsets_page():
    nav = _make_nav()
    nav.page = FakePage(page_id=1)
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_OFF, ""))
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

    def get_title(self):
        return self._cfg.get("title", "")

    def get_state(self, key, default=None):
        return self._state.get(key, default)

    def set_state(self, key, value):
        self._state[key] = value


class OpenPage:
    """Fake page created by the patched page_class."""

    def __init__(self, app, config):
        self.page_id = config.get("page_id")
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


# --- idle session cleanup ---------------------------------------------------


def test_navigate_away_from_idle_panel_leaves_idle_session():
    """Any navigation to a panel other than the idle page (gesture, function
    button, service) is a wake input and clears the idle session."""
    panel = OpenPanel("p1", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=3)
    nav.page = FakePage(page_id=3, started=True)
    nav.panel = OpenPanel("old")
    nav._idle_panel = OpenPanel("sleep-panel")
    nav._idle_panel_active = True

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=3),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl("p1")

    assert nav._idle_panel_active is False


def test_open_idle_panel_itself_keeps_idle_session():
    """Re-opening the idle page (e.g. the sleep button on the idle page itself)
    must not clear the idle session."""
    panel = OpenPanel("sleep-panel", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=3)
    nav.page = FakePage(page_id=3, started=True)
    nav.panel = OpenPanel("old")
    nav._idle_panel = panel
    nav._idle_panel_active = True

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=3),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl("sleep-panel")

    assert nav._idle_panel_active is True


def test_close_idle_panel_leaves_idle_session():
    """Closing the idle page (close button / close_panel service) is a wake
    input: the idle session must not survive the close."""
    panel = OpenPanel("sleep-panel", panel_type="grid")
    nav = _make_nav_for_open(panel, page_id=3)
    nav.panel = panel
    nav._idle_panel = panel
    nav._idle_panel_active = True

    nav._close_panel_impl()

    assert nav._idle_panel_active is False


# --- BUFFER_OVERFLOW -------------------------------------------------------


def test_buffer_overflow_schedules_re_render():
    """Buffer overflow event schedules a debounced re-render timer."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    assert nav._buffer_overflow_timer is not None  # run_in returns "handle"


def test_buffer_overflow_recover_refreshes_panel():
    """_buffer_overflow_recover refreshes the panel (no full set_panel batch)."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav._buffer_overflow_recover({})
    assert nav.calls["refresh_panel"] == 1
    assert nav.calls["display_panel"] == []
    assert nav._buffer_overflow_timer is None


def test_buffer_overflow_recover_skips_when_no_panel():
    """_buffer_overflow_recover does nothing when no panel/page is active."""
    nav = _make_nav()
    nav.panel = None
    nav.page = None
    nav._buffer_overflow_recover({})
    assert nav.calls["refresh_panel"] == 0


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


def test_buffer_overflow_recovery_backs_off_exponentially():
    """Each consecutive recovery doubles the debounce delay."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    for _ in range(3):
        nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
        nav._buffer_overflow_recover({})
    assert nav.app.run_in_delays == [
        nav_module.OVERFLOW_RECOVERY_DELAY,
        nav_module.OVERFLOW_RECOVERY_DELAY * 2,
        nav_module.OVERFLOW_RECOVERY_DELAY * 4,
    ]


def test_buffer_overflow_recovery_pauses_after_max_attempts():
    """After max consecutive recoveries, further overflows are ignored."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    for _ in range(nav_module.OVERFLOW_RECOVERY_MAX_ATTEMPTS):
        nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
        nav._buffer_overflow_recover({})
    scheduled = len(nav.app.run_in_delays)
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    assert len(nav.app.run_in_delays) == scheduled  # no new timer
    assert nav.calls["refresh_panel"] == nav_module.OVERFLOW_RECOVERY_MAX_ATTEMPTS


def test_buffer_overflow_backoff_resets_after_quiet_period():
    """A quiet period without overflows resets the recovery backoff."""
    nav = _make_nav()
    nav.panel = DummyPanel("p1")
    nav.page = FakePage(page_id=3, started=True)
    nav._overflow_recoveries = nav_module.OVERFLOW_RECOVERY_MAX_ATTEMPTS
    nav._last_overflow_ts = time.monotonic() - nav_module.OVERFLOW_RECOVERY_RESET - 1
    nav.process_event(HAUIEvent(ESPEvent.BUFFER_OVERFLOW, "1"))
    assert nav.app.run_in_delays == [nav_module.OVERFLOW_RECOVERY_DELAY]


def test_open_idle_panel_without_idle_panel_is_a_noop():
    """No configured idle page: nothing to switch to, current panel stays."""
    device = FakeDevice()
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    opened: list = []
    nav.open_panel = lambda pid, **kw: opened.append(pid)
    nav.close_panel = lambda: opened.append("close")
    nav.create_snapshot = lambda: opened.append("snapshot")

    nav.open_idle_panel()

    assert opened == []


def test_open_idle_panel_enters_idle_session_and_snapshots_once():
    """Repeated entries (timeout/button/service) must not overwrite the
    pre-idle snapshot with the idle page itself."""
    device = FakeDevice()
    device.device_info["display_state"] = "on"
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav._idle_panels = [DummyPanel("sleep-a"), DummyPanel("sleep-b")]
    nav._idle_panel = nav._idle_panels[0]
    nav._idle_panel_idx = 0
    snapshots: list = []
    nav.create_snapshot = lambda: snapshots.append("snapshot")
    nav.open_panel = lambda pid, **kw: None

    nav.open_idle_panel()
    nav.open_idle_panel()  # repeated entry while already idle

    assert device._first_touch_consumed is False  # visible idle page is one-touch
    assert nav._idle_panel_active is True
    assert len(snapshots) == 1
    assert nav._idle_panel_idx == 2  # carousel still advances


def test_open_idle_panel_arms_wake_touch_when_display_dark():
    device = FakeDevice()
    device.device_info["display_state"] = "off"
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav._idle_panels = [DummyPanel("sleep")]
    nav.open_panel = lambda pid, **kw: None

    nav.open_idle_panel()

    assert device._first_touch_consumed is True


def test_exit_idle_to_prev_or_home_noops_when_not_idle():
    device = FakeDevice()
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav._snapshot = (None, {}, None, {}, [])
    nav._snapshot_time = time.monotonic()
    opened: list = []
    nav.open_home_panel = lambda **kw: opened.append("home")

    nav.exit_idle_to_prev_or_home({})

    assert opened == []  # no navigation away from normal operation

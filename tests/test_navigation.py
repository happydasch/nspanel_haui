"""Characterization tests for HAUINavigationController.process_event.

These lock the *current* event-dispatch behaviour (branch by branch) so the
state machine can be refactored without silent regressions. They spy on the
high-level navigation methods rather than exercising the full display stack.
"""

import time

import pytest
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.controller.navigation import HAUINavigationController
from nspanel_haui.haui.mapping.const import AUTO_PAGE_HOLD, ESPEvent


class DummyPanel:
    def __init__(self, panel_id, key=""):
        self.id = panel_id
        self._key = key

    def get(self, key, default=None):
        return self._key if key == "key" else default

    def get_type(self):
        return "grid"

    def show_in_navigation(self):
        return True


class FakePage:
    def __init__(self, page_id, started=False, suspended=()):
        self.page_id = page_id
        self._started = started
        self._suspended = suspended
        self.events = []
        self.refresh_calls = 0
        self.panel = None

    def refresh_panel(self):
        self.refresh_calls += 1

    def is_started(self):
        return self._started

    def start(self):
        self._started = True

    def set_panel(self, panel):
        self.panel = panel

    def stop(self):
        self._started = False

    def process_event(self, event):
        self.events.append(event)

    def suspended_auto_switches(self):
        return self._suspended


class FakeDevice:
    def __init__(self, **cfg):
        self.connected = cfg.pop("connected", True)
        self.device_info = {}
        self.config = {}
        self._cfg = {**cfg}
        self.check_wakeup_calls = 0
        self._first_touch_consumed = False

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def get_name(self):
        return "Fake Panel"

    def check_wakeup(self):
        self.check_wakeup_calls += 1

    def apply_auto_switches(self):
        pass

    def on_idle_page_opened(self):
        """Mirror HAUIDevice: arm the wake guard only on a dark display."""
        self._first_touch_consumed = self.device_info.get("display_state", "off") not in (
            "on",
            "dim",
        )


class FakeApp:
    def __init__(self, device):
        self.hass = None  # skip debouncer executor wiring in HAUIBase
        self.device = device
        self.controller = {}
        self.cancel_calls = []
        self.fire_event_calls = []
        self.run_in_delays = []
        self.run_every_calls = []
        self.logs = []

    def log(self, msg, *a, **k):
        self.logs.append((msg, k.get("level")))

    def fire_event(self, event_type, data=None):
        self.fire_event_calls.append((event_type, data))

    def cancel_timer(self, handle):
        self.cancel_calls.append(handle)

    def run_in(self, cb, delay, **kwargs):
        self.run_in_delays.append(delay)
        if delay == 0:
            cb(kwargs)
        return "handle"

    def run_every(self, cb, start, interval, on_loop=False, **kwargs):
        self.run_every_calls.append((cb, start, interval))
        return "interval-handle"


def _make_nav(**device_cfg):
    device = FakeDevice(**device_cfg)
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    # Spy on the high-level branch outcomes.
    nav.calls = {
        "reset_activity": 0,
        "open_idle": [],
        "exit_idle": 0,
        "leave_restore": 0,
        "display_panel": [],
        "refresh_panel": 0,
        "unset_page": 0,
    }
    original_reset_activity = nav.reset_activity

    def reset_activity():
        original_reset_activity()
        nav.calls["reset_activity"] += 1

    nav.reset_activity = reset_activity
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


def _make_nav_for_refresh(**device_cfg):
    device = FakeDevice(**device_cfg)
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    return nav


def _make_idle_nav(**device_cfg):
    """A nav whose inactivity deadline has passed and has an idle page."""
    cfg = {"use_auto_page": True, "timeout_page": 10, **device_cfg}
    nav = _make_nav(**cfg)
    nav.panel = DummyPanel("home")
    nav.page = FakePage(page_id=3, started=True)
    nav._idle_panels = [DummyPanel("idle")]
    nav._idle_panel = nav._idle_panels[0]
    nav._resume_pending = False
    nav._activity_ts = time.monotonic() - 11
    return nav


# --- interaction events reset the hub's activity clock ---------------------


def test_touch_start_resets_the_activity_clock():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert nav.calls["reset_activity"] == 1


def test_touch_end_resets_the_activity_clock():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.TOUCH_END, "1,1,2,2"))
    assert nav.calls["reset_activity"] == 1


def test_component_tap_resets_the_activity_clock():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.COMPONENT, "7,4,1"))
    assert nav.calls["reset_activity"] == 1


def test_gesture_resets_the_activity_clock():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_left"))
    assert nav.calls["reset_activity"] == 1


def test_button_resets_the_clock_when_interaction_enabled():
    nav = _make_nav(reset_interaction_on_button=True)
    nav.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    assert nav.calls["reset_activity"] == 1


def test_button_skips_the_clock_when_interaction_disabled():
    nav = _make_nav(reset_interaction_on_button=False)
    nav.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    assert nav.calls["reset_activity"] == 0


def test_unrelated_events_do_not_reset_the_clock():
    nav = _make_nav()
    nav.process_event(HAUIEvent(ESPEvent.PAGE, "3"))
    nav.process_event(HAUIEvent(ESPEvent.DISPLAY_ON, ""))
    assert nav.calls["reset_activity"] == 0


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


# --- level-triggered idle check --------------------------------------------


def _assert_no_idle_opened(nav):
    nav._check_inactivity({})
    assert nav.calls["open_idle"] == []


def test_check_inactivity_opens_the_idle_page_when_due():
    nav = _make_idle_nav()
    nav._check_inactivity({})
    assert nav.calls["open_idle"] == [{"autostart": True}]


def test_check_inactivity_skips_a_disconnected_device():
    nav = _make_idle_nav()
    nav.app.device.connected = False
    _assert_no_idle_opened(nav)


def test_check_inactivity_waits_for_the_restored_page():
    nav = _make_idle_nav()
    nav._resume_pending = True
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_without_page():
    nav = _make_idle_nav()
    nav.page = None
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_without_panel():
    nav = _make_idle_nav()
    nav.panel = None
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_during_navigation():
    nav = _make_idle_nav()
    nav._navigating = True
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_while_a_page_change_is_pending():
    nav = _make_idle_nav()
    nav._page_timeout = "pending-handle"
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_while_the_idle_page_is_active():
    nav = _make_idle_nav()
    nav._idle_panel_active = True
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_while_the_idle_page_is_suspended():
    nav = _make_idle_nav()
    nav._idle_panel_suspended = True
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_without_an_idle_page():
    nav = _make_idle_nav()
    nav._idle_panels = []
    nav._idle_panel = None
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_when_auto_page_is_off():
    nav = _make_idle_nav(use_auto_page=False)
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_when_the_timeout_is_zero():
    nav = _make_idle_nav(timeout_page=0)
    _assert_no_idle_opened(nav)


@pytest.mark.parametrize("timeout_page", [True, -1, float("nan")])
def test_check_inactivity_skips_invalid_page_timeouts(timeout_page):
    nav = _make_idle_nav(timeout_page=timeout_page)

    nav._check_inactivity({})

    assert nav.calls["open_idle"] == []
    assert any(level == "WARNING" and "timeout_page" in message for message, level in nav.app.logs)


@pytest.mark.parametrize(("is_night", "use_auto_page"), [(False, None), (True, 1)])
def test_check_inactivity_skips_invalid_active_profile_flags(is_night, use_auto_page):
    prefix = "night_" if is_night else ""
    nav = _make_idle_nav(**{f"{prefix}use_auto_page": use_auto_page, f"{prefix}timeout_page": 10})
    nav._idle_profile_night = is_night

    nav._check_inactivity({})

    assert nav.calls["open_idle"] == []
    assert any(
        level == "WARNING" and f"{prefix}use_auto_page" in message
        for message, level in nav.app.logs
    )


def test_check_inactivity_logs_missing_active_profile_values():
    nav = _make_idle_nav()
    del nav.app.device._cfg["use_auto_page"]
    del nav.app.device._cfg["timeout_page"]

    nav._check_inactivity({})

    assert nav.calls["open_idle"] == []
    assert any(
        level == "WARNING" and "use_auto_page" in message and "timeout_page" in message
        for message, level in nav.app.logs
    )


def test_check_inactivity_skips_before_the_timeout():
    nav = _make_idle_nav()
    nav._activity_ts = time.monotonic() - 5
    _assert_no_idle_opened(nav)


def test_check_inactivity_skips_while_the_page_holds_the_idle_page():
    nav = _make_idle_nav()
    nav.page = FakePage(page_id=3, started=True, suspended=(AUTO_PAGE_HOLD,))
    _assert_no_idle_opened(nav)


def test_a_shorter_timeout_applies_on_the_next_tick():
    nav = _make_idle_nav(timeout_page=30)
    nav._activity_ts = time.monotonic() - 10
    _assert_no_idle_opened(nav)
    nav.app.device._cfg["timeout_page"] = 5
    nav._check_inactivity({})
    assert nav.calls["open_idle"] == [{"autostart": True}]


def test_recording_interaction_restarts_the_timeout():
    nav = _make_idle_nav()
    nav.reset_activity()
    assert time.monotonic() - nav._activity_ts < 1
    _assert_no_idle_opened(nav)


def test_the_night_profile_selects_its_own_idle_settings():
    nav = _make_idle_nav(
        use_auto_page=False,
        night_use_auto_page=True,
        night_timeout_page=10,
    )
    nav._idle_profile_night = True
    nav._check_inactivity({})
    assert nav.calls["open_idle"] == [{"autostart": True}]


def test_repeated_checks_do_not_advance_the_carousel():
    nav = _make_nav_for_refresh(use_auto_page=True, timeout_page=10)
    nav._idle_panels = [DummyPanel("idle-a"), DummyPanel("idle-b")]
    nav._idle_panel = nav._idle_panels[0]
    nav._idle_panel_idx = 0
    nav.panel = DummyPanel("home")
    nav.page = FakePage(page_id=3, started=True)
    nav._resume_pending = False
    nav._activity_ts = time.monotonic() - 11
    nav.open_panel = lambda panel_id, **kwargs: None

    nav._check_inactivity({})
    assert nav._idle_panel_idx == 1
    assert nav._idle_panel_active is True

    nav._check_inactivity({})
    assert nav._idle_panel_idx == 1


def test_check_inactivity_restarts_the_timeout_after_a_reconnect():
    nav = _make_nav_for_refresh(use_auto_page=True, timeout_page=10)
    nav.panel = DummyPanel("home")
    nav.page = FakePage(page_id=nav_module.get_page_id_for_panel("grid"), started=True)
    nav._idle_panels = [DummyPanel("idle")]
    nav._idle_panel = nav._idle_panels[0]
    opened = []
    nav.open_idle_panel = lambda **kwargs: opened.append(kwargs)
    nav._resume_pending = False
    nav._activity_ts = time.monotonic() - 100

    nav.prepare_resume()
    assert nav._resume_pending is True
    nav._check_inactivity({})
    assert opened == []

    nav.display_panel(nav.panel)
    assert nav._resume_pending is False
    nav._check_inactivity({})
    assert opened == []

    nav._activity_ts = time.monotonic() - 11
    nav._check_inactivity({})
    assert opened == [{"autostart": True}]


def test_an_empty_night_idle_key_disables_the_idle_page_with_a_warning():
    app = FakeApp(
        FakeDevice(
            night_idle_panel="",
            idle_panel="day_idle",
            night_use_auto_page=True,
        )
    )
    app.device_config = FakeDeviceConfig({"day_idle": DummyPanel("day-idle")})
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav

    nav.set_idle_profile(True)

    assert nav._idle_panels == []
    assert any(level == "WARNING" and "night_idle_panel" in message for message, level in app.logs)


def test_an_empty_day_idle_key_does_not_inherit_the_night_page():
    app = FakeApp(
        FakeDevice(
            use_auto_page=True,
            idle_panel="",
            idle_panel_extra="",
            night_idle_panel="night_idle",
        )
    )
    app.device_config = FakeDeviceConfig({"night_idle": DummyPanel("night-idle", key="night_idle")})
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav

    nav.set_idle_profile(False)

    assert nav._idle_panels == []
    assert any(
        level == "WARNING" and "idle_panel is empty" in message for message, level in app.logs
    )


def test_an_unresolved_day_idle_key_is_logged_without_falling_back_to_night():
    app = FakeApp(
        FakeDevice(
            use_auto_page=True,
            idle_panel="missing_day_panel",
            idle_panel_extra="",
            night_use_auto_page=True,
            night_idle_panel="night_idle",
        )
    )
    app.device_config = FakeDeviceConfig({"night_idle": DummyPanel("night-idle", key="night_idle")})
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav

    nav.set_idle_profile(False)

    assert nav._idle_panels == []
    assert any(level == "WARNING" and "missing_day_panel" in message for message, level in app.logs)
    assert not any("not inherited" in message for message, _ in app.logs)


def test_an_unresolved_night_idle_key_is_not_reported_as_empty():
    app = FakeApp(
        FakeDevice(
            use_auto_page=True,
            idle_panel="day_idle",
            night_use_auto_page=True,
            night_idle_panel="missing_night_panel",
        )
    )
    app.device_config = FakeDeviceConfig({"day_idle": DummyPanel("day-idle", key="day_idle")})
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav

    nav.set_idle_profile(True)

    assert nav._idle_panels == []
    assert any(
        level == "WARNING" and "missing_night_panel" in message for message, level in app.logs
    )
    assert not any("not inherited" in message for message, _ in app.logs)


# --- auto-navigate-home from the same clock --------------------------------


def _nav_with_home(**device_cfg):
    cfg = {"auto_navigate_home_timeout": 10, **device_cfg}
    nav = _make_nav(**cfg)
    nav._home_panel = DummyPanel("home")
    nav.panel = DummyPanel("other")
    nav.page = FakePage(page_id=3, started=True)
    nav._resume_pending = False
    nav._activity_ts = time.monotonic() - 11
    nav.opened_home = []
    nav.open_home_panel = lambda: nav.opened_home.append(True)
    return nav


def test_nav_home_opens_the_home_panel_after_the_timeout():
    nav = _nav_with_home()
    nav._check_inactivity({})
    assert nav.opened_home == [True]


def test_nav_home_waits_for_navigation_and_page_acknowledgement():
    nav = _nav_with_home()
    nav._navigating = True
    nav._check_inactivity({})
    assert nav.opened_home == []

    nav._navigating = False
    nav._page_timeout = "pending-handle"
    nav._check_inactivity({})
    assert nav.opened_home == []


@pytest.mark.parametrize("timeout", [True, -1, float("nan")])
def test_nav_home_skips_invalid_timeouts(timeout):
    nav = _nav_with_home(auto_navigate_home_timeout=timeout)

    nav._check_inactivity({})

    assert nav.opened_home == []
    assert any(
        level == "WARNING" and "auto_navigate_home_timeout" in message
        for message, level in nav.app.logs
    )


def test_nav_home_is_off_at_zero():
    nav = _nav_with_home(auto_navigate_home_timeout=0)
    nav._check_inactivity({})
    assert nav.opened_home == []


def test_nav_home_skips_the_panel_it_is_already_on():
    nav = _nav_with_home()
    nav.panel = nav._home_panel
    nav._check_inactivity({})
    assert nav.opened_home == []


def test_nav_home_timeout_drops_idle_snapshot_after_timeout():
    nav = _nav_with_home()
    nav._idle_panel_active = True
    nav._snapshot = nav_module.NavigationSnapshot(None, {}, None, {}, [])
    nav._check_inactivity({})
    assert nav._snapshot is None
    assert nav.opened_home == []


# --- the 1 s interval timer ------------------------------------------------


def test_start_part_starts_and_stop_part_cancels_the_inactivity_check():
    nav = _make_nav_for_refresh()
    nav._resolve_special_panels = lambda **kwargs: []
    nav.start_part()
    assert len(nav.app.run_every_calls) == 1
    _, start, interval = nav.app.run_every_calls[0]
    assert (start, interval) == ("now+1", 1)
    handle = nav._idle_check_timer
    assert handle == "interval-handle"

    nav.stop_part()
    assert handle in nav.app.cancel_calls


def test_cancel_timeouts_keeps_the_inactivity_check_running():
    nav = _make_nav_for_refresh()
    nav._idle_check_timer = "interval-handle"
    nav.cancel_timeouts()
    assert "interval-handle" not in nav.app.cancel_calls


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

    def prepare_page_load(self, panel):
        self.create_called = True

    def stop(self):
        self._started = False

    def is_started(self):
        return self._started


class FakeDeviceConfig:
    def __init__(self, panel):
        self._panels = panel if isinstance(panel, dict) else {panel.id: panel}

    def get_panel(self, panel_id):
        return self._panels.get(panel_id)


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
    assert nav._idle_panel_suspended is False


def test_notification_overlay_close_restores_idle_session():
    """Closing a notification stack shown from idle returns to idle and still wakes."""
    idle = OpenPanel("idle", panel_type="grid", nav_panel=False)
    notification_list = OpenPanel("notification_list", panel_type="popup_select", nav_panel=False)
    notification = OpenPanel("notification", panel_type="popup_notify", nav_panel=False)
    nav = _make_nav_for_open(idle, page_id=3)
    nav.app.device_config = FakeDeviceConfig(
        {panel.id: panel for panel in (idle, notification_list, notification)}
    )
    nav.app.device.device_info["display_state"] = "dim"
    nav._idle_panel = idle
    nav._idle_panel_active = True
    nav.panel = idle
    nav.page = FakePage(page_id=3, started=True)
    nav._stack = [(idle, {})]

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=4),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl(notification_list.id)

    assert nav._idle_panel_active is False
    assert nav._idle_panel_suspended is True

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=5),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._open_panel_impl(notification.id)

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=4),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._close_panel_impl()

    assert nav.panel is notification_list
    assert nav._idle_panel_active is False
    assert nav._idle_panel_suspended is True

    with (
        patch.object(nav_module, "get_page_id_for_panel", return_value=3),
        patch.object(nav_module, "get_page_class_for_panel", return_value=OpenPage),
    ):
        nav._close_panel_impl()

    assert nav.panel is idle
    assert nav._idle_panel_active is True
    assert nav._idle_panel_suspended is False
    assert nav.app.device._first_touch_consumed is False


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


def test_nav_home_timeout_on_idle_page_exits_to_home():
    """With timeout_page shorter than auto_navigate_home_timeout the idle page
    opens first; once the nav-home timeout has passed, leaving the idle page
    must go home instead of restoring the panel the idle page covered."""
    other = DummyPanel("other", key="other")
    idle = DummyPanel("idle", key="idle")
    app = FakeApp(FakeDevice(auto_navigate_home_timeout=60))
    app.device_config = FakeDeviceConfig(other)
    nav = HAUINavigationController(app, {})
    opened = []
    nav.open_home_panel = lambda **kw: opened.append("home")
    nav.reload_panel = lambda: opened.append("restored")
    nav._home_panel = DummyPanel("home", key="home")
    nav.panel = other
    nav.create_snapshot()
    nav.panel = nav._idle_panel = idle
    nav._idle_panel_active = True
    nav._resume_pending = False
    nav.page = FakePage(page_id=3, started=True)
    nav._activity_ts = time.monotonic() - 61

    nav._check_inactivity({})
    nav.exit_idle_to_prev_or_home({"snapshot_max_age_seconds": -1})

    assert opened == ["home"]


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


def test_open_idle_panel_does_not_arm_wake_touch_when_display_dim():
    """A dimmed display is visible, so one touch exits the idle page."""
    device = FakeDevice()
    device.device_info["display_state"] = "dim"
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav._idle_panels = [DummyPanel("sleep")]
    nav.open_panel = lambda pid, **kw: None

    nav.open_idle_panel()

    assert device._first_touch_consumed is False


def test_exit_idle_to_prev_or_home_noops_when_not_idle():
    device = FakeDevice()
    app = FakeApp(device)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav._snapshot = nav_module.NavigationSnapshot(None, {}, None, {}, [])
    opened: list = []
    nav.open_home_panel = lambda **kw: opened.append("home")

    nav.exit_idle_to_prev_or_home({})

    assert opened == []  # no navigation away from normal operation


def test_stale_page_change_recovery_on_touch() -> None:
    """A touch during a stale page change forces the recovery callback.

    Regression: when a goto_page command is lost (buffer overflow / serial
    lag), the display stays on the old page while the hub waits for the page
    ack.  A touch during that wait must re-send the command immediately instead
    of doing nothing until the 10 s page_timeout fires.
    """
    nav = _make_nav()
    recovery_calls = []
    nav._page_timeout_callback = lambda _kwargs: recovery_calls.append("recovered")
    nav._page_timeout = "handle"  # a page change is pending
    nav._page_change_ts = time.monotonic() - 2.0  # ...and is stale

    nav.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert recovery_calls == ["recovered"]


def test_fresh_page_change_does_not_trigger_recovery() -> None:
    """A touch during a normal, fresh page transition does not force a reload."""
    nav = _make_nav()
    recovery_calls = []
    nav._page_timeout_callback = lambda _kwargs: recovery_calls.append("recovered")
    nav._page_timeout = "handle"
    nav._page_change_ts = time.monotonic()  # just requested

    nav.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert recovery_calls == []


def test_page_ack_clears_page_change_timestamp() -> None:
    """The page ack resets the pending-change timestamp."""
    nav = _make_nav()
    nav._page_timeout = "handle"
    nav._page_change_ts = time.monotonic()
    page = FakePage(1)
    nav.page = page
    nav._panel = DummyPanel("p")

    nav.process_event(HAUIEvent(ESPEvent.PAGE, "1"))

    assert nav._page_change_ts == 0.0

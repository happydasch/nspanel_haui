"""Navigation controller flow tests: close/stack, timers, fallbacks, reload, snapshot.

Uses a fake config whose ``reload()`` swaps in new panel objects with new
UUIDs, like ``reload_panels`` does in production.
"""

import uuid

import pytest
from nspanel_haui.haui.controller.navigation import HAUINavigationController
from nspanel_haui.haui.mapping.panel import PANEL_MAPPING
from nspanel_haui.haui.utils.page import get_page_class_for_panel, get_page_id_for_panel


class FPanel:
    def __init__(self, key, nav=True, panel_type="grid", close_timeout=0, unlock_code=""):
        self.id = uuid.uuid4()
        self._cfg = {"key": key, "unlock_code": unlock_code, "close_timeout": close_timeout}
        self._nav = nav
        self._type = panel_type
        self._state = {}

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def get_type(self):
        return self._type

    def get_title(self):
        return self._cfg.get("title", "")

    def show_in_navigation(self):
        return self._nav

    def apply_kwargs(self, kwargs):
        # close_timeout comes from kwargs for popups, like the real panel
        if "close_timeout" in kwargs:
            self._cfg["close_timeout"] = kwargs["close_timeout"]

    def get_state(self, key, default=None):
        return self._state.get(key, default)

    def set_state(self, key, value):
        self._state[key] = value


class FConfig:
    def __init__(self, specs):
        self._specs = specs  # key -> kwargs for FPanel
        self.reload()

    def reload(self):
        self._by_key = {k: FPanel(k, **v) for k, v in self._specs.items()}
        self._by_id = {p.id: p for p in self._by_key.values()}

    def get_panels(self, filter_nav_panel=None):
        panels = list(self._by_key.values())
        if filter_nav_panel is None:
            return panels
        return [p for p in panels if p.show_in_navigation() == filter_nav_panel]

    def get_panel(self, panel_id):
        if isinstance(panel_id, uuid.UUID):
            return self._by_id.get(panel_id)
        return self._by_key.get(panel_id)


class FDevice:
    connected = True
    sleeping = False

    def __init__(self, home="a"):
        self._cfg = {"home_panel": home}

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def get_name(self):
        return "test-panel"


class FApp:
    hass = None

    def __init__(self, specs):
        self.device = FDevice()
        self.device_config = FConfig(specs)
        self.controller = {}
        self.timers = {}
        self.cancelled = []
        self._n = 0

    def log(self, *a, **k):
        pass

    def run_in(self, cb, delay, **kw):
        self._n += 1
        handle = f"t{self._n}"
        self.timers[handle] = (cb, delay)
        return handle

    def cancel_timer(self, handle):
        self.cancelled.append(handle)
        self.timers.pop(handle, None)

    def fire_event(self, event_type, data=None):
        record = getattr(self, "fire_events", None)
        if record is None:
            self.fire_events = []
            record = self.fire_events
        record.append((event_type, data))


class FPage:
    hook = None
    # whether the loaded page fits the panel it is asked to show (is_loaded_for)
    loaded_for = True

    def __init__(self, app, config):
        self.page_id = config["page_id"]
        self._started = False

    def prepare_page_load(self, panel):
        if FPage.hook:
            FPage.hook()

    def is_loaded_for(self, panel):
        return FPage.loaded_for

    def is_started(self):
        return self._started

    def stop(self):
        self._started = False


SPECS = {
    "a": {},
    "b": {},
    "p1": {"nav": False},
    "p2": {"nav": False},
    "weird": {"nav": False, "panel_type": "no_such_type"},
}


def _nav(monkeypatch, specs):
    monkeypatch.setitem(PANEL_MAPPING, "grid", (PANEL_MAPPING["grid"][0], FPage))
    FPage.hook = None
    FPage.loaded_for = True
    app = FApp(specs)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav.goto_page = lambda pid, force=False: None
    nav.display_panel = lambda panel: None
    nav.start_part()
    return nav


@pytest.fixture
def nav(monkeypatch):
    return _nav(monkeypatch, SPECS)


@pytest.fixture
def locked_nav(monkeypatch):
    return _nav(
        monkeypatch,
        {
            **SPECS,
            "locked": {"unlock_code": "12"},
            "locked_sub": {"nav": False, "unlock_code": "12"},
            "popup_unlock": {"nav": False},
        },
    )


def keys(nav):
    return nav.panel.get("key")


# -- close / stack ----------------------------------------------------------


def test_close_walks_back_through_stack_to_nav_panel(nav):
    nav.open_panel("a")
    nav.open_panel("p1")
    nav.open_panel("p2")
    nav.close_panel()
    assert keys(nav) == "p1"
    nav.close_panel()
    assert keys(nav) == "a"


def test_close_without_stack_reopens_current_nav(nav):
    nav.open_panel("b")
    nav.close_panel()
    assert keys(nav) == "b"


def test_close_without_nav_opens_home(nav):
    nav.close_panel()
    assert keys(nav) == "a"


def test_opening_nav_panel_clears_stack(nav):
    nav.open_panel("a")
    nav.open_panel("p1")
    nav.open_panel("b")
    nav.close_panel()
    assert keys(nav) == "b"


# -- unlock popup -------------------------------------------------------------


def test_prev_and_next_on_the_unlock_popup_move_past_the_locked_panel(locked_nav):
    """Guarding a navigation panel, the popup has that panel's prev/next; they
    work on every opening (the popup never becomes the current nav panel)."""
    for _ in range(2):
        locked_nav.open_panel("b")
        locked_nav.open_panel("locked")
        assert keys(locked_nav) == "popup_unlock"
        locked_nav.open_prev_panel()
        assert keys(locked_nav) == "b"
        locked_nav.open_panel("locked")
        locked_nav.open_next_panel()
        assert keys(locked_nav) == "a"


def test_closing_unlock_popup_of_locked_nav_panel_goes_home(locked_nav):
    """Closing the popup (close_panel service) must not reopen the locked
    navigation panel, which would only open the popup again."""
    locked_nav.open_panel("b")
    locked_nav.open_panel("locked")
    assert keys(locked_nav) == "popup_unlock"
    locked_nav.close_panel()
    assert keys(locked_nav) == "a"


def test_closing_unlock_popup_of_locked_stacked_panel_goes_back(locked_nav):
    locked_nav.open_panel("b")
    locked_nav.open_panel("locked_sub")
    assert keys(locked_nav) == "popup_unlock"
    locked_nav.close_panel()
    assert keys(locked_nav) == "b"


def test_unlocking_opens_the_guarded_panel(locked_nav):
    for key in ("locked", "locked_sub"):
        locked_nav.open_panel("b")
        locked_nav.open_panel(key)
        locked_nav.app.device_config.get_panel(key).set_state("locked", False)
        locked_nav.close_panel()
        assert keys(locked_nav) == key


# -- close timeout ------------------------------------------------------------


def test_opening_panel_cancels_previous_close_timeout(nav):
    nav.open_panel("a")
    nav.open_panel("p1", close_timeout=5)
    stale = nav._close_timeout
    assert stale in nav.app.timers
    nav.open_panel("p2")  # no close_timeout of its own
    assert stale not in nav.app.timers
    assert nav._close_timeout is None


# -- home fallback ------------------------------------------------------------


def test_missing_panel_falls_back_to_home(nav):
    nav.open_panel("b")
    nav.open_panel("gone")
    assert keys(nav) == "a"


def test_unknown_panel_type_falls_back_to_home(nav):
    nav.open_panel("b")
    nav.open_panel("weird")
    assert keys(nav) == "a"


def test_unknown_panel_type_helpers_return_none():
    assert get_page_id_for_panel("no_such_type") is None
    assert get_page_class_for_panel("no_such_type") is None


# -- reload during navigation -------------------------------------------------


def test_reload_requested_during_open_runs_after_open(nav):
    nav.open_panel("a")
    new_ids = {}

    def hook():
        nav.app.device_config.reload()
        new_ids["b"] = nav.app.device_config.get_panel("b").id
        nav.reload_panels()  # navigating: queued

    FPage.hook = hook
    nav.open_panel("b")
    FPage.hook = None
    assert nav.panel is nav.app.device_config.get_panel("b")
    assert nav.get_current_nav_panel() is nav.app.device_config.get_panel("b")
    assert nav._home_panel is nav.app.device_config.get_panel("a")


def _record_page_loads(nav):
    """Record goto_page (a page load) and display_panel (a render in place)."""
    calls = []
    nav.goto_page = lambda pid, force=False: calls.append("goto_page")
    nav.display_panel = lambda panel: calls.append("display_panel")
    return calls


def test_reload_renders_an_unchanged_page_in_place(nav):
    nav.open_panel("a")
    nav.page._started = True
    calls = _record_page_loads(nav)

    nav.reload_panels()

    assert calls == ["display_panel"]


def test_reload_loads_the_page_again_when_it_reads_something_new(nav):
    """A new theme or background is painted only while the page loads."""
    nav.open_panel("a")
    nav.page._started = True
    calls = _record_page_loads(nav)
    FPage.loaded_for = False

    nav.reload_panels()

    assert calls == ["goto_page"]
    assert keys(nav) == "a"


def test_reload_requested_during_close_runs_after_close(nav):
    nav.open_panel("a")
    nav.open_panel("p1")

    def hook():
        nav.app.device_config.reload()
        nav.reload_panels()

    FPage.hook = hook
    nav.close_panel()
    FPage.hook = None
    assert nav.panel is nav.app.device_config.get_panel("a")
    assert nav._home_panel is nav.app.device_config.get_panel("a")


# -- snapshot -----------------------------------------------------------------


def test_snapshot_restore_returns_to_previous_panel(nav):
    nav.open_panel("b")
    nav.create_snapshot()
    nav.open_panel("a")
    assert nav.restore_snapshot() is True
    assert keys(nav) == "b"


def test_snapshot_restore_after_reload_returns_to_previous_panel(nav):
    nav.open_panel("b")
    nav.create_snapshot()
    nav.open_panel("a")
    nav.app.device_config.reload()
    nav.reload_panels()
    assert nav.restore_snapshot() is True
    assert nav.panel is nav.app.device_config.get_panel("b")


def test_snapshot_restore_after_reload_keeps_popup_stack(nav):
    nav.open_panel("a")
    nav.open_panel("p1")
    nav.open_panel("p2")
    nav.create_snapshot()
    nav.app.device_config.reload()
    assert nav.restore_snapshot() is True
    assert nav.panel is nav.app.device_config.get_panel("p2")
    nav.close_panel()
    assert nav.panel is nav.app.device_config.get_panel("p1")


def test_snapshot_restore_goes_home_when_panel_deleted(nav):
    nav.open_panel("p1")
    nav.create_snapshot()
    del nav.app.device_config._specs["p1"]
    nav.app.device_config.reload()
    nav.reload_panels()
    assert nav.restore_snapshot() is False
    assert keys(nav) == "a"

"""Timer page: the countdown keeps updating after the panel is reopened."""

from nspanel_haui.haui.page.timer import TimerPage

_PAGE_ID = 12


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)


class _DeviceConfig:
    def get_panels(self, show_in_navigation):
        return ["panel_a", "panel_b"]


class _App:
    def __init__(self):
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.controller = {}
        self.intervals = {}
        self.cancelled = set()

    def log(self, msg, **kwargs):
        pass

    def run_in(self, cb, delay, **kwargs):
        return f"run_in-{delay}"

    def run_every(self, cb, start, interval, **kwargs):
        handle = f"every-{len(self.intervals)}"
        self.intervals[handle] = cb
        return handle

    def cancel_timer(self, handle):
        self.cancelled.add(handle)

    def active_intervals(self):
        return [cb for h, cb in self.intervals.items() if h not in self.cancelled]


class _Panel:
    id = "timer-panel"

    def __init__(self):
        self.state = {}

    def get(self, key, default=None):
        return default

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def get_type(self):
        return "timer"

    def get_title(self, default=""):
        return default


def _timer_page():
    page = TimerPage(_App(), {"page_id": _PAGE_ID})
    page.send_cmd = lambda cmd: None
    page.get_color = lambda key: 0
    page.translate = lambda text: text
    page._auto_assign_fncs = lambda panel: None
    return page


def test_running_timer_display_updates_after_reopen():
    page = _timer_page()
    panel = _Panel()
    page.set_panel(panel)
    btn_up = TimerPage.COMPONENTS.btn_up_2.name
    page.callback_function_component(btn_up, btn_up)
    page.callback_function_component(TimerPage.COMPONENTS.btn_start.name, "start_timer")

    page.set_panel(None)
    assert page.app.active_intervals() == []

    page.set_panel(panel)

    assert page.app.active_intervals() == [page.update_timer]


def test_stopped_timer_has_no_display_updates_after_reopen():
    page = _timer_page()
    panel = _Panel()
    page.set_panel(panel)

    page.set_panel(None)
    page.set_panel(panel)

    assert page.app.active_intervals() == []


def test_show_notification_default_matches_descriptor():
    """The editor shows the descriptor default for panels without the key."""
    (option,) = [o for o in TimerPage.DESCRIPTOR.options if o.key == "show_notification"]
    page = _timer_page()
    page.set_panel(_Panel())
    opened = []
    page.app.controller["navigation"] = type(
        "Nav", (), {"open_panel": lambda s, key, **kw: opened.append(key)}
    )()

    page.callback_timer_ended({})

    assert bool(opened) is option.default

"""Header function-button auto-assignment tests.

Covers ``_auto_assign_fncs`` (which navigation / notification / sleep function
each of the four header slots gets on a given panel) and the single-nav slot
swap.  Regression target: the sleep button must appear on the home panel
whenever ``show_idle_button`` is set and the notifications button is not
actively occupying the left-secondary slot.
"""

from nspanel_haui.haui.abstract.component import Component
from nspanel_haui.haui.abstract.mixins.function_btn_mixin import (
    FncType,
    FunctionButtonMixin,
)


class FakeNotif:
    def __init__(self, count=0):
        self._count = count
        self.opened = 0

    def has_notifications(self):
        return self._count > 0

    def get_notifications(self):
        return [("t", "m", "", 0, False, "info", False)] * self._count

    def open_notifications(self):
        self.opened += 1


class FakeNav:
    def __init__(self):
        self.opened = []
        self.sleep_calls = []

    def open_panel(self, key, **kwargs):
        self.opened.append(key)

    def open_idle_panel(self, **kwargs):
        self.sleep_calls.append(kwargs)


class FakeDevice:
    def __init__(self, **cfg):
        self.cfg = cfg
        self.touch_grace_arms = 0

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    def arm_idle_touch_grace(self):
        self.touch_grace_arms += 1


class FakeApp:
    def __init__(self, device, notif):
        self.device = device
        self.controller = {"notification": notif, "navigation": FakeNav()}


class FakePanel:
    def __init__(self, device, key="home", cfg=None, popup=False, in_nav=True):
        self.device = device
        self._key = key
        self._cfg = cfg or {}
        self._popup = popup
        self._in_nav = in_nav

    def get(self, key, default=None):
        if key == "key":
            return self._key
        return self._cfg.get(key, default)

    def get_state(self, key, default=None):
        return default

    def can_show_popup(self):
        return self._popup

    def show_in_navigation(self):
        return self._in_nav

    def show_button(self, name):
        key = f"show_{name}_button"
        return self._cfg.get(key, self.device.get(key))

    def show_home_button(self):
        return self.show_button("home")

    def show_idle_button(self):
        return self.show_button("idle")

    def show_notifications_button(self):
        return self.show_button("notifications")


class FakePage(FunctionButtonMixin):
    def __init__(self, app):
        self.app = app
        self._fnc_items = {}
        self._fnc_id_by_component = {}

    def log(self, *a, **k):
        pass

    def get_color(self, key):
        return 0


def _build(device_cfg, notif_count=0, panel_cfg=None, in_nav=True):
    device = FakeDevice(**device_cfg)
    app = FakeApp(device, FakeNotif(notif_count))
    page = FakePage(app)
    panel = FakePanel(device, key="home", cfg=panel_cfg, in_nav=in_nav)
    page.set_function_buttons(
        Component(3, "bFncLPri"),
        Component(4, "bFncLSec"),
        Component(5, "bFncRPri"),
        Component(6, "bFncRSec"),
    )
    return page, panel


def _slot(page, fnc_id):
    item = page._fnc_items[fnc_id]
    return item["fnc_name"], item["fnc_args"].get("visible")


HOME = {"home_panel": "home", "show_home_button": False}


def test_sleep_button_shows_when_notifications_disabled():
    """Regression: notifications off + sleep on => sleep button on home."""
    page, panel = _build({**HOME, "show_idle_button": True, "show_notifications_button": False})
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_IDLE, True)


def test_sleep_button_shows_when_notifications_empty():
    """Notifications enabled but none pending => sleep takes the slot."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": True},
        notif_count=0,
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_IDLE, True)


def test_notifications_button_wins_when_pending():
    """Pending notifications keep the slot on right-secondary."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": True},
        notif_count=2,
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_R_SEC) == (FncType.NAV_NOTIF, True)


def test_notifications_button_opens_notifications_through_controller():
    page, panel = _build({**HOME, "show_notifications_button": True}, notif_count=1)
    page._auto_assign_fncs(panel)

    page.callback_function_components(None, Component(6, "bFncRSec"), 0)

    assert page.app.controller["notification"].opened == 1
    assert page.app.controller["navigation"].opened == []


def test_sleep_button_arms_touch_grace_before_opening_sleep():
    """The sleep button arms the device's residual-touch grace before opening the idle page.

    The sleep button is a touch, and the ESP32 can re-publish that touch's
    touch_start once its touch poller catches up — the grace window stops the
    duplicate from dismissing the just-opened idle page. Arming happens
    before open_idle_panel() so the window is live the moment it opens.
    """
    page, panel = _build({**HOME, "show_idle_button": True, "show_notifications_button": False})
    page._auto_assign_fncs(panel)

    page.callback_function_components(None, Component(4, "bFncLSec"), 0)

    nav = page.app.controller["navigation"]
    assert page.app.device.touch_grace_arms == 1
    assert nav.sleep_calls == [{}]
    assert nav.opened == []


def test_no_sleep_button_when_disabled():
    """Sleep off + notifications off => left-secondary slot is hidden."""
    page, panel = _build({**HOME, "show_idle_button": False, "show_notifications_button": False})
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_L_SEC) == (None, False)


def test_prev_next_visible_with_multiple_nav_panels():
    """Prev/next nav buttons are visible on a navigable home panel."""
    page, panel = _build({**HOME, "show_idle_button": True}, in_nav=True)
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_L_PRI) == (FncType.NAV_PREV, True)
    assert _slot(page, page.FNC_BTN_R_PRI) == (FncType.NAV_NEXT, True)


def test_notification_overrides_sleep_when_right_slots_claimed():
    """Pagination claims right_sec and NEXT right_pri => the notification
    button takes over the idle (sleep) button on the home panel."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": True},
        notif_count=1,
        in_nav=True,
    )
    # grid.py claims right_sec for pagination before auto-assign runs
    page.set_function_component(
        Component(6, "bFncRSec"), page.FNC_BTN_R_SEC, "next_page", visible=True
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_R_SEC) == ("next_page", True)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_NOTIF, True)


def test_sleep_button_survives_when_pagination_but_notifications_disabled():
    """No notifications => pagination keeps right_sec and sleep stays put."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": False},
        in_nav=True,
    )
    page.set_function_component(
        Component(6, "bFncRSec"), page.FNC_BTN_R_SEC, "next_page", visible=True
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_R_SEC) == ("next_page", True)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_IDLE, True)


def test_notification_takes_free_right_slot_and_sleep_stays():
    """With a free right_sec the notification uses it and the sleep button
    keeps its own slot — the left-secondary fallback must not trigger."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": True},
        notif_count=2,
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_R_SEC) == (FncType.NAV_NOTIF, True)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_IDLE, True)


def test_notification_fallback_slot_opens_notifications():
    """Tapping the former sleep slot (now the notification button) opens the
    notification popup, not the idle page."""
    page, panel = _build(
        {**HOME, "show_idle_button": True, "show_notifications_button": True},
        notif_count=1,
        in_nav=True,
    )
    page.set_function_component(
        Component(6, "bFncRSec"), page.FNC_BTN_R_SEC, "next_page", visible=True
    )
    page._auto_assign_fncs(panel)
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_NOTIF, True)

    page._fnc_id_by_component[4] = page.FNC_BTN_L_SEC
    page.callback_function_components(None, Component(4, "bFncLSec"), 0)

    assert page.app.controller["notification"].opened == 1
    assert page.app.controller["navigation"].sleep_calls == []
    assert page.app.controller["navigation"].opened == []


def test_single_nav_swap_moves_sleep_to_primary():
    """With a single nav panel, prev/next collapse and sleep surfaces in the
    visible primary-left slot."""
    page, panel = _build({**HOME, "show_idle_button": True}, in_nav=True)
    page._auto_assign_fncs(panel)
    page._swap_slots_if_single_nav(page.FNC_BTN_L_PRI, page.FNC_BTN_L_SEC)
    name, visible = _slot(page, page.FNC_BTN_L_PRI)
    assert name == FncType.NAV_IDLE
    assert visible is True
    # the displaced prev button is now hidden in the secondary slot
    assert _slot(page, page.FNC_BTN_L_SEC) == (FncType.NAV_PREV, False)

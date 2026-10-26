"""Tests for US time/date formatting, display models, ack-required
notifications, HA event emission, and the sleep panel carousel."""

import types
from unittest.mock import MagicMock

from nspanel_haui.haui.controller.navigation import HAUINavigationController
from nspanel_haui.haui.controller.notification import HAUINotificationController, Notification
from nspanel_haui.haui.controller.update import HAUIUpdateController
from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.device_config import tft_filename_for_model


class _App:
    def __init__(self, device_cfg=None, hub_cfg=None):
        dev_cfg = {"debug_level": 0, **(device_cfg or {})}
        self.device_config = hub_cfg or {}  # hub-level defaults
        self._runtime_device_name = ""
        self.device = HAUIDevice(self, dev_cfg)
        self.controller = {"notification": MagicMock()}
        self.fire_event_calls = []
        self.run_in_calls = []
        self.dummy_app = self

    # HAUIDevice helpers -------------------------------------------------
    def log(self, msg, *a, **k):
        pass

    def callback_event(self, event):
        pass

    def fire_event(self, event_type, data=None):
        self.fire_event_calls.append((event_type, data))


# --- US time/date format overrides --------------------------------------


def test_time_format_helpers_fall_back_to_hub_default():
    """An empty per-device value inherits the hub default."""
    app = _App(device_cfg={}, hub_cfg={"time_format": "%H:%M"})
    assert app.device.get_time_format() == "%H:%M"


def test_time_format_helpers_use_device_override():
    app = _App(device_cfg={"time_format": "%I:%M %p", "date_format": "%m/%d/%Y"})
    assert app.device.get_time_format() == "%I:%M %p"
    assert app.device.get_date_format() == "%m/%d/%Y"


def test_date_format_locale_falls_back_and_overrides():
    app = _App(device_cfg={"date_format_locale": "short"})
    assert app.device.get_date_format_locale() == "short"
    app2 = _App(device_cfg={}, hub_cfg={"date_format_locale": "medium"})
    assert app2.device.get_date_format_locale() == "medium"


# --- display models -------------------------------------------------------


def test_tft_filename_for_model_mapping():
    assert tft_filename_for_model("eu") == "nspanel_haui.tft"
    assert tft_filename_for_model("us") == "nspanel_haui_portrait.tft"
    # Unknown/empty models fall back to the landscape default.
    assert tft_filename_for_model(None) == "nspanel_haui.tft"
    assert tft_filename_for_model("bogus") == "nspanel_haui.tft"


def test_update_controller_tft_filename_uses_display_model():
    app = _App(device_cfg={"display_model": "us"})
    ctrl = _update_ctrl(app)
    assert ctrl._get_tft_filename() == "nspanel_haui_portrait.tft"


def test_update_controller_tft_filename_explicit_override_wins():
    app = _App(device_cfg={"display_model": "us"})
    ctrl = _update_ctrl(app, config={"tft_filename": "custom.tft"})
    assert ctrl._get_tft_filename() == "custom.tft"


def test_update_controller_tft_filename_default_model():
    app = _App(device_cfg={})
    ctrl = _update_ctrl(app)
    assert ctrl._get_tft_filename() == "nspanel_haui.tft"


def _update_ctrl(app, config=None):
    ctrl = HAUIUpdateController.__new__(HAUIUpdateController)
    ctrl.config = app.device_config
    ctrl._config = config or {}
    # self.get reads the *update* config dict
    ctrl.get = lambda key, default=None: ctrl._config.get(key, default)
    ctrl.app = app
    ctrl.log = lambda *a, **kw: None
    return ctrl


# --- ack-required notifications ------------------------------------------


class _NotifApp(_App):
    def __init__(self):
        super().__init__(device_cfg={"name": "kitchen", "display_model": "eu"})
        self._timers = {}
        self.canceled = []

    def run_in(self, cb, delay, **kwargs):
        handle = f"h{len(self._timers)}"
        self._timers[handle] = (cb, delay)
        self.run_in_calls.append((handle, delay))
        return handle

    def cancel_timer(self, handle):
        self.canceled.append(handle)

    def trigger(self, handle):
        cb, _ = self._timers.pop(handle)
        cb({})


def test_open_notification_button_label_is_dismiss():
    app = _NotifApp()
    ctrl = HAUINotificationController(app, {})
    ctrl.app = app
    app.device = types.SimpleNamespace(get=lambda k, d=None: None, get_name=lambda: "dev")
    nav = MagicMock()
    app.controller["navigation"] = nav
    n = Notification("T", "M", "", True, "critical", False)
    ctrl.translate = lambda s: s
    ctrl.open_notification(n)
    kwargs = nav.open_panel.call_args[1]
    assert kwargs["btn_right"] == "Dismiss"


def test_notification_ha_event_fired():
    app = _NotifApp()
    ctrl = HAUINotificationController(app, {})
    app.device = types.SimpleNamespace(get_name=lambda: "kitchen", get=lambda k, d=None: None)
    ctrl.add_notification("Doorbell", "Someone is here", icon="mdi:bell")
    (event_type, data) = app.fire_event_calls[0]
    assert event_type == "nspanel_haui.notification"
    assert data["state"] == "added"
    assert data["device"] == "kitchen"
    assert data["title"] == "Doorbell"


# --- sleep panel carousel --------------------------------------------------


class _Panel:
    def __init__(self, key, panel_type="clock"):
        self.key = key
        self.id = f"id-{key}"
        self._type = panel_type

    def get(self, k, default=None):
        if k == "key":
            return self.key
        return default

    def get_type(self):
        return self._type

    def get_title(self):
        return ""


class _CarouselCfg:
    def __init__(self, panels):
        self._by_key = {p.key: p for p in panels}

    def get_panel(self, key):
        return self._by_key.get(key)

    def get_panels(self, filter_nav_panel=False):
        return list(self._by_key.values())


class _CarouselApp(_App):
    def __init__(self, panels, **device_cfg):
        super().__init__(device_cfg, {})
        self.device_cfg = device_cfg  # mutable reference for config-change tests
        def _dev_get(key, d=None):
            if key == "debug_level":
                return 0
            if key == "idle_panel_extra":
                # stored comma-separated in config, fine to pass through
                return (device_cfg or {}).get(key, d)
            return (device_cfg or {}).get(key, d)

        self.device = types.SimpleNamespace(
            get=_dev_get,
            get_name=lambda: "nav",
            sleeping=False,
            device_info={},
        )
        self.device_config = _CarouselCfg(panels)
        self.controller = {}
        self.fire_event_calls = []


def _nav_with_carousel(panels, **device_cfg):
    app = _CarouselApp(panels, **device_cfg)
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav.create_snapshot = lambda: None
    nav._cancel_idle_timer = lambda: None
    nav.open_panel = lambda pid, **kw: nav.opened.append((pid, kw.get("autostart", False)))
    nav.opened = []
    nav._resolve_special_panels(log=False)
    return nav


def test_idle_panel_carousel_resolves_keys():
    panels = [
        _Panel("clock"),
        _Panel("clocktwo"),
        _Panel("weather"),
        _Panel("grid", "grid"),
    ]
    nav = _nav_with_carousel(
        panels, idle_panel="clock", idle_panel_extra="weather, clocktwo, weather"
    )
    keys = [p.key for p in nav._idle_panels]
    assert keys == ["clock", "weather", "clocktwo"]  # deduplicated, order kept


def test_idle_panel_carousel_cycles():
    panels = [_Panel("clock"), _Panel("clocktwo")]
    nav = _nav_with_carousel(panels, idle_panel="clock", idle_panel_extra="clocktwo")
    nav.open_idle_panel()
    nav.open_idle_panel()
    assert [pid for pid, _ in nav.opened] == ["id-clock", "id-clocktwo"]


def test_idle_panel_carousel_resets_when_config_changes():
    """A reload that changes the carousel list resets the cursor to the start."""
    panels = [_Panel("clock"), _Panel("clocktwo"), _Panel("weather")]
    app = _CarouselApp(panels, idle_panel="clock", idle_panel_extra="clocktwo")
    nav = HAUINavigationController(app, {})
    app.controller["navigation"] = nav
    nav.create_snapshot = lambda: None
    nav._cancel_idle_timer = lambda: None
    nav.open_panel = lambda pid, **kw: None
    nav._resolve_special_panels(log=False)

    nav.open_idle_panel()  # idx -> 1
    nav.open_idle_panel()  # idx -> 2
    assert nav._idle_panel_idx == 2
    # Re-resolving the same list preserves the cursor.
    nav._resolve_idle_panels()
    assert nav._idle_panel_idx == 2
    # Re-resolving a changed list resets it.
    app.device_cfg["idle_panel_extra"] = "weather"
    nav._resolve_idle_panels()
    assert nav._idle_panel_idx == 0
    assert [p.key for p in nav._idle_panels] == ["clock", "weather"]


# --- page-changed events ----------------------------------------------------


def test_page_changed_event_fired_on_open():
    panels = [_Panel("clock"), _Panel("clocktwo")]
    nav = _nav_with_carousel(panels, home_panel="clock", idle_panel="")
    nav.app.fire_event_calls.clear()
    nav._fire_page_event("opened", panels[0])
    (event_type, data) = nav.app.fire_event_calls[-1]
    assert event_type == "nspanel_haui.page_changed"
    assert data["action"] == "opened"
    assert data["panel"] == "clock"

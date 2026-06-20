from contextlib import nullcontext

from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.mapping.const import ESPAction, ESPEvent


class DummyPanel:
    def __init__(self, panel_id, key=""):
        self.id = panel_id
        self._key = key

    def get(self, key, default=None):
        return self._key if key == "key" else default


class DummyPage:
    """Records button-state display writes (Nextion serial commands)."""

    def __init__(self):
        self.left_calls = []
        self.right_calls = []

    def set_button_left_state(self, state):
        self.left_calls.append(state)

    def set_button_right_state(self, state):
        self.right_calls.append(state)

    @property
    def rec_cmd(self):
        """Re-entrant command batch context manager for test page."""
        return nullcontext()


class DummyNavigation:
    def __init__(self):
        self.opened_calls = []  # list of (panel_id, kwargs)
        self.panel = None
        self._current_nav = None
        self._home_panel = None

    def cancel_timeouts(self):
        pass

    def open_panel(self, panel_id, **kwargs):
        self.opened_calls.append((panel_id, kwargs))

    def get_current_panel(self):
        return self.panel

    def get_current_nav_panel(self):
        return self._current_nav

    def open_home_panel(self, autostart=False):
        if self._home_panel is not None:
            self.open_panel(self._home_panel.id, autostart=autostart)


class DummyESPHomeProxy:
    def __init__(self):
        self.publish_calls = []
        self._device_id: str | None = None

    def publish(self, topic, payload, retain=False):
        self.publish_calls.append((topic, payload))


class DummyESPHomeController:
    def __init__(self):
        self.esphome = DummyESPHomeProxy()


class DummyApp:
    def __init__(self):
        self.controller = {
            "navigation": DummyNavigation(),
            "esphome": DummyESPHomeController(),
        }
        self.service_calls = []

    def log(self, msg, *args, **kwargs):
        pass

    def call_service(self, service, **kwargs):
        self.service_calls.append((service, kwargs))

    def entity_exists(self, entity_id):
        return False

    def get_entity(self, entity_id):
        raise RuntimeError("Not implemented")

    def run_in(self, cb, delay, **kwargs):
        # Fire immediately - in production this schedules async via HA event loop.
        cb({})
        return "dummy-handle"


def test_set_device_info_and_on_connection_changed():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})

    device.set_device_info({"foo": "bar"})
    assert device.device_info["foo"] == "bar"

    device.on_connection_changed(True)
    assert app.controller["esphome"].esphome.publish_calls[0] == ("play_sound", "startup")
    assert app.controller["navigation"].opened_calls[0] == ("sys_system", {})


def test_reconnect_restores_current_nav_panel():
    """On reconnect, the current nav panel is restored with force=True.

    Popups (non-nav panels) are intentionally skipped - they should not
    survive a disconnect. See test_reconnect_skips_popup_restores_nav.
    """
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # Simulate: first connect (initial_connect_done becomes True)
    device.on_connection_changed(True)
    assert device._initial_connect_done is True
    assert nav.opened_calls[0] == ("sys_system", {})

    # Simulate: a nav panel is active (as if the user navigated to it)
    panel = DummyPanel("my-grid-panel")
    nav.panel = panel
    nav._current_nav = panel

    # Simulate: reconnect (on_connection_changed called again with True)
    device.on_connection_changed(True)
    # Should re-open the current nav panel with force=True
    assert nav.opened_calls[1] == (panel.id, {"force": True})


def test_reconnect_skips_popup_restores_nav():
    """When current panel is a popup (≠ nav panel), reconnect restores the
    nav panel instead, with force=True."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.on_connection_changed(True)

    # Simulate: a nav panel exists, but current panel is a popup
    nav_panel = DummyPanel("grid-panel")
    popup = DummyPanel("popup_alarm")
    nav._current_nav = nav_panel
    nav.panel = popup

    # Reconnect - should skip popup, open nav panel instead
    device.on_connection_changed(True)
    assert nav.opened_calls[1] == (nav_panel.id, {"force": True})


def test_reconnect_falls_back_to_nav_panel():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.on_connection_changed(True)

    # No current panel, but a nav panel exists
    nav.panel = None
    nav._current_nav = DummyPanel("nav-panel")

    device.on_connection_changed(True)
    assert nav.opened_calls[1] == (nav._current_nav.id, {"force": True})


def test_reconnect_falls_back_to_home_panel():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.on_connection_changed(True)

    # No panel, no nav panel, but a home panel
    nav.panel = None
    nav._current_nav = None
    nav._home_panel = DummyPanel("home-panel")

    device.on_connection_changed(True)
    assert nav.opened_calls[1] == (nav._home_panel.id, {"autostart": False})


def test_relay_event_updates_display_when_interaction_enabled():
    """Default (reset_interaction_on_button True): relay change writes display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    page = DummyPage()
    app.controller["navigation"].page = page

    device.process_event(HAUIEvent(ESPEvent.RELAY_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.RELAY_RIGHT, "1"))

    assert device._btn_left_info["state"] is True
    assert device._btn_right_info["state"] is True
    assert page.left_calls == [True]
    assert page.right_calls == [True]


def test_relay_event_skips_display_when_interaction_disabled():
    """reset_interaction_on_button False: relay only toggles device, display untouched.

    Internal button state is still tracked, but no Nextion serial write is
    issued so a button press cannot wake or alter the display.
    """
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": False})
    page = DummyPage()
    app.controller["navigation"].page = page

    device.process_event(HAUIEvent(ESPEvent.RELAY_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.RELAY_RIGHT, "1"))

    # Device state is tracked...
    assert device._btn_left_info["state"] is True
    assert device._btn_right_info["state"] is True
    # ...but the display was never written to.
    assert page.left_calls == []
    assert page.right_calls == []


def _spy_button_press(device):
    """Replace check_wakeup/toggle_* with recorders, return the call log."""
    calls = {"wakeup": 0, "toggle_left": 0, "toggle_right": 0}
    device.check_wakeup = lambda from_button=False: calls.__setitem__("wakeup", calls["wakeup"] + 1)
    device.toggle_left_button_state = lambda: calls.__setitem__(
        "toggle_left", calls["toggle_left"] + 1
    )
    device.toggle_right_button_state = lambda: calls.__setitem__(
        "toggle_right", calls["toggle_right"] + 1
    )
    return calls


def test_button_press_wakes_and_exits_when_interaction_enabled():
    """Default (reset_interaction_on_button True): press resets idle timer,
    exits sleep/wakeup, and toggles the relay/entity."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "0"))

    publishes = app.controller["esphome"].esphome.publish_calls
    assert publishes.count((ESPAction.RESET_LAST_INTERACTION, "0")) == 2
    assert calls["wakeup"] == 2
    assert calls["toggle_left"] == 1
    assert calls["toggle_right"] == 1


def test_button_press_only_toggles_when_interaction_disabled():
    """reset_interaction_on_button False: press must NOT touch the display
    (no idle-timer reset, no sleep/wakeup exit) — only toggle the relay/entity.
    The toggle still happens on the first press, regardless of display state."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": False})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "0"))

    publishes = app.controller["esphome"].esphome.publish_calls
    # Display untouched: no idle-timer reset, no wakeup/home navigation.
    assert (ESPAction.RESET_LAST_INTERACTION, "0") not in publishes
    assert calls["wakeup"] == 0
    # ...but the relay/entity still toggles on the press.
    assert calls["toggle_left"] == 1
    assert calls["toggle_right"] == 1


# --- check_wakeup: always exit on touch -----------------------------------------


def _wakeup_harness():
    """Device + navigation set up with an active sleep panel."""
    app = DummyApp()
    nav = app.controller["navigation"]
    nav.panel = DummyPanel("sleep-panel")
    nav._sleep_panel_active = True
    nav.exit_calls = []
    nav.exit_sleep_to_prev_or_home = lambda cfg: nav.exit_calls.append(cfg)
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "wakeup_panel": "",
            "home_panel": "",
        },
    )
    device.device_info["display_state"] = "off"
    return device, nav


def test_first_touch_always_exits():
    """A single touch always exits the sleep/wake panel immediately."""
    device, nav = _wakeup_harness()
    device.woke_up = True
    device.check_wakeup()
    assert len(nav.exit_calls) == 1


def test_hardware_button_always_exits():
    device, nav = _wakeup_harness()
    device.woke_up = True
    device.check_wakeup(from_button=True)
    assert len(nav.exit_calls) == 1


def test_no_exit_when_no_sleep_or_wakeup_panel_active():
    device, nav = _wakeup_harness()
    nav._sleep_panel_active = False
    device.woke_up = True
    device.check_wakeup()
    assert nav.exit_calls == []


def test_first_touch_exits_when_display_already_on() -> None:
    """Touch exits even when the display is already ON."""
    device, nav = _wakeup_harness()
    device.woke_up = True
    device.device_info["display_state"] = "on"
    device.check_wakeup()
    assert len(nav.exit_calls) == 1


def test_button_press_wakes_on_press_event() -> None:
    """Button press (value '1') immediately resets timer and wakes display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "1"))

    publishes = app.controller["esphome"].esphome.publish_calls
    assert publishes.count((ESPAction.RESET_LAST_INTERACTION, "0")) == 2
    # check_wakeup is called on press (wake), NOT on release (toggle only)
    assert calls["wakeup"] == 2
    # Entity toggle stays on release — press alone does NOT toggle.
    assert calls["toggle_left"] == 0
    assert calls["toggle_right"] == 0


def test_button_press_no_wake_when_interaction_disabled() -> None:
    """Button press (value '1') with interaction disabled: no wake, no toggle."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": False})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))

    publishes = app.controller["esphome"].esphome.publish_calls
    assert (ESPAction.RESET_LAST_INTERACTION, "0") not in publishes
    assert calls["wakeup"] == 0
    assert calls["toggle_left"] == 0


def test_full_press_release_sequence() -> None:
    """Full button cycle: press wakes, release toggles, both paths work."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    # Press
    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))
    # Release
    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))

    publishes = app.controller["esphome"].esphome.publish_calls
    # Press triggers one RESET_LAST_INTERACTION, release triggers another
    # (from _on_button_release).  Both are harmless duplicates.
    assert publishes.count((ESPAction.RESET_LAST_INTERACTION, "0")) == 2
    # Woken on press (not just on release)
    assert calls["wakeup"] == 2  # press + release both call check_wakeup
    # Toggle happens only on release
    assert calls["toggle_left"] == 1


def test_press_event_sets_device_info_key() -> None:
    """Button press event updates device_info with the button-left key."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))

    assert device.device_info.get("button_left") == "1"


def test_release_event_sets_device_info_key() -> None:
    """Button release event updates device_info with the button-left key."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))

    assert device.device_info.get("button_left") == "0"


def test_first_touch_exits_when_display_dim() -> None:
    """Touch exits even when the display is dimmed."""
    device, nav = _wakeup_harness()
    device.woke_up = True
    device.device_info["display_state"] = "dim"
    device.check_wakeup()
    assert len(nav.exit_calls) == 1


def test_first_touch_exits_when_display_unknown() -> None:
    """Touch exits even when display_state is not yet known."""
    device, nav = _wakeup_harness()
    device.woke_up = True
    # No display_state in device_info (e.g. not yet received from device).
    del device.device_info["display_state"]
    device.check_wakeup()
    assert len(nav.exit_calls) == 1

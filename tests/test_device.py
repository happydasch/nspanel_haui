import time
from datetime import datetime, timedelta
from datetime import time as dt_time

from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.device import HAUIDevice, _time_in_window
from nspanel_haui.haui.mapping.const import ESPAction, ESPEvent


class DummyPanel:
    def __init__(self, panel_id, key=""):
        self.id = panel_id
        self._key = key

    def get(self, key, default=None):
        return self._key if key == "key" else default


class DummyNavigation:
    def __init__(self):
        self.opened_calls = []  # list of (panel_id, kwargs)
        self.panel = None
        self._current_nav = None
        self._home_panel = None
        self._idle_panel_active = False

    @property
    def idle_panel_active(self):
        return self._idle_panel_active

    def cancel_timeouts(self):
        pass

    def mark_awake(self):
        self._idle_panel_active = False

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
    device_slug = "nspanel_haui"

    def __init__(self):
        self.controller = {
            "navigation": DummyNavigation(),
            "esphome": DummyESPHomeController(),
        }
        self.service_calls = []

    def item_exists(self, entity_id):
        return False

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
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "sound_on_startup": True, "use_do_not_disturb": False}
    )

    device.set_device_info({"foo": "bar"})
    assert device.device_info["foo"] == "bar"

    device.on_connection_changed(True)
    assert app.controller["esphome"].esphome.publish_calls[0] == ("play_sound", "startup")
    assert app.controller["navigation"].opened_calls[0] == ("sys_system", {})


def _publish_topics(app):
    return [topic for topic, _ in app.controller["esphome"].esphome.publish_calls]


def test_startup_sound_plays_on_fresh_boot_uptime():
    """A low uptime (fresh boot) plays the startup sound."""
    app = DummyApp()
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "sound_on_startup": True, "use_do_not_disturb": False}
    )
    device.set_device_info({"uptime": 5})
    device.on_connection_changed(True)
    assert "play_sound" in _publish_topics(app)
    assert ("play_sound", "startup") in app.controller["esphome"].esphome.publish_calls


def test_startup_sound_silent_on_reconnect_uptime():
    """A high uptime (Wi-Fi reconnect, device stayed up) stays silent."""
    app = DummyApp()
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "sound_on_startup": True, "use_do_not_disturb": False}
    )
    device.set_device_info({"uptime": 600})
    device.on_connection_changed(True)
    assert "play_sound" not in _publish_topics(app)


def test_startup_sound_plays_when_uptime_missing():
    """Firmware without an uptime value keeps the previous every-connect behavior."""
    app = DummyApp()
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "sound_on_startup": True, "use_do_not_disturb": False}
    )
    device.set_device_info({"foo": "bar"})
    device.on_connection_changed(True)
    assert ("play_sound", "startup") in app.controller["esphome"].esphome.publish_calls


def test_startup_sound_disabled_suppresses_regardless_of_uptime():
    """sound_on_startup False suppresses the sound even for a fresh boot."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    device.set_device_info({"uptime": 5})
    device.on_connection_changed(True)
    assert "play_sound" not in _publish_topics(app)


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


class _RelayItem:
    def __init__(self):
        self.calls = []

    def call_service(self, service, **kwargs):
        self.calls.append(service)


class _RelayApp(DummyApp):
    def __init__(self, relays, slug):
        super().__init__()
        self.relays = relays
        self.device_slug = slug
        self._runtime_device_name = None

    def item_exists(self, entity_id):
        return entity_id in self.relays

    def get_item(self, entity_id):
        return self.relays[entity_id]


def test_toggle_button_uses_default_relay_entity_from_device_slug() -> None:
    """Without a button_*_entity the toggle targets switch.{slug}_relay_{side}."""
    left, right = _RelayItem(), _RelayItem()
    app = _RelayApp(
        {"switch.nspanel_living_relay_left": left, "switch.nspanel_living_relay_right": right},
        "nspanel_living",
    )
    device = HAUIDevice(
        app,
        {
            "name": "NSPanel-Living",
            "button_left_entity": "",
            "button_right_entity": "",
            "use_relay_left": False,
            "use_relay_right": False,
        },
    )
    device._register_callbacks()

    device.toggle_left_button_state()
    device.toggle_right_button_state()

    assert left.calls == ["toggle"]
    assert right.calls == ["toggle"]


def test_toggle_button_prefers_configured_entity_and_skips_hardware_relay() -> None:
    custom = _RelayItem()
    app = _RelayApp({"light.hall": custom}, "nspanel_haui")
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "button_left_entity": "light.hall",
            "button_right_entity": "",
            "use_relay_left": True,
        },
    )
    device._register_callbacks()

    # use_relay_left True: the firmware relay switches itself, hub must not toggle
    device.toggle_left_button_state()

    assert custom.calls == []


def test_relay_event_does_not_touch_display() -> None:
    """The device never mirrors relay state onto the display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.process_event(HAUIEvent(ESPEvent.RELAY_LEFT, "1"))

    assert app.service_calls == []


# --- sleep schedule ----------------------------------------------------------


def _schedule_device(app, **cfg) -> HAUIDevice:
    return HAUIDevice(app, {"name": "nspanel_haui", **cfg})


def _window_around_now(*, offset_before: int, offset_after: int) -> dict[str, str]:
    """A schedule window that always contains the current time (midnight-safe)."""
    now = datetime.now()
    return {
        "sleep_schedule_start": (now - timedelta(seconds=offset_before)).strftime("%H:%M"),
        "sleep_schedule_end": (now + timedelta(seconds=offset_after)).strftime("%H:%M"),
    }


def _one_hour_from_now() -> str:
    """A wall-clock time one hour ahead (start == end -> never-active window)."""
    return (datetime.now() + timedelta(hours=1)).strftime("%H:%M")


def test_time_in_window_day_and_overnight() -> None:
    # same-day window
    assert _time_in_window(dt_time(12, 0), dt_time(10, 0), dt_time(14, 0)) is True
    assert _time_in_window(dt_time(9, 59), dt_time(10, 0), dt_time(14, 0)) is False
    assert _time_in_window(dt_time(15, 0), dt_time(10, 0), dt_time(14, 0)) is False
    # inclusive boundaries
    assert _time_in_window(dt_time(10, 0), dt_time(10, 0), dt_time(14, 0)) is True
    assert _time_in_window(dt_time(14, 0), dt_time(10, 0), dt_time(14, 0)) is True
    # overnight window (start > end)
    assert _time_in_window(dt_time(22, 0), dt_time(22, 0), dt_time(6, 0)) is True
    assert _time_in_window(dt_time(2, 0), dt_time(22, 0), dt_time(6, 0)) is True
    assert _time_in_window(dt_time(6, 0), dt_time(22, 0), dt_time(6, 0)) is True
    assert _time_in_window(dt_time(12, 0), dt_time(22, 0), dt_time(6, 0)) is False


def test_sleep_schedule_inactive_when_disabled() -> None:
    app = DummyApp()
    device = _schedule_device(
        app,
        use_sleep_schedule=False,
        sleep_schedule_start="22:00",
        sleep_schedule_end="06:00",
    )

    assert device._display_off_schedule_active(datetime(2026, 10, 25, 2, 0, 0)) is None
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 2, 0, 0)) is None


def test_sleep_schedule_inactive_when_window_incomplete_or_malformed() -> None:
    app = DummyApp()
    incomplete = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="22:00",
        sleep_schedule_end="",
    )
    malformed = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="banana",
        sleep_schedule_end="06:00",
    )

    assert incomplete._display_off_schedule_active(datetime(2026, 10, 25, 2, 0, 0)) is None
    assert incomplete._next_schedule_boundary(datetime(2026, 10, 25, 2, 0, 0)) is None
    assert malformed._display_off_schedule_active(datetime(2026, 10, 25, 2, 0, 0)) is None
    assert malformed._next_schedule_boundary(datetime(2026, 10, 25, 2, 0, 0)) is None


def test_display_off_schedule_active_inside_and_outside_window() -> None:
    app = DummyApp()
    device = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="10:00",
        sleep_schedule_end="14:00",
    )
    overnight = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="22:00",
        sleep_schedule_end="06:00",
    )

    assert device._display_off_schedule_active(datetime(2026, 10, 25, 12, 0, 0)) is True
    assert device._display_off_schedule_active(datetime(2026, 10, 25, 15, 0, 0)) is False
    assert overnight._display_off_schedule_active(datetime(2026, 10, 25, 2, 0, 0)) is True
    assert overnight._display_off_schedule_active(datetime(2026, 10, 25, 12, 0, 0)) is False


def test_next_schedule_boundary_picks_nearest_flip() -> None:
    app = DummyApp()
    device = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="10:00",
        sleep_schedule_end="14:00",
    )

    # inside the window -> window end today
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 12, 0, 0)) == datetime(
        2026, 10, 25, 14, 0, 0
    )
    # before the window -> window start today
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 9, 0, 0)) == datetime(
        2026, 10, 25, 10, 0, 0
    )
    # after the window -> window start tomorrow
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 15, 0, 0)) == datetime(
        2026, 10, 26, 10, 0, 0
    )


def test_next_schedule_boundary_overnight() -> None:
    app = DummyApp()
    device = _schedule_device(
        app,
        use_sleep_schedule=True,
        sleep_schedule_start="22:00",
        sleep_schedule_end="06:00",
    )

    # inside the overnight window -> window end today
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 2, 0, 0)) == datetime(
        2026, 10, 25, 6, 0, 0
    )
    # outside, before the window -> window start today
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 12, 0, 0)) == datetime(
        2026, 10, 25, 22, 0, 0
    )
    # late in the window -> window end tomorrow
    assert device._next_schedule_boundary(datetime(2026, 10, 25, 23, 30, 0)) == datetime(
        2026, 10, 26, 6, 0, 0
    )


def _spy_button_press(device):
    """Replace check_wakeup/toggle_* with recorders, return the call log."""
    calls = {"wakeup": 0, "toggle_left": 0, "toggle_right": 0}
    device.check_wakeup = lambda: calls.__setitem__("wakeup", calls["wakeup"] + 1)
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
    """Device + navigation set up with an active idle page session."""
    app = DummyApp()
    nav = app.controller["navigation"]
    nav.panel = DummyPanel("sleep-panel")
    nav._idle_panel_active = True
    nav.exit_calls = []
    nav.exit_idle_to_prev_or_home = lambda cfg: nav.exit_calls.append(cfg)
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "home_panel": "",
        },
    )
    device.device_info["display_state"] = "off"
    return device, nav


def test_first_touch_only_wakes():
    """First touch after sleep wakes the display but does NOT exit."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True
    device.check_wakeup()
    assert len(nav.exit_calls) == 0
    assert device._first_touch_consumed is False


def test_second_touch_exits():
    """Second touch exits after the wake touch was consumed."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = False
    device.check_wakeup()
    assert len(nav.exit_calls) == 1


def test_dark_wake_touch_and_poller_duplicate_do_not_exit_idle_page():
    """A delayed display-state update and duplicate poller event must not turn
    one dark-screen touch into an idle-page exit; the next real touch does.
    """
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True

    # The firmware can publish "on" before the queued touch-start reaches HA.
    device.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))  # poller duplicate

    assert nav.exit_calls == []

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))  # next physical touch
    assert len(nav.exit_calls) == 1


def test_hardware_button_wakes_on_first_press():
    """First hardware button press after sleep wakes but does not exit.

    The press event runs the same touch-driven decision as a screen touch:
    with the display still off it only wakes; the release (or a second
    press) then exits.
    """
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))

    assert len(nav.exit_calls) == 0
    assert device._first_touch_consumed is False


def test_two_touch_rearms_when_display_turns_off_on_sleep_screen():
    """After a wake, the sleep panel stays; when the display turns off the
    next touch must only wake it, not exit."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))  # wakes only
    device.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))

    device.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "off"))
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert len(nav.exit_calls) == 0
    device.process_event(HAUIEvent(ESPEvent.DISPLAY_STATE, "on"))
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))
    assert len(nav.exit_calls) == 1


def test_hardware_button_press_and_release_exits_dark_sleep_screen():
    """One physical button press (press + release) wakes and exits, as documented."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))

    assert len(nav.exit_calls) == 1


def test_no_exit_when_idle_panel_not_active():
    """Without an idle session there is nothing to exit — wake is firmware-side."""
    device, nav = _wakeup_harness()
    nav._idle_panel_active = False
    device._first_touch_consumed = True
    device.check_wakeup()
    assert nav.exit_calls == []


def test_first_touch_exits_when_display_already_on() -> None:
    """An idle page opened while on exits on the first touch."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = False
    device.device_info["display_state"] = "on"
    device.check_wakeup()
    assert len(nav.exit_calls) == 1


def test_residual_touch_start_does_not_dismiss_just_opened_sleep() -> None:
    """A leftover touch_start of the sleep-button tap must not exit the sleep screen.

    Regression: with a quick tap on the sleep button, the ESP32's 200 ms touch
    poller can deliver a duplicate touch_start *after* the sleep panel already
    opened (serial read lag).  The display is still "on" in that flow, so the
    duplicate otherwise took the one-touch wake path and immediately dismissed
    the sleep screen the button had just opened.
    """
    device, nav = _wakeup_harness()
    device.device_info["display_state"] = "on"
    device.arm_idle_touch_grace()

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))

    assert len(nav.exit_calls) == 0
    assert device._first_touch_consumed is False  # check_wakeup was never reached


def test_touch_after_grace_window_exits_sleep_normally() -> None:
    """Touches after the grace window behave as before (one-touch exit when on)."""
    device, nav = _wakeup_harness()
    device.device_info["display_state"] = "on"
    device.arm_idle_touch_grace()
    device._idle_touch_grace_until = time.monotonic() - 1.0  # window expired

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert len(nav.exit_calls) == 1
    assert device._first_touch_consumed is False


def test_idle_touch_grace_does_not_swallow_hardware_button() -> None:
    """Hardware-button presses are new interactions, never swallowed by the grace window."""
    device, nav = _wakeup_harness()
    device.device_info["display_state"] = "on"
    device.arm_idle_touch_grace()

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))

    assert len(nav.exit_calls) == 1


def test_grace_not_armed_means_touch_start_not_swallowed() -> None:
    """Without a touch-initiated idle page, touch_starts always reach check_wakeup."""
    device, nav = _wakeup_harness()
    device.device_info["display_state"] = "on"

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert len(nav.exit_calls) == 1


def test_disconnect_resets_wake_guards() -> None:
    """Disconnect clears the idle session and the touch/wake guards so the next
    interaction after reconnect starts on a clean slate."""
    app = DummyApp()
    nav = app.controller["navigation"]
    nav._idle_panel_active = True
    device = HAUIDevice(app, {"name": "nspanel_haui"})
    device._first_touch_consumed = True
    device._idle_touch_grace_until = time.monotonic() + 10

    device.on_connection_changed(False)

    assert nav._idle_panel_active is False
    assert device._first_touch_consumed is False
    assert device._idle_touch_grace_until == 0.0


def test_sleep_wakeup_events_do_not_drive_idle_session() -> None:
    """SLEEP/WAKEUP are hardware events (no-hub path) and must not open or
    close the hub's idle page session by themselves."""
    device, nav = _wakeup_harness()
    device.process_event(HAUIEvent(ESPEvent.DISPLAY_OFF, ""))
    assert nav._idle_panel_active is True  # untouched by the hardware event
    assert nav.exit_calls == []

    nav._idle_panel_active = False
    device.process_event(HAUIEvent(ESPEvent.DISPLAY_ON, ""))
    assert nav._idle_panel_active is False
    assert nav.exit_calls == []


def test_button_press_wakes_on_press_event() -> None:
    """Button press (value '1') immediately resets timer and wakes display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "1"))

    publishes = app.controller["esphome"].esphome.publish_calls
    assert publishes.count((ESPAction.RESET_LAST_INTERACTION, "0")) == 2
    # check_wakeup runs on press so the display wakes without waiting for release
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
    """A dimmed display is visible, so the first touch exits the idle page."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True
    device.device_info["display_state"] = "dim"
    device.check_wakeup()
    assert len(nav.exit_calls) == 1
    assert device._first_touch_consumed is False


def test_first_touch_wakes_when_display_unknown() -> None:
    """First touch wakes even when display_state is not yet known (does not exit)."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = True
    # No display_state in device_info (e.g. not yet received from device).
    del device.device_info["display_state"]
    device.check_wakeup()
    assert len(nav.exit_calls) == 0
    assert device._first_touch_consumed is False


class _Switch:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def turn_on(self):
        self.state = "on"

    def turn_off(self):
        self.state = "off"


class _SwitchApp(DummyApp):
    def __init__(self, switches):
        super().__init__()
        self.switches = switches
        self._runtime_device_name = None
        self.device_slug = "nspanel_haui"

    def item_exists(self, entity_id):
        return entity_id in self.switches

    def get_item(self, entity_id):
        return self.switches[entity_id]

    def find_entity_id(self, domain, original_name):
        return getattr(self, "_resolved_entity", None)


def test_sync_config_switch_turns_off_switch_on_when_hub_enabled() -> None:
    """Hub config True with the firmware switch reporting "off" turns it on."""
    switch = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_auto_dimming": switch})
    device = HAUIDevice(app, {"name": "nspanel_haui", "use_auto_dimming": True})

    device._sync_config_switch("use_auto_dimming", "switch.nspanel_haui_use_auto_dimming")

    assert switch.state == "on"


def test_sync_config_switch_honors_an_explicit_value_override() -> None:
    """An explicit hub_value overrides the config value (used by the schedule)."""
    switch = _Switch("on")
    app = _SwitchApp({"switch.nspanel_haui_use_auto_dimming": switch})
    device = HAUIDevice(app, {"name": "nspanel_haui", "use_auto_dimming": True})

    device._sync_config_switch(
        "use_auto_dimming", "switch.nspanel_haui_use_auto_dimming", hub_value=False
    )

    assert switch.state == "off"


def test_behavior_sync_inside_schedule_window_forces_sleeping_on() -> None:
    """Inside the window the sleep schedule wins over a disabled auto-sleep toggle."""
    switch = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_auto_display_off": switch})
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "use_auto_display_off": False,
            "use_sleep_schedule": True,
            **_window_around_now(offset_before=3600, offset_after=3600),
        },
    )

    device._sync_behavior_config()

    assert switch.state == "on"


def test_behavior_sync_outside_schedule_window_forces_sleeping_off() -> None:
    """Outside the window the hub turns auto-sleep off even if the toggle says on."""
    switch = _Switch("on")
    app = _SwitchApp({"switch.nspanel_haui_use_auto_display_off": switch})
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "use_auto_display_off": True,
            "use_sleep_schedule": True,
            # A start == end window is never active on a wall clock: under the
            # window math it is a zero-length same-day window that no longer
            # contains the current minute.
            "sleep_schedule_start": _one_hour_from_now(),
            "sleep_schedule_end": _one_hour_from_now(),
        },
    )

    device._sync_behavior_config()

    assert switch.state == "off"


def test_behavior_sync_without_schedule_keeps_using_the_toggle() -> None:
    """With the schedule off, use_auto_display_off is synced from the config value."""
    switch = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_auto_display_off": switch})
    device = HAUIDevice(
        app,
        {"name": "nspanel_haui", "use_auto_display_off": True, "use_sleep_schedule": False},
    )

    device._sync_behavior_config()

    assert switch.state == "on"


def test_sync_button_interaction_turns_off_switch_on_when_enabled() -> None:
    """reset_interaction_on_button True with the switch "off" turns it on."""
    switch = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_button_interaction": switch})
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})

    device._sync_button_interaction()

    assert switch.state == "on"


class _Number:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state


def test_display_model_syncs_to_the_firmware_display_model_entity() -> None:
    """The firmware's \"Display Model\" number mirrors the hub's display_model."""
    number = _Number("0")
    app = _SwitchApp({"number.nspanel_haui_display_model": number})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert number.state == 1


def test_landscape_display_model_syncs_to_zero() -> None:
    """EU use the landscape gesture dimensions (0)."""
    number = _Number("1")
    app = _SwitchApp({"number.nspanel_haui_display_model": number})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "eu"})

    device._sync_display_model()

    assert number.state == 0


def test_display_model_sync_uses_the_registry_resolved_entity_id() -> None:
    """When the entity registry resolves a non-slug id (area-prefixed naming),
    the sync writes that entity instead of guessing ``number.{slug}_...``."""
    number = _Number("0")
    app = _SwitchApp({"number.goscinny_nspanel_goscinny_display_model": number})
    app._resolved_entity = "number.goscinny_nspanel_goscinny_display_model"
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert number.state == 1


def test_display_model_sync_falls_back_to_the_slug_id_without_a_resolver() -> None:
    """Clean installs without a registry resolver keep using number.<slug>_display_model."""
    number = _Number("0")
    app = _SwitchApp({"number.nspanel_haui_display_model": number})
    app.find_entity_id = None
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert number.state == 1


def test_display_model_sync_is_a_noop_when_no_entity_resolves() -> None:
    """Missing display_model entity (old firmware) must not raise."""
    app = _SwitchApp({})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert device is not None


def test_behavior_sync_uses_resolved_entity_ids_for_all_targets() -> None:
    """Every behavior value finds its entity through the registry."""

    class _Esp:
        def __init__(self, state=None):
            self.calls = []
            self.state = state

        def get_state(self):
            return self.state

        def turn_on(self):
            self.calls.append("on")
            self.state = "on"

        def turn_off(self):
            self.calls.append("off")
            self.state = "off"

        def set_state(self, state):
            self.calls.append(state)
            self.state = state

    items = {
        "switch.salon_nspanel_haui_use_auto_dimming": _Esp("on"),
        "switch.salon_nspanel_haui_use_auto_page": _Esp("on"),
        "switch.salon_nspanel_haui_use_auto_display_off": _Esp("on"),
        "number.salon_nspanel_haui_timeout_dimming": _Esp("10"),
        "number.salon_nspanel_haui_timeout_page": _Esp("30"),
        "number.salon_nspanel_haui_timeout_display_off": _Esp("120"),
        "number.salon_nspanel_haui_display_model": _Esp("0"),
    }
    app = _SwitchApp(items)
    app.device_slug = "nspanel_haui"

    def _resolve(domain, original_name):
        by_name = {
            "switch": {
                "Use Auto-Dimming": "switch.salon_nspanel_haui_use_auto_dimming",
                "Use Auto-Page": "switch.salon_nspanel_haui_use_auto_page",
                "Use Auto Display-Off": "switch.salon_nspanel_haui_use_auto_display_off",
            },
            "number": {
                "Timeout Dimming": "number.salon_nspanel_haui_timeout_dimming",
                "Timeout Page": "number.salon_nspanel_haui_timeout_page",
                "Timeout Display-Off": "number.salon_nspanel_haui_timeout_display_off",
                "Display Model": "number.salon_nspanel_haui_display_model",
            },
        }
        return by_name[domain].get(original_name)

    app.find_entity_id = _resolve
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "use_auto_dimming": True,
            "use_auto_page": False,
            "use_auto_display_off": True,
            "timeout_dimming": 25,
            "timeout_page": 40,
            "timeout_display_off": 90,
            "display_model": "us",
        },
    )

    device._sync_behavior_config()

    # Timeout numbers were all written; the auto-page switch was turned off.
    assert items["number.salon_nspanel_haui_timeout_dimming"].state == 25
    assert items["number.salon_nspanel_haui_timeout_page"].state == 40
    assert items["number.salon_nspanel_haui_timeout_display_off"].state == 90
    assert items["number.salon_nspanel_haui_display_model"].state == 1
    assert "off" in items["switch.salon_nspanel_haui_use_auto_page"].calls


def test_dimming_timeout_syncs_to_the_firmware_timeout_dimming_entity() -> None:
    """The firmware's "Timeout Dimming" number is number.<slug>_timeout_dimming."""
    number = _Number("10")
    app = _SwitchApp({"number.nspanel_haui_timeout_dimming": number})
    device = HAUIDevice(app, {"name": "nspanel_haui", "timeout_dimming": 25})

    device._sync_behavior_config()

    assert number.state == 25


def test_connect_pushes_the_device_settings_to_the_firmware() -> None:
    """A device that rebooted restores its own switch states; the hub re-applies its config."""
    relay = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_relay_left": relay})
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "use_relay_left": True, "sound_on_startup": False}
    )

    device.on_connection_changed(True)

    assert relay.state == "on"


def test_switching_the_display_model_installs_the_matching_tft() -> None:
    """A saved display_model change re-installs the TFT; the first sync and
    re-syncs with the same model do not (the version check cannot see the layout)."""
    installs: list = []
    app = _SwitchApp({})
    app.controller["update"] = type(
        "Update", (), {"install_tft": lambda self: installs.append(1)}
    )()
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "eu"})

    device.sync_config_to_device()
    assert installs == []

    device.config["display_model"] = "us"
    device.sync_config_to_device()
    device.sync_config_to_device()

    assert installs == [1]


def test_touch_start_native_event_calls_wakeup() -> None:
    """The native "1" touch_start triggers the wake decision."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = False

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))

    assert len(nav.exit_calls) == 1
    assert device._last_native_touch_ts > 0.0


def test_touch_start_poller_duplicate_ignored_within_window() -> None:
    """The poller "" duplicate of a native press is ignored."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = False

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, "1"))
    assert len(nav.exit_calls) == 1

    # Poller duplicate arrives immediately after the native event.
    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert len(nav.exit_calls) == 1


def test_touch_start_poller_fallback_when_native_lost() -> None:
    """The poller "" event acts as a wake fallback when the native event was lost."""
    device, nav = _wakeup_harness()
    device._first_touch_consumed = False
    # No native event for this press — the last one is outside the window.
    device._last_native_touch_ts = time.monotonic() - 2.0

    device.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))

    assert len(nav.exit_calls) == 1

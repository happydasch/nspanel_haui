import time
from datetime import datetime
from datetime import time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.device import DISPLAY_MODEL_OPTIONS, HAUIDevice
from custom_components.nspanel_haui.haui.mapping.const import ESPAction, ESPEvent


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
        self.page = None
        self._current_nav = None
        self._home_panel = None
        self._idle_panel_active = False
        self.prepare_resume_calls = 0

    @property
    def idle_panel_active(self):
        return self._idle_panel_active

    def prepare_resume(self):
        self.prepare_resume_calls += 1

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
        self.state_listeners = {}  # handle -> (callback, entity_id)

    def listen_state(self, cb, entity_id, **kwargs):
        handle = f"listen-{len(self.state_listeners)}"
        self.state_listeners[handle] = (cb, entity_id)
        return handle

    def cancel_listen_state(self, handle):
        self.state_listeners.pop(handle, None)

    def now(self):
        return datetime.now()

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
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})

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
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})
    device.set_device_info({"uptime": 5})
    device.on_connection_changed(True)
    assert "play_sound" in _publish_topics(app)
    assert ("play_sound", "startup") in app.controller["esphome"].esphome.publish_calls


def test_startup_sound_silent_on_reconnect_uptime():
    """A high uptime (Wi-Fi reconnect, device stayed up) stays silent."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})
    device.set_device_info({"uptime": 600})
    device.on_connection_changed(True)
    assert "play_sound" not in _publish_topics(app)


def test_startup_sound_plays_when_uptime_missing():
    """Firmware without an uptime value keeps the previous every-connect behavior."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})
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
    def __init__(self, state="off"):
        self.state = state
        self.calls = []

    def get_state(self):
        return self.state

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

    def find_entity_id(self, domain, original_name):
        relay_side = {"Relay Left": "left", "Relay Right": "right"}.get(original_name)
        if domain == "switch" and relay_side:
            candidate = f"switch.living_room_panel_relay_{relay_side}"
            return candidate if candidate in self.relays else None
        return None


def test_toggle_button_uses_registry_resolved_default_relay_entity() -> None:
    """Unconfigured button actions resolve the matching relay on this device."""
    left, right = _RelayItem(), _RelayItem()
    app = _RelayApp(
        {
            "switch.living_room_panel_relay_left": left,
            "switch.living_room_panel_relay_right": right,
        },
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


def test_default_relay_is_resolved_when_registry_becomes_available_later() -> None:
    relay = _RelayItem()
    app = _RelayApp({"switch.living_room_panel_relay_left": relay}, "nspanel_living")
    app.registry_ready = False
    original_resolve = app.find_entity_id
    app.find_entity_id = lambda domain, name: (
        original_resolve(domain, name) if app.registry_ready else None
    )
    device = HAUIDevice(
        app,
        {
            "name": "NSPanel-Living",
            "button_left_entity": "",
            "use_relay_left": False,
        },
    )

    device._register_callbacks()
    app.registry_ready = True
    device.toggle_left_button_state()

    assert relay.calls == ["toggle"]


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


@pytest.mark.parametrize(
    ("entity_id", "state", "service"),
    [
        ("scene.morning", "unknown", "turn_on"),
        ("script.bed", "off", "turn_on"),
        ("button.door", "unknown", "press"),
        ("light.hall", "off", "toggle"),
        ("lock.front", "locked", "unlock"),
        ("lock.front", "unlocked", "lock"),
        ("vacuum.room", "docked", "start"),
        ("input_select.mode", "a", "select_next"),
        ("climate.hall", "heat", "toggle"),
    ],
)
def test_button_entity_runs_the_action_its_domain_provides(entity_id, state, service) -> None:
    """An entity button runs the domain's own service, never a blanket toggle."""
    item = _RelayItem(state)
    app = _RelayApp({entity_id: item}, "nspanel_haui")
    device = HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "button_left_entity": entity_id,
            "use_relay_left": False,
        },
    )
    device._register_callbacks()

    device.toggle_left_button_state()

    assert item.calls == [service]


def test_relay_event_does_not_touch_display() -> None:
    """The device never mirrors relay state onto the display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.process_event(HAUIEvent(ESPEvent.RELAY_LEFT, "1"))

    assert app.service_calls == []


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
    """Default: firmware resets the timer on press; HAUI handles wake/navigation and toggles."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "0"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "0"))

    publishes = app.controller["esphome"].esphome.publish_calls
    # The firmware's Use Button Interaction switch owns timer resets; HAUI
    # only handles navigation and button actions here.
    assert (ESPAction.RESET_LAST_INTERACTION, "0") not in publishes
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


def test_reset_interaction_timer_publishes_a_firmware_reset():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.reset_interaction_timer()

    assert app.controller["esphome"].esphome.publish_calls == [
        (ESPAction.RESET_LAST_INTERACTION, "0")
    ]


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
    """Button press (value '1') immediately wakes the display."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "reset_interaction_on_button": True})
    calls = _spy_button_press(device)

    device.process_event(HAUIEvent(ESPEvent.BUTTON_LEFT, "1"))
    device.process_event(HAUIEvent(ESPEvent.BUTTON_RIGHT, "1"))

    publishes = app.controller["esphome"].esphome.publish_calls
    assert (ESPAction.RESET_LAST_INTERACTION, "0") not in publishes
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
    # ESPHome owns the timer reset; HAUI handles the wake and entity toggle.
    assert (ESPAction.RESET_LAST_INTERACTION, "0") not in publishes
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
        self.turn_on_calls = 0
        self.turn_off_calls = 0

    def get_state(self):
        return self.state

    def turn_on(self):
        self.turn_on_calls += 1
        self.state = "on"

    def turn_off(self):
        self.turn_off_calls += 1
        self.state = "off"


class _SwitchApp(DummyApp):
    def __init__(self, switches):
        super().__init__()
        self.switches = switches
        self._runtime_device_name = None
        self.device_slug = "nspanel_haui"
        self.logs = []

    def log(self, msg, *args, **kwargs):
        self.logs.append((msg, kwargs.get("level", "INFO")))

    def item_exists(self, entity_id):
        return entity_id in self.switches

    def get_item(self, entity_id):
        return self.switches[entity_id]

    def find_entity_id(self, domain, original_name):
        resolved = getattr(self, "_resolved_entity", None)
        if resolved:
            return resolved
        suffixes = {
            ("switch", "Use Button Interaction"): "use_button_interaction",
            ("switch", "Use Auto-Dimming"): "use_auto_dimming",
            ("switch", "Use Auto Display-Off"): "use_auto_display_off",
            ("switch", "Use Relay Left"): "use_relay_left",
            ("switch", "Use Relay Right"): "use_relay_right",
            ("switch", "Relay Left"): "relay_left",
            ("switch", "Relay Right"): "relay_right",
            ("select", "Display Model"): "display_model",
            ("number", "Timeout Dimming"): "timeout_dimming",
            ("number", "Timeout Display-Off"): "timeout_display_off",
            ("number", "Brightness Full"): "brightness_full",
            ("number", "Brightness Dimmed"): "brightness_dimmed",
        }
        suffix = suffixes.get((domain, original_name))
        entity_id = f"{domain}.{self.device_slug}_{suffix}" if suffix else None
        return entity_id if entity_id in self.switches else None


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


class _Select:
    def __init__(self, state):
        self.state = state
        self.calls = []

    def get_state(self):
        return self.state

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))
        self.state = kwargs.get("option", self.state)


def test_portrait_display_model_selects_the_portrait_gesture_size() -> None:
    """The firmware's "Display Model" select mirrors the hub's portrait model."""
    select = _Select("Landscape")
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert select.calls == [("select_option", {"option": "Portrait"})]


def test_landscape_display_model_selects_the_landscape_gesture_size() -> None:
    """EU panels use the landscape gesture dimensions."""
    select = _Select("Portrait")
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "eu"})

    device._sync_display_model()

    assert select.state == "Landscape"


def test_display_model_sync_uses_the_registry_resolved_entity_id() -> None:
    """When the entity registry resolves a non-slug id (area-prefixed naming),
    the sync writes that entity instead of guessing ``select.{slug}_...``."""
    select = _Select("Landscape")
    app = _SwitchApp({"select.goscinny_nspanel_goscinny_display_model": select})
    app._resolved_entity = "select.goscinny_nspanel_goscinny_display_model"
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert select.state == "Portrait"


def test_display_model_sync_does_not_guess_a_slug_id_without_a_resolver() -> None:
    """A missing registry match must not guess an ESPHome entity id."""
    select = _Select("Landscape")
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    app.find_entity_id = None
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert select.calls == []


def test_display_model_sync_is_a_noop_when_no_entity_resolves() -> None:
    """Missing display_model entity (old firmware) must not raise."""
    app = _SwitchApp({})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device._sync_display_model()

    assert device is not None


@pytest.mark.parametrize("state", ["unknown", "unavailable"])
def test_display_model_sync_skips_an_unresolved_firmware_state(state: str) -> None:
    """A display model the panel has not restored yet is not written.

    The device starts before its firmware published the select; "unknown" is a
    Home Assistant state, not an option, so the start-up sync leaves it alone.
    """
    select = _Select(state)
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device.sync_config_to_device()

    assert select.calls == []


def test_display_model_sync_writes_once_the_firmware_reports_a_value() -> None:
    """The sync after the panel reports its option applies the hub's orientation."""
    select = _Select("unknown")
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "us"})

    device.sync_config_to_device()
    assert select.calls == []

    select.state = "Landscape"
    device.sync_config_to_device()

    assert select.state == "Portrait"


def test_display_model_defaults_to_the_landscape_panel() -> None:
    """A device without the setting runs the landscape TFT, never an undefined model."""
    device = HAUIDevice(_SwitchApp({}), {"name": "nspanel_haui"})

    assert device.display_model == "eu"
    assert device.is_portrait is False


def test_the_firmware_select_offers_the_options_the_hub_writes() -> None:
    """The firmware's Display Model options are the strings the hub syncs to it."""
    path = Path(__file__).resolve().parent.parent / "esphome" / "nspanel_haui" / "select.yaml"
    selects = yaml.safe_load(path.read_text())["select"]
    model = next(select for select in selects if select.get("id") == "display_model")

    assert tuple(model["options"]) == DISPLAY_MODEL_OPTIONS


def test_the_firmware_display_model_is_written_for_a_device_without_the_setting() -> None:
    """A device whose store never set a model still tells the panel to be landscape."""
    select = _Select("Portrait")
    app = _SwitchApp({"select.nspanel_haui_display_model": select})
    device = HAUIDevice(app, {"name": "nspanel_haui"})

    device.sync_config_to_device()

    assert select.state == "Landscape"


def test_dimming_timeout_syncs_to_the_firmware_timeout_dimming_entity() -> None:
    """The firmware's "Timeout Dimming" number is number.<slug>_timeout_dimming."""
    number = _Number("10")
    app = _SwitchApp({"number.nspanel_haui_timeout_dimming": number})
    device = HAUIDevice(app, {"name": "nspanel_haui", "timeout_dimming": 25})

    device._sync_behavior_config()

    assert number.state == 25


@pytest.mark.parametrize("state", ["unknown", "unavailable"])
def test_timeout_dimming_sync_skips_an_unresolved_firmware_state(state: str) -> None:
    """The numeric sync waits for the panel's value instead of converting "unknown"."""
    number = _Number(state)
    app = _SwitchApp({"number.nspanel_haui_timeout_dimming": number})
    device = HAUIDevice(app, {"name": "nspanel_haui", "timeout_dimming": 25})

    device._sync_behavior_config()

    assert number.state == state


def test_connect_pushes_the_device_settings_to_the_firmware() -> None:
    """A device that rebooted restores its own switch states; the hub re-applies its config."""
    relay = _Switch("off")
    app = _SwitchApp({"switch.nspanel_haui_use_relay_left": relay})
    device = HAUIDevice(
        app, {"name": "nspanel_haui", "use_relay_left": True, "sound_on_startup": False}
    )

    device.on_connection_changed(True)

    assert relay.state == "on"


def test_connect_restarts_the_hub_inactivity_clock() -> None:
    """The restored page is displayed first; the idle timeout starts from the connect."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})

    device.on_connection_changed(True)

    assert app.controller["navigation"].prepare_resume_calls == 1


def test_switching_the_display_model_does_not_install_a_tft_unasked() -> None:
    """A saved display_model change leaves the TFT alone: the editor asks
    first, so the hub must not flash the display on the save alone."""
    installs: list = []
    app = _SwitchApp({})
    app.controller["update"] = type(
        "Update",
        (),
        {
            "start_async_tft_install": lambda self, version, url, on_complete: installs.append(
                (version, url)
            )
        },
    )()
    device = HAUIDevice(app, {"name": "nspanel_haui", "display_model": "eu"})

    device.sync_config_to_device()
    device.config["display_model"] = "us"
    device.sync_config_to_device()

    assert installs == []


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


# --- schedule ------------------------------------------------------------------

_SCHEDULE_IDS = {
    ("switch", "Use Auto Display-Off"): "switch.device_off",
    ("number", "Timeout Dimming"): "number.device_timeout_dim",
    ("number", "Timeout Display-Off"): "number.device_timeout_off",
    ("number", "Brightness Full"): "number.device_brightness_full",
    ("number", "Brightness Dimmed"): "number.device_brightness_dim",
    ("number", "Duration Dimming"): "number.device_duration_dim",
}


class _ScheduleApp(_SwitchApp):
    """A fixed clock and fixed sun times; timers are recorded, not fired."""

    def __init__(self, now: datetime) -> None:
        super().__init__(
            {
                "switch.device_off": _Switch("on"),
                "number.device_timeout_dim": _Number("10"),
                "number.device_timeout_off": _Number("120"),
                "number.device_brightness_full": _Number("50"),
                "number.device_brightness_dim": _Number("20"),
                "number.device_duration_dim": _Number("2"),
            }
        )
        self.current = now
        self.sun = {"sunrise": dt_time(7, 0), "sunset": dt_time(17, 0)}
        self.timers: list[tuple] = []
        self.cancelled: list[str] = []

    def find_entity_id(self, domain, original_name):
        return _SCHEDULE_IDS.get((domain, original_name))

    def now(self):
        return self.current

    def get_sun_time(self, event, day):
        point = self.sun[event]
        return datetime.combine(day, point) if point is not None else None

    def run_in(self, cb, delay, **kwargs):
        self.timers.append((cb, delay))
        return f"timer-{len(self.timers)}"

    def cancel_timer(self, handle):
        self.cancelled.append(handle)


def _entry(start: str, end: str, **settings) -> dict:
    return {
        "start": start,
        "end": end,
        "sound": True,
        "brightness": 20,
        "display_off": True,
        "timeout_display_off": 30,
        **settings,
    }


def _scheduled(app: _ScheduleApp, *entries: dict, **cfg) -> HAUIDevice:
    return HAUIDevice(
        app,
        {
            "name": "nspanel_haui",
            "brightness": 80,
            "brightness_dim": 20,
            "timeout_dimming": 10,
            "timeout_display_off": 120,
            "duration_dimming": 2,
            "use_auto_display_off": True,
            "schedule": list(entries),
            **cfg,
        },
    )


def test_active_schedule_entry_applies_its_brightness_and_screen_off() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    device = _scheduled(app, _entry("22:00", "06:00", brightness=5, display_off=False))

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_full"].state == 5
    assert app.switches["number.device_timeout_off"].state == 30
    assert app.switches["switch.device_off"].state == "off"
    # The entry sets no dimming values: the device settings stay.
    assert app.switches["number.device_timeout_dim"].state == "10"
    assert app.switches["number.device_brightness_dim"].state == "20"
    assert app.switches["number.device_duration_dim"].state == "2"


def test_an_entry_overrides_the_dimming_settings_it_sets() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    device = _scheduled(
        app,
        _entry(
            "22:00",
            "06:00",
            brightness=5,
            brightness_dim=2,
            timeout_dimming=5,
            duration_dimming=0.5,
        ),
    )

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_dim"].state == 2
    assert app.switches["number.device_timeout_dim"].state == 5
    assert app.switches["number.device_duration_dim"].state == 0.5


def test_outside_every_entry_the_device_settings_apply() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 12, 0))
    app.switches["switch.device_off"].state = "off"
    app.switches["number.device_timeout_off"].state = "30"
    app.switches["number.device_brightness_full"].state = "5"
    app.switches["number.device_brightness_dim"].state = "2"
    device = _scheduled(app, _entry("22:00", "06:00", brightness=5, display_off=False))

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_full"].state == 80
    assert app.switches["number.device_brightness_dim"].state == 20
    assert app.switches["number.device_timeout_off"].state == 120
    assert app.switches["switch.device_off"].state == "on"


def test_the_first_matching_schedule_entry_wins() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    device = _scheduled(
        app,
        _entry("22:00", "06:00", brightness=5),
        _entry("20:00", "23:30", brightness=40),
    )

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_full"].state == 5


def test_schedule_entries_follow_sunset_and_sunrise() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 18, 0))
    device = _scheduled(app, _entry("sunset", "sunrise", brightness=5))

    device._sync_behavior_config()
    assert app.switches["number.device_brightness_full"].state == 5

    app.current = datetime(2026, 1, 2, 7, 30)
    device._sync_behavior_config()
    assert app.switches["number.device_brightness_full"].state == 80


def test_schedule_entry_without_its_sun_event_is_inactive_and_logged() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 18, 0))
    app.sun["sunset"] = None
    device = _scheduled(app, _entry("sunset", "sunrise", brightness=5))

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_full"].state == 80
    assert any("No sunset" in msg and level == "WARNING" for msg, level in app.logs)


def test_without_a_schedule_brightness_and_the_display_off_switch_are_left_alone() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    app.switches["switch.device_off"].state = "off"
    device = _scheduled(app, brightness=None)

    device._sync_behavior_config()

    # No brightness setting: the value set on the panel stays.
    assert app.switches["number.device_brightness_full"].state == "50"
    # The switch belongs to its live state (automations may control it).
    assert app.switches["switch.device_off"].state == "off"
    assert app.switches["number.device_timeout_off"].state == "120"


def test_brightness_setting_is_synced_without_a_schedule() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    device = _scheduled(app, brightness=65)

    device._sync_behavior_config()

    assert app.switches["number.device_brightness_full"].state == 65


def test_schedule_timer_is_armed_for_the_next_boundary() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 21, 30))
    device = _scheduled(app, _entry("22:00", "06:00"), _entry("sunset", "23:00"))

    device._arm_schedule_timer()

    ((callback, delay),) = app.timers
    assert delay == 30 * 60
    assert callback == device._schedule_boundary_callback


def test_no_schedule_timer_without_entries() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 21, 30))
    device = _scheduled(app)

    device._arm_schedule_timer()

    assert app.timers == []


def test_schedule_boundary_applies_the_new_settings_and_rearms() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 21, 30))
    device = _scheduled(app, _entry("22:00", "06:00", brightness=5))
    device.sync_config_to_device()
    assert app.switches["number.device_brightness_full"].state == 80
    (callback, _delay) = app.timers[-1]

    app.current = datetime(2026, 1, 1, 22, 0)
    callback({})

    assert app.switches["number.device_brightness_full"].state == 5
    # Re-armed for the entry's end, eight hours later.
    assert app.timers[-1][1] == 8 * 3600


def test_schedule_timer_counts_real_time_across_a_clock_change() -> None:
    # Berlin's clocks go forward at 02:00 on 29 March 2026: 21:00 to 07:00 is nine hours.
    app = _ScheduleApp(datetime(2026, 3, 28, 21, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    device = _scheduled(app, _entry("07:00", "08:00"))

    device._arm_schedule_timer()

    assert app.timers[-1][1] == 9 * 3600


def test_without_any_sun_event_the_schedule_is_checked_again_a_day_later() -> None:
    """Polar night: the entry starts once the sun sets again, without a reconnect."""
    app = _ScheduleApp(datetime(2026, 1, 1, 12, 0))
    app.sun = {"sunrise": None, "sunset": None}
    device = _scheduled(app, _entry("sunset", "sunrise"))

    device._arm_schedule_timer()

    assert app.timers[-1][1] == 24 * 3600


class _LaggingSwitch(_Switch):
    """A switch whose write lands after the sync, as Home Assistant's service call does."""

    def __init__(self, state):
        super().__init__(state)
        self.pending = None

    def turn_on(self):
        self.turn_on_calls += 1
        self.pending = "on"

    def turn_off(self):
        self.turn_off_calls += 1
        self.pending = "off"

    def settle(self):
        if self.pending is not None:
            self.state, self.pending = self.pending, None


def test_a_saved_display_off_setting_leaves_the_active_entry_in_charge() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 23, 0))
    switch = _LaggingSwitch("off")
    app.switches["switch.device_off"] = switch
    device = _scheduled(app, _entry("22:00", "06:00", display_off=False))

    device.sync_config_to_device({"use_auto_display_off"})
    switch.settle()

    assert switch.state == "off"
    assert switch.turn_on_calls == 0


def test_a_saved_display_off_setting_applies_outside_every_entry() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 12, 0))
    app.switches["switch.device_off"].state = "on"
    device = _scheduled(app, _entry("22:00", "06:00"), use_auto_display_off=False)

    device.sync_config_to_device({"use_auto_display_off"})

    assert app.switches["switch.device_off"].state == "off"
    assert app.switches["switch.device_off"].turn_off_calls == 1


def test_stopping_the_device_cancels_the_schedule_timer() -> None:
    app = _ScheduleApp(datetime(2026, 1, 1, 21, 30))
    device = _scheduled(app, _entry("22:00", "06:00"))
    device._arm_schedule_timer()

    device.stop_part()

    assert app.cancelled == ["timer-1"]


def test_a_malformed_schedule_entry_raises_instead_of_being_skipped():
    """Saved settings are validated; an entry that slipped past must not be ignored."""
    app = DummyApp()
    device = HAUIDevice(app, {"schedule": [_entry("10pm", "07:00", sound=False)]})

    with pytest.raises(ValueError, match="10pm"):
        device.play_sound("notification")

    assert app.controller["esphome"].esphome.publish_calls == []


# --- time and date formats ----------------------------------------------------

_FORMATS = [
    ("time_format", "get_time_format", "%I:%M %p"),
    ("date_format", "get_date_format", "%m/%d/%Y"),
    ("date_format_locale", "get_date_format_locale", "short"),
]


def _format_device(device_cfg, hub_cfg):
    app = DummyApp()
    app.device_config = hub_cfg
    return HAUIDevice(app, device_cfg)


@pytest.mark.parametrize(("key", "getter", "value"), _FORMATS)
def test_a_format_the_device_leaves_empty_takes_the_hub_default(key, getter, value):
    device = _format_device({}, {key: value})

    assert getattr(device, getter)() == value


@pytest.mark.parametrize(("key", "getter", "value"), _FORMATS)
def test_a_format_set_on_the_device_overrides_the_hub_default(key, getter, value):
    device = _format_device({key: value}, {key: "hub default"})

    assert getattr(device, getter)() == value


def test_a_date_format_set_on_the_device_replaces_the_locale_date_layout():
    device = _format_device({"date_format": "%m/%d/%Y"}, {"date_format_locale": "full"})

    assert device.get_date_format_locale() == ""


def test_a_display_state_the_panel_never_reported_is_not_off():
    """Unknown is not "off": it stopped work that had barely started, and said so.

    Before the first handshake nothing knows whether the panel is lit, and every
    reader of this property answered "off" for it - so anything that stops on a dark
    display stopped before the device had said a word.
    """
    device = _format_device({}, {})

    assert device.display_state == ""
    assert device.display_visible is False, "not visible either - it is unknown"

    device.set_device_info({"display_state": "dim"})

    assert device.display_state == "dim"
    assert device.display_visible is True

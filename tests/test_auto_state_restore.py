"""Automatic firmware switch states are automation-owned outside explicit Settings edits."""

from datetime import datetime

from custom_components.nspanel_haui.haui.device import HAUIDevice

DIMMING = "switch.panel_use_auto_dimming"
DISPLAY_OFF = "switch.panel_use_auto_display_off"
SWITCH_IDS = {
    "Use Auto-Dimming": DIMMING,
    "Use Auto Display-Off": DISPLAY_OFF,
}


class _Switch:
    def __init__(self, state):
        self.state = state
        self.calls = []

    def get_state(self):
        return self.state

    def turn_on(self):
        self.calls.append("on")
        self.state = "on"

    def turn_off(self):
        self.calls.append("off")
        self.state = "off"


class _Navigation:
    page = None

    def set_idle_profile(self, is_night):
        pass

    def cancel_timeouts(self):
        pass

    def prepare_resume(self):
        pass

    def get_current_panel(self):
        return None

    def get_current_nav_panel(self):
        return None

    def open_home_panel(self):
        pass


class _App:
    device_slug = "panel"

    def __init__(self, dimming="on", display_off="on"):
        self.controller = {"navigation": _Navigation()}
        self.switches = {
            DIMMING: _Switch(dimming),
            DISPLAY_OFF: _Switch(display_off),
        }

    def find_entity_id(self, domain, original_name):
        return SWITCH_IDS.get(original_name) if domain == "switch" else None

    def item_exists(self, entity_id):
        return entity_id in self.switches

    def get_item(self, entity_id):
        return self.switches[entity_id]

    def now(self):
        return datetime.now()

    def run_in(self, callback, delay, **kwargs):
        return "timer"

    def cancel_timer(self, handle):
        pass

    def log(self, *args, **kwargs):
        pass


def _device(app, **config):
    device = HAUIDevice(app, {"name": "panel", **config})
    app.device = device
    device.sync_config_to_device()
    return device

    app = _App(dimming="off", display_off="on")
    device = _device(
        app,
        use_auto_dimming=True,
        use_auto_display_off=False,
        sound_on_startup=False,
        day_night_schedule_mode="off",
    )
    device.sync_config_to_device()
    device._initial_connect_done = True
    device.on_connection_changed(True)

    assert {entity: switch.state for entity, switch in app.switches.items()} == {
        DIMMING: "off",
        DISPLAY_OFF: "on",
    }
    assert all(not switch.calls for switch in app.switches.values())


def test_only_changed_settings_toggles_are_written():
    app = _App(dimming="on", display_off="on")
    device = _device(app, use_auto_dimming=True, use_auto_display_off=True)
    device.config["use_auto_display_off"] = False

    device.sync_config_to_device({"use_auto_display_off"})

    assert app.switches[DISPLAY_OFF].state == "off"
    assert app.switches[DISPLAY_OFF].calls == ["off"]
    assert app.switches[DIMMING].state == "on"
    assert app.switches[DIMMING].calls == []


def test_unrelated_config_reload_does_not_reapply_auto_switch_settings():
    app = _App(dimming="off", display_off="on")
    device = _device(app, use_auto_dimming=True, use_auto_display_off=False)
    device.config["use_relay_left"] = False
    device.sync_config_to_device(set())

    assert app.switches[DIMMING].state == "off"
    assert app.switches[DISPLAY_OFF].state == "on"
    assert all(not switch.calls for switch in app.switches.values())


def test_external_automation_state_survives_page_changes_and_state_reports():
    app = _App(dimming="on", display_off="off")
    device = _device(app, use_auto_dimming=False, use_auto_display_off=True)
    app.controller["navigation"].page = object()
    device.sync_config_to_device()
    app.controller["navigation"].page = None
    device.sync_config_to_device()

    assert app.switches[DIMMING].state == "on"
    assert app.switches[DISPLAY_OFF].state == "off"
    assert all(not switch.calls for switch in app.switches.values())


def test_settings_page_does_not_hold_or_write_automatic_switches():
    from custom_components.nspanel_haui.haui.page.settings import SettingsPage

    app = _App(dimming="on", display_off="off")
    device = _device(app)
    page = SettingsPage.__new__(SettingsPage)

    assert page.suspends_auto_page() is False
    device.sync_config_to_device()
    assert app.switches[DIMMING].state == "on"
    assert app.switches[DISPLAY_OFF].state == "off"
    assert all(not switch.calls for switch in app.switches.values())

"""The device settings own the firmware's auto switches; the page on screen can hold some off.

``HAUIDevice.apply_auto_switches`` gives Use Auto-Dimming and Use Auto
Display-Off their setting, or off while the page on screen holds them
(``HAUIPage.suspended_auto_switches``). It runs on every page change and
whenever one of the switches reports a new state. So a switch turned on
anywhere else goes straight back to its setting: a display-off switch left on
turned the display off although the setting was off. And a toggle that Home
Assistant reports late (a popup reopened right after it closed) still ends
with the right value. Automatic page switching has no firmware switch: the
hub owns it.
"""

from contextlib import nullcontext
from datetime import datetime

from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.page.notify import NotifyPage
from nspanel_haui.haui.page.qr import QRPage
from nspanel_haui.haui.page.settings import SettingsPage

DIMMING = "switch.panel_use_auto_dimming"
DISPLAY_OFF = "switch.panel_use_auto_display_off"
SWITCH_IDS = {
    "Use Auto-Dimming": DIMMING,
    "Use Auto Display-Off": DISPLAY_OFF,
}


class _Switch:
    """A switch whose new state Home Assistant reports only later (``_App.flush``)."""

    def __init__(self, app, entity_id, state):
        self.app = app
        self.entity_id = entity_id
        self.state = state
        self.calls = []

    def get_state(self):
        return self.state

    def turn_on(self):
        self.calls.append("on")
        self.app.pending.append((self.entity_id, "on"))

    def turn_off(self):
        self.calls.append("off")
        self.app.pending.append((self.entity_id, "off"))


class _Navigation:
    def __init__(self):
        self.page = None

    def set_idle_profile(self, is_night):
        pass


class _App:
    device_slug = "panel"

    def __init__(self, dimming="on", display_off="on", entity_ids=SWITCH_IDS):
        self.entity_ids = entity_ids
        self.controller = {"navigation": _Navigation()}
        self.pending = []
        self.listeners = {}
        states = dict(zip(entity_ids.values(), (dimming, display_off), strict=True))
        self.switches = {eid: _Switch(self, eid, state) for eid, state in states.items()}

    # what HAUIDevice uses of the app

    def find_entity_id(self, domain, original_name):
        return self.entity_ids.get(original_name) if domain == "switch" else None

    def item_exists(self, entity_id):
        return entity_id in self.switches

    def get_item(self, entity_id):
        return self.switches[entity_id]

    def listen_state(self, cb, entity_id, **kwargs):
        handle = f"listen-{len(self.listeners)}"
        self.listeners[handle] = (cb, entity_id)
        return handle

    def cancel_listen_state(self, handle):
        self.listeners.pop(handle, None)

    def now(self):
        return datetime.now()

    def run_in(self, cb, delay, **kwargs):
        return "timer"

    def cancel_timer(self, handle):
        pass

    def log(self, *args, **kwargs):
        pass

    # Home Assistant

    def report(self, entity_id, state):
        """A switch reports a new state, from the device or from anywhere else."""
        self.pending.append((entity_id, state))
        self.flush()

    def flush(self):
        """Report the queued states one by one, as Home Assistant's state events would."""
        for _ in range(50):
            if not self.pending:
                return
            entity_id, state = self.pending.pop(0)
            switch = self.switches[entity_id]
            old, switch.state = switch.state, state
            if old == state:
                continue
            for cb, listened in list(self.listeners.values()):
                if listened == entity_id:
                    cb(entity_id, "state", old, state, {})
        raise AssertionError("the auto switches never settle")

    def states(self):
        return {eid: switch.state for eid, switch in self.switches.items()}


def _device(app, **config):
    device = HAUIDevice(app, {"name": "panel", **config})
    app.device = device
    device.sync_config_to_device()
    app.flush()
    return device


def _show(app, page):
    """Navigation shows ``page`` (``None``: no page) and applies the auto switches."""
    app.controller["navigation"].page = page
    app.device.apply_auto_switches()
    app.flush()


def test_a_display_off_switch_turned_on_elsewhere_goes_back_off():
    """The reported bug: the display turned off although auto display-off was off."""
    app = _App(display_off="off")
    _device(app, use_auto_display_off=False)

    app.report(DISPLAY_OFF, "on")  # a restored value, a toggle in Home Assistant, ...

    assert app.states()[DISPLAY_OFF] == "off"


def test_connect_sets_every_switch_to_its_setting():
    app = _App(dimming="off", display_off="on")

    _device(app, use_auto_dimming=True, use_auto_display_off=False)

    assert app.states() == {DIMMING: "on", DISPLAY_OFF: "off"}


def test_an_unavailable_switch_gets_its_setting_once_it_reports():
    app = _App(display_off="unavailable")
    _device(app, use_auto_display_off=False)
    assert app.switches[DISPLAY_OFF].calls == []

    app.report(DISPLAY_OFF, "on")

    assert app.states()[DISPLAY_OFF] == "off"


def test_switches_follow_the_active_night_profile():
    now = datetime.now()
    app = _App()

    _device(
        app,
        use_auto_dimming=True,
        use_auto_display_off=True,
        night_use_auto_dimming=False,
        night_use_auto_display_off=True,
        day_night_schedule_mode="fixed",
        day_night_start=f"{(now.hour - 1) % 24:02d}:00",
        day_night_end=f"{(now.hour + 1) % 24:02d}:00",
    )

    assert app.states() == {DIMMING: "off", DISPLAY_OFF: "on"}


def test_the_sleep_schedule_owns_display_off():
    now = datetime.now()
    app = _App(display_off="off")

    _device(
        app,
        use_auto_display_off=False,
        use_sleep_schedule=True,
        sleep_schedule_start=f"{(now.hour - 1) % 24:02d}:00",
        sleep_schedule_end=f"{(now.hour + 1) % 24:02d}:00",
    )

    assert app.states()[DISPLAY_OFF] == "on"


def test_the_switches_are_found_by_name_after_a_device_rename():
    entity_ids = {
        "Use Auto-Dimming": "switch.area_panel_auto_dimming",
        "Use Auto Display-Off": "switch.area_panel_auto_display_off",
    }
    app = _App(dimming="off", display_off="on", entity_ids=entity_ids)

    _device(app, use_auto_display_off=False)

    assert app.states() == {
        "switch.area_panel_auto_dimming": "on",
        "switch.area_panel_auto_display_off": "off",
    }


# pages that hold switches off


def _notify_page(app):
    return NotifyPage(app, {"page_id": 4})


class _Panel:
    def get(self, key, default=None):
        return default


def test_a_popup_holds_its_switches_off_and_gives_them_back_when_it_closes():
    app = _App()
    _device(app)
    popup = _notify_page(app)
    popup._suspended_auto = ("auto_dimming", "auto_display_off")

    _show(app, popup)
    assert app.states() == {DIMMING: "off", DISPLAY_OFF: "off"}
    _show(app, None)

    assert app.states() == {DIMMING: "on", DISPLAY_OFF: "on"}


def test_a_popup_reopened_before_ha_reports_its_restore_still_restores_on_close():
    """The reload race: the next page shows before HA reported the previous change."""
    app = _App()
    _device(app)
    popup = _notify_page(app)
    popup._suspended_auto = ("auto_dimming",)
    _show(app, popup)

    app.controller["navigation"].page = None
    app.device.apply_auto_switches()  # the popup closes: "on" goes out ...
    app.controller["navigation"].page = popup
    app.device.apply_auto_switches()  # ... it reopens while HA still says "off"
    app.flush()
    assert app.states()[DIMMING] == "off"
    _show(app, None)

    assert app.states()[DIMMING] == "on"


def test_a_switch_turned_on_elsewhere_while_a_popup_holds_it_goes_back_off():
    app = _App()
    _device(app)
    popup = _notify_page(app)
    popup._suspended_auto = ("auto_dimming",)
    _show(app, popup)

    app.report(DIMMING, "on")

    assert app.states()[DIMMING] == "off"


def test_the_settings_page_holds_off_auto_dimming():
    app = _App()
    _device(app)

    _show(app, SettingsPage.__new__(SettingsPage))

    assert app.states() == {DIMMING: "off", DISPLAY_OFF: "on"}


def _qr_page(app):
    page = QRPage.__new__(QRPage)
    page.app = app
    page.prepare()
    page.panel = _Panel()
    page._rec_cmd_cm = lambda: nullcontext()
    page.log = lambda *args, **kwargs: None
    page._apply_zoom_state = lambda: None
    return page


def test_the_big_qr_code_holds_off_dimming_until_shrunk():
    app = _App()
    _device(app)
    qr = _qr_page(app)
    _show(app, qr)
    assert app.states() == {DIMMING: "on", DISPLAY_OFF: "on"}

    qr.callback_qr_code(None, None)
    app.flush()
    assert app.states() == {DIMMING: "off", DISPLAY_OFF: "on"}
    qr.callback_qr_code_big(None, None)
    app.flush()

    assert app.states() == {DIMMING: "on", DISPLAY_OFF: "on"}


def test_closing_the_qr_page_with_the_big_code_gives_the_switches_back():
    app = _App()
    _device(app)
    qr = _qr_page(app)
    _show(app, qr)
    qr.callback_qr_code(None, None)
    app.flush()

    _show(app, None)

    assert app.states() == {DIMMING: "on", DISPLAY_OFF: "on"}


def test_the_editor_preview_leaves_the_real_switches_alone():
    """The virtual app shares the settings but drives no firmware of its own."""
    from nspanel_haui.virtual_panel import VirtualDevice

    app = _App(display_off="on")
    device = VirtualDevice(app, {"name": "panel", "use_auto_display_off": False})
    app.device = device
    device.sync_config_to_device()
    _show(app, SettingsPage.__new__(SettingsPage))
    app.report(DISPLAY_OFF, "on")

    assert all(switch.calls == [] for switch in app.switches.values())
    assert app.listeners == {}

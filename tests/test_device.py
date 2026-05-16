from nspanel_haui.haui.device import HAUIDevice


class DummyPanel:
    def __init__(self, panel_id):
        self.id = panel_id


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


def test_set_device_info_and_connected():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": True})

    device.set_device_info({"foo": "bar"})
    assert device.device_info["foo"] == "bar"

    device.set_connected(True)
    assert device.connected is True
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
    device.set_connected(True)
    assert device._initial_connect_done is True
    assert nav.opened_calls[0] == ("sys_system", {})

    # Simulate: a nav panel is active (as if the user navigated to it)
    panel = DummyPanel("my-grid-panel")
    nav.panel = panel
    nav._current_nav = panel

    # Simulate: reconnect (set_connected called again with True)
    device.set_connected(True)
    # Should re-open the current nav panel with force=True
    assert nav.opened_calls[1] == (panel.id, {"force": True})


def test_reconnect_skips_popup_restores_nav():
    """When current panel is a popup (≠ nav panel), reconnect restores the
    nav panel instead, with force=True."""
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.set_connected(True)

    # Simulate: a nav panel exists, but current panel is a popup
    nav_panel = DummyPanel("grid-panel")
    popup = DummyPanel("popup_alarm")
    nav._current_nav = nav_panel
    nav.panel = popup

    # Reconnect - should skip popup, open nav panel instead
    device.set_connected(True)
    assert nav.opened_calls[1] == (nav_panel.id, {"force": True})


def test_reconnect_falls_back_to_nav_panel():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.set_connected(True)

    # No current panel, but a nav panel exists
    nav.panel = None
    nav._current_nav = DummyPanel("nav-panel")

    device.set_connected(True)
    assert nav.opened_calls[1] == (nav._current_nav.id, {"force": True})


def test_reconnect_falls_back_to_home_panel():
    app = DummyApp()
    device = HAUIDevice(app, {"name": "nspanel_haui", "sound_on_startup": False})
    nav = app.controller["navigation"]

    # First connect
    device.set_connected(True)

    # No panel, no nav panel, but a home panel
    nav.panel = None
    nav._current_nav = None
    nav._home_panel = DummyPanel("home-panel")

    device.set_connected(True)
    assert nav.opened_calls[1] == (nav._home_panel.id, {"autostart": False})

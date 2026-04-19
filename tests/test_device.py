from apps.nspanel_haui.haui.device import HAUIDevice


class DummyNavigation:
    def __init__(self):
        self.opened_panel = None

    def open_panel(self, panel):
        self.opened_panel = panel


class DummyApp:
    def __init__(self):
        self.controller = {"navigation": DummyNavigation()}
        self.service_calls = []

    def log(self, msg, *args, **kwargs):
        pass

    def call_service(self, service, **kwargs):
        self.service_calls.append((service, kwargs))

    def entity_exists(self, entity_id):
        return False

    def get_entity(self, entity_id):
        raise RuntimeError("Not implemented")


def test_set_device_info_and_connected():
    app = DummyApp()
    device = HAUIDevice(app, {})

    device.set_device_info({"foo": "bar"})
    assert device.device_info["foo"] == "bar"

    device.set_connected(True)
    assert device.connected is True
    assert app.service_calls[0][0] == "esphome/nspanel_haui_play_sound"
    assert app.controller["navigation"].opened_panel == "sys_system"

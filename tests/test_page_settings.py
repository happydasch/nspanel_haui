"""Settings page tests for ESPHome entity resolution."""

from contextlib import nullcontext

from nspanel_haui.haui.page.settings import SettingsPage


class _Item:
    def __init__(self, entity_id, state):
        self.entity_id = entity_id
        self.state = state
        self.calls = []

    def get_state(self):
        return self.state

    def listen_state(self, callback):
        return f"listen:{self.entity_id}"

    def turn_off(self):
        self.calls.append("off")

    def turn_on(self):
        self.calls.append("on")

    def set_state(self, state):
        self.state = state


class _App:
    def __init__(self, entities):
        self.entities = entities
        self.lookups = []

    def find_entity_id(self, domain, original_name):
        self.lookups.append((domain, original_name))
        item = self.entities.get(original_name)
        return item.entity_id if item is not None else None

    def get_item(self, entity_id):
        return next(item for item in self.entities.values() if item.entity_id == entity_id)

    def log(self, message, **kwargs):
        pass

    def cancel_listen_state(self, handle):
        pass


def _settings_page(entities):
    page = SettingsPage.__new__(SettingsPage)
    page.app = _App(entities)
    page.prepare()
    page._rec_cmd_cm = lambda: nullcontext()
    page.on_release = lambda *args, **kwargs: None
    page.bind_slider = lambda *args, **kwargs: None
    page.set_function_component = lambda *args, **kwargs: None
    page._auto_assign_fncs = lambda panel: None
    return page


def test_settings_resolves_brightness_and_auto_dimming_by_firmware_name():
    auto_dimming = _Item("switch.area_panel_auto_dimming", "on")
    full = _Item("number.area_panel_full", "60")
    dimmed = _Item("number.area_panel_dimmed", "20")
    page = _settings_page(
        {
            "Use Auto-Dimming": auto_dimming,
            "Brightness Full": full,
            "Brightness Dimmed": dimmed,
        }
    )

    page.start_panel(object())
    page.process_brightness_full(75)
    page.process_brightness_dim(15)

    assert page.app.lookups == [
        ("switch", "Use Auto-Dimming"),
        ("number", "Brightness Full"),
        ("number", "Brightness Dimmed"),
    ]
    assert auto_dimming.calls == ["off"]
    assert full.state == 75
    assert dimmed.state == 15


def test_settings_tolerates_missing_firmware_entities():
    page = _settings_page({})

    page.start_panel(object())
    page.process_brightness_full(75)
    page.process_brightness_dim(15)
    page._stop_panel(object())

    assert page.app.lookups == [
        ("switch", "Use Auto-Dimming"),
        ("number", "Brightness Full"),
        ("number", "Brightness Dimmed"),
    ]

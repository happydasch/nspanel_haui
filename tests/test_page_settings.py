"""Settings page tests for ESPHome entity resolution."""

from contextlib import nullcontext

from custom_components.nspanel_haui.haui.page.settings import SettingsPage


class _Item:
    def __init__(self, entity_id, state):
        self.entity_id = entity_id
        self.state = state

    def get_state(self):
        return self.state

    def listen_state(self, callback):
        return f"listen:{self.entity_id}"

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

    def item_exists(self, entity_id):
        return any(item.entity_id == entity_id for item in self.entities.values())

    def log(self, message, **kwargs):
        pass

    def cancel_listen_state(self, handle):
        pass


def _settings_page(entities):
    page = SettingsPage.__new__(SettingsPage)
    page.app = _App(entities)
    page.translate = lambda text: text
    page.prepare()
    page._rec_cmd_cm = lambda: nullcontext()
    page.on_release = lambda *args, **kwargs: None
    page.bind_slider = lambda *args, **kwargs: None
    page.set_function_component = lambda *args, **kwargs: None
    page._auto_assign_fncs = lambda panel: None
    return page


def test_settings_brightness_widgets_use_theme_colors():
    page = _settings_page({})
    colors = {"text": 1234, "component_active": 5678}
    updated = []
    page.get_color = lambda key: colors[key]
    page.set_component_text_color = lambda component, color: updated.append((component, color))
    page.set_title = lambda title: None
    page.set_component_text = lambda component, text: None

    class _Panel:
        def get_title(self, default):
            return default

    page.render_panel(_Panel())

    assert updated == [
        (page.COMPONENTS.t_brght_title, colors["text"]),
        (page.COMPONENTS.t_brght_pct, colors["text"]),
        (page.COMPONENTS.t_brght_dim_pct, colors["text"]),
        (page.COMPONENTS.t_brght_ico, colors["component_active"]),
        (page.COMPONENTS.t_brght_dim_ico, colors["component_active"]),
    ]


def test_settings_resolves_brightness_by_firmware_name():
    full = _Item("number.area_panel_full", "60")
    dimmed = _Item("number.area_panel_dimmed", "20")
    page = _settings_page({"Brightness Full": full, "Brightness Dimmed": dimmed})

    page.start_panel(object())
    page.process_brightness_full(75)
    page.process_brightness_dim(15)

    assert page.app.lookups == [("number", "Brightness Full"), ("number", "Brightness Dimmed")]
    assert full.state == 75
    assert dimmed.state == 15


def test_settings_tolerates_missing_firmware_entities():
    page = _settings_page({})

    page.start_panel(object())
    page.process_brightness_full(75)
    page.process_brightness_dim(15)
    page._stop_panel(object())

    assert page.app.lookups == [("number", "Brightness Full"), ("number", "Brightness Dimmed")]

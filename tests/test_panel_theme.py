"""Per-panel theme resolution and load-time display commands."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

import custom_components.nspanel_haui.haui.abstract.haui_page as page_module
from custom_components.nspanel_haui.haui.abstract.haui_page import HAUIPage
from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.color import (
    BUILTIN_THEMES,
    THEME_GLOBALS,
    ThemeLibrary,
)


def _app():
    custom = deepcopy(BUILTIN_THEMES["dark"])
    custom["name"] = "Custom"
    custom["colors"]["background"] = 1234
    domain, values = next(iter(custom["icons"]["dark"].items()))
    icon_key = next(iter(values))
    custom["icons"]["dark"][domain][icon_key] = 5678
    library = ThemeLibrary({**BUILTIN_THEMES, "custom": custom}, "dark")
    return SimpleNamespace(theme_library=library, theme=library.theme("dark")), domain, icon_key


def test_theme_library_caches_resolved_themes_and_rejects_unknown_ids():
    app, domain, icon_key = _app()
    selected = app.theme_library.theme("custom")

    assert selected is app.theme_library.theme("custom")
    assert selected.get("background") == 1234
    assert selected.get_icon_color(domain, icon_key) == 5678
    with pytest.raises(KeyError):
        app.theme_library.theme("missing")


def test_panel_theme_follows_device_or_uses_its_selected_palette():
    app, domain, icon_key = _app()
    default_panel = HAUIPanel(app, {"theme_id": ""})
    custom_panel = HAUIPanel(app, {"theme_id": "custom"})

    assert default_panel.theme is app.theme
    assert custom_panel.theme is app.theme_library.theme("custom")
    assert custom_panel.get_color("background") == 1234
    assert custom_panel.get_icon_color(domain, icon_key) == 5678


def test_page_load_commands_use_panel_theme_and_force_reload_on_theme_change():
    app, _, _ = _app()
    themed = HAUIPanel(app, {"theme_id": "custom"})
    default = HAUIPanel(app, {"theme_id": ""})
    page = HAUIPage.__new__(HAUIPage)

    commands = page.page_load_commands(themed)
    page._load_commands = commands

    assert f"{THEME_GLOBALS['background']}=1234" in commands
    assert not page.is_loaded_for(default)
    assert page.is_loaded_for(themed)


def test_page_item_factory_passes_the_current_panel_theme(monkeypatch):
    app, _, _ = _app()
    panel = HAUIPanel(app, {"theme_id": "custom"})
    page = HAUIPage.__new__(HAUIPage)
    page.app = app
    page.panel = panel

    class Item:
        def __init__(self, app, config, *, theme):
            self.theme = theme

    monkeypatch.setattr(page_module, "HAUIItem", Item)
    item = page._make_item({"item": "light.kitchen"})

    assert item.theme is panel.theme

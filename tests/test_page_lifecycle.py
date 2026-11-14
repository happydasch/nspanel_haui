"""HAUIPage base lifecycle: system colors and item popups."""

from __future__ import annotations

from typing import Any

from custom_components.nspanel_haui.haui.abstract.haui_page import HAUIPage
from custom_components.nspanel_haui.haui.mapping.color import (
    BUILTIN_THEMES,
    COLORS,
    THEME_GLOBALS,
    Theme,
)

OVERRIDE = 1234


def _theme(background: int = OVERRIDE) -> Theme:
    palette = BUILTIN_THEMES["dark"]
    return Theme(
        "dark",
        {
            **palette,
            "colors": {
                **palette["colors"],
                "background": background,
                "header_text": OVERRIDE,
            },
        },
        theme_id="custom",
    )


class _Device:
    def get(self, key: str, default: Any = None) -> Any:
        return {}.get(key, default)


class _DeviceConfig:
    def get_panels(self, nav: bool | None = None) -> list:
        return []


class _ESPHome:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Any]] = []

    def send_cmd(self, command: str, value: Any) -> None:
        self.sent.append((command, value))


class _App:
    def __init__(self) -> None:
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.esphome = _ESPHome()
        self.controller: dict[str, Any] = {"esphome": self.esphome}
        self.theme = _theme()

    def log(self, *a: Any, **k: Any) -> None:
        pass


class _Panel:
    id = "panel-1"

    theme = _theme()

    def get(self, key: str, default: Any = None) -> Any:
        return {"key": "p1"}.get(key, default)

    def get_type(self) -> str:
        return "test"


class _OwnPalettePage(HAUIPage):
    """Like about/clock/clocktwo/weather: own palette, start_panel without super()."""

    USE_SYSTEM_COLORS = False

    def page_load_commands(self, panel: Any) -> list[str]:
        return [*super().page_load_commands(panel), "own.background.val=1"]

    def start_panel(self, panel: Any) -> None:
        self.started_with = self.get_color("header_text")

    def render_panel(self, panel: Any) -> None:
        self.rendered_with = self.get_color("background")


class _SystemPalettePage(_OwnPalettePage):
    USE_SYSTEM_COLORS = True


def _sent_commands(app: _App) -> list[str]:
    cmds: list[str] = []
    for _command, value in app.esphome.sent:
        cmds.extend(value if isinstance(value, list) else [value])
    return cmds


def test_own_palette_page_ignores_selected_theme_without_calling_super() -> None:
    app = _App()
    page = _OwnPalettePage(app, {"page_id": 1})

    page.set_panel(_Panel())

    assert page.started_with == COLORS["header_text"]
    assert page.rendered_with == COLORS["background"]


def test_system_palette_page_uses_selected_theme() -> None:
    app = _App()
    page = _SystemPalettePage(app, {"page_id": 1})

    page.set_panel(_Panel())

    assert page.started_with == OVERRIDE
    assert page.rendered_with == OVERRIDE


class _OptionPanel(_Panel):
    def __init__(self, **options: Any) -> None:
        self._options = {"key": "p1", **options}

    def get(self, key: str, default: Any = None) -> Any:
        return self._options.get(key, default)


class _RememberingPage(HAUIPage):
    """Falls back to its own attribute for a missing option, as select and light do."""

    def prepare(self) -> None:
        self.mode = "default"

    def start_panel(self, panel: Any) -> None:
        self.mode_at_start = self.mode
        self.mode = panel.get("mode", self.mode)


def test_each_panel_starts_from_the_page_defaults() -> None:
    page = _RememberingPage(_App(), {"page_id": 1})

    page.set_panel(_OptionPanel(mode="set by the first panel"))
    page.set_panel(_OptionPanel())

    assert page.mode_at_start == "default"
    assert page.mode == "default"


def test_panel_render_does_not_repaint_the_page() -> None:
    """The page loads in the theme (its Preinitialize code), so a render never clears it."""
    app = _App()
    page = _SystemPalettePage(app, {"page_id": 1})

    page.set_panel(_Panel())

    assert [cmd for cmd in _sent_commands(app) if cmd.startswith("cls")] == []


def test_page_load_preparation_sends_the_device_theme_first() -> None:
    """Theme globals and page load commands precede goto_page.

    An own-palette page sends the selected theme for the next solid-colour page.
    """
    app = _App()
    page = _OwnPalettePage(app, {"page_id": 1})

    page.prepare_page_load(_Panel())

    theme = [
        f"{name}={OVERRIDE if key in ('background', 'header_text') else COLORS[key]}"
        for key, name in THEME_GLOBALS.items()
    ]
    assert _sent_commands(app) == [*theme, "own.background.val=1"]


def test_loaded_page_fits_only_a_panel_with_the_same_load_commands() -> None:
    """Navigation shows a panel on the loaded page only if the page loaded with its theme."""
    app = _App()
    page = _OwnPalettePage(app, {"page_id": 1})
    first_panel = _Panel()
    first_panel.theme = app.theme
    assert not page.is_loaded_for(first_panel)

    page.prepare_page_load(first_panel)
    assert page.is_loaded_for(first_panel)

    app.theme = _theme(OVERRIDE + 1)
    other_panel = _Panel()
    other_panel.theme = app.theme
    assert not page.is_loaded_for(other_panel)


# --- execute_item popups -----------------------------------------------------


class _Navigation:
    def __init__(self) -> None:
        self.opened: list[tuple[str, dict]] = []

    def open_panel(self, key: str, **kwargs: Any) -> None:
        self.opened.append((key, kwargs))


class _Item:
    def __init__(self, item: str, **cfg: Any) -> None:
        self._cfg = {"item": item, **cfg}
        self.executed = False

    def is_internal(self) -> bool:
        return False

    def get_item_type(self) -> str:
        return self._cfg["item"].split(".")[0] if "." in self._cfg["item"] else ""

    def get_item_state(self) -> str:
        return "disarmed"

    def get_item_id(self) -> str:
        return self._cfg["item"]

    def get_name(self) -> str:
        return self._cfg["item"]

    def get(self, key: str, default: Any = None) -> Any:
        return self._cfg.get(key, default)

    def get_config(self) -> dict:
        return dict(self._cfg)

    def execute(self) -> None:
        self.executed = True


def _executing_page() -> tuple[HAUIPage, _Navigation]:
    app = _App()
    nav = _Navigation()
    app.controller["navigation"] = nav
    return HAUIPage(app, {"page_id": 1}), nav


def test_alarm_item_opens_alarm_popup_with_its_entity() -> None:
    page, nav = _executing_page()
    item = _Item("alarm_control_panel.home")

    page.execute_item(item)

    assert [key for key, _ in nav.opened] == ["popup_alarm"]
    kwargs = nav.opened[0][1]
    assert kwargs["item"] == "alarm_control_panel.home"
    assert kwargs["item_id"] == "alarm_control_panel.home"
    assert not item.executed


def test_popup_key_opens_that_popup_for_any_item() -> None:
    """popup_timer has no entity domain; an item reaches it through popup_key."""
    page, nav = _executing_page()
    item = _Item("input_button.kitchen_timer", popup_key="popup_timer")

    page.execute_item(item)

    assert [key for key, _ in nav.opened] == ["popup_timer"]
    assert not item.executed


def test_empty_popup_key_uses_default_popup() -> None:
    """The editor stores an empty string after clearing the field to mean 'use the default'."""
    page, nav = _executing_page()

    page.execute_item(_Item("light.kitchen", popup_key=""))

    assert [key for key, _ in nav.opened] == ["popup_light"]


def test_item_without_popup_is_executed() -> None:
    page, nav = _executing_page()
    item = _Item("switch.fan")

    page.execute_item(item)

    assert nav.opened == []
    assert item.executed

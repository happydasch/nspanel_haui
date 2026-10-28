"""HAUIPage base lifecycle: system colors and item popups."""

from __future__ import annotations

from typing import Any

from nspanel_haui.haui.abstract.haui_page import HAUIPage
from nspanel_haui.haui.mapping.color import COLORS, ColorTheme

OVERRIDE = 1234


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
        self._color_theme = ColorTheme({"background": OVERRIDE, "header_text": OVERRIDE})

    def log(self, *a: Any, **k: Any) -> None:
        pass


class _Panel:
    id = "panel-1"

    def get(self, key: str, default: Any = None) -> Any:
        return {"key": "p1"}.get(key, default)

    def get_type(self) -> str:
        return "test"


class _OwnPalettePage(HAUIPage):
    """Like about/clock/clocktwo/weather: own palette, start_panel without super()."""

    USE_SYSTEM_COLORS = False

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


def test_own_palette_page_ignores_color_overrides_without_calling_super() -> None:
    app = _App()
    page = _OwnPalettePage(app, {"page_id": 1})

    page.set_panel(_Panel())

    assert page.started_with == COLORS["header_text"]
    assert page.rendered_with == COLORS["background"]
    assert f"cls {COLORS['background']}" in _sent_commands(app)


def test_system_palette_page_uses_color_overrides() -> None:
    app = _App()
    page = _SystemPalettePage(app, {"page_id": 1})

    page.set_panel(_Panel())

    assert page.started_with == OVERRIDE
    assert page.rendered_with == OVERRIDE
    assert f"cls {OVERRIDE}" in _sent_commands(app)


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
    """The editor stores "" after clearing the field; that means 'use the default'."""
    page, nav = _executing_page()

    page.execute_item(_Item("light.kitchen", popup_key=""))

    assert [key for key, _ in nav.opened] == ["popup_light"]


def test_item_without_popup_is_executed() -> None:
    page, nav = _executing_page()
    item = _Item("switch.fan")

    page.execute_item(item)

    assert nav.opened == []
    assert item.executed

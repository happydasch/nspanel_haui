"""Function button touch enable/disable via update_function_component."""

from __future__ import annotations

from custom_components.nspanel_haui.haui.abstract.component import Component
from custom_components.nspanel_haui.haui.abstract.mixins.function_btn_mixin import (
    FncType,
    FunctionButtonMixin,
)

BTN = Component(7, "bShuffle")


class RecordingPage(FunctionButtonMixin):
    def __init__(self) -> None:
        self._fnc_items = {}
        self._fnc_id_by_component = {}
        self.touch: list[tuple[str, bool]] = []
        self.colors: list[tuple[str, int]] = []
        self.color_map: dict[str, int] = {}

    def log(self, *a, **k) -> None:
        pass

    def get_color(self, key: str) -> int:
        return self.color_map.get(key, 0)

    def set_component_touch(self, component: Component, state: bool) -> None:
        self.touch.append((component.name, state))

    def set_component_value(self, *a) -> None:
        pass

    def set_component_text(self, *a) -> None:
        pass

    def set_component_text_color(self, component: Component, color: int) -> None:
        self.colors.append((component.name, color))

    def set_component_text_color_pressed(self, *a) -> None:
        pass

    def set_component_back_color(self, *a) -> None:
        pass

    def set_component_back_color_pressed(self, *a) -> None:
        pass

    def show_component(self, *a) -> None:
        pass

    def hide_component(self, *a) -> None:
        pass


def _page() -> RecordingPage:
    page = RecordingPage()
    page.set_function_component(BTN, BTN.name)
    return page


def test_touch_kwarg_disables_button() -> None:
    """Pages pass ``touch=`` to enable/disable a button."""
    page = _page()
    page.update_function_component(BTN.name, touch=False)
    assert page.touch == [("bShuffle", False)]


def test_notification_indicator_uses_header_accent_color() -> None:
    """The notification header button renders in the accent color."""
    page = _page()
    page.color_map = {"header_accent": 123, "header_text": 456}
    page.set_function_component(BTN, BTN.name, FncType.NAV_NOTIF)

    page.update_function_component(BTN.name)

    assert page.colors == [("bShuffle", 123)]


def test_other_header_buttons_keep_header_text_color() -> None:
    """Only the notification indicator defaults to the accent color."""
    page = _page()
    page.color_map = {"header_accent": 123, "header_text": 456}

    page.update_function_component(BTN.name)

    assert page.colors == [("bShuffle", 456)]

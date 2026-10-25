"""Function button touch enable/disable via update_function_component."""

from __future__ import annotations

from nspanel_haui.haui.abstract.component import Component
from nspanel_haui.haui.abstract.mixins.function_btn_mixin import FunctionButtonMixin

BTN = Component(7, "bShuffle")


class RecordingPage(FunctionButtonMixin):
    def __init__(self) -> None:
        self._fnc_items = {}
        self._fnc_id_by_component = {}
        self.touch: list[tuple[str, bool]] = []

    def log(self, *a, **k) -> None:
        pass

    def get_color(self, key: str) -> int:
        return 0

    def set_component_touch(self, component: Component, state: bool) -> None:
        self.touch.append((component.name, state))

    def set_component_value(self, *a) -> None:
        pass

    def set_component_text(self, *a) -> None:
        pass

    def set_component_text_color(self, *a) -> None:
        pass

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

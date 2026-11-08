"""Scheme-aware fixed icon color resolution for domain entities."""

from types import SimpleNamespace

import pytest
from nspanel_haui.haui.mapping.color import ColorTheme
from nspanel_haui.haui.utils.item import get_item_color


class _Item:
    def __init__(self, domain: str, state: str, scheme: str) -> None:
        self.app = SimpleNamespace(color_theme=ColorTheme({}, scheme))
        self._entity = SimpleNamespace(attributes={})
        self._domain = domain
        self._state = state

    def has_item(self) -> bool:
        return True

    def get_item(self) -> SimpleNamespace:
        return self._entity

    def get_item_type(self) -> str:
        return self._domain

    def get_item_state(self) -> str:
        return self._state

    def get_icon_color(self, domain: str, key: str, scheme: str | None = None) -> int | None:
        return self.app.color_theme.get_icon_color(domain, key, scheme)


@pytest.mark.parametrize(
    ("domain", "state", "light_color"),
    [
        ("weather", "sunny", 39840),
        ("climate", "heat", 47521),
        ("alarm_control_panel", "armed_home", 49477),
    ],
)
def test_domain_icon_colors_follow_light_scheme(domain: str, state: str, light_color: int) -> None:
    item = _Item(domain, state, "light")

    assert get_item_color(item, default_color=123) == light_color


def test_panel_background_hint_does_not_override_selected_color_scheme() -> None:
    item = _Item("weather", "sunny", "light")

    assert get_item_color(item, default_color=123, icon_scheme="dark") == 65504

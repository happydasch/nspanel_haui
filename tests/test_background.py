"""Background choices and their display picture mapping."""

from types import SimpleNamespace

from custom_components.nspanel_haui.haui.mapping.background import BACKGROUNDS
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.clock_common import (
    LIGHT_BACKGROUND_TEXT_COLOR,
    background_commands,
    light_background_selected,
    readable_background_text_color,
    readable_foreground_color,
)
from custom_components.nspanel_haui.haui.page.clocktwo import ClockTwoPage
from custom_components.nspanel_haui.haui.page.weather import WeatherPage


def test_light_background_is_available_on_each_picture_page() -> None:
    """Each page exposes Light and maps it to the shared TFT picture id."""
    assert BACKGROUNDS["light"] == 2
    expected_keys = ["scheme", *BACKGROUNDS]
    for page_cls in (ClockPage, WeatherPage, ClockTwoPage):
        option = next(
            option for option in page_cls.DESCRIPTOR.options if option.key == "background"
        )
        assert [key for key, _label in option.choices] == expected_keys
        assert option.choices[0] == ("scheme", "Use color scheme")
        page = SimpleNamespace(render_template=lambda value, *_args: value)
        panel = SimpleNamespace(
            get=lambda key, default=None: "light" if key == "background" else default
        )
        assert background_commands(page, panel) == ["system.vBackground.val=2"]
        assert light_background_selected(page, panel)


def test_theme_background_uses_solid_picture_not_layout_helper() -> None:
    from custom_components.nspanel_haui.haui.mapping.color import Theme

    for variant, picture_id in (("dark", 1), ("light", 2)):
        page = SimpleNamespace(
            app=SimpleNamespace(theme=Theme(variant)),
            render_template=lambda value, *_args: value,
        )
        panel = SimpleNamespace(
            get=lambda key, default=None: "scheme" if key == "background" else default
        )
        assert background_commands(page, panel) == [f"system.vBackground.val={picture_id}"]
        assert picture_id != 0


def test_light_background_uses_dark_foreground_for_contrast() -> None:
    assert readable_background_text_color("header_text", True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_background_text_color("component_text", True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_background_text_color("component_accent", True) is None
    assert readable_background_text_color("header_text", False) is None
    assert readable_foreground_color(65535, True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_foreground_color(62694, True) == 62694

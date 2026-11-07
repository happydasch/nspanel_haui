"""Background choices and their display picture mapping."""

from types import SimpleNamespace

from nspanel_haui.haui.mapping.background import BACKGROUNDS
from nspanel_haui.haui.page.clock import ClockPage
from nspanel_haui.haui.page.clock_common import (
    LIGHT_BACKGROUND_TEXT_COLOR,
    background_commands,
    light_background_selected,
    readable_background_text_color,
    readable_foreground_color,
)
from nspanel_haui.haui.page.clocktwo import ClockTwoPage
from nspanel_haui.haui.page.weather import WeatherPage


def test_light_background_is_available_on_each_picture_page() -> None:
    """Each page exposes Light and maps it to the shared TFT picture id."""
    assert BACKGROUNDS["light"] == 2
    for page_cls, page_name in (
        (ClockPage, "clock"),
        (WeatherPage, "weather"),
        (ClockTwoPage, "clocktwo"),
    ):
        option = next(
            option for option in page_cls.DESCRIPTOR.options if option.key == "background"
        )
        assert any(choice[0] == "light" for choice in option.choices)
        page = SimpleNamespace(render_template=lambda value, *_args: value)
        panel = SimpleNamespace(
            get=lambda key, default=None: "light" if key == "background" else default
        )
        assert background_commands(page, panel, page_name) == [f"{page_name}.background.val=2"]
        assert light_background_selected(page, panel)


def test_light_background_uses_dark_foreground_for_contrast() -> None:
    assert readable_background_text_color("header_text", True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_background_text_color("component_text", True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_background_text_color("component_accent", True) is None
    assert readable_background_text_color("header_text", False) is None
    assert readable_foreground_color(65535, True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_foreground_color(62694, True) == 62694

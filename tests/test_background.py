"""Background choices and the picture each one draws."""

from support.page_app import PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.background import BACKGROUNDS
from custom_components.nspanel_haui.haui.mapping.color import Theme
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.clock_common import (
    LIGHT_BACKGROUND_TEXT_COLOR,
    readable_foreground_color,
)
from custom_components.nspanel_haui.haui.page.clocktwo import ClockTwoPage
from custom_components.nspanel_haui.haui.page.weather import WeatherPage

PAGES = (ClockPage, WeatherPage, ClockTwoPage)


def _page(page_cls, app: PageApp, background: dict | None = None):
    panel = HAUIPanel(app, {"type": page_cls.DESCRIPTOR.type_key, **(background or {})})
    return page_cls(app, {"page_id": page_cls.DESCRIPTOR.page_id}), panel


def test_each_background_page_offers_the_pictures_the_tft_embeds() -> None:
    """The Background field names a picture of the display, the dark fill by default."""
    assert BACKGROUNDS["light"] == 2
    for page_cls in PAGES:
        option = next(
            option for option in page_cls.DESCRIPTOR.options if option.key == "background"
        )
        assert [key for key, _label in option.choices] == list(BACKGROUNDS)
        assert option.default == "dark"

        app = PageApp({})
        page, panel = _page(page_cls, app, {"background": "light"})
        page.prepare_page_load(panel)
        assert "system.vBackground.val=2" in app.cmds


def test_a_panel_without_a_background_choice_draws_the_dark_fill() -> None:
    """The default picture is a picture of its own: a light theme does not change it."""
    for page_cls in PAGES:
        app = PageApp({})
        app.theme = Theme("light")
        page, panel = _page(page_cls, app)
        page.prepare_page_load(panel)
        page.start_panel(panel)

        assert f"system.vBackground.val={BACKGROUNDS['dark']}" in app.cmds
        assert page.get_color("text") == Theme("dark").get("text")


def test_light_background_uses_dark_foreground_for_contrast() -> None:
    assert readable_foreground_color(65535, True) == LIGHT_BACKGROUND_TEXT_COLOR
    assert readable_foreground_color(62694, True) == 62694


def test_a_background_that_names_no_picture_falls_back_to_the_themes_fill() -> None:
    """An empty, unknown or removed Background value must still set a picture."""
    for page_cls in PAGES:
        for background in ("", "unknown", "{{ broken", "scheme", "theme"):
            app = PageApp({})
            app.theme = Theme("ocean")
            page, panel = _page(page_cls, app, {"background": background})

            commands = page.page_load_commands(panel)

            expected = BACKGROUNDS[app.theme.background_variant()]
            assert commands[0] == f"system.vBackground.val={expected}"


def test_clock_paints_its_entity_buttons_in_the_background_palette() -> None:
    """The HMI compiles the clock's item buttons dark; a light page must repaint them."""
    for background, variant in (("light", "light"), ("cat", "dark")):
        app = PageApp({})
        app.theme = Theme("light")
        page, panel = _page(ClockPage, app, {"background": background})

        page.start_panel(panel)

        palette = Theme(variant)
        assert f"bEntity1.bco={palette.get('component_background')}" in app.cmds
        assert f"bEntity1.bco2={palette.get('component_pressed')}" in app.cmds

"""Clocktwo (word clock) page."""

import datetime
from types import SimpleNamespace

from support.page_app import PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.background import BACKGROUNDS
from custom_components.nspanel_haui.haui.mapping.color import Theme
from custom_components.nspanel_haui.haui.page.clocktwo import ClockTwoPage
from custom_components.nspanel_haui.haui.utils.color import contrast_ratio


def _panel(app: PageApp, config: dict | None = None) -> HAUIPanel:
    return HAUIPanel(app, {"type": "clocktwo", **(config or {})})


def _page(app: PageApp) -> ClockTwoPage:
    return ClockTwoPage(app, {"page_id": ClockTwoPage.DESCRIPTOR.page_id})


def test_init_interface_draws_the_entire_word_clock_matrix():
    app = PageApp({})
    page = _page(app)
    panel = _panel(app)
    page.read_options(panel)

    page.init_interface(panel)

    assert len(app.cmds) == (110 + 4) * 2
    assert app.cmds[:2] == [f"l1.pco={app.theme.get('component_background')}", 'l1.txt="I"']


def test_intro_text_full_hour_default_matches_descriptor():
    """The editor shows the descriptor default for panels without the key."""
    (option,) = [o for o in ClockTwoPage.DESCRIPTOR.options if o.key == "show_intro_text_full_hour"]
    app = PageApp({})
    page = _page(app)
    page.read_options(_panel(app, {"show_intro_text": False}))

    words, _ = page.get_words_from_time(datetime.datetime(2026, 1, 1, 15, 0))

    assert ("it-is" in words) is option.default


def test_dark_display_keeps_the_word_clock_current():
    """The dark display is awake; see test_page_clock."""
    page = ClockTwoPage.__new__(ClockTwoPage)
    page._recording = False
    page._rec_cmd_depth = 0
    page._rec_cmd = []
    page.app = SimpleNamespace(device=SimpleNamespace(device_info={"display_state": "off"}))
    page.send_cmds = lambda commands: None
    updated = []
    page.update_interface = lambda: updated.append(True)

    page.callback_update_time({})

    assert updated == [True]


def test_background_setting_selects_the_pictures_contrast_palette() -> None:
    """The picture decides the page's colors; the selected theme does not."""
    app = PageApp({})
    app.theme = Theme("light")
    page = _page(app)
    panel = _panel(app, {"background": "dark"})
    page.read_options(panel)

    assert page.get_color("background") == Theme("dark").get("background")
    commands = page.page_load_commands(panel)
    assert commands[0] == "system.vBackground.val=1"
    assert "thmBg=65535" in commands[1:]


def test_background_is_sent_before_the_page_loads():
    """The page's Preinitialize code draws the background picture it reads."""
    app = PageApp({})
    page = _page(app)

    commands = page.page_load_commands(_panel(app))

    assert commands == ["system.vBackground.val=1", *app.theme.display_commands()]


def test_options_saved_for_the_shown_panel_apply_without_a_page_load():
    """A panel shown again on the loaded page reads its options anew."""
    app = PageApp({})
    page = _page(app)
    page.read_options(_panel(app, {"clock_language": "de", "off_color": 5}))
    page.read_options(_panel(app))

    assert page._clock_language == "en"
    assert page._off_color == app.theme.get("component_background")


def test_the_page_load_leaves_no_dot_on_the_compiled_picture() -> None:
    """The HMI's own loop skips the top-left dot; the hub sends its crop itself."""
    for background in ("dark", "light", "cat"):
        app = PageApp({})
        page = _page(app)

        page.start_panel(_panel(app, {"background": background}))

        assert f"s1.picc={BACKGROUNDS[background]}" in app.cmds


def test_a_light_page_keeps_the_unlit_letters_visible_but_quiet() -> None:
    """No light palette tone sits where a grid needs to: its card all but
    disappears on the page, and much above 2:1 competes with the lit words. The
    letters are mixed to the contrast target the dark page's own grid reads at."""
    app = PageApp({})
    app.theme = Theme("light")
    page = _page(app)

    page.read_options(_panel(app, {"background": "light"}))

    page_color = page.get_color("background")
    off_page = contrast_ratio(page._off_color, page_color)
    # A soft watermark: above the card tone's 1.16:1, well below the 2.3:1 that
    # started reading as a lit letter.
    assert 1.25 <= off_page <= 1.55, off_page
    assert contrast_ratio(page._off_color, page._letter_color) >= 8.0


def test_a_dark_page_keeps_its_quiet_card_tone() -> None:
    """The dark picture's card tone is already a step off the page."""
    app = PageApp({})
    page = _page(app)

    page.read_options(_panel(app, {"background": "dark"}))

    assert page._off_color == page.get_color("component_background")


def test_an_off_letter_color_the_user_set_wins_over_the_page_tone() -> None:
    app = PageApp({})
    app.theme = Theme("light")
    page = _page(app)

    page.read_options(_panel(app, {"background": "light", "off_color": 5}))

    assert page._off_color == 5

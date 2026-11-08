"""Clocktwo (word clock) page."""

import datetime
import threading
from types import SimpleNamespace

from custom_components.nspanel_haui.haui.mapping.color import ColorTheme
from custom_components.nspanel_haui.haui.page.clocktwo import ClockTwoPage


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)


def test_init_interface_batches_the_entire_word_clock_matrix():
    page = ClockTwoPage.__new__(ClockTwoPage)
    page._rec_cmd_lock = threading.RLock()
    page._recording = False
    page._rec_cmd_depth = 0
    page._rec_cmd = []
    page.app = SimpleNamespace(device={}, controller={}, log=lambda *a, **k: None)
    batches = []
    page.send_cmds = lambda commands: batches.append(commands)
    page._off_color = 8452
    page._clock_language = "en"

    page.init_interface(None)

    assert len(batches) == 1
    assert len(batches[0]) == (110 + 4) * 2
    assert page._letter_current_state == [False] * 110
    assert page._special_current_state == [False] * 4


def test_intro_text_full_hour_default_matches_descriptor():
    """The editor shows the descriptor default for panels without the key."""
    (option,) = [o for o in ClockTwoPage.DESCRIPTOR.options if o.key == "show_intro_text_full_hour"]
    page = ClockTwoPage.__new__(ClockTwoPage)
    page.get_color = lambda key: 0
    page.prepare()
    page.read_options(_Panel({"show_intro_text": False}))

    words, _ = page.get_words_from_time(datetime.datetime(2026, 1, 1, 15, 0))

    assert ("it-is" in words) is option.default


def test_dark_display_keeps_the_word_clock_current():
    """The dark display is awake; see test_page_clock."""
    page = ClockTwoPage.__new__(ClockTwoPage)
    page._rec_cmd_lock = threading.RLock()
    page._recording = False
    page._rec_cmd_depth = 0
    page._rec_cmd = []
    page.app = SimpleNamespace(device=SimpleNamespace(device_info={"display_state": "off"}))
    page.send_cmds = lambda commands: None
    updated = []
    page.update_interface = lambda: updated.append(True)

    page.callback_update_time({})

    assert updated == [True]


def test_background_setting_can_use_selected_color_scheme() -> None:
    page = ClockTwoPage.__new__(ClockTwoPage)
    page.app = SimpleNamespace(color_theme=ColorTheme({}, "light"))
    page._use_color_scheme = True
    page._background_variant = "light"
    page._light_background = True
    page.render_template = lambda value, _parse=False: value

    assert page.get_color("background") == page.app.color_theme.get("background")
    commands = page.page_load_commands(_Panel({"background": "scheme"}))
    assert commands[0] == "thmBg=65535"
    assert commands[0] == "thmBg=65535"
    assert commands[-1] == "system.vBackground.val=2"


def test_background_is_sent_before_the_page_loads():
    """The page's Preinitialize code draws the background picture it reads."""
    page = ClockTwoPage.__new__(ClockTwoPage)
    page.app = SimpleNamespace(color_theme=SimpleNamespace(display_commands=lambda: ["thmBg=1"]))
    page.render_template = lambda template, parse_icons=True: template

    assert page.page_load_commands(_Panel({})) == ["thmBg=1", "system.vBackground.val=1"]


def test_options_saved_for_the_shown_panel_apply_without_a_page_load():
    """A panel shown again on the loaded page reads its options anew."""
    page = ClockTwoPage.__new__(ClockTwoPage)
    page.get_color = lambda key: 0
    page.read_options(_Panel({"clock_language": "de", "off_color": 5}))
    page.read_options(_Panel({}))

    assert page._clock_language == "en"
    assert page._off_color == 0

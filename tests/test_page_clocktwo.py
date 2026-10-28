"""Clocktwo (word clock) page."""

import datetime
import threading
from types import SimpleNamespace

from nspanel_haui.haui.page.clocktwo import ClockTwoPage


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
    page.render_template = lambda template, parse_icons=True: template
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.prepare()
    page.create_panel(_Panel({"show_intro_text": False}))

    # create_panel() sends the background command before the page loads so the
    # Nextion's Preinitialize event picks up the correct background picture.
    assert "clocktwo.background.val=1" in page.cmds

    words, _ = page.get_words_from_time(datetime.datetime(2026, 1, 1, 15, 0))

    assert ("it-is" in words) is option.default

"""Clocktwo (word clock) page."""

import datetime

from nspanel_haui.haui.page.clocktwo import ClockTwoPage


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)


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

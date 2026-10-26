"""Notify popup: notification text size and paging."""

from nspanel_haui.haui.page.notify import NotifyPage


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_slug(self):
        return "test_slug"


class _App:
    device = _Device()
    controller: dict = {}

    def log(self, msg, **kwargs):
        pass

    def run_every(self, callback, delay, interval):
        return "mock_timer_handle"

    def cancel_timer(self, handle):
        pass


class _Panel:
    def get(self, key, default=None):
        return default

    def get_title(self, default=""):
        return default


def test_short_message_does_not_start_paging():
    page = NotifyPage(_App(), {"page_id": 4})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._icon = "mdi:information"
    page._notification = "Short message"
    page._btn_left = ""
    page._btn_right = ""
    page._text_size = "auto"
    page._notif_type = "info"

    page.render_panel(_Panel())

    assert "tText.font=3" in page.cmds
    assert page._page_handle is None


def test_long_message_starts_paging():
    page = NotifyPage(_App(), {"page_id": 4})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._icon = "mdi:information"
    # ~60 chars -> font size 2 -> max 48 chars per page -> 2 pages
    page._notification = "A" * 60
    page._btn_left = ""
    page._btn_right = ""
    page._text_size = "auto"
    page._notif_type = "info"

    page.render_panel(_Panel())

    assert "tText.font=2" in page.cmds
    assert page._page_handle == "mock_timer_handle"
    assert page._total_pages == 2


def test_stop_panel_cancels_timer():
    page = NotifyPage(_App(), {"page_id": 4})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._icon = "mdi:information"
    page._notification = "A" * 60
    page._btn_left = ""
    page._btn_right = ""
    page._text_size = "auto"
    page._notif_type = "info"
    page._saved_auto = {}

    page.render_panel(_Panel())
    assert page._page_handle == "mock_timer_handle"

    page._stop_panel(_Panel())
    assert page._page_handle is None


def test_advance_page_updates_text_and_title():
    page = NotifyPage(_App(), {"page_id": 4})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._icon = "mdi:information"
    page._notification = "A" * 60
    page._btn_left = ""
    page._btn_right = ""
    page._text_size = "auto"
    page._notif_type = "info"

    page.render_panel(_Panel())
    assert page._total_pages == 2

    page.cmds.clear()
    page._advance_page()

    commands = " ".join(page.cmds)
    assert 'tText.txt="' in commands
    assert "AAAAAAAAAAAAAAAA" in commands
    assert "tTitle.txt=" in commands
    assert "(2/2)" in commands

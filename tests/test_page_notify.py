"""Notify popup: notification text size and manual paging."""

from nspanel_haui.haui.page.notify import _FNC_NEXT_PAGE, NotifyPage


class _Device:
    def get(self, key, default=None):
        return {}.get(key, default)

    def get_slug(self):
        return "test_slug"


class _Item:
    def __init__(self):
        self.turned_off = 0
        self.turned_on = 0

    def get_state(self):
        return "off"

    def turn_off(self):
        self.turned_off += 1

    def turn_on(self):
        self.turned_on += 1


class _App:
    device = _Device()
    controller: dict = {}

    def __init__(self):
        self.items = {}

    def log(self, msg, **kwargs):
        pass

    def get_item(self, entity_id):
        return self.items.setdefault(entity_id, _Item())


class _Panel:
    def get(self, key, default=None):
        return default

    def get_title(self, default=""):
        return default

    def get_state(self, key, default=None):
        return default

    def set_state(self, key, value):
        pass

    def show_in_navigation(self):
        return False

    def can_show_popup(self):
        return True

    def show_home_button(self):
        return False

    def show_idle_button(self):
        return False

    def show_notifications_button(self):
        return False


def _build_page(notification: str, notif_type: str = "info") -> NotifyPage:
    page = NotifyPage(_App(), {"page_id": 4})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._icon = "mdi:information"
    page._notification = notification
    page._btn_left = ""
    page._btn_right = ""
    page._text_size = "auto"
    page._notif_type = notif_type
    page.set_function_component(
        page.COMPONENTS.fnc_left_sec,
        page.FNC_BTN_L_SEC,
        _FNC_NEXT_PAGE,
        icon="\ue900",
        color=0,
        visible=False,
    )
    return page


def test_short_message_does_not_show_next_page_button():
    page = _build_page("Short message")

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "tText.font=3" in commands
    assert "vis bFncLSec,0" in commands
    assert "vis bFncLSec,1" not in commands
    assert not hasattr(page, "_page_handle")


def test_long_message_shows_next_page_button_without_timer():
    page = _build_page("A" * 60)

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "tText.font=2" in commands
    assert page._total_pages == 2
    assert "vis bFncLSec,1" in commands
    assert not hasattr(page, "_page_handle")


def test_next_page_button_advances_manually():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    assert page._total_pages == 2

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_L_SEC, _FNC_NEXT_PAGE)

    commands = " ".join(page.cmds)
    assert "AAAAAAAAAAAAAAAA" in commands
    assert "tTitle.txt=" in commands
    assert "(2/2)" in commands
    # final page: button hidden again
    assert "vis bFncLSec,0" in commands


def test_next_page_button_does_not_advance_past_last_page():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    page.callback_function_component(page.FNC_BTN_L_SEC, _FNC_NEXT_PAGE)

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_L_SEC, _FNC_NEXT_PAGE)

    assert "tText.txt=" not in " ".join(page.cmds)


def test_stop_panel_restores_auto_state_without_timer():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    page._saved_auto = {"auto_dimming": True, "auto_page": True, "auto_display_off": True}
    closed = []
    page._close_callback_fnc = lambda: closed.append(True)

    page._stop_panel(_Panel())

    assert closed == [True]
    assert page.app.items["switch.test_slug_use_auto_page"].turned_on == 1
    assert page.app.items["switch.test_slug_use_auto_dimming"].turned_on == 1
    assert page.app.items["switch.test_slug_use_auto_display_off"].turned_on == 1


def test_critical_type_colours_icon_differently():
    page = _build_page("Short message", notif_type="critical")
    page.get_color = lambda key: {
        "component_text": 1,
        "header_accent": 2,
        "component_active": 3,
        "header_background": 4,
        "background": 5,
    }.get(key, 0)

    page.render_panel(_Panel())

    assert "tIcon.pco=3" in " ".join(page.cmds)

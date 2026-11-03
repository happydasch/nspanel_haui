"""Notify popup: notification text size and manual paging."""

from nspanel_haui.haui.page.notify import _FNC_NEXT_PAGE, NotifyPage


class _Device:
    def get(self, key, default=None):
        return {}.get(key, default)

    def get_slug(self):
        return "test_slug"


class _Item:
    def __init__(self, entity_id):
        self.entity_id = entity_id
        self.state = "on"
        self.turned_off = 0
        self.turned_on = 0

    def get_state(self):
        return self.state

    def turn_off(self):
        self.turned_off += 1
        self.state = "off"

    def turn_on(self):
        self.turned_on += 1
        self.state = "on"


class _App:
    device = _Device()
    controller: dict = {}

    def __init__(self):
        self.items = {}

    def log(self, msg, **kwargs):
        pass

    def find_entity_id(self, domain, original_name):
        names = {
            "Use Auto-Dimming": "switch.area_panel_use_auto_dimming",
            "Use Auto-Page": "switch.area_panel_use_auto_page",
            "Use Auto Display-Off": "switch.area_panel_use_auto_display_off",
        }
        return names.get(original_name) if domain == "switch" else None

    def item_exists(self, entity_id):
        return entity_id in {
            "switch.area_panel_use_auto_dimming",
            "switch.area_panel_use_auto_page",
            "switch.area_panel_use_auto_display_off",
        }

    def get_item(self, entity_id):
        return self.items.setdefault(entity_id, _Item(entity_id))


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
        page.COMPONENTS.fnc_right_sec,
        page.FNC_BTN_R_SEC,
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
    assert "vis bFncRSec,0" in commands
    assert "vis bFncRSec,1" not in commands
    assert not hasattr(page, "_page_handle")


def test_long_message_shows_next_page_button_without_timer():
    page = _build_page("A" * 60)

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "tText.font=2" in commands
    assert page._total_pages == 2
    assert "vis bFncRSec,1" in commands
    assert not hasattr(page, "_page_handle")


def test_next_page_button_advances_manually():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    assert page._total_pages == 2

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    commands = " ".join(page.cmds)
    assert "AAAAAAAAAAAAAAAA" in commands
    assert "tTitle.txt=" in commands
    assert "(2/2)" in commands
    # final page: button hidden again
    assert "vis bFncRSec,0" in commands


def test_next_page_button_does_not_advance_past_last_page():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    assert "tText.txt=" not in " ".join(page.cmds)


def test_stop_panel_restores_auto_state_without_timer():
    page = _build_page("A" * 60)
    page.render_panel(_Panel())
    page._saved_auto = page._save_auto_state()
    closed = []
    page._close_callback_fnc = lambda: closed.append(True)

    page._stop_panel(_Panel())

    assert closed == [True]
    assert page.app.items["switch.area_panel_use_auto_page"].turned_on == 1
    assert page.app.items["switch.area_panel_use_auto_dimming"].turned_on == 1
    assert page.app.items["switch.area_panel_use_auto_display_off"].turned_on == 1


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


def test_no_icon_hides_icon_component():
    page = _build_page("Short message")
    page._icon = ""

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "vis tIcon,0" in commands
    assert "tIcon.txt=" not in commands
    assert "tIcon.pco=" not in commands


def test_long_message_small_font_pages_correctly():
    # len >= 150 => font 1 (24px, most chars/line): 22 chars x 4 lines = 88/page.
    page = _build_page("A" * 200)

    page.render_panel(_Panel())

    assert "tText.font=1" in " ".join(page.cmds)
    assert page._total_pages == 3
    assert "vis bFncRSec,1" in " ".join(page.cmds)

"""Notify popup: notification text size and manual paging."""

import json
from pathlib import Path

from nspanel_haui.haui.page.notify import _FNC_NEXT_PAGE, _TEXT_BOXES, NotifyPage
from nspanel_haui.haui.utils.text import fit_text

LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"

# Fills two pages of the small font in every text box.
LONG = "The washing machine has finished. Please empty it soon. " * 4
# Fits one page at the medium font beside the icon, not at the large one.
MEDIUM = "The washing machine has finished. Please empty it before the clothes get wrinkled."
# Needs the small font beside the icon; the full width fits it at the medium font.
WIDE = (
    "The dishwasher has finished. Please open the door and let the dishes dry "
    "before you put them away in the cupboard."
)


class _Device:
    is_portrait = False

    def get(self, key, default=None):
        return {}.get(key, default)

    def get_slug(self):
        return "test_slug"


class _App:
    device = _Device()
    controller: dict = {}

    def log(self, msg, **kwargs):
        pass


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
    page = _build_page(LONG)

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "tText.font=1" in commands
    assert page._total_pages == 2
    assert "vis bFncRSec,1" in commands
    assert not hasattr(page, "_page_handle")


def test_next_page_button_advances_manually():
    page = _build_page(LONG)
    page.render_panel(_Panel())
    assert page._total_pages == 2

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    commands = " ".join(page.cmds)
    second_page = fit_text(LONG, 1, _TEXT_BOXES["landscape"]["tText"])[1]
    assert f'tText.txt="{second_page}"'.replace("\n", "\\r") in commands
    assert "tTitle.txt=" in commands
    assert "(2/2)" in commands
    # final page: button hidden again
    assert "vis bFncRSec,0" in commands


def test_next_page_button_does_not_advance_past_last_page():
    page = _build_page(LONG)
    page.render_panel(_Panel())
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    assert "tText.txt=" not in " ".join(page.cmds)


def test_stop_panel_runs_the_close_callback_and_releases_the_auto_switches():
    page = _build_page(LONG)
    page.start_panel(_Panel())
    page.render_panel(_Panel())
    closed = []
    page._close_callback_fnc = lambda: closed.append(True)

    page._stop_panel(_Panel())

    assert closed == [True]
    assert page.suspended_auto_switches() == ()


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


def test_auto_text_size_picks_the_largest_font_that_fits_one_page():
    box = _TEXT_BOXES["landscape"]["tText"]
    assert len(fit_text(MEDIUM, 3, box)) > 1
    page = _build_page(MEDIUM)

    page.render_panel(_Panel())

    assert "tText.font=2" in " ".join(page.cmds)
    assert page._total_pages == 1
    assert "vis bFncRSec,1" not in " ".join(page.cmds)


def test_fixed_text_size_is_paged_at_that_size():
    page = _build_page(MEDIUM)
    page._text_size = 3

    page.render_panel(_Panel())

    assert "tText.font=3" in " ".join(page.cmds)
    assert page._total_pages == len(fit_text(MEDIUM, 3, _TEXT_BOXES["landscape"]["tText"])) > 1


def test_text_boxes_match_the_hmi_layouts():
    """The fitting geometry must follow the HMIs (rerun gen_virtual_layout after changes)."""
    for orientation, boxes in _TEXT_BOXES.items():
        layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
        widgets = {c["name"]: c["attrs"] for c in layout["pages"]["4"]["components"]}
        for name, box in boxes.items():
            attrs = widgets[name]
            assert box == (attrs["w"], attrs["h"], attrs["borderw"], attrs["txt_maxl"]), name


class _QueuedPanel(_Panel):
    """A queued-notification popup: carries the controller's ``notif_id`` marker."""

    def get(self, key, default=None):
        return "abc" if key == "notif_id" else default


def test_queued_notification_popup_only_holds_off_the_page_switch():
    """The display keeps dimming and turning off: the popup must not keep it lit."""
    page = _build_page("Short message")

    page.start_panel(_QueuedPanel())

    assert page.suspended_auto_switches() == ("auto_page",)


def test_ad_hoc_popup_still_suspends_every_auto_switch():
    page = _build_page("Short message")

    page.start_panel(_Panel())

    assert sorted(page.suspended_auto_switches()) == [
        "auto_dimming",
        "auto_display_off",
        "auto_page",
    ]


def test_message_beside_an_icon_uses_the_narrow_text_box():
    page = _build_page("Short message")

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert 'tText.txt="Short' in commands
    assert "vis tText,1" in commands
    assert "vis tTextFull,0" in commands


def test_message_without_an_icon_uses_the_full_width():
    page = _build_page("Short message")
    page._icon = ""

    page.render_panel(_Panel())

    commands = " ".join(page.cmds)
    assert "tTextFull.font=3" in commands
    assert 'tTextFull.txt="Short message"' in commands
    assert "vis tTextFull,1" in commands
    assert "vis tText,0" in commands
    assert "tText.txt=" not in commands


def test_full_width_fits_a_larger_font():
    beside_icon = _build_page(WIDE)
    beside_icon.render_panel(_Panel())
    full_width = _build_page(WIDE)
    full_width._icon = ""
    full_width.render_panel(_Panel())

    assert "tText.font=1" in " ".join(beside_icon.cmds)
    assert "tTextFull.font=2" in " ".join(full_width.cmds)
    assert full_width._total_pages == 1


def test_full_width_pages_advance_in_the_full_width_box():
    page = _build_page(LONG)
    page._icon = ""
    page.render_panel(_Panel())
    assert page._total_pages == 2

    page.cmds.clear()
    page.callback_function_component(page.FNC_BTN_R_SEC, _FNC_NEXT_PAGE)

    commands = " ".join(page.cmds)
    assert 'tTextFull.txt="' in commands
    assert "tText.txt=" not in commands


def test_portrait_full_height_box_fits_a_larger_font():
    # Portrait stacks the icon above the text: without it the text box is taller.
    class _PortraitDevice(_Device):
        is_portrait = True

    beside_icon = _build_page(MEDIUM)
    beside_icon.app.device = _PortraitDevice()
    beside_icon.render_panel(_Panel())
    full_width = _build_page(MEDIUM)
    full_width.app.device = _PortraitDevice()
    full_width._icon = ""
    full_width.render_panel(_Panel())

    assert "tText.font=2" in " ".join(beside_icon.cmds)
    assert "tTextFull.font=3" in " ".join(full_width.cmds)

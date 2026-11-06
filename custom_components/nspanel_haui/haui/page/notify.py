from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import NotifType, PopupPanelKey
from ..mapping.descriptor import PageDescriptor, _
from ..mapping.icons import ICO_NEXT_PAGE
from ..utils.icon import parse_icon
from ..utils.text import TextBox, fit_text, parse_notification_text

_NOTIF_TYPE_COLORS: dict[str, str] = {
    NotifType.INFO: "component_text",
    NotifType.WARNING: "header_accent",
    NotifType.CRITICAL: "component_active",
}

# Custom function name for the manual next-page header button.
_FNC_NEXT_PAGE = "notif_next_page"

# The page's text widgets as the HMIs define them (w, h, borderw, txt_maxl);
# tests/test_page_notify.py checks them against the exported layouts.
_TEXT_BOXES: dict[str, dict[str, TextBox]] = {
    "landscape": {
        "tText": TextBox(284, 170, 2, 150),
        "tTextFull": TextBox(426, 170, 2, 200),
    },
    "portrait": {
        "tText": TextBox(296, 240, 2, 150),
        "tTextFull": TextBox(296, 335, 2, 200),
    },
}
# Fonts the automatic text size picks from, largest first: 48, 32 and 24 px.
_AUTO_FONTS = (3, 2, 1)


class CommonNotifyPage(HAUIPage):
    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        # Message text: tText beside the icon, tTextFull across the icon's
        # area when there is no icon.
        t_text_full=Component(8, "tTextFull"),
        t_text=Component(9, "tText"),
        t_icon=Component(10, "tIcon"),
        btn_left=Component(11, "bBtnLeft"),
        btn_right=Component(12, "bBtnRight"),
    )


class NotifyPage(CommonNotifyPage):
    DESCRIPTOR = PageDescriptor(
        type_key="notify",
        page_name="notify",
        page_id=4,
        label=_("Notification"),
        description=_("Pop-up notification panel with icon and optional buttons."),
        is_system=True,
        sys_panel_default={
            "key": PopupPanelKey.POPUP_NOTIFY,
            "show_in_navigation": False,
        },
        can_show_popup=True,
        icon="mdi:email-outline",
        preview_kwargs={"notification": _("Example notification: your message text appears here.")},
    )

    # panel

    def prepare(self) -> None:

        self._icon = ""
        self._text_box = self.COMPONENTS.t_text
        self._notification = ""
        self._title = ""
        self._chunks: list[str] = []
        self._current_page = 0
        self._total_pages = 0
        self._btn_left = ""
        self._btn_right = ""
        self._notif_type = NotifType.INFO
        self._button_callback_fnc = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        # A queued notification popup stays open until it is dismissed, so it
        # only holds off the automatic page switch.  Suspending dimming and
        # display-off as well kept the display lit until someone dismissed it,
        # and suspending display-off while the display is off wakes it.
        queued = bool(panel.get("notif_id", ""))
        self._saved_auto = self._save_auto_state(("auto_page",) if queued else None)

        self._notif_type = panel.get("notif_type", NotifType.INFO)
        self._icon = parse_icon(panel.get("icon", ""))
        self._notification = parse_notification_text(panel.get("notification", ""))
        self._btn_left = parse_icon(panel.get("btn_left", ""))
        self._btn_right = parse_icon(panel.get("btn_right", ""))
        self._text_size = panel.get("text_size", "auto")
        self._button_callback_fnc = panel.get("button_callback_fnc", None)
        self._close_callback_fnc = panel.get("close_callback_fnc", None)

        # set button callbacks
        self.on_release(
            {
                self.COMPONENTS.btn_left: self.callback_button,
                self.COMPONENTS.btn_right: self.callback_button,
            }
        )

        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )

        # The manual next-page button uses the inner-right header slot.  The
        # outer-right slot keeps NAV_CLOSE, which is the only dismissal for
        # buttonless notify popups (update notices, entity-unavailable, timer).
        # It is hidden until _start_paging finds more than one page of text.
        self.set_function_component(
            self.COMPONENTS.fnc_right_sec,
            self.FNC_BTN_R_SEC,
            _FNC_NEXT_PAGE,
            icon=ICO_NEXT_PAGE,
            color=self.get_color("header_accent"),
            visible=False,
        )

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        self._restore_auto_state(self._saved_auto)
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel) -> None:
        # Keep the configured title as the base; _start_paging appends the page counter.
        self._title = self.get("title", panel.get_title())
        self.set_component_text(self.COMPONENTS.title, self._title)

        if self._icon:
            icon_color_key = _NOTIF_TYPE_COLORS.get(self._notif_type, "component_text")
            icon_color = panel.get("icon_color", self.get_color(icon_color_key))
            self.set_component_text_color(self.COMPONENTS.t_icon, icon_color)
            self.set_component_text(self.COMPONENTS.t_icon, self._icon)
            self.show_component(self.COMPONENTS.t_icon)
            self._text_box = self.COMPONENTS.t_text
            self.hide_component(self.COMPONENTS.t_text_full)
        else:
            # No icon: hide its slot and give the text the full width.
            self.hide_component(self.COMPONENTS.t_icon)
            self._text_box = self.COMPONENTS.t_text_full
            self.hide_component(self.COMPONENTS.t_text)

        font_size, self._chunks = self._fit_text()
        self.send_cmd(f"{self._text_box.name}.font={font_size}")

        if self._btn_left:
            btn_left_color = panel.get("btn_left_color", self.get_color("component_text"))
            btn_left_back_color = panel.get("btn_left_back_color", self.get_color("background"))
            self.set_component_text_color(self.COMPONENTS.btn_left, btn_left_color)
            self.set_component_back_color(self.COMPONENTS.btn_left, btn_left_back_color)
            self.set_component_text(self.COMPONENTS.btn_left, self._btn_left)
            self.show_component(self.COMPONENTS.btn_left)

        if self._btn_right:
            btn_right_color = panel.get("btn_right_color", self.get_color("component_text"))
            btn_right_back_color = panel.get("btn_right_back_color", self.get_color("background"))
            self.set_component_text_color(self.COMPONENTS.btn_right, btn_right_color)
            self.set_component_back_color(self.COMPONENTS.btn_right, btn_right_back_color)
            self.set_component_text(self.COMPONENTS.btn_right, self._btn_right)
            self.show_component(self.COMPONENTS.btn_right)

        # Show the first page immediately; _start_paging appends the page
        # counter to the title when the text does not fit on one page, and
        # shows the manual next-page button while more pages remain.
        self._start_paging()

    def _fit_text(self) -> tuple[int, list[str]]:
        """Font size and pages of the notification text in the shown text widget.

        ``auto`` picks the largest font that shows the whole message on one
        page, else the smallest font, paged.  A fixed ``text_size`` is paged
        at that size.
        """
        portrait = hasattr(self.app, "device") and getattr(self.app.device, "is_portrait", False)
        box = _TEXT_BOXES["portrait" if portrait else "landscape"][self._text_box.name]
        if self._text_size != "auto":
            font = int(self._text_size)
            return font, fit_text(self._notification, font, box)
        for font in _AUTO_FONTS:
            pages = fit_text(self._notification, font, box)
            if len(pages) <= 1:
                break
        return font, pages

    # paging

    def _start_paging(self) -> None:
        """Show the first page of the fitted text (``_fit_text``).

        Paging is manual: the inner-right header button advances to the
        next page.  Long text never advances on its own and is never
        truncated — the final page stays visible until the popup closes.
        """
        self._total_pages = len(self._chunks)
        self._current_page = 0

        if self._total_pages > 1:
            self._set_page_text()
        else:
            self.set_component_text(
                self._text_box,
                self._chunks[0] if self._chunks else self._notification,
            )
        self.show_component(self._text_box)
        self._update_next_page_button()

    def _set_page_text(self) -> None:
        """Render the current page and its ``(page/total)`` title counter."""
        self.set_component_text(self._text_box, self._chunks[self._current_page])
        counter = f"({self._current_page + 1}/{self._total_pages})"
        self.set_component_text(
            self.COMPONENTS.title,
            f"{self._title} {counter}" if self._title else counter,
        )
        self._update_next_page_button()

    def _update_next_page_button(self) -> None:
        """Show the manual next-page button only while another page remains."""
        if self.FNC_BTN_R_SEC not in self._fnc_items:
            return
        self.update_function_component(
            self.FNC_BTN_R_SEC,
            visible=self._total_pages > 1 and self._current_page < self._total_pages - 1,
        )

    def _advance_page(self, _data: dict | None = None) -> None:
        """Advance to the next page of the notification text."""
        if not self._chunks or self._current_page >= self._total_pages - 1:
            return

        self._current_page += 1
        self._set_page_text()

    # callback

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        """Handle the manual next-page header button."""
        if fnc_name == _FNC_NEXT_PAGE:
            self._advance_page()

    def callback_button(self, event: HAUIEvent, component: Component) -> None:
        self.log(f"Got button press: {component}")
        if self._button_callback_fnc:
            btn_left = True if component == self.COMPONENTS.btn_left else False
            btn_right = True if component == self.COMPONENTS.btn_right else False
            self._button_callback_fnc(btn_left, btn_right)
        close_on_button = self.panel.get("close_on_button", True) if self.panel else True
        if close_on_button:
            self.log("Closing panel on button press")
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

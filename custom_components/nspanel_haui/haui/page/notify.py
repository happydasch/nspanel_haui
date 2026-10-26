from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, _
from ..mapping.icons import DEFAULT_NOTIF_ICON_FALLBACK, DEFAULT_NOTIF_ICONS
from ..utils.icon import parse_icon
from ..utils.text import chunk_text, parse_notification_text

_NOTIF_TYPE_COLORS = {
    "info": "component_text",
    "warning": "header_accent",
    "critical": "component_active",
}


class CommonNotifyPage(HAUIPage):
    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        # tTextFull is retained for layout compatibility; notifications now
        # always render beside the icon in tText, paging long text instead.
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
            "key": "popup_notify",
            "show_in_navigation": False,
        },
        can_show_popup=True,
        icon="mdi:email-outline",
    )

    # panel

    def prepare(self) -> None:

        self._icon = ""
        self._notification = ""
        self._title = ""
        self._chunks: list[str] = []
        self._current_page = 0
        self._total_pages = 0
        self._page_handle: str | None = None
        self._btn_left = ""
        self._btn_right = ""
        self._notif_type = "info"
        self._button_callback_fnc = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        self._saved_auto = self._save_auto_state()

        self._notif_type = panel.get("notif_type", "info")
        self._icon = parse_icon(panel.get("icon", ""))
        if not self._icon:
            fallback_icon = DEFAULT_NOTIF_ICONS.get(
                self._notif_type, DEFAULT_NOTIF_ICON_FALLBACK
            )
            self._icon = parse_icon(fallback_icon)
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

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # stop any paging timer
        if self._page_handle is not None:
            self.app.cancel_timer(self._page_handle)
            self._page_handle = None
        self._restore_auto_state(self._saved_auto)
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel) -> None:
        # Keep the configured title as the base; _start_paging appends the page counter.
        self._title = self.get("title", panel.get_title())
        self.set_component_text(self.COMPONENTS.title, self._title)

        # Always show an icon; start_panel falls back to the severity default.
        icon_color_key = _NOTIF_TYPE_COLORS.get(self._notif_type, "component_text")
        icon_color = panel.get("icon_color", self.get_color(icon_color_key))
        self.set_component_text_color(self.COMPONENTS.t_icon, icon_color)
        self.set_component_text(self.COMPONENTS.t_icon, self._icon)
        self.show_component(self.COMPONENTS.t_icon)

        font_size = self._calculate_text_display(self._notification)
        self.send_cmd(f"{self.COMPONENTS.t_text.name}.font={font_size}")

        if self._btn_left:
            btn_left_color = panel.get("btn_left_color", self.get_color("component_text"))
            btn_left_back_color = panel.get(
                "btn_left_back_color", self.get_color("background")
            )
            self.set_component_text_color(self.COMPONENTS.btn_left, btn_left_color)
            self.set_component_back_color(self.COMPONENTS.btn_left, btn_left_back_color)
            self.set_component_text(self.COMPONENTS.btn_left, self._btn_left)
            self.show_component(self.COMPONENTS.btn_left)

        if self._btn_right:
            btn_right_color = panel.get("btn_right_color", self.get_color("component_text"))
            btn_right_back_color = panel.get(
                "btn_right_back_color", self.get_color("background")
            )
            self.set_component_text_color(self.COMPONENTS.btn_right, btn_right_color)
            self.set_component_back_color(self.COMPONENTS.btn_right, btn_right_back_color)
            self.set_component_text(self.COMPONENTS.btn_right, self._btn_right)
            self.show_component(self.COMPONENTS.btn_right)

        # Show the first page immediately; _start_paging handles paging and
        # appends the page counter to the title when the text does not fit.
        self._start_paging(font_size)

    def _calculate_text_display(self, message: str) -> int:
        """Return the font size used for the notification text."""
        text_size = self._text_size
        if text_size == "auto":
            if len(message) < 50:
                return 3  # large
            if len(message) < 150:
                return 2  # medium
            return 1  # small
        return int(text_size)

    # paging

    def _start_paging(self, font_size: int) -> None:
        """Split the notification text into pages and start the pager."""
        if self._page_handle is not None:
            self.app.cancel_timer(self._page_handle)
            self._page_handle = None

        if font_size == 3:
            chars_per_line = 22
            lines = 2
        elif font_size == 2:
            chars_per_line = 16
            lines = 3
        else:
            chars_per_line = 11
            lines = 4

        if hasattr(self.app, "device") and getattr(self.app.device, "is_portrait", False):
            lines = int(lines * 1.5)

        self._chunks = chunk_text(self._notification, chars_per_line, lines)
        self._total_pages = len(self._chunks)
        self._current_page = 0

        if self._total_pages > 1:
            self._set_page_text()
            self._page_handle = self.app.run_every(self._advance_page, 0, 4.0)
        else:
            self.set_component_text(
                self.COMPONENTS.t_text,
                self._chunks[0] if self._chunks else self._notification,
            )
        self.show_component(self.COMPONENTS.t_text)

    def _set_page_text(self) -> None:
        """Render the current page and its ``(page/total)`` title counter."""
        self.set_component_text(self.COMPONENTS.t_text, self._chunks[self._current_page])
        counter = f"({self._current_page + 1}/{self._total_pages})"
        self.set_component_text(
            self.COMPONENTS.title,
            f"{self._title} {counter}" if self._title else counter,
        )

    def _advance_page(self, _data: dict | None = None) -> None:
        """Advance to the next page of the notification text."""
        if not self._chunks or self._current_page >= self._total_pages - 1:
            if self._page_handle is not None:
                self.app.cancel_timer(self._page_handle)
                self._page_handle = None
            return

        self._current_page += 1
        self._set_page_text()

    # callback

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

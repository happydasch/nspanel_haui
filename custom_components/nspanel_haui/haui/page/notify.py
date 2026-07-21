from __future__ import annotations

from typing import TYPE_CHECKING

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, _
from ..utils.icon import parse_icon
from ..utils.text import parse_notification_text

if TYPE_CHECKING:
    pass

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
        self._btn_left = ""
        self._btn_right = ""
        self._notif_type = "info"
        self._button_callback_fnc = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        self._saved_auto = self._save_auto_state()

        self._icon = parse_icon(panel.get("icon", ""))
        self._notification = parse_notification_text(panel.get("notification", ""))
        self._btn_left = parse_icon(panel.get("btn_left", ""))
        self._btn_right = parse_icon(panel.get("btn_right", ""))
        self._text_size = panel.get("text_size", "auto")
        self._notif_type = panel.get("notif_type", "info")
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
        self._restore_auto_state(self._saved_auto)
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel) -> None:
        title = self.get("title", panel.get_title())
        self.set_component_text(self.COMPONENTS.title, title)

        if self._icon:
            # Use severity-based icon color
            icon_color_key = _NOTIF_TYPE_COLORS.get(self._notif_type, "component_text")
            icon_color = panel.get("icon_color", self.get_color(icon_color_key))
            self.set_component_text_color(self.COMPONENTS.t_icon, icon_color)
            # Apply font size via _calculate_text_display
            _, _, font_size = self._calculate_text_display(self._notification, has_icon=True)
            self.send_cmd(f"font {self.COMPONENTS.t_text.name},{font_size}")
            self.set_component_text(self.COMPONENTS.t_icon, self._icon)
            self.set_component_text(self.COMPONENTS.t_text, self._notification)
            self.show_component(self.COMPONENTS.t_text)
            self.show_component(self.COMPONENTS.t_icon)
        else:
            _, _, font_size = self._calculate_text_display(self._notification, has_icon=False)
            self.send_cmd(f"font {self.COMPONENTS.t_text_full.name},{font_size}")
            self.set_component_text(self.COMPONENTS.t_text_full, self._notification)
            self.show_component(self.COMPONENTS.t_text_full)
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

    def _calculate_text_display(
        self, message: str, has_icon: bool
    ) -> tuple[Component, str, int]:
        """Calculate text display mode based on message length and icon presence.

        Returns:
            tuple: (text_component, text_content, font_size)
        """
        # Determine font size
        text_size = self._text_size
        if text_size == "auto":
            if len(message) < 50:
                font_size = 3  # large
            elif len(message) < 150:
                font_size = 2  # medium
            else:
                font_size = 1  # small
        else:
            font_size = text_size

        if has_icon:
            return self.COMPONENTS.t_text, message, font_size
        return self.COMPONENTS.t_text_full, message, font_size

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

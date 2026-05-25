from __future__ import annotations

from typing import TYPE_CHECKING

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import NotifEvent
from ..mapping.descriptor import PageDescriptor
from ..mapping.icons import ICO_NEXT_MESSAGE, ICO_PREV_MESSAGE
from ..utils.icon import parse_icon

if TYPE_CHECKING:
    pass


class CommonNotifyPage(HAUIPage):
    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        title=Component(2, "tTitle"),
        t_text_full=Component(7, "tTextFull"),
        t_text=Component(8, "tText"),
        t_icon=Component(9, "tIcon"),
        btn_left=Component(10, "bBtnLeft"),
        btn_right=Component(11, "bBtnRight"),
    )


class NotifyPage(CommonNotifyPage):
    DESCRIPTOR = PageDescriptor(
        type_key="notify",
        page_name="notify",
        label="Notification",
        description="Pop-up notification panel with icon and optional buttons.",
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
        self._button_callback_fnc = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        self._saved_auto = self._save_auto_state()

        self._icon = parse_icon(panel.get("icon", ""))
        self._notification = parse_icon(panel.get("notification", ""))
        self._btn_left = parse_icon(panel.get("btn_left", ""))
        self._btn_right = parse_icon(panel.get("btn_right", ""))
        self._button_callback_fnc = panel.get("button_callback_fnc", None)
        self._close_callback_fnc = panel.get("close_callback_fnc", None)

        # set button callbacks
        for btn in [self.COMPONENTS.btn_left, self.COMPONENTS.btn_right]:
            self.add_component_callback(btn, self.callback_button)

        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )

    def _stop_panel(self, panel: HAUIPanel) -> None:
        self._restore_auto_state(self._saved_auto)
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel) -> None:
        title = self.get("title", panel.get_title())
        self.set_component_text(self.COMPONENTS.title, title)

        if self._icon:
            icon_color = panel.get("icon_color")
            if icon_color:
                self.set_component_text_color(self.COMPONENTS.t_icon, icon_color)
            else:
                self.set_component_text_color(
                    self.COMPONENTS.t_icon, self.get_color("component_text")
                )
            self.set_component_text(self.COMPONENTS.t_icon, self._icon)
            self.set_component_text(self.COMPONENTS.t_text, self._notification)
            self.hide_component(self.COMPONENTS.t_text_full)
            self.show_component(self.COMPONENTS.t_text)
            self.show_component(self.COMPONENTS.t_icon)
        else:
            self.set_component_text(self.COMPONENTS.t_text_full, self._notification)
            self.hide_component(self.COMPONENTS.t_text)
            self.hide_component(self.COMPONENTS.t_icon)
            self.show_component(self.COMPONENTS.t_text_full)
        if self._btn_left:
            btn_left_color = panel.get("btn_left_color", self.get_color("component_text"))
            btn_left_back_color = panel.get("btn_left_back_color", self.get_color("background"))
            self.set_component_text_color(self.COMPONENTS.btn_left, btn_left_color)
            self.set_component_back_color(self.COMPONENTS.btn_left, btn_left_back_color)
            self.set_component_text(self.COMPONENTS.btn_left, self._btn_left)
            self.show_component(self.COMPONENTS.btn_left)
        else:
            self.hide_component(self.COMPONENTS.btn_left)
        if self._btn_right:
            btn_right_color = panel.get("btn_right_color", self.get_color("component_text"))
            btn_right_back_color = panel.get("btn_right_back_color", self.get_color("background"))
            self.set_component_text_color(self.COMPONENTS.btn_right, btn_right_color)
            self.set_component_back_color(self.COMPONENTS.btn_right, btn_right_back_color)
            self.set_component_text(self.COMPONENTS.btn_right, self._btn_right)
            self.show_component(self.COMPONENTS.btn_right)
        else:
            self.hide_component(self.COMPONENTS.btn_right)

    # callback

    def callback_button(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got button press: {component}-{button_state}")
        if self._button_callback_fnc:
            btn_left = True if component == self.COMPONENTS.btn_left else False
            btn_right = True if component == self.COMPONENTS.btn_right else False
            self._button_callback_fnc(btn_left, btn_right)
        close_on_button = self.panel.get("close_on_button", True) if self.panel else True
        if close_on_button:
            self.log("Closing panel on button press")
            navigation = self.app.controller["navigation"]
            navigation.close_panel()


class NotifsPage(CommonNotifyPage):
    DESCRIPTOR = PageDescriptor(
        type_key="notifs",
        page_name="notifs",
        label="Notifications",
        description="Notification list with prev/next navigation.",
        is_system=True,
        sys_panel_default={
            "key": "popup_notifs",
            "show_in_navigation": False,
        },
        can_show_popup=True,
        icon="mdi:email-multiple-outline",
    )

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        self._index = 0

        # set button callbacks
        for btn in [self.COMPONENTS.btn_left, self.COMPONENTS.btn_right]:
            self.add_component_callback(btn, self.callback_button)

        notifications = self.app.controller["notification"].get_notifications()
        count = len(notifications)
        prev_btn = {
            "fnc_component": self.COMPONENTS.fnc_left_sec,
            "fnc_name": "prev_notification",
            "fnc_args": {
                "icon": ICO_PREV_MESSAGE,
                "color": self.get_color("component_accent"),
                "visible": count > 1,
            },
        }
        next_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "next_notification",
            "fnc_args": {
                "icon": ICO_NEXT_MESSAGE,
                "color": self.get_color("component_accent"),
                "visible": count > 1,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            prev_btn,
            self.COMPONENTS.fnc_right_pri,
            next_btn,
        )

    def render_panel(self, panel: HAUIPanel) -> None:
        title = panel.get_title(self.translate("Notifications"))
        self.set_component_text(self.COMPONENTS.title, title)

        notifications = self.app.controller["notification"].get_notifications()
        if not notifications:
            self.set_component_text(self.COMPONENTS.t_text_full, self.translate("No notifications"))
            self.hide_component(self.COMPONENTS.t_text)
            self.hide_component(self.COMPONENTS.t_icon)
            self.show_component(self.COMPONENTS.t_text_full)
            self.hide_component(self.COMPONENTS.btn_left)
            self.hide_component(self.COMPONENTS.btn_right)
            return

        # clamp index
        self._index = max(0, min(self._index, len(notifications) - 1))
        notif = notifications[self._index]
        # notif tuple: (title, message, icon, timeout, persistent)
        notif_title, message, icon_name, _, persistent = notif
        icon = parse_icon(icon_name) if icon_name else ""

        # show per-notification title when available
        display_title = notif_title or title
        self.set_component_text(self.COMPONENTS.title, display_title)

        if icon:
            self.set_component_text_color(self.COMPONENTS.t_icon, self.get_color("component_text"))
            self.set_component_text(self.COMPONENTS.t_icon, icon)
            self.set_component_text(self.COMPONENTS.t_text, message)
            self.hide_component(self.COMPONENTS.t_text_full)
            self.show_component(self.COMPONENTS.t_text)
            self.show_component(self.COMPONENTS.t_icon)
        else:
            self.set_component_text(self.COMPONENTS.t_text_full, message)
            self.hide_component(self.COMPONENTS.t_text)
            self.hide_component(self.COMPONENTS.t_icon)
            self.show_component(self.COMPONENTS.t_text_full)

        # dismiss button - accent color signals persistent (sound loops until dismissed)
        dismiss_label = self.translate("Dismiss")
        btn_color = (
            self.get_color("component_accent") if persistent else self.get_color("component_text")
        )
        self.set_component_text_color(self.COMPONENTS.btn_right, btn_color)
        self.set_component_back_color(self.COMPONENTS.btn_right, self.get_color("background"))
        self.set_component_text(self.COMPONENTS.btn_right, dismiss_label)
        self.show_component(self.COMPONENTS.btn_right)
        self.hide_component(self.COMPONENTS.btn_left)

    # callback

    def callback_button(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got notification button press: {component}")
        if component == self.COMPONENTS.btn_right:
            # dismiss current notification
            notifications = self.app.controller["notification"].get_notifications()
            if notifications:
                self._index = max(0, min(self._index, len(notifications) - 1))
                self.app.controller["notification"].remove_notification(notifications[self._index])
                # close panel if no notifications remain
                if not self.app.controller["notification"].has_notifications():
                    self.app.controller["navigation"].close_panel()
                    return
                # clamp and re-render
                self._index = max(0, self._index - 1)
                self.refresh_panel()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        notifications = self.app.controller["notification"].get_notifications()
        count = len(notifications)
        if fnc_name == "prev_notification":
            self._index = (self._index - 1) % count if count else 0
            self.refresh_panel()
        elif fnc_name == "next_notification":
            self._index = (self._index + 1) % count if count else 0
            self.refresh_panel()

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        if event.name in (
            NotifEvent.NOTIF_ADD,
            NotifEvent.NOTIF_REMOVE,
            NotifEvent.NOTIF_CLEAR,
        ):
            if self.panel is not None:
                count = len(self.app.controller["notification"].get_notifications())
                with self.rec_cmd:
                    self.render_panel(self.panel)
                    self.update_function_component(self.FNC_BTN_L_SEC, visible=count > 1)
                    self.update_function_component(self.FNC_BTN_R_SEC, visible=count > 1)

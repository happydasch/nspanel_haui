from ..abstract.panel import HAUIPanel
from ..helper.icon import parse_icon
from ..mapping.color import COLORS
from ..mapping.const import NOTIF_EVENT
from . import HAUIPage


class CommonNotifyPage(HAUIPage):
    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # notification components
    TXT_TEXT_FULL, TXT_TEXT, TXT_ICON = (7, "tTextFull"), (8, "tText"), (9, "tIcon")
    # buttons
    BTN_LEFT, BTN_RIGHT = (10, "bBtnLeft"), (11, "bBtnRight")


class NotifyPage(CommonNotifyPage):
    # panel

    def start_page(self) -> None:
        self._icon = ""
        self._notification = ""
        self._btn_left = ""
        self._btn_right = ""
        self._button_callback_fnc = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        name = self.app.device.get_name()

        # auto components
        self.auto_dimming = self.app.get_entity(f"switch.{name}_use_auto_dimming")
        self.auto_page = self.app.get_entity(f"switch.{name}_use_auto_page")
        self.auto_sleeping = self.app.get_entity(f"switch.{name}_use_auto_sleeping")

        self._use_auto_dimming = self.auto_dimming.get_state()
        self._use_auto_page = self.auto_page.get_state()
        self._use_auto_sleeping = self.auto_sleeping.get_state()

        self.auto_dimming.turn_off()
        self.auto_page.turn_off()
        self.auto_sleeping.turn_off()

        self._icon = parse_icon(panel.get("icon", ""))
        self._notification = parse_icon(panel.get("notification", ""))
        self._btn_left = parse_icon(panel.get("btn_left", ""))
        self._btn_right = parse_icon(panel.get("btn_right", ""))
        self._button_callback_fnc = panel.get("button_callback_fnc")
        self._close_callback_fnc = panel.get("close_callback_fnc")

        # set button callbacks
        for btn in [self.BTN_LEFT, self.BTN_RIGHT]:
            self.add_component_callback(btn, self.callback_button)

        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )

    def stop_panel(self, panel: HAUIPanel) -> None:
        # restore previous auto values
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()
        if self._use_auto_page:
            self.auto_page.turn_on()
        if self._use_auto_sleeping:
            self.auto_sleeping.turn_on()
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel) -> None:
        title = self.get("title", panel.get_title())
        self.set_component_text(self.TXT_TITLE, title)

        if self._icon:
            icon_color = panel.get("icon_color")
            if icon_color:
                self.set_component_text_color(self.TXT_ICON, icon_color)
            else:
                self.set_component_text_color(self.TXT_ICON, COLORS["component"])
            self.set_component_text(self.TXT_ICON, self._icon)
            self.set_component_text(self.TXT_TEXT, self._notification)
            self.hide_component(self.TXT_TEXT_FULL)
            self.show_component(self.TXT_TEXT)
            self.show_component(self.TXT_ICON)
        else:
            self.set_component_text(self.TXT_TEXT_FULL, self._notification)
            self.hide_component(self.TXT_TEXT)
            self.hide_component(self.TXT_ICON)
            self.show_component(self.TXT_TEXT_FULL)
        if self._btn_left:
            btn_left_color = panel.get("btn_left_color", COLORS["component"])
            btn_left_back_color = panel.get("btn_left_back_color", COLORS["background"])
            self.set_component_text_color(self.BTN_LEFT, btn_left_color)
            self.set_component_back_color(self.BTN_LEFT, btn_left_back_color)
            self.set_component_text(self.BTN_LEFT, self._btn_left)
            self.show_component(self.BTN_LEFT)
        else:
            self.hide_component(self.BTN_LEFT)
        if self._btn_right:
            btn_right_color = panel.get("btn_right_color", COLORS["component"])
            btn_right_back_color = panel.get("btn_right_back_color", COLORS["background"])
            self.set_component_text_color(self.BTN_RIGHT, btn_right_color)
            self.set_component_back_color(self.BTN_RIGHT, btn_right_back_color)
            self.set_component_text(self.BTN_RIGHT, self._btn_right)
            self.show_component(self.BTN_RIGHT)
        else:
            self.hide_component(self.BTN_RIGHT)

    # callback

    def callback_button(self, event, component, button_state) -> None:
        if button_state:
            return
        self.log(f"Got button press: {component}-{button_state}")
        if self._button_callback_fnc:
            btn_left = True if component == self.BTN_LEFT else False
            btn_right = True if component == self.BTN_RIGHT else False
            self._button_callback_fnc(btn_left, btn_right)
        close_on_button = self.panel.get("close_on_button", True)
        if close_on_button:
            self.log("Closing panel on button press")
            navigation = self.app.controller["navigation"]
            navigation.close_panel()


class NotificationPage(CommonNotifyPage):
    # panel

    def start_page(self):
        self._index = 0

    def start_panel(self, panel: HAUIPanel) -> None:
        self._index = 0

        # set button callbacks
        for btn in [self.BTN_LEFT, self.BTN_RIGHT]:
            self.add_component_callback(btn, self.callback_button)

        notifications = self.app.controller["notification"].get_notifications()
        count = len(notifications)
        prev_btn = {
            "fnc_component": self.BTN_FNC_LEFT_SEC,
            "fnc_name": "prev_notification",
            "fnc_args": {
                "icon": self.ICO_PREV_MESSAGE,
                "color": COLORS["component_accent"],
                "visible": count > 1,
            },
        }
        next_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "next_notification",
            "fnc_args": {
                "icon": self.ICO_NEXT_MESSAGE,
                "color": COLORS["component_accent"],
                "visible": count > 1,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            prev_btn,
            self.BTN_FNC_RIGHT_PRI,
            next_btn,
        )

    def render_panel(self, panel: HAUIPanel) -> None:
        title = panel.get_title(self.translate("Notifications"))
        self.set_component_text(self.TXT_TITLE, title)

        notifications = self.app.controller["notification"].get_notifications()
        if not notifications:
            self.set_component_text(self.TXT_TEXT_FULL, self.translate("No notifications"))
            self.hide_component(self.TXT_TEXT)
            self.hide_component(self.TXT_ICON)
            self.show_component(self.TXT_TEXT_FULL)
            self.hide_component(self.BTN_LEFT)
            self.hide_component(self.BTN_RIGHT)
            return

        # clamp index
        self._index = max(0, min(self._index, len(notifications) - 1))
        notif = notifications[self._index]
        # notif tuple: (title, message, icon, timeout, persistent)
        notif_title, message, icon_name, _, persistent = notif
        icon = parse_icon(icon_name) if icon_name else ""

        # show per-notification title when available
        display_title = notif_title or title
        self.set_component_text(self.TXT_TITLE, display_title)

        if icon:
            self.set_component_text_color(self.TXT_ICON, COLORS["component"])
            self.set_component_text(self.TXT_ICON, icon)
            self.set_component_text(self.TXT_TEXT, message)
            self.hide_component(self.TXT_TEXT_FULL)
            self.show_component(self.TXT_TEXT)
            self.show_component(self.TXT_ICON)
        else:
            self.set_component_text(self.TXT_TEXT_FULL, message)
            self.hide_component(self.TXT_TEXT)
            self.hide_component(self.TXT_ICON)
            self.show_component(self.TXT_TEXT_FULL)

        # dismiss button — accent color signals persistent (sound loops until dismissed)
        dismiss_label = self.translate("Dismiss")
        btn_color = COLORS["component_accent"] if persistent else COLORS["component"]
        self.set_component_text_color(self.BTN_RIGHT, btn_color)
        self.set_component_back_color(self.BTN_RIGHT, COLORS["background"])
        self.set_component_text(self.BTN_RIGHT, dismiss_label)
        self.show_component(self.BTN_RIGHT)
        self.hide_component(self.BTN_LEFT)

    # callback

    def callback_button(self, event, component, button_state) -> None:
        if button_state:
            return
        self.log(f"Got notification button press: {component}")
        if component == self.BTN_RIGHT:
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

    def process_event(self, event) -> None:
        super().process_event(event)
        if event.name in (
            NOTIF_EVENT["notif_add"],
            NOTIF_EVENT["notif_remove"],
            NOTIF_EVENT["notif_clear"],
        ):
            if self.panel is not None:
                count = len(self.app.controller["notification"].get_notifications())
                with self.rec_cmd:
                    self.render_panel(self.panel)
                    self.update_function_component(self.FNC_BTN_L_SEC, visible=count > 1)
                    self.update_function_component(self.FNC_BTN_R_SEC, visible=count > 1)

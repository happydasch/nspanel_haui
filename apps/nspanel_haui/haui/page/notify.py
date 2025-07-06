from ..mapping.color import COLORS
from ..helper.icon import parse_icon
from ..abstract.panel import HAUIPanel

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

    _icon = ""
    _notification = ""
    _btn_left = ""
    _btn_right = ""
    _button_callback_fnc = None
    _close_callback_fnc = None

    # panel

    def start_panel(self, panel: HAUIPanel):
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

    def stop_panel(self, panel: HAUIPanel):
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

    def render_panel(self, panel: HAUIPanel):
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
            btn_right_back_color = panel.get(
                "btn_right_back_color", COLORS["background"]
            )
            self.set_component_text_color(self.BTN_RIGHT, btn_right_color)
            self.set_component_back_color(self.BTN_RIGHT, btn_right_back_color)
            self.set_component_text(self.BTN_RIGHT, self._btn_right)
            self.show_component(self.BTN_RIGHT)
        else:
            self.hide_component(self.BTN_RIGHT)

    # callback

    def callback_button(self, event, component, button_state):
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

    _icon = ""
    _notification = ""
    _btn_left = ""
    _btn_right = ""
    _button_callback_fnc = None
    _close_callback_fnc = None

    # panel

    def start_panel(self, panel: HAUIPanel):
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

    def stop_panel(self, panel: HAUIPanel):
        # notify about close
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel: HAUIPanel):
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
            btn_right_back_color = panel.get(
                "btn_right_back_color", COLORS["background"]
            )
            self.set_component_text_color(self.BTN_RIGHT, btn_right_color)
            self.set_component_back_color(self.BTN_RIGHT, btn_right_back_color)
            self.set_component_text(self.BTN_RIGHT, self._btn_right)
            self.show_component(self.BTN_RIGHT)
        else:
            self.hide_component(self.BTN_RIGHT)

    # callback

    def callback_button(self, event, component, button_state):
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

    _icon = ""
    _notification = ""
    _btn_left = ""
    _btn_right = ""
    _button_callback_fnc = None
    _close_callback_fnc = None

    # panel

    def start_panel(self, panel: HAUIPanel):
        # set button callbacks
        for btn in [self.BTN_LEFT, self.BTN_RIGHT]:
            self.add_component_callback(btn, self.callback_button)

        # set function buttons
        prev_btn = {
            "fnc_component": self.BTN_FNC_LEFT_SEC,
            "fnc_name": "prev_notifiction",
            "fnc_args": {
                "icon": self.ICO_PREV_MESSAGE,
                "color": COLORS["component_accent"],
                "visible": True,
            },
        }
        next_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "next_notifiction",
            "fnc_args": {
                "icon": self.ICO_NEXT_MESSAGE,
                "color": COLORS["component_accent"],
                "visible": True,
            },
        }

        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            prev_btn,
            self.BTN_FNC_RIGHT_PRI,
            next_btn,
        )

    def render_panel(self, panel: HAUIPanel):
        title = self.get("title", panel.get_title(self.translate("Notifications")))
        self.set_component_text(self.TXT_TITLE, title)

    # callback

    def callback_button(self, event, component, button_state):
        if button_state:
            return
        self.log(f"Got button press: {component}-{button_state}")

from ..helper.icon import parse_icon
from . import HAUIPage


class PopupNotifyPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')

    TXT_TEXT_FULL, TXT_TEXT, TXT_ICON = (6, 'tTextFull'), (7, 'tText'), (8, 'tIcon')
    BTN_LEFT, BTN_RIGHT = (9, 'bBtnLeft'), (10, 'bBtnRight')

    # page

    def start_page(self):
        # set light function button callbacks
        for btn in [self.BTN_LEFT, self.BTN_RIGHT]:
            self.add_component_callback(btn, self.callback_button)

    # panel

    def start_panel(self, panel):
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_close_nav_button(self.BTN_NAV_CLOSE)

        self._icon = parse_icon(panel.get('icon', ''))
        self._notification = parse_icon(panel.get('notification', ''))
        self._btn_left = parse_icon(panel.get('btn_left', ''))
        self._btn_right = parse_icon(panel.get('btn_right', ''))
        self._button_callback_fnc = panel.get('button_callback_fnc')
        self._close_callback_fnc = panel.get('close_callback_fnc')

        title = self.get('title', panel.get_title())
        self.set_component_text(self.TXT_TITLE, title)

    def close_panel(self, panel):
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def render_panel(self, panel):
        if self._icon:
            icon_color = panel.get('icon_color')
            if icon_color:
                self.set_component_text_color(self.TXT_ICON, icon_color)
            else:
                self.set_component_text_color(self.TXT_ICON, 65535)
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
            btn_left_color = panel.get('btn_left_color')
            if btn_left_color:
                self.set_component_text_color(self.BTN_LEFT, btn_left_color)
            else:
                self.set_component_text_color(self.BTN_LEFT, 19773)
            self.set_component_text(self.BTN_LEFT, self._btn_left)
            self.show_component(self.BTN_LEFT)
        else:
            self.hide_component(self.BTN_LEFT)
        if self._btn_right:
            btn_right_color = panel.get('btn_right_color')
            if btn_right_color:
                self.set_component_text_color(self.BTN_RIGHT, btn_right_color)
            else:
                self.set_component_text_color(self.BTN_RIGHT, 19773)
            self.set_component_text(self.BTN_RIGHT, self._btn_right)
            self.show_component(self.BTN_RIGHT)
        else:
            self.hide_component(self.BTN_RIGHT)

    # callback

    def callback_button(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got button press: {component}-{button_state}')
        navigation = self.app.controller['navigation']
        if self._button_callback_fnc:
            btn_left = True if component == self.BTN_LEFT else False
            btn_right = True if component == self.BTN_RIGHT else False
            self._button_callback_fnc(btn_left, btn_right)
        navigation.close_panel()
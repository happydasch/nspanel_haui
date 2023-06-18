from ..helper.icon import get_icon

from . import HAUIPage


class AlarmPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')
    #
    TXT_ICON = (7, 'tIcon')
    #
    BTN_KEY_1, BTN_KEY_2, BTN_KEY_3 = (8, 'bKey1'), (9, 'bKey2'), (10, 'bKey3')
    BTN_KEY_4, BTN_KEY_5, BTN_KEY_6 = (11, 'bKey4'), (12, 'bKey5'), (13, 'bKey6')
    BTN_KEY_7, BTN_KEY_8, BTN_KEY_9 = (14, 'bKey7'), (15, 'bKey8'), (16, 'bKey9')
    BTN_KEY_EMPTY, BTN_KEY_0, BTN_KEY_CLR = (17, 'bKeyEmpty'), (18, 'bKey0'), (19, 'bKeyClr')
    #
    B1_FNC, B2_FNC = (20, 'b1Fnc'), (21, 'b2Fnc')
    B3_FNC, B4_FNC = (22, 'b3Fnc'), (23, 'b4Fnc')

    # panel

    def start_panel(self, panel):
        self.set_prev_next_nav_buttons(self.BTN_NAV_LEFT, self.BTN_NAV_RIGHT)


class PopupUnlockPage(HAUIPage):

    # page

    def start_page(self):
        # add components
        for c in [
            AlarmPage.BTN_KEY_0, AlarmPage.BTN_KEY_1, AlarmPage.BTN_KEY_2,
            AlarmPage.BTN_KEY_3, AlarmPage.BTN_KEY_4, AlarmPage.BTN_KEY_5,
            AlarmPage.BTN_KEY_6, AlarmPage.BTN_KEY_7, AlarmPage.BTN_KEY_8,
            AlarmPage.BTN_KEY_9, AlarmPage.BTN_KEY_EMPTY, AlarmPage.BTN_KEY_CLR
        ]:
            self.add_component_callback(c, self.callback_keypad)
        self.add_component_callback(AlarmPage.B1_FNC, self.callback_unlock)

    # panel

    def start_panel(self, panel):
        self._input = ''
        self.set_button_state_buttons(AlarmPage.BTN_STATE_BTN_LEFT, AlarmPage.BTN_STATE_BTN_RIGHT)
        self.set_prev_next_nav_buttons(AlarmPage.BTN_NAV_LEFT, AlarmPage.BTN_NAV_RIGHT)
        # store panel infos
        self._title = panel.get('title', self.translate('Unlock Panel'))
        self._unlock_panel = panel.get('unlock_panel')
        if self._unlock_panel:
            self._title = self._unlock_panel.get_title(self._title)
            self._unlock_code = self._unlock_panel.get('unlock_code')

    def config_panel(self, panel):
        # if there is a unlock panel available, set nav buttons based on nav_panel
        if self._unlock_panel:
            panel._config['nav_panel'] = self._unlock_panel.get('nav_panel', False)
        super().config_panel(panel)
        panel._config['nav_panel'] = False

    def before_render_panel(self, panel):
        navigation = self.app.controller['navigation']
        if not self._unlock_panel:
            self.log('No unlock_panel provided')
            navigation.close_panel()
            return False
        if not self._unlock_code:
            self.log('No unlock_code provided')
            navigation.close_panel()
            return False
        return True

    def render_panel(self, panel):
        self.set_component_text(AlarmPage.TXT_TITLE, self._title)
        # set unlock function
        self.set_component_text(AlarmPage.B1_FNC, self.translate('Unlock'))
        self.show_component(AlarmPage.B1_FNC)
        # show icon
        self.set_component_text_color(AlarmPage.TXT_ICON, (255, 0, 0))
        self.set_component_text(AlarmPage.TXT_ICON, get_icon('lock'))
        self.show_component(AlarmPage.TXT_ICON)

    # callback

    def callback_keypad(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got keypad press: {component}-{button_state}')
        self.start_rec_cmd()
        # process keypad value
        if component[1].startswith('bKey'):
            bKeyVal = component[1][4:]
            if bKeyVal not in ['Empty', 'Clr']:
                self._input += str(bKeyVal)
            elif bKeyVal == 'Clr':
                self.set_component_text(AlarmPage.TXT_TITLE, '')
                self._input = ''
        # show either password stars or title
        if len(self._input):
            self.set_component_password(AlarmPage.TXT_TITLE, True)
            self.set_component_text(AlarmPage.TXT_TITLE, self._input)
        else:
            self.set_component_password(AlarmPage.TXT_TITLE, False)
            self.set_component_text(AlarmPage.TXT_TITLE, self._title)
        # check unlock code
        if str(self._input) == str(self._unlock_code):
            self.set_component_text_color(AlarmPage.TXT_ICON, (0, 255, 0))
            self.set_component_text(AlarmPage.TXT_ICON, get_icon('lock-open'))
        else:
            self.set_component_text_color(AlarmPage.TXT_ICON, (255, 0, 0))
            self.set_component_text(AlarmPage.TXT_ICON, get_icon('lock'))
        self.stop_rec_cmd(send_commands=True)

    def callback_unlock(self, event, component, button_state):
        if button_state:
            return
        if str(self._input) != str(self._unlock_code):
            return
        self.log(f'Got unlock press: {component}-{button_state}')
        # unlock panel and close this unlock popup
        self._unlock_panel._config['locked'] = False
        self.app.controller['navigation'].close_panel()

from ..mapping.color import COLORS

from . import HAUIPage


class AlarmPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')

    # keypad
    BTN_KEY_1, BTN_KEY_2, BTN_KEY_3 = (7, 'bKey1'), (8, 'bKey2'), (9, 'bKey3')
    BTN_KEY_4, BTN_KEY_5, BTN_KEY_6 = (10, 'bKey4'), (11, 'bKey5'), (12, 'bKey6')
    BTN_KEY_7, BTN_KEY_8, BTN_KEY_9 = (13, 'bKey7'), (14, 'bKey8'), (15, 'bKey9')
    BTN_KEY_CLR, BTN_KEY_0, BTN_KEY_DEL = (16, 'bKeyClr'), (17, 'bKey0'), (18, 'bKeyDel')

    # functions
    B1_FNC, B2_FNC, B3_FNC, B4_FNC = (19, 'b1Fnc'), (20, 'b2Fnc'), (21, 'b3Fnc'), (22, 'b4Fnc')

    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, self.BTN_FNC_RIGHT_SEC)
        self.set_function_components(self.BTN_FNC_RIGHT_SEC, self.FNC_BTN_R_SEC, 'armed_indicator')


class PopupUnlockPage(HAUIPage):

    # panel

    def start_panel(self, panel):
        # store panel infos
        self._input = ''
        self._unlock_panel = unlock_panel = panel.get('unlock_panel')
        self._title = panel.get('title', self.translate('Unlock Panel'))
        # lock right secondary function button
        lock_btn = {
            'fnc_component': AlarmPage.BTN_FNC_RIGHT_SEC,
            'fnc_id': AlarmPage.FNC_BTN_R_SEC,
            'fnc_name': 'unlock_indicator',
            'fnc_args': {
                'locked': True,
                'icon': self.ICO_LOCKED,
                'color': COLORS['component'],
                'back_color_pressed': COLORS['background']
            }
        }

        self.start_rec_cmd()

        # set function buttons
        self.set_function_buttons(
            AlarmPage.BTN_FNC_LEFT_PRI, AlarmPage.BTN_FNC_LEFT_SEC,
            AlarmPage.BTN_FNC_RIGHT_PRI, lock_btn)

        # set components
        for c in [
            AlarmPage.BTN_KEY_0, AlarmPage.BTN_KEY_1, AlarmPage.BTN_KEY_2,
            AlarmPage.BTN_KEY_3, AlarmPage.BTN_KEY_4, AlarmPage.BTN_KEY_5,
            AlarmPage.BTN_KEY_6, AlarmPage.BTN_KEY_7, AlarmPage.BTN_KEY_8,
            AlarmPage.BTN_KEY_9, AlarmPage.BTN_KEY_CLR, AlarmPage.BTN_KEY_DEL
        ]:
            self.add_component_callback(c, self.callback_keypad)
        self.add_component_callback(AlarmPage.B1_FNC, self.callback_unlock)
        self.set_function_component(
            component=AlarmPage.B1_FNC,
            fnc_id=AlarmPage.B1_FNC[1],
            fnc_name=AlarmPage.B1_FNC[1],
            color=COLORS['text_disabled'],
            text=self.translate('Unlock'),
            locked=getattr(panel, 'locked', False))

        # prepare unlock panel using config from locked panel
        if unlock_panel:
            config = panel.get_config(return_copy=False)
            config['mode'] = unlock_panel.get_mode()
            self._title = unlock_panel.get_title(self._title)
            self._unlock_code = unlock_panel.get('unlock_code')

        self.stop_rec_cmd(send_commands=True)

    def before_render_panel(self, panel):
        # check if unlock panel is available
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
        self.update_components()

    # misc

    def update_components(self):
        # show either password stars or title
        if len(self._input):
            passwd = f'{AlarmPage.ICO_PASSWORD}' * len(self._input)
            self.set_component_text(AlarmPage.TXT_TITLE, passwd)
        else:
            self.set_component_text(AlarmPage.TXT_TITLE, self._title)

        # update unlock indicator in header
        color = COLORS['component']
        if len(self._input) > 0:
            color = COLORS['component_accent']
        self.update_function_component(AlarmPage.FNC_BTN_R_SEC, color=color)

        # update unlock button
        unlock_btn_enabled = False
        if str(self._input) == str(self._unlock_code):
            unlock_btn_enabled = True
        if unlock_btn_enabled:
            self.update_function_component(
                fnc_id=AlarmPage.B1_FNC[1],
                touch_events=True,
                color=COLORS['component_active'],
                color_pressed=COLORS['component'],
                back_color=COLORS['background'],
                back_color_pressed=COLORS['component_pressed'])
        else:
            self.update_function_component(
                fnc_id=AlarmPage.B1_FNC[1],
                touch_events=False,
                color=COLORS['text_disabled'],
                color_pressed=COLORS['text_disabled'],
                back_color=COLORS['background'],
                back_color_pressed=COLORS['background'])

    # callback

    def callback_keypad(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got keypad press: {component}-{button_state}')
        self.start_rec_cmd()

        # process keypad value
        if component[1].startswith('bKey'):
            bKeyVal = component[1][4:]
            if bKeyVal not in ['Del', 'Clr']:
                self._input += str(bKeyVal)
            elif bKeyVal == 'Clr':
                self._input = ''
            elif bKeyVal == 'Del':
                self._input = self._input[:-1]

        self.update_components()

        self.stop_rec_cmd(send_commands=True)

    def callback_unlock(self, event, component, button_state):
        if button_state:
            return
        if str(self._input) != str(self._unlock_code):
            self.start_rec_cmd()
            self._input = ''
            self.update_components()
            self.stop_rec_cmd(send_commands=True)
            return
        # unlock panel and close this unlock popup
        self.log(f'Panel {self._unlock_panel.id} unlocked, closing unlock popup.')
        self._unlock_panel.locked = False
        self.app.controller['navigation'].close_panel()

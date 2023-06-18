from . import HAUIPage


class QRPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')
    # qr components
    QR_CODE_BIG = (7, 'qrCodeBig')
    QR_CODE = (8, 'qrCode')
    # q components
    Q1_ICON, Q1_TITLE, Q1_TEXT = (9, 'q1Icon'), (10, 'q1Title'), (11, 'q1Text')
    Q1_TEXT_ADD = (12, 'q1TextAdd')
    Q2_ICON, Q2_TITLE, Q2_TEXT = (13, 'q2Icon'), (14, 'q2Title'), (15, 'q2Text')
    Q2_TEXT_ADD = (16, 'q2TextAdd')

    # page

    def start_page(self):
        self.add_component_callback(self.QR_CODE, self.callback_qr_code)
        self.add_component_callback(self.QR_CODE_BIG, self.callback_qr_code_big)

        device_name = self.app.device.get_device_name()
        self.auto_dimming = self.app.get_entity(f'switch.{device_name}_use_auto_dimming')
        self._use_auto_dimming = self.auto_dimming.get_state()
        self.auto_page = self.app.get_entity(f'switch.{device_name}_use_auto_page')
        self._use_auto_page = self.auto_page.get_state()

    def stop_page(self):
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()
        if self._use_auto_page:
            self.auto_page.turn_on()

    # panel

    def start_panel(self, panel):
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_prev_next_nav_buttons(self.BTN_NAV_LEFT, self.BTN_NAV_RIGHT)

        self.start_rec_cmd()
        qr_code = panel.get('qr_code', '')
        entities = panel.get_entities()
        if len(entities) == 0:
            self.show_qr(big=True)
        else:
            self.show_qr(big=False)
        self.set_component_text(self.QR_CODE, qr_code)
        self.set_component_text(self.QR_CODE_BIG, qr_code)
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.stop_rec_cmd(send_commands=True)

    def render_panel(self, panel):
        entities = panel.get_entities()
        max_len = 16
        for i in range(2):
            if len(entities) <= i:
                break
            idx = i + 1
            entity = entities[i]
            q_icon = getattr(self, f'Q{idx}_ICON')
            q_title = getattr(self, f'Q{idx}_TITLE')
            q_text = getattr(self, f'Q{idx}_TEXT')
            q_text_add = getattr(self, f'Q{idx}_TEXT_ADD')
            self.set_component_text(q_icon, entity.get_icon())
            self.set_component_text(q_title, entity.get_name())
            value = entity.get_value()
            value_add = ''
            if len(value) > max_len:
                value_add = value[max_len - 1:]
                value = value[:max_len - 1]
            self.set_component_text(q_text, value)
            self.set_component_text(q_text_add, value_add)

    # misc

    def show_qr(self, big=False):
        if big:
            self.hide_component(self.QR_CODE)
        else:
            self.hide_component(self.QR_CODE_BIG)

        for component in [
            self.Q1_ICON, self.Q1_TITLE, self.Q1_TEXT, self.Q1_TEXT_ADD,
            self.Q2_ICON, self.Q2_TITLE, self.Q2_TEXT, self.Q2_TEXT_ADD,
        ]:
            if big:
                self.hide_component(component)
            else:
                self.show_component(component)

        if big:
            self.show_component(self.QR_CODE_BIG)
        else:
            self.show_component(self.QR_CODE)

    # callback

    def callback_qr_code(self, event, component, button_state):
        if not self.panel or button_state:
            return
        self.log(f'Got qr code press: {component}-{button_state}')
        self.start_rec_cmd()
        self.show_qr(big=True)
        self.auto_dimming.turn_off()
        self.auto_page.turn_off()
        self.stop_rec_cmd(send_commands=True)

    def callback_qr_code_big(self, event, component, button_state):
        if not self.panel or button_state:
            return
        entities = self.panel.get_entities()
        if len(entities) == 0:
            return
        self.log(f'Got big qr code press: {component}-{button_state}')
        # switch to small qr code
        self.start_rec_cmd()
        self.show_qr(big=False)
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()
        if self._use_auto_page:
            self.auto_page.turn_on()
        self.stop_rec_cmd(send_commands=True)

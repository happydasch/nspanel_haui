from ..const import ESP_REQUEST, ESP_RESPONSE

from . import HAUIPage


class SettingsPage(HAUIPage):

    # common components
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')

    TXT_BRGHT_ICO, TXT_BRGHT = (6, 'tBrghtIco'), (7, 'tBrght')
    TXT_BRGHT_PCT, SLD_BRGHT = (8, 'tBrghtPct'), (9, 'hBrght')
    TXT_BRGHT_DIM_ICO, TXT_BRGHT_DIM = (10, 'tBrghtDimIco'), (11, 'tBrghtDim')
    TXT_BRGHT_DIM_PCT, SLD_BRGHT_DIM = (12, 'tBrghtDimPct'), (13, 'hBrghtDim')

    # page

    def start_page(self):
        device_name = self.app.device.get_device_name()
        # auto dimming component
        self.auto_dimming = self.app.get_entity(f'switch.{device_name}_use_auto_dimming')
        self._use_auto_dimming = self.auto_dimming.get_state()
        self.auto_dimming.turn_off()
        # brightness components
        self.brightness_full_entity = self.app.get_entity(f'number.{device_name}_brightness_full')
        self.brightness_dimmed_entity = self.app.get_entity(f'number.{device_name}_brightness_dimmed')
        self._handle_brightness_full = self.brightness_full_entity.listen_state(self.callback_brightness)
        self._handle_brightness_dimmed = self.brightness_dimmed_entity.listen_state(self.callback_brightness)
        self._full_brightness = self.brightness_full_entity.get_state()
        self._dimmed_brightness = self.brightness_dimmed_entity.get_state()
        # display components
        self.add_component_callback(self.SLD_BRGHT, self.callback_slider_brightness)
        self.add_component_callback(self.SLD_BRGHT_DIM, self.callback_slider_brightness)

    def stop_page(self):
        # remove exisiting handles
        if self._handle_brightness_full:
            self.app.cancel_listen_state(self._handle_brightness_full)
        if self._handle_brightness_dimmed:
            self.app.cancel_listen_state(self._handle_brightness_dimmed)
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()

    # panel

    def start_panel(self, panel):
        self.set_close_nav_button(self.BTN_NAV_CLOSE)

    def render_panel(self, panel):
        title = panel.get_title(self.translate('Settings'))
        self.set_component_text(self.TXT_TITLE, title)
        self.set_component_text(self.TXT_BRGHT, self.translate('Full Brightness:'))
        self.set_component_text(self.TXT_BRGHT_DIM, self.translate('Dimmed Brightness:'))
        # update settings
        brightness_full_state = self.brightness_full_entity.get_state()
        if brightness_full_state != 'unavailable':
            brightness_full = int(float(brightness_full_state))
            self.set_brightness_full_slider(brightness_full)
        brightness_dimmed_state = self.brightness_dimmed_entity.get_state()
        if brightness_dimmed_state != 'unavailable':
            brightness_dimmed = int(float(brightness_dimmed_state))
            self.set_brightness_dim_slider(brightness_dimmed)

    # misc

    def set_brightness_full_slider(self, value):
        self.set_component_value(self.SLD_BRGHT, value)
        self.send_cmd(f'click {self.TXT_BRGHT_PCT[1]},0')

    def set_brightness_dim_slider(self, value):
        self.set_component_value(self.SLD_BRGHT_DIM, value)
        self.send_cmd(f'click {self.TXT_BRGHT_DIM_PCT[1]},0')

    # callback

    def callback_slider_brightness(self, event, component, button_state):
        self.log(f'Got slider brightness press: {component}-{button_state}')
        if button_state:
            return
        self.send_mqtt(ESP_REQUEST['req_component_int'], component[1])

    def callback_brightness(self, entity, attribute, old, new, cb_args):
        self.log(f'Got brightness callback: {entity}.{attribute}:{new}')
        # callback from ha
        if self.brightness_full_entity and entity == self.brightness_full_entity.entity_id:
            if new.isnumeric():
                if self._full_brightness != new:
                    self._full_brightness = new
                    self.set_brightness_full_slider(new)
        elif self.brightness_dimmed_entity and entity == self.brightness_dimmed_entity.entity_id:
            if new.isnumeric():
                if self._dimmed_brightness != new:
                    self._dimmed_brightness = new
                    self.set_brightness_dim_slider(new)

    # event

    def process_event(self, event):
        super().process_event(event)
        # check for values for full and dimmed brightness
        if event.name == ESP_RESPONSE['res_component_int']:
            # parse json response, set brightness
            data = event.as_json()
            if data.get('name', '') == self.SLD_BRGHT[1]:
                if self._full_brightness != data['value']:
                    self._full_brightness = data['value']
                    self.brightness_full_entity.set_state(state=data['value'])
            elif data.get('name', '') == self.SLD_BRGHT_DIM[1]:
                if self._dimmed_brightness != data['value']:
                    self._dimmed_brightness = data['value']
                    self.brightness_dimmed_entity.set_state(state=data['value'])

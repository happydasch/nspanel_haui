import threading

from ..const import ESP_REQUEST, ESP_RESPONSE, ESP_EVENT
from ..helper.color import pos_to_color, color_to_pos
from ..helper.icon import get_icon
from ..mapping.color import COLORS
from ..config import HAUIConfigEntity
from ..utils import scale
from . import HAUIPage


class LightPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # function buttons
    BTN_LIGHT_FNC_1, BTN_LIGHT_FNC_2 = (7, 'btLightFnc1'), (8, 'btLightFnc2')
    BTN_LIGHT_FNC_3, BTN_LIGHT_FNC_4 = (9, 'btLightFnc3'), (10, 'btLightFnc4')
    # selectors
    PIC_COLOR_WHEEL, H_BRIGHTNESS = (11, 'pColorWheel'), (12, 'hBrightness')
    H_COLOR_TEMP, BTN_POWER = (13, 'hColorTemp'), (14, 'bPower')
    # info
    TXT_INFO = (15, 'tInfo')

    # hardcoded to not request too often, needed for color to pos
    PIC_COLOR_WHEEL_WH = 200
    PIC_COLOR_WHEEL_X = 125
    PIC_COLOR_WHEEL_Y = 75

    # icons for light functions
    ICO_BRIGHTNESS = get_icon('brightness-6')
    ICO_COLOR = get_icon('palette')
    ICO_COLOR_TEMP = get_icon('thermometer')
    ICO_EFFECT = get_icon('fire')
    ICO_POWER = get_icon('power')

    # panel

    def start_panel(self, panel):
        # set component callbacks
        self.add_component_callback(self.PIC_COLOR_WHEEL, self.callback_color_wheel)
        self.add_component_callback(self.H_BRIGHTNESS, self.callback_brightness)
        self.add_component_callback(self.H_COLOR_TEMP, self.callback_color_temp)
        self.add_component_callback(self.BTN_POWER, self.callback_power)
        # set function buttons
        power_off_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_id': self.FNC_BTN_R_SEC,
            'fnc_name': 'power_off',
            'fnc_args': {
                'icon': self.ICO_POWER,
                'color': COLORS['component_accent'],
                'visible': False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, power_off_btn)
        # set light function button callbacks
        for btn in [self.BTN_LIGHT_FNC_1, self.BTN_LIGHT_FNC_2, self.BTN_LIGHT_FNC_3, self.BTN_LIGHT_FNC_4]:
            self.add_component_callback(btn, self.callback_light_function_button)
        # light functions like brightness, color, etc
        self._light_functions = {}
        self._current_light_function = None
        # touch track
        self._touch_track = False
        self._touch_timer = None
        self._touch_color = None
        # title and entity to control
        title = panel.get_title(self.translate('Light'))
        entity = None
        entity_id = panel.get('entity_id')
        if entity_id:
            entity = HAUIConfigEntity(self.app, {'entity': entity_id})
        entities = panel.get_entities()
        if len(entities):
            entity = entities[0]
        if entity is not None:
            title = entity.get_name()
            self.set_light_entity(entity)
        self._title = title

    def render_panel(self, panel):
        # set basic panel info
        self.set_component_text(self.TXT_TITLE, self._title)
        if not self.update_functions() and self.panel.get_mode() == 'popup':
            self.stop_rec_cmd(send_commands=False)
            navigation = self.app.controller['navigation']
            navigation.close_panel()

    # misc

    def set_light_entity(self, entity):
        self._light_entity = entity
        if not entity or not entity.has_entity_id():
            return
        for attr_name in ['state', 'effect', 'brightness', 'color_temp', 'rgb_color']:
            self.add_entity_listener(
                entity.get_entity_id(),
                self.callback_light_entity,
                attribute=attr_name)

    def get_light_function(self, fnc_name):
        for fnc in self._light_functions:
            if fnc['name'] == fnc_name:
                return fnc
        return None

    def set_light_function(self, idx, ico, name, val, status, show_info, **kwargs):
        btn = getattr(self, f'BTN_LIGHT_FNC_{idx}')
        self.set_component_text(btn, ico)
        if status is True:
            self.send_cmd(f'tsw {btn[1]},1')
            self.set_component_text_color(btn, COLORS['component'])
        else:
            self.send_cmd(f'tsw {btn[1]},0')
            self.set_component_text_color(btn, COLORS['text_inactive'])
        self.show_component(btn)
        return btn

    def set_brightness_info(self, value):
        fnc = self.get_light_function('brightness')
        if fnc is None:
            return
        if value > 0:
            txt_value = f'{value}%'
        else:
            txt_value = self.translate('Off')
        self.set_component_value(self.H_BRIGHTNESS, value)
        self.set_component_text(self.TXT_INFO, txt_value)

    def set_color_info(self, value):
        fnc = self.get_light_function('color')
        if fnc is None:
            return
        self.set_component_text_color(self.BTN_POWER, value)
        self.update_color_wheel()

    def set_color_temp_info(self, value):
        fnc = self.get_light_function('color_temp')
        if fnc is None:
            return
        self.set_component_value(self.H_COLOR_TEMP, value)
        self.set_component_text(self.TXT_INFO, f'{value}K')

    def set_effect_info(self, value):
        fnc = self.get_light_function('effect')
        if fnc is None:
            return
        btn = fnc['btn']
        if value != 'None':
            self.set_component_text_color(btn, COLORS['component_accent'])
        else:
            self.set_component_text_color(btn, COLORS['component'])

    def update_functions(self):
        if self._light_entity is None or not self._light_entity.has_entity():
            return False
        entity = self._light_entity.get_entity()

        # entity power
        power = None
        power_val = entity.get_state()
        # functions
        color = None
        brightness = None
        color_temp = None
        effect = None
        color_val = 0
        brightness_val = self._light_entity.get_entity_attr('brightness', 0)
        color_temp_val = self._light_entity.get_entity_attr('color_temp', 0)
        effect_val = self._light_entity.get_entity_attr('effect', None)
        # check what is supported
        attr = entity.attributes
        color_modes = attr.get('supported_color_modes', [])

        # get currently available functions
        functions = []
        # power on / off
        if power_val == 'on':
            power = True
        elif power_val == 'off':
            power = False
        # brightness
        if 'brightness' in attr:
            brightness = True
        # color
        list_color_modes = ['hs', 'rgb', 'rgbw', 'rgbww', 'xy']
        if any(item in list_color_modes for item in color_modes):
            if power_val == 'on':
                color = True
            else:
                color = False
        # color temp
        if 'color_temp' in color_modes:
            if 'color_temp' in attr:
                color_temp = True
            else:
                color_temp = False
        # effects
        if 'effect_list' in attr:
            if 'effect' in attr:
                effect = True
            else:
                effect = False

        # update light functions
        idx = 1
        for ico, name, val, status, show_info in [
            (self.ICO_BRIGHTNESS, 'brightness', brightness_val, brightness, True),
            (self.ICO_COLOR, 'color', color_val, color, False),
            (self.ICO_COLOR_TEMP, 'color_temp', color_temp_val, color_temp, True),
            (self.ICO_EFFECT, 'effect', effect_val, effect, False)
        ]:
            if status:
                function = dict(idx=idx, ico=ico, name=name, val=val, status=status, show_info=show_info)
                functions.append(function)
                idx += 1

        # set initial values
        if brightness is not None:
            # scale to 0-100 from 0-255
            brightness_val = round(scale(brightness_val, (0, 255), (0, 100)))
            self.set_component_value(self.H_BRIGHTNESS, brightness_val)
        if color_temp is not None:
            # scale ha color temp range to 0-100
            color_temp_val = round(scale(color_temp_val, (attr.min_mireds, attr.max_mireds), (0, 100)))
            self.set_component_value(self.H_COLOR_TEMP, color_temp_val)
        if color is not None:
            self.update_color_wheel()

        # check current function if it is still available
        names = [fnc['name'] for fnc in functions]
        if self._current_light_function is not None and self._current_light_function not in names:
            self._current_light_function = None

        # set light functions
        self._light_functions = functions
        light_function = None
        for fnc in self._light_functions:
            if fnc['name'] == self._current_light_function:
                light_function = fnc
                break
        if power is not None:
            self.update_light_functions(light_function)
            self.update_light_function_info()
            self.update_power_button()
            return True
        else:
            self.update_not_available()
        return False

    def update_light_functions(self, fnc):
        # show function components
        to_show = None
        if fnc is not None:
            if fnc['name'] == 'brightness':
                to_show = self.H_BRIGHTNESS
            elif fnc['name'] == 'color':
                to_show = self.PIC_COLOR_WHEEL
            elif fnc['name'] == 'color_temp':
                to_show = self.H_COLOR_TEMP
            # function info
            if fnc['show_info']:
                self.show_component(self.TXT_INFO)
            else:
                self.hide_component(self.TXT_INFO)
        else:
            self.hide_component(self.TXT_INFO)
        # function buttons
        for i in range(4):
            if i < len(self._light_functions):
                function = self._light_functions[i]
                btn = self.set_light_function(**function)
                function['btn'] = btn
                if function['name'] == self._current_light_function:
                    self.set_component_value(btn, 1)
                else:
                    self.set_component_value(btn, 0)
            else:
                idx = i + 1
                btn = getattr(self, f'BTN_LIGHT_FNC_{idx}')
                self.hide_component(btn)
        # function components
        for x in [self.H_BRIGHTNESS, self.PIC_COLOR_WHEEL, self.H_COLOR_TEMP]:
            self.show_component(x) if x == to_show else self.hide_component(x)

    def update_light_function_info(self):
        for fnc in self._light_functions:
            name = fnc['name']
            val = fnc['val']
            # set value
            if name == 'brightness':
                val = round(scale(val, (0, 255), (0, 100)))
                self.set_brightness_info(val)
            elif name == 'color':
                self.set_color_info(val)
            elif name == 'color_temp':
                self.set_color_temp_info(val)
            elif name == 'effect':
                self.set_effect_info(val)

    def update_color_wheel(self):
        if self._current_light_function != 'color':
            return
        rgb_color = self._light_entity.get_entity_attr('rgb_color')
        if rgb_color is None:
            return
        # reduce wh to match max circle pos at border
        radius = 6
        wh = self.PIC_COLOR_WHEEL_WH - (2 * radius)
        # get pos xy based on smaller circle
        pos_x, pos_y = color_to_pos(rgb_color, wh)
        # refresh color wheel to remove circle
        self.send_cmd(f'ref {self.PIC_COLOR_WHEEL[0]}')
        if pos_x is not None and pos_y is not None and pos_x > 0 and pos_y > 0:
            self.log(f'Set color wheel: {pos_x},{pos_y}')
            # adjust pos based on radius of circle
            pos_x += self.PIC_COLOR_WHEEL_X + radius
            pos_y += self.PIC_COLOR_WHEEL_Y + radius
            self.send_cmd('doevents')
            # draw circle
            color = COLORS['component_pressed']
            self.send_cmd(f'cirs {pos_x},{pos_y},{radius},{color}')

    def update_power_button(self):
        # update function button
        if self._light_entity.get_entity_state() == 'on' and self._current_light_function is not None:
            color = COLORS['component_accent']
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, color=color)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

        # show on / off button only if there is nothing active
        if self._light_entity.get_entity_state() == 'on':
            rgb_color = self._light_entity.get_entity_attr('rgb_color')
            color = self.parse_color(rgb_color)
        else:
            color = COLORS['entity_unavailable']
        if self._current_light_function is None:
            self.set_component_text_color(self.BTN_POWER, color)
            self.show_component(self.BTN_POWER)
        else:
            self.hide_component(self.BTN_POWER)

    def update_not_available(self):
        self.log('update_not_available')
        color = COLORS['entity_unavailable']
        self.set_component_text_color(self.BTN_POWER, color)
        self.show_component(self.BTN_POWER)

    # callback

    def callback_light_entity(self, entity, attribute, old, new, kwargs):
        self.log(f'Got light entity callback: {entity}.{attribute}:{new}')
        self.start_rec_cmd()
        if attribute == 'state':
            if not self.update_functions() and self.panel.get_mode() == 'popup':
                self.stop_rec_cmd(send_commands=False)
                navigation = self.app.controller['navigation']
                navigation.close_panel()
        elif attribute == 'effect':
            self.set_effect_info(new)
        elif attribute == 'rgb_color':
            self.set_color_info(new)
        elif attribute == 'brightness':
            if new is not None:
                value = round(scale(new, (0, 255), (0, 100)))
            else:
                value = 0
            self.set_brightness_info(value)
        elif attribute == 'color_temp':
            self.set_color_temp_info(new)
        self.stop_rec_cmd(send_commands=True)

    def callback_function_component(self, fnc_id, fnc_name):
        if fnc_id != self.FNC_BTN_R_SEC:
            return
        # turn of power on right secondary function button
        self.process_power(False)

    def callback_light_function_button(self, event, component, button_state):
        if button_state:
            # wait for release
            return
        self.log(f'Got light function press: {component}-{button_state}')
        # check for current function
        fnc = [f for f in self._light_functions if f['btn'] == component]
        fnc = fnc[0] if len(fnc) else None
        # check if current function still available or if toggled
        if fnc is None or self._current_light_function == fnc['name']:
            self.log(f'Unsetting function {fnc}, current: {self._current_light_function}')
            self._current_light_function = fnc = None
        else:
            self._current_light_function = fnc['name']
            # check for light function
            if fnc['name'] == 'effect':
                navigation = self.app.controller['navigation']
                selection = self._light_entity.get_entity_attr('effect_list', [])
                no_effect = self.translate('No effect')
                effects = []
                for name in selection:
                    value = name
                    if value == 'None':
                        value = no_effect
                    effects.append({'name': name, 'value': value})
                if len(effects):
                    navigation.open_popup(
                        'popup_select',
                        title=self.translate('Select effect'),
                        selection=effects,
                        selection_callback_fnc=self.callback_effect,
                        close_on_select=True)
        # update components
        self.start_rec_cmd()
        for btn in [self.BTN_LIGHT_FNC_1, self.BTN_LIGHT_FNC_2, self.BTN_LIGHT_FNC_3, self.BTN_LIGHT_FNC_4]:
            if btn != component or (fnc and fnc['name'] == 'effect'):
                self.set_component_value(btn, 0)
        # make sure power button is visible if needed
        self.update_power_button()
        self.update_light_functions(fnc)
        # make sure color is selected on color wheel
        if fnc and fnc['name'] == 'color':
            self.update_color_wheel()
        self.stop_rec_cmd(send_commands=True)

    def callback_color_wheel(self, event, component, button_state):
        self.log(f'Got color wheel press: {component}-{button_state}')
        if button_state:
            self._touch_track = True
            # will get set to false by touch end

    def callback_brightness(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got brightness press: {component}-{button_state}')
        self.send_mqtt(ESP_REQUEST['req_component_int'], self.H_BRIGHTNESS[1], force=True)

    def callback_color_temp(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got color temp press: {component}-{button_state}')
        self.send_mqtt(ESP_REQUEST['req_component_int'], self.H_COLOR_TEMP[1], force=True)

    def callback_power(self, event, component, button_state):
        if button_state:
            return
        self.log(f'Got power press: {component}-{button_state}')
        self.send_mqtt(ESP_REQUEST['req_component_int'], self.BTN_POWER[1], force=True)

    def callback_effect(self, selection):
        self.log(f'Got effect selection: {selection}')
        self._light_entity.call_entity_service('turn_on', effect=selection)

    # event

    def process_event(self, event):
        super().process_event(event)
        # touch on color wheel
        if event.name == ESP_EVENT['touch']:
            values = event.as_str().split(',')
            if self._touch_track:
                pos_x, pos_y = [int(val) if val.isdigit() else 0 for val in values]
                if pos_x > 0 and pos_y > 0:
                    pos_x -= self.PIC_COLOR_WHEEL_X
                    pos_y -= self.PIC_COLOR_WHEEL_Y
                    color = pos_to_color(pos_x, pos_y, self.PIC_COLOR_WHEEL_WH)
                    self.process_color(color)
        elif event.name == ESP_EVENT['touch_end']:
            values = event.as_str().split(',')
            if self._touch_track:
                self._touch_track = False
                _, _, pos_x, pos_y = [int(val) if val.isdigit() else 0 for val in values]
                if pos_x > 0 and pos_y > 0:
                    pos_x -= self.PIC_COLOR_WHEEL_X
                    pos_y -= self.PIC_COLOR_WHEEL_Y
                    color = pos_to_color(pos_x, pos_y, self.PIC_COLOR_WHEEL_WH)
                    self.process_color(color)
        # requested values
        if event.name == ESP_RESPONSE['res_component_int']:
            data = event.as_json()
            name = data.get('name', '')
            value = int(data.get('value', 0))
            if name == self.BTN_POWER[1]:
                self.process_power(value)
            elif name == self.H_BRIGHTNESS[1]:
                self.process_brightness(value)
            elif name == self.H_COLOR_TEMP[1]:
                self.process_color_temp(value)

    def process_color(self, color):
        current_color = self._light_entity.get_entity_attr('rgb_color', None)
        if color is not None and self._touch_color != color and current_color != color:
            self.log(f'Processing color value {color}')
            if self._touch_timer is not None:
                self._touch_timer.cancel()
            self._touch_timer = threading.Timer(
                0.05,
                self._light_entity.call_entity_service,
                args=['turn_on'],
                kwargs={'rgb_color': color})
            self._touch_timer.start()
            self._touch_color = color

    def process_brightness(self, brightness):
        self.log(f'Processing brightness value {brightness}')
        # scale 0-100 to ha brightness range
        brightness_ha = round(scale(brightness, (0, 100), (0, 255)))
        self._light_entity.call_entity_service('turn_on', brightness=brightness_ha)

    def process_color_temp(self, color_temp):
        self.log(f'Processing color temp {color_temp}')
        entity = self._light_entity.get_entity()
        # scale 0-100 from slider to color range of lamp
        color_temp = scale(color_temp, (0, 100), (entity.attributes.min_mireds, entity.attributes.max_mireds))
        self._light_entity.call_entity_service('turn_on', color_temp=color_temp)

    def process_power(self, power):
        self.log(f'Processing power value {power}')
        if self._light_entity.get_entity_state() == 'on':
            self._light_entity.call_entity_service('turn_off')
        else:
            self._light_entity.call_entity_service('turn_on')


class PopupLightPage(LightPage):

    def before_render_panel(self, panel):
        entity = self._light_entity
        # check if the provided entity is valid
        # if a invalid entity is provided, return false
        # to prevent panel from rendering
        navigation = self.app.controller['navigation']
        if entity is None or not entity.has_entity_id() or not entity.has_entity():
            self.log('No entity for popup light provided')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_type() != 'light':
            self.log(f'Entity {entity.get_entity_id()} is not a light entity')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_state() == 'unavailable':
            self.log(f'Entity {entity.get_entity_id()} is not available')
            navigation.close_panel()
            return False
        return True

from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..config import HAUIConfigEntity
from ..features import VacuumFeatures

from . import HAUIPage


class VacuumPage(HAUIPage):

    '''
    https://developers.home-assistant.io/docs/core/entity/vacuum/
    https://github.com/home-assistant/core/blob/master/homeassistant/components/vacuum/__init__.py
    '''

    ICO_START = get_icon('mdi:play')
    ICO_PAUSE = get_icon('mdi:pause')
    ICO_STOP = get_icon('mdi:stop')
    ICO_LOCATE = get_icon('mdi:map-marker')
    ICO_HOME = get_icon('mdi:home')
    ICO_BATTERY = get_icon('mdi:battery')
    ICO_FAN = get_icon('mdi:fan')

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # basic info
    TXT_STATUS, TXT_BATTERY, TXT_BATTERY_ICON = (7, 'tStatus'), (8, 'tBattery'), (9, 'tBatteryIcon')
    # control
    BTN_FAN, BTN_ACTION, BTN_HOME = (10, 'bFan'), (11, 'bAction'), (12, 'bHome')
    # entities
    BTN_ENTITY_1, BTN_ENTITY_2, BTN_ENTITY_3 = (13, 'bEntity1'), (14, 'bEntity2'), (15, 'bEntity3')
    BTN_ENTITY_4, BTN_ENTITY_5, BTN_ENTITY_6 = (16, 'bEntity4'), (17, 'bEntity5'), (18, 'bEntity6')

    NUM_ENTITIES = 6

    _vacuum_entity = None
    _entities = []
    _title = ''

    # panel

    def start_panel(self, panel):
        # set function buttons
        vacuum_locate_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_name': 'locate',
            'fnc_args': {
                'icon': self.ICO_LOCATE,
                'color': COLORS['component_accent'],
                'visible': False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, vacuum_locate_btn)
        # set title and entity
        entity = None
        entity_id = panel.get('entity_id')
        if entity_id:
            entity = HAUIConfigEntity(self.app, {'entity': entity_id})
        entities = panel.get_entities()
        if len(entities) > 0:
            entity = entities.pop(0)
        title = panel.get_title(self.translate('Vacuum'))
        if entity is not None:
            title = entity.get_entity_attr('friendly_name', title)
        self._title = title
        self._entities = entities
        self.set_vacuum_entity(entity)

    def render_panel(self, panel):
        self.update_vacuum_entity()

    # misc

    def set_vacuum_entity(self, entity):
        self._vacuum_entity = entity
        if not entity or not entity.has_entity_id():
            return
        features = entity.get_entity_attr('supported_features', 0)
        # add listener
        self.add_entity_listener(entity.get_entity_id(), self.callback_vacuum_entity)
        # header locate
        locate = False
        if features & VacuumFeatures.LOCATE:
            locate = True
        self.update_function_component(self.FNC_BTN_R_SEC, visible=locate)
        # fan button
        fan = False
        if features & VacuumFeatures.FAN_SPEED:
            fan = True
        self.set_function_component(
            self.BTN_FAN, self.BTN_FAN[1], 'fan',
            color=COLORS['component_active'],
            icon=self.ICO_FAN, visible=fan)
        # start/stop button
        action = False
        if features & VacuumFeatures.START:
            action = True
        self.set_function_component(
            self.BTN_ACTION, self.BTN_ACTION[1], 'action',
            icon=self.ICO_START, visible=action)
        # return home button
        return_home = False
        if features & VacuumFeatures.RETURN_HOME:
            return_home = True
        self.set_function_component(
            self.BTN_HOME, self.BTN_HOME[1], 'return_home',
            icon=self.ICO_HOME, visible=return_home)
        # entity buttons
        total_entities = len(self._entities)
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ''
            color = COLORS['text']
            if i < total_entities:
                entity = self._entities[i]
                icon = entity.get_icon()
                color = entity.get_color()
                visible = True
            else:
                entity = None
            component = getattr(self, f'BTN_ENTITY_{i+1}')
            self.set_function_component(
                component, component[1], 'entity', entity=entity,
                icon=icon, color=color, visible=visible)

    def update_vacuum_entity(self):
        self.set_component_text(self.TXT_TITLE, self._title)
        if self._vacuum_entity is None:
            return
        entity = self._vacuum_entity
        state = entity.get_entity_state()
        features = entity.get_entity_attr('supported_features', 0)
        # status text
        status_text = self.translate_state(entity.get_entity_type(), state)
        battery_level = entity.get_entity_attr('battery_level', 0)
        battery_icon = entity.get_entity_attr('battery_icon', self.ICO_BATTERY)
        self.set_component_text(self.TXT_STATUS, status_text)
        self.set_component_text(self.TXT_BATTERY, f'{battery_level}%')
        self.set_component_text(self.TXT_BATTERY_ICON, get_icon(battery_icon))
        # pause/start/stop button
        active = False
        pause, start, stop = False, False, False
        icon = self.ICO_START
        if state in ['cleaning', 'returning']:
            start = False
            if features & VacuumFeatures.PAUSE:
                pause = True
            if features & VacuumFeatures.STOP:
                stop = True
        elif state in ['docked', 'idle']:
            if features & VacuumFeatures.START:
                start = True
        active = True
        if start:
            icon = self.ICO_START
        elif pause:
            icon = self.ICO_PAUSE
        elif stop:
            icon = self.ICO_STOP
        else:
            icon = self.ICO_START
            active = False
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.BTN_ACTION[1], touch=active, color=color, color_pressed=color_pressed,
            icon=icon, back_color_pressed=back_color_pressed)
        # home button
        active = False
        if state != 'docked':
            active = True
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.BTN_HOME[1], touch=active, color=color, color_pressed=color_pressed,
            back_color_pressed=back_color_pressed)

    # callback

    def callback_function_component(self, fnc_id, fnc_name):
        if self._vacuum_entity is None:
            return
        # header
        entity = self._vacuum_entity
        state = self._vacuum_entity.get_entity_state()
        # fan
        if fnc_name == 'fan':
            navigation = self.app.controller['navigation']
            current = entity.get_entity_attr('fan_speed', '')
            selection = entity.get_entity_attr('fan_speed_list', [])
            speeds = []
            for name in selection:
                value = self.translate_state('vacuum', name, attr='fan_speed')
                speeds.append({'name': name, 'value': value})
            if len(speeds) > 0:
                navigation.open_popup(
                    'popup_select',
                    title=self.translate('Select Fan Speed'),
                    selection=speeds,
                    selected=current,
                    selection_callback_fnc=self.callback_fan_speed,
                    close_on_select=True)
        # start
        elif fnc_name == 'action':
            if state == 'cleaning':
                entity.call_entity_service('stop')
            else:
                entity.call_entity_service('start')
        # locate
        elif fnc_name == 'locate':
            entity.call_entity_service('locate')
        # return home
        elif fnc_name == 'return_home':
            entity.call_entity_service('return_to_base')
        # entity
        elif fnc_name == 'entity':
            entity = self._fnc_items[fnc_id]['fnc_args'].get('entity')
            if entity is not None:
                entity.execute()
        else:
            self.log(f'{fnc_id}, {fnc_name}')

    def callback_vacuum_entity(self, entity, attribute, old, new, kwargs):
        if attribute == 'state':
            self.start_rec_cmd()
            self.update_vacuum_entity()
            self.stop_rec_cmd(send_commands=True)
        else:
            self.log(f'Unknown vacuum entity attribute: {attribute}')

    def callback_fan_speed(self, selection):
        self.log(f'Got fan speed selection: {selection}')
        self._vacuum_entity.call_entity_service('set_fan_speed', fan_speed=selection)


class PopupVacuumPage(VacuumPage):

    def before_render_panel(self, panel):
        entity = self._vacuum_entity
        # if a invalid entity is provided, return false
        # to prevent panel from rendering
        navigation = self.app.controller['navigation']
        if entity is None or not entity.has_entity_id() or not entity.has_entity():
            self.log('No entity for popup vacuum provided')
            navigation.close_panel()
            return False
        if entity is not None and entity.get_entity_type() != 'vacuum':
            self.log(f'Entity {entity.get_entity_id()} is not a media entity')
            navigation.close_panel()
            return False
        if entity is not None and entity.get_entity_state() == 'unavailable':
            self.log(f'Entity {entity.get_entity_id()} is not available')
            navigation.close_panel()
            return False
        return True

from ..mapping.color import COLORS
from ..helper.icon import get_icon, get_icon_name_by_action
from ..helper.text import trim_text
from . import HAUIPage


class RowPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # row entities
    R1_ICO, R1_NAME, R1_BTN_UP, R1_BTN_STOP, R1_BTN_DOWN = (7, 'r1Icon'), (8, 'r1Name'), (9, 'r1BtnUp'), (10, 'r1BtnStop'), (11, 'r1BtnDown')
    R1_TOGGLE, R1_SLIDER, R1_SLIDER_VAL, R1_BTN_TXT, R1_OVL = (12, 'r1Toggle'), (13, 'r1Slider'), (14, 'r1SliderVal'), (15, 'r1BtnText'), (16, 'r1Overlay')
    R2_ICO, R2_NAME, R2_BTN_UP, R2_BTN_STOP, R2_BTN_DOWN = (17, 'r2Icon'), (18, 'r2Name'), (19, 'r2BtnUp'), (20, 'r2BtnStop'), (21, 'r2BtnDown')
    R2_TOGGLE, R2_SLIDER, R2_SLIDER_VAL, R2_BTN_TXT, R2_OVL = (22, 'r2Toggle'), (23, 'r2Slider'), (24, 'r2SliderVal'), (25, 'r2BtnText'), (26, 'r2Overlay')
    R3_ICO, R3_NAME, R3_BTN_UP, R3_BTN_STOP, R3_BTN_DOWN = (27, 'r3Icon'), (28, 'r3Name'), (29, 'r3BtnUp'), (30, 'r3BtnStop'), (31, 'r3BtnDown')
    R3_TOGGLE, R3_SLIDER, R3_SLIDER_VAL, R3_BTN_TXT, R3_OVL = (32, 'r3Toggle'), (33, 'r3Slider'), (34, 'r3SliderVal'), (35, 'r3BtnText'), (36, 'r3Overlay')
    R4_ICO, R4_NAME, R4_BTN_UP, R4_BTN_STOP, R4_BTN_DOWN = (37, 'r4Icon'), (38, 'r4Name'), (39, 'r4BtnUp'), (40, 'r4BtnStop'), (41, 'r4BtnDown')
    R4_TOGGLE, R4_SLIDER, R4_SLIDER_VAL, R4_BTN_TXT, R4_OVL = (42, 'r4Toggle'), (43, 'r4Slider'), (44, 'r4SliderVal'), (45, 'r4BtnText'), (46, 'r4Overlay')
    R5_ICO, R5_NAME, R5_BTN_UP, R5_BTN_STOP, R5_BTN_DOWN = (47, 'r5Icon'), (48, 'r5Name'), (49, 'r5BtnUp'), (50, 'r5BtnStop'), (51, 'r5BtnDown')
    R5_TOGGLE, R5_SLIDER, R5_SLIDER_VAL, R5_BTN_TXT, R5_OVL = (52, 'r5Toggle'), (53, 'r5Slider'), (54, 'r5SliderVal'), (55, 'r5BtnText'), (56, 'r5Overlay')
    # additional icons
    ICO_COVER_UP = get_icon('mdi:chevron-up')
    ICO_COVER_DOWN = get_icon('mdi:chevron-down')
    ICO_COVER_STOP = get_icon('mdi:stop')
    # definitions
    NUM_ROWS = 5
    LEN_NAME = 20

    # panel

    def start_panel(self, panel):
        # set vars
        self._entities = panel.get_entities()
        self._active_entities = {}  # active haui entities, id = component (overlay, ex: self.G1_OVL)
        self._active_handles = []
        self._current_page = panel.get('initial_page', 0)
        # set function buttons
        page_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_id': self.FNC_BTN_R_SEC,
            'fnc_name': 'next_page',
            'fnc_args': {
                'icon': self.ICO_NEXT_PAGE,
                'color': COLORS['component_accent'],
                'visible': True if len(self._entities) > self.NUM_ROWS else False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, page_btn)
        # set entity overlay callbacks
        for i in range(self.NUM_ROWS):
            idx = i + 1
            btn = getattr(self, f'R{idx}_OVL')
            self.add_component_callback(btn, self.callback_row_entries)

    def stop_panel(self, panel):
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_row_entries()

    # misc

    def set_row_entries(self):
        # check if there are any listener active and cancel them
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)
        # get current entities to display
        start = 0 + (self._current_page * self.NUM_ROWS)
        end = min(len(self._entities), start + self.NUM_ROWS)
        if len(self._entities) > start:
            entities = self._entities[start:end]
        else:
            entities = []
        # set buttons
        entity_ids = set()
        for i in range(self.NUM_ROWS):
            entity = None
            idx = i + 1
            if len(entities) > i:
                entity = entities[i]
            # click events are captured by overlay, assign
            # entities to overlay
            ovl = getattr(self, f'R{idx}_OVL')
            self._active_entities[ovl] = entity
            # visibility of row entry
            visible = False
            if entity is not None:
                # internal entity
                if entity.is_internal():
                    internal_type = entity.get_internal_type()
                    if internal_type in ['navigate', 'service']:
                        visible = True
                # standard entity
                else:
                    visible = True
                    entity_ids.add(entity.get_entity_id())
            self.set_row_entry(idx, visible=visible)
        # create listener for active entities
        for entity_id in entity_ids:
            handle = self.add_entity_listener(entity_id, self.callback_entity_state, attribute='all')
            self._active_handles.append(handle)

    def set_row_entry(self, idx, visible=True):
        # visibility of row entry components
        ovl = getattr(self, f'R{idx}_OVL')
        entity = self._active_entities[ovl]
        # detail visibility
        detail_visible = None
        if entity is not None:
            detail_visible = self.get_entity_display_type(entity)
        # visibility
        if visible:
            # left part of item
            for n in ['ICO', 'NAME', 'OVL']:
                item = getattr(self, f'R{idx}_{n}')
                self.show_component(item)
            # detail part of item
            for n in [
                'BTN_TXT', 'BTN_UP', 'BTN_STOP', 'BTN_DOWN',
                'TOGGLE', 'SLIDER', 'SLIDER_VAL'
            ]:
                item = getattr(self, f'R{idx}_{n}')
                show = False
                readonly = None
                color = None
                back_color_pressed = None
                # check detail
                if detail_visible:
                    # 'BTN_UP', 'BTN_STOP', 'BTN_DOWN' cover control
                    if detail_visible == 'cover' and n in ['BTN_UP', 'BTN_DOWN', 'BTN_STOP']:
                        show = True
                    # 'TOGGLE' on / off control
                    elif detail_visible == 'toggle' and n == 'TOGGLE':
                        show = True
                    # 'SLIDER', 'SLIDER_VAL' value slider
                    elif detail_visible == 'number' and n in ['SLIDER', 'SLIDER_VAL']:
                        show = True
                    # BTN_TXT
                    elif detail_visible == ['button', 'timer'] and n == 'BTN_TXT':
                        show = True
                        readonly = False
                        color = COLORS['component_active']
                        back_color_pressed = COLORS['component_pressed']
                    # 'BTN_TXT' will be used as default, text as disabled btn
                    elif n == 'BTN_TXT':
                        show = True
                        readonly = True
                        color = COLORS['component']
                        back_color_pressed = COLORS['background']
                # set component
                if not show:
                    self.hide_component(item)
                    continue
                if color is not None:
                    self.set_component_text_color(item, color)
                if back_color_pressed is not None:
                    self.set_component_back_color_pressed(item, back_color_pressed)
                if readonly is not None:
                    self.set_component_touch(item, not readonly)
                self.show_component(item)
                self.update_row_entry(idx)
        else:
            for n in [
                'ICO', 'NAME', 'OVL', 'BTN_UP', 'BTN_STOP', 'BTN_DOWN',
                'TOGGLE', 'SLIDER', 'SLIDER_VAL', 'BTN_TXT'
            ]:
                item = getattr(self, f'R{idx}_{n}')
                self.hide_component(item)
        '''
        for n in ['BTN_TXT']:
            item = getattr(self, f'R{idx}_{n}')
            self.set_component_text(item, '')
        for n in ['SLIDER', 'SLIDER_VAL']:
            item = getattr(self, f'R{idx}_{n}')
            self.set_component_value(item, 0)
        haui_entity = self._active_entities[ovl]
        # remaining items are depending of type
        if haui_entity is None or not visible:
            for n in [
                'BTN_TXT', 'BTN_UP', 'BTN_STOP', 'BTN_DOWN',
                'TOGGLE', 'SLIDER', 'SLIDER_VAL'
            ]:
                item = getattr(self, f'R{idx}_{n}')
        elif haui_entity is not None and visible:
            display_type = self.get_entity_display_type(haui_entity)
            '''

    def update_row_entries(self):
        entities = self._active_entities
        # row entries
        for idx in range(1, self.NUM_ROWS + 1):
            if idx > len(entities):
                break
            self.update_row_entry(idx)

    def update_row_entry(self, idx):
        ovl = getattr(self, f'R{idx}_OVL')
        entity = self._active_entities[ovl]
        if entity is None:
            return
        ico = getattr(self, f'R{idx}_ICO')
        name = getattr(self, f'R{idx}_NAME')
        self.set_component_text(name, trim_text(entity.get_name(), self.LEN_NAME))
        self.set_component_text(ico, entity.get_icon())
        self.set_component_text_color(ico, entity.get_color())
        display_type = self.get_entity_display_type(entity)
        if display_type == 'text':
            self.update_entity_text(entity, idx)
        elif display_type == 'button':
            self.update_entity_button(entity, idx)
        elif display_type == 'toggle':
            self.update_entity_toggle(entity, idx)
        elif display_type == 'timer':
            self.update_entity_timer(entity, idx)
        elif display_type == 'number':
            self.update_entity_number(entity, idx)
        elif display_type == 'cover':
            self.update_entity_cover(entity, idx)

    # entity detail

    def get_entity_display_type(self, haui_entity):
        """ Returns how the entity should be displayed.

        Entities support different display types:
        - text (button with touch disabled)
        - button (button)
        - number (slider with number)
        - timer (button)
        - cover (3 buttons: up, stop, down)

        Args:
            haui_entity (HAUIConfigEntity): entity

        Returns:
            str: display type
        """
        entity_type = haui_entity.get_entity_type()
        # default display type is text
        display_type = 'text'
        # check for special cases
        if entity_type == 'cover':
            display_type = 'cover'
        elif entity_type in [
            'button', 'input_button', 'scene', 'script',
            'lock'
        ]:
            display_type = 'button'
        elif entity_type in ['number', 'input_number']:
            display_type = 'number'
        elif entity_type == 'timer':
            display_type = 'timer'

        return display_type

    def update_entity_text(self, haui_entity, idx):
        item = getattr(self, f'R{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_button(self, haui_entity, idx):
        item = getattr(self, f'R{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_timer(self, haui_entity, idx):
        item = getattr(self, f'R{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_toggle(self, haui_entity, idx):
        toggle = getattr(self, f'R{idx}_TOGGLE')
        value = int(toggle.get_value())
        self.set_component_value(toggle, value)

    def update_entity_number(self, haui_entity, idx):
        slider = getattr(self, f'R{idx}_SLIDER')
        slider_val = getattr(self, f'R{idx}_SLIDER_VAL')
        minval = haui_entity.get_attr('min', 0)
        maxval = haui_entity.get_attr('max', 100)
        value = haui_entity.get_state()
        self.set_component_value(slider_val, value)
        self.send_cmd(f'{slider[1]}.minval={minval}')
        self.send_cmd(f'{slider[1]}.maxval={maxval}')
        self.set_component_value(slider, value)

    def update_entity_cover(self, haui_entity, idx):
        btn_up = getattr(self, f'R{idx}_BTN_UP')
        btn_stop = getattr(self, f'R{idx}_BTN_STOP')
        btn_down = getattr(self, f'R{idx}_BTN_DOWN')
        icon_up = ''
        icon_stop = ''
        icon_down = ''
        icon_up_status = False
        icon_stop_status = False
        icon_down_status = False
        entity_type = haui_entity.get_entity_type()
        entity_state = haui_entity.get_entity_state()
        bits = haui_entity.get_attr('supported_features')
        pos = haui_entity.get_attr('current_position')
        device_class = haui_entity.get_attr('device_class', 'window')
        if bits & 0x01:  # SUPPORT_OPEN
            if pos != 100 and not (entity_state == 'open' and pos == 'disable'):
                icon_up_status = True
            icon_up = get_icon_name_by_action(
                entity_type=entity_type,
                action='open',
                device_class=device_class)
            icon_up = get_icon(icon_up)
        if bits & 0x02:  # SUPPORT_CLOSE
            if pos != 0 and not (entity_state == 'closed' and pos == 'disable'):
                icon_down_status = True
            icon_down = get_icon_name_by_action(
                entity_type=entity_type,
                action='close',
                device_class=device_class)
            icon_down = get_icon(icon_down)
        if bits & 0x08:  # SUPPORT_STOP
            icon_stop = get_icon_name_by_action(
                entity_type=entity_type, action='stop', device_class=device_class)
            icon_stop = get_icon(icon_stop)
            icon_stop_status = True
        self.set_component_touch(btn_up, icon_up_status)
        self.set_component_touch(btn_stop, icon_stop_status)
        self.set_component_touch(btn_down, icon_down_status)
        self.set_component_text(btn_up, icon_up)
        self.set_component_text(btn_stop, icon_stop)
        self.set_component_text(btn_down, icon_down)

    # callback

    def callback_entity_state(self, entity, attribute, old, new, kwargs):
        entity_ids = set([haui_entity.get_entity_id() for haui_entity in self._active_entities.values() if haui_entity is not None])
        if entity not in entity_ids:
            return
        self.start_rec_cmd()
        idx = 0
        for ovl, haui_entity in self._active_entities.items():
            idx += 1
            if haui_entity is None:
                continue
            if entity == haui_entity.get_entity_id():
                self.update_row_entry(idx)
        self.stop_rec_cmd(send_commands=True)

    def callback_function_component(self, fnc_id, fnc_name):
        if fnc_name == 'next_page':
            count_pages = (len(self._entities) % self.NUM_ROWS) + 1
            self._current_page += 1
            if self._current_page >= count_pages:
                self._current_page = 0
            self.start_rec_cmd()
            self.set_row_entries()
            self.stop_rec_cmd(send_commands=True)

    def callback_row_entries(self, event, component, button_state):
        if button_state:
            return
        if component not in self._active_entities:
            return
        haui_entity = self._active_entities[component]
        self.execute_entity(haui_entity)

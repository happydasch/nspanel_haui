from ..mapping.color import COLORS
from ..helper.color import generate_color_palette, rgb565_to_rgb
from ..helper.text import trim_text

from . import HAUIPage
import random


class GridPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # grid entities
    G1_BTN, G1_ICO, G1_NAME, G1_OVL, G1_POWER = (7, 'g1Btn'), (8, 'g1Icon'), (9, 'g1Name'), (10, 'g1Overlay'), (11, 'g1Power')
    G2_BTN, G2_ICO, G2_NAME, G2_OVL, G2_POWER = (12, 'g2Btn'), (13, 'g2Icon'), (14, 'g2Name'), (15, 'g2Overlay'), (16, 'g2Power')
    G3_BTN, G3_ICO, G3_NAME, G3_OVL, G3_POWER = (17, 'g3Btn'), (18, 'g3Icon'), (19, 'g3Name'), (20, 'g3Overlay'), (21, 'g3Power')
    G4_BTN, G4_ICO, G4_NAME, G4_OVL, G4_POWER = (22, 'g4Btn'), (23, 'g4Icon'), (24, 'g4Name'), (25, 'g4Overlay'), (26, 'g4Power')
    G5_BTN, G5_ICO, G5_NAME, G5_OVL, G5_POWER = (27, 'g5Btn'), (28, 'g5Icon'), (29, 'g5Name'), (30, 'g5Overlay'), (31, 'g5Power')
    G6_BTN, G6_ICO, G6_NAME, G6_OVL, G6_POWER = (32, 'g6Btn'), (33, 'g6Icon'), (34, 'g6Name'), (35, 'g6Overlay'), (36, 'g6Power')
    # definitions
    NUM_GRIDS = 6
    LEN_NAME = 15

    # panel

    def start_panel(self, panel):
        # set vars
        self._entities = panel.get_entities()
        self._active_entities = {}  # active haui entities, id = component (overlay, ex: self.G1_OVL)
        self._active_handles = []
        self._entity_mapping = {}
        self._current_page = panel.get('initial_page', 0)
        self._color_seed = panel.get('color_seed', random.randint(0, 1000))
        # set function buttons
        page_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_id': self.FNC_BTN_R_SEC,
            'fnc_name': 'next_page',
            'fnc_args': {
                'icon': self.ICO_NEXT_PAGE,
                'color': COLORS['component_accent'],
                'visible': True if len(self._entities) > self.NUM_GRIDS else False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, page_btn)
        # set power and grid button callbacks
        for i in range(self.NUM_GRIDS):
            power = getattr(self, f'G{i+1}_POWER')
            ovl = getattr(self, f'G{i+1}_OVL')
            self.add_component_callback(power, self.callback_power_buttons)
            self.add_component_callback(ovl, self.callback_grid_entries)

    def stop_panel(self, panel):
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_grid_entries()

    # misc

    def set_grid_entries(self):
        # check if there are any listener active and cancel them
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)
        # get current entities to display
        start = 0 + (self._current_page * self.NUM_GRIDS)
        end = min(len(self._entities), start + self.NUM_GRIDS)
        if len(self._entities) > start:
            entities = self._entities[start:end]
        else:
            entities = []
        # set buttons
        entity_ids = set()
        for i in range(self.NUM_GRIDS):
            entity = None
            idx = i + 1
            if len(entities) > i:
                entity = entities[i]
            # click events are captured by overlay, assign
            # entities to button overlay
            ovl = getattr(self, f'G{idx}_OVL')
            power = getattr(self, f'G{idx}_POWER')
            self._active_entities[ovl] = entity
            # visibility of grid button
            visible = False
            if entity is not None:
                self._entity_mapping[entity] = {'ovl': ovl, 'power': power}
                # internal entity
                if entity.is_internal():
                    internal_type = entity.get_internal_type()
                    if internal_type in ['navigate', 'service']:
                        visible = True
                # standard entity
                else:
                    visible = True
                    entity_ids.add(entity.get_entity_id())
            self.set_grid_entry(idx, visible=visible)
        # create listener for active entities
        for entity_id in entity_ids:
            handle = self.add_entity_listener(entity_id, self.callback_entity_state, attribute='all')
            self._active_handles.append(handle)

    def set_grid_entry(self, idx, visible):
        # visibility of grid button components
        btn = getattr(self, f'G{idx}_BTN')
        ico = getattr(self, f'G{idx}_ICO')
        name = getattr(self, f'G{idx}_NAME')
        ovl = getattr(self, f'G{idx}_OVL')
        power = getattr(self, f'G{idx}_POWER')
        entity = self._active_entities[ovl]
        panel = self.panel
        # power button, only show if requested and a entity is set
        power_visible = False
        if entity is not None:
            power_visible = panel.get('show_power_button', False)
            if not entity.is_internal():
                power_visible = entity.get('show_power_button', power_visible)
        # colors for grid button
        color_pressed = COLORS['text']
        back_color_pressed = COLORS['component_pressed']
        power_color = panel.get('power_color', COLORS['component_active'])
        text_color = panel.get('text_color')
        back_color = panel.get('back_color')
        color_mode = panel.get('color_mode')
        color_seed = panel.get('color_seed', self._color_seed)
        if entity is not None:
            back_color = entity.get('back_color', back_color)
            color_mode = entity.get('color_mode', color_mode)
            color_seed = entity.get('color_seed', color_seed)
        # no background color check if color mode or set default
        if back_color is None:
            if color_mode is not None:
                self.log(f'Using random seed for grid: {color_seed}')
                colors = generate_color_palette(
                    rgb565_to_rgb(COLORS['background']),
                    color_mode, color_seed, 6)
                back_color = colors[idx - 1]
                back_color_pressed = [int(x * 0.5) for x in back_color]
                # for light back colors use dark text color
                if color_mode in ['pastel', 'light', 'lighten']:
                    if text_color is None:
                        text_color = COLORS['background']
                    color_pressed = COLORS['component_pressed']
                    power_color = COLORS['background']
                elif color_mode in ['vibrant']:
                    if text_color is None:
                        text_color = COLORS['component']
                    color_pressed = COLORS['component']
                    power_color = COLORS['component']
            else:
                back_color = COLORS['background']
                text_color = COLORS['text']
        # update grid button
        if visible:
            if text_color is not None:
                for x in [btn, name]:
                    self.set_component_text_color(x, text_color)
                if power_color is not None and color_mode is not None:
                    self.set_component_text_color(power, power_color)
            if color_pressed is not None:
                for x in [btn, power]:
                    self.set_component_text_color_pressed(x, color_pressed)
            if back_color is not None:
                for x in [ico, name, btn, power]:
                    self.set_component_back_color(x, back_color)
            if back_color_pressed is not None:
                for x in [btn, power]:
                    self.set_component_back_color_pressed(x, back_color_pressed)
            for x in [btn, ico, name, ovl]:
                self.show_component(x)
            if power_visible:
                self.show_component(power)
            else:
                self.hide_component(power)
            self.update_grid_entry(idx)
        else:
            for x in [btn, ico, name, ovl, power]:
                self.hide_component(x)

    def update_grid_entries(self):
        entities = self._active_entities
        # grid buttons
        for idx in range(1, self.NUM_GRIDS + 1):
            if idx > len(entities):
                break
            self.update_grid_entry(idx)

    def update_grid_entry(self, idx):
        # update a single button
        ovl = getattr(self, f'G{idx}_OVL')
        ico = getattr(self, f'G{idx}_ICO')
        name = getattr(self, f'G{idx}_NAME')
        entity = self._active_entities[ovl]
        # set text
        self.set_component_text(name, trim_text(entity.get_name(), self.LEN_NAME))
        self.set_component_text_color(ico, entity.get_color())
        self.set_component_text(ico, entity.get_icon())

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
                self.update_grid_entry(idx)
        self.stop_rec_cmd(send_commands=True)

    def callback_function_component(self, fnc_id, fnc_name):
        if fnc_name == 'next_page':
            count_pages = (len(self._entities) % self.NUM_GRIDS) + 1
            self._current_page += 1
            if self._current_page >= count_pages:
                self._current_page = 0
            self.start_rec_cmd()
            self.set_grid_entries()
            self.stop_rec_cmd(send_commands=True)

    def callback_power_buttons(self, event, component, button_state):
        if button_state:
            return
        for haui_entity, mapping in self._entity_mapping.items():
            if mapping['power'] != component:
                continue
            if not haui_entity.has_entity():
                break
            haui_entity.execute()

    def callback_grid_entries(self, event, component, button_state):
        if button_state:
            return
        if component not in self._active_entities:
            return
        haui_entity = self._active_entities[component]
        self.execute_entity(haui_entity)

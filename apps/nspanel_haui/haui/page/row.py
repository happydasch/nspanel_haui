from ..mapping.color import COLORS
from ..helper.icon import get_icon, get_icon_name_by_action
from . import HAUIPage


class RowPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')

    # Entity 1
    E1_ICO, E1_NAME, E1_OVL = (7, 'e1Icon'), (8, 'e1Name'), (12, 'e1Ovl')
    E1_BTN_UP, E1_BTN_STOP, E1_BTN_DOWN = (9, 'e1BtnUp'), (10, 'e1BtnStop'), (11, 'e1BtnDown')
    E1_TOGGLE, E1_SLIDER, E1_SLIDER_VAL = (13, 'e1Toggle'), (14, 'e1Slider'), (15, 'e1SliderVal')
    E1_BTN_TXT = (16, 'e1BtnText')

    # Entity 2
    E2_ICO, E2_NAME, E2_OVL = (17, 'e2Icon'), (18, 'e2Name'), (22, 'e2Ovl')
    E2_BTN_UP, E2_BTN_STOP, E2_BTN_DOWN = (19, 'e2BtnUp'), (20, 'e2BtnStop'), (21, 'e2BtnDown')
    E2_TOGGLE, E2_SLIDER, E2_SLIDER_VAL = (23, 'e2Toggle'), (24, 'e2Slider'), (25, 'e2SliderVal')
    E2_BTN_TXT = (26, 'e2BtnText')

    # Entity 3
    E3_ICO, E3_NAME, E3_OVL = (27, 'e3Icon'), (28, 'e3Name'), (32, 'e3Ovl')
    E3_BTN_UP, E3_BTN_STOP, E3_BTN_DOWN = (29, 'e3BtnUp'), (30, 'e3BtnStop'), (31, 'e3BtnDown')
    E3_TOGGLE, E3_SLIDER, E3_SLIDER_VAL = (33, 'e3Toggle'), (34, 'e3Slider'), (35, 'e3SliderVal')
    E3_BTN_TXT = (36, 'e3BtnText')

    # Entity 4
    E4_ICO, E4_NAME, E4_OVL = (37, 'e4Icon'), (38, 'e4Name'), (42, 'e4Ovl')
    E4_BTN_UP, E4_BTN_STOP, E4_BTN_DOWN = (39, 'e4BtnUp'), (40, 'e4BtnStop'), (41, 'e4BtnDown')
    E4_TOGGLE, E4_SLIDER, E4_SLIDER_VAL = (43, 'e4Toggle'), (44, 'e4Slider'), (45, 'e4SliderVal')
    E4_BTN_TXT = (46, 'e4BtnText')

    # panel

    def start_panel(self, panel):
        # set entity overlay callbacks
        for i in range(4):
            btn = getattr(self, f'E{i+1}_OVL')
            self.add_component_callback(btn, self.callback_entity_overlay)

        # active entities
        self._active = {}

        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, self.BTN_FNC_RIGHT_SEC)

        self.start_rec_cmd()
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        # check entities
        entities = panel.get_entities()
        entity_ids = []
        for i in range(4):
            entity = None
            idx = i + 1
            if i < len(entities):
                entity = entities[i]
            # click events are captured by overlay, assign
            # entities to button overlay
            ovl = getattr(self, f'E{idx}_OVL')
            self._active[ovl] = entity
            if not entity:
                self.set_entity_detail(entity, idx, 0)
                continue
            # standard entity
            if not entity.is_internal():
                self.set_entity_detail(entity, idx, 1)
                # add entity state callbacks for standard entities
                entity_ids.append(entity.get_entity_id())
                continue
            # internal entity
            else:
                internal_type = entity.get_internal_type()
                if internal_type in ['navigate', 'service']:
                    self.set_entity_detail(entity, idx, 1)
                    continue
            # hide entity by default
            self.set_entity_detail(entity, idx, 0)

        # make entity_ids unique and add listener
        for entity_id in set(entity_ids):
            if entity_id is not None:
                self.add_entity_listener(
                    entity_id, self.callback_entity_state, attribute='all')

        self.stop_rec_cmd(send_commands=True)

    def render_panel(self, panel):
        self.update_entities(panel.get_entities())

    # misc

    def get_display_type(self, haui_entity):
        """ Returns what how the entity should be displayed.

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

    def set_entity_detail(self, haui_entity, idx, vis=1):
        for i in ['ICO', 'NAME', 'OVL']:
            item = getattr(self, f'E{idx}_{i}')
            self.send_cmd(f'vis {item[1]},{vis}')
        for i in ['ICO', 'NAME', 'BTN_TXT']:
            item = getattr(self, f'E{idx}_{i}')
            self.set_component_text(item, '')
        for i in ['SLIDER', 'SLIDER_VAL']:
            item = getattr(self, f'E{idx}_{i}')
            self.set_component_value(item, 0)
        # remaining items are depending of type
        if haui_entity is None or vis == 0:
            for i in [
                'BTN_TXT', 'BTN_UP', 'BTN_STOP', 'BTN_DOWN',
                'TOGGLE', 'SLIDER', 'SLIDER_VAL'
            ]:
                item = getattr(self, f'E{idx}_{i}')
        elif haui_entity is not None and vis == 1:
            display_type = self.get_display_type(haui_entity)
            for i in [
                'BTN_TXT', 'BTN_UP', 'BTN_STOP', 'BTN_DOWN',
                'TOGGLE', 'SLIDER', 'SLIDER_VAL'
            ]:
                item = getattr(self, f'E{idx}_{i}')
                visible = False
                readonly = None
                color = None
                # 'BTN_UP', 'BTN_STOP', 'BTN_DOWN' cover control
                if display_type == 'cover' and i in ['BTN_UP', 'BTN_DOWN', 'BTN_STOP']:
                    visible = True
                # 'TOGGLE' on / off control
                elif display_type == 'toggle' and i == 'TOGGLE':
                    visible = True
                # 'SLIDER', 'SLIDER_VAL' value slider
                elif display_type == 'number' and i in ['SLIDER', 'SLIDER_VAL']:
                    visible = True
                # BTN_TXT
                elif display_type == ['button', 'timer'] and i == 'BTN_TXT':
                    visible = True
                    readonly = False
                    color = COLORS['component_acitve']
                # 'BTN_TXT' will be used as default, text as disabled btn
                elif i == 'BTN_TXT':
                    visible = True
                    readonly = True
                    color = COLORS['component']
                # set component
                if color is not None:
                    self.set_component_text_color(item, color)
                if readonly is not None:
                    self.send_cmd(f'tsw {item[1]},{int(readonly)}')
                if visible:
                    self.show_component(item)
                else:
                    self.hide_component(item)

    def update_entities(self, entities):
        for i in range(4):
            if i >= len(entities):
                break
            self.update_entity_detail(entities[i], i + 1)

    def update_entity_detail(self, haui_entity, idx):
        ico = getattr(self, f'E{idx}_ICO')
        name = getattr(self, f'E{idx}_NAME')
        self.set_component_text(ico, haui_entity.get_icon())
        self.set_component_text_color(ico, haui_entity.get_color())
        self.set_component_text(name, haui_entity.get_name())
        display_type = self.get_display_type(haui_entity)
        if display_type == 'text':
            self.update_entity_text(haui_entity, idx)
        elif display_type == 'button':
            self.update_entity_button(haui_entity, idx)
        elif display_type == 'toggle':
            self.update_entity_toggle(haui_entity, idx)
        elif display_type == 'timer':
            self.update_entity_timer(haui_entity, idx)
        elif display_type == 'number':
            self.update_entity_number(haui_entity, idx)
        elif display_type == 'cover':
            self.update_entity_cover(haui_entity, idx)

    def update_entity_text(self, haui_entity, idx):
        item = getattr(self, f'E{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_button(self, haui_entity, idx):
        item = getattr(self, f'E{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_timer(self, haui_entity, idx):
        item = getattr(self, f'E{idx}_BTN_TXT')
        self.set_component_text(item, haui_entity.get_value())

    def update_entity_toggle(self, haui_entity, idx):
        toggle = getattr(self, f'E{idx}_TOGGLE')
        value = int(toggle.get_value())
        self.set_component_value(toggle, value)

    def update_entity_number(self, haui_entity, idx):
        slider = getattr(self, f'E{idx}_SLIDER')
        slider_val = getattr(self, f'E{idx}_SLIDER_VAL')
        minval = haui_entity.get_attr('min', 0)
        maxval = haui_entity.get_attr('max', 100)
        value = haui_entity.get_state()
        self.set_component_value(slider_val, value)
        self.send_cmd(f'{slider[1]}.minval={minval}')
        self.send_cmd(f'{slider[1]}.maxval={maxval}')
        self.set_component_value(slider, value)

    def update_entity_cover(self, haui_entity, idx):
        btn_up = getattr(self, f'E{idx}_BTN_UP')
        btn_stop = getattr(self, f'E{idx}_BTN_STOP')
        btn_down = getattr(self, f'E{idx}_BTN_DOWN')
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
        if bits & 0b00000001:  # SUPPORT_OPEN
            if pos != 100 and not (entity_state == 'open' and pos == 'disable'):
                icon_up_status = True
            icon_up = get_icon_name_by_action(
                entity_type=entity_type,
                action='open',
                device_class=device_class)
            icon_up = get_icon(icon_up)
        if bits & 0b00000010:  # SUPPORT_CLOSE
            if pos != 0 and not (entity_state == 'closed' and pos == 'disable'):
                icon_down_status = True
            icon_down = get_icon_name_by_action(
                entity_type=entity_type,
                action='close',
                device_class=device_class)
            icon_down = get_icon(icon_down)
        if bits & 0b00001000:  # SUPPORT_STOP
            icon_stop = get_icon_name_by_action(
                entity_type=entity_type, action='stop', device_class=device_class)
            icon_stop = get_icon(icon_stop)
            icon_stop_status = True
        self.send_cmd(f'tsw {btn_up[1]},{int(icon_up_status)}')
        self.send_cmd(f'tsw {btn_stop[1]},{int(icon_stop_status)}')
        self.send_cmd(f'tsw {btn_down[1]},{int(icon_down_status)}')
        self.set_component_text(btn_up, icon_up)
        self.set_component_text(btn_stop, icon_stop)
        self.set_component_text(btn_down, icon_down)

    # callback

    def callback_entity_overlay(self, event, component, button_state):
        if button_state:
            # wait for release
            return
        self.log(f'Got entity overlay press: {component}-{button_state}')
        # process entity overlay press
        if component in self._active:
            self.process_entity_detail_push(component)

    def callback_entity_state(self, entity, attribute, old, new, kwargs):
        self.log(f'Got entity state callback: {entity}.{attribute}:{new}')
        self.refresh_panel()

    # event

    def process_entity_detail_push(self, component):
        if component not in self._active:
            return
        haui_entity = self._active[component]
        self.execute_entity(haui_entity)

from . import HAUIPage


class GridPage(HAUIPage):

    # common components
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')
    # grid buttons 1-6
    G1_BTN, G2_BTN, G3_BTN = (7, 'g1Btn'), (8, 'g2Btn'), (9, 'g3Btn')
    G4_BTN, G5_BTN, G6_BTN = (10, 'g4Btn'), (11, 'g5Btn'), (12, 'g6Btn')
    G1_ICO, G2_ICO, G3_ICO = (13, 'g1Icon'), (14, 'g2Icon'), (15, 'g3Icon')
    G4_ICO, G5_ICO, G6_ICO = (16, 'g4Icon'), (17, 'g5Icon'), (18, 'g6Icon')
    G1_NAME, G2_NAME, G3_NAME = (19, 'g1Name'), (20, 'g2Name'), (21, 'g3Name')
    G4_NAME, G5_NAME, G6_NAME = (22, 'g4Name'), (23, 'g5Name'), (24, 'g6Name')
    G1_OVL, G2_OVL, G3_OVL = (25, 'g1Overlay'), (26, 'g2Overlay'), (27, 'g3Overlay')
    G4_OVL, G5_OVL, G6_OVL = (28, 'g4Overlay'), (29, 'g5Overlay'), (30, 'g6Overlay')

    # page

    def start_page(self):
        # set grid button callbacks
        for i in range(6):
            btn = getattr(self, f'G{i+1}_OVL')
            self.add_component_callback(btn, self.callback_grid_buttons)

    # panel

    def start_panel(self, panel):
        # active entities
        self._active = {}

        self.set_prev_next_nav_buttons(self.BTN_NAV_LEFT, self.BTN_NAV_RIGHT)

        self.start_rec_cmd()
        self.set_component_text(self.TXT_TITLE, panel.get_title())

        # check grid buttons
        entities = panel.get_entities()
        entity_ids = []
        for i in range(6):
            entity = None
            idx = i + 1
            if i < len(entities):
                entity = entities[i]
            # click events are captured by overlay, assign
            # entities to button overlay
            ovl = getattr(self, f'G{idx}_OVL')
            self._active[ovl] = entity
            if not entity:
                self.set_grid_button(idx, 0)
                continue
            # standard entity
            if not entity.is_internal():
                self.set_grid_button(idx, 1)
                # add entity state callbacks for standard entities
                entity_ids.append(entity.get_entity_id())

                continue
            # internal entity
            else:
                internal_type = entity.get_internal_type()
                if internal_type in ['navigate', 'service']:
                    self.set_grid_button(idx, 1)
                    continue
            # hide button by default
            self.set_grid_button(idx, 0)

        # make entity_ids unique and add listener
        for entity_id in set(entity_ids):
            if entity_id is not None:
                self.add_entity_listener(
                    entity_id, self.callback_entity_state, attribute='all')

        self.stop_rec_cmd(send_commands=True)


    def render_panel(self, panel):
        self.update_grid_buttons(panel.get_entities())

    # misc

    def update_grid_buttons(self, entities):
        # 6 grid buttons
        for i in range(6):
            if i >= len(entities):
                break
            self.update_grid_button(entities[i], i + 1)

    def update_grid_button(self, haui_entity, idx):
        # update a single button
        ico = getattr(self, f'G{idx}_ICO')
        name = getattr(self, f'G{idx}_NAME')
        self.set_component_text_color(ico, haui_entity.get_color())
        self.set_component_text(ico, haui_entity.get_icon())
        self.set_component_text(name, haui_entity.get_name())

    def set_grid_button(self, idx, vis=1):
        btn = getattr(self, f'G{idx}_BTN')
        ico = getattr(self, f'G{idx}_ICO')
        name = getattr(self, f'G{idx}_NAME')
        ovl = getattr(self, f'G{idx}_OVL')
        for x in [btn, ico, name, ovl]:
            self.send_cmd(f'vis {x[0]},{vis}')
        self.set_component_text(ico, '')
        self.set_component_text(name, '')

    # callback

    def callback_grid_buttons(self, event, component, button_state):
        if button_state:
            # wait for release
            return
        self.log(f'Got grid button press: {component}-{button_state}')
        # process grid button press
        if component in self._active:
            self.process_grid_button_push(component)

    def callback_entity_state(self, entity, attribute, old, new, kwargs):
        self.log(f'Got entity state callback: {entity}.{attribute}:{new}')
        self.refresh_panel()

    def callback_notify_close(self, btn_left, btn_right):
        self.log(f'Got notification of close {btn_left},{btn_right}')

    # event

    def process_grid_button_push(self, component):
        if component not in self._active:
            return
        haui_entity = self._active[component]
        self.execute_entity(haui_entity)

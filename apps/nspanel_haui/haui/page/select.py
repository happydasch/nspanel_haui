from ..helper.icon import get_icon
from . import HAUIPage


class PopupSelectPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')

    BTN_SELECT_1, BTN_SELECT_2, BTN_SELECT_3 = (6, 'bSel1'), (7, 'bSel2'), (8, 'bSel3')
    BTN_SELECT_4, BTN_SELECT_5, BTN_SELECT_6 = (9, 'bSel4'), (10, 'bSel5'), (11, 'bSel6')
    BTN_SELECT_7, BTN_SELECT_8, BTN_SELECT_9 = (12, 'bSel7'), (13, 'bSel8'), (14, 'bSel9')
    BTN_SELECT_10, BTN_SELECT_11, BTN_SELECT_12 = (15, 'bSel10'), (16, 'bSel11'), (17, 'bSel12')
    BTN_NEXT = (18, 'bNext')

    ICO_NEXT = get_icon('chevron-double-right')

    def start_page(self):
        for i in range(12):
            idx = i + 1
            btn = getattr(self, 'BTN_SELECT_' + str(idx))
            self.add_component_callback(btn, self.callback_select)
        self.add_component_callback(self.BTN_NEXT, self.callback_next)

    # panel

    def start_panel(self, panel):
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_close_nav_button(self.BTN_NAV_CLOSE)
        # get params
        self._selection = panel.get('selection', [])
        self._close_on_select = panel.get('close_on_select', True)
        self._selection_callback_fnc = panel.get('selection_callback_fnc')
        self._close_callback_fnc = panel.get('close_callback_fnc')
        self._current_page = 0
        self._active = {}

    def close_panel(self, panel):
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def before_render_panel(self, panel):
        selection = self._selection
        # check if a selection is provided
        navigation = self.app.controller['navigation']
        if selection is None or not len(selection):
            self.log('No selection popup select provided')
            navigation.close_panel()
            return False
        return True

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.load_selection()

    # misc

    def load_selection(self):
        selection = self._selection
        if len(selection) > 12:
            self.set_component_text(self.BTN_NEXT, self.ICO_NEXT)
            self.show_component(self.BTN_NEXT)
        else:
            self.hide_component(self.BTN_NEXT)
        self._active = {}
        for i in range(12):
            idx = i + 1
            sel_i = (self._current_page * 12) + i
            btn = getattr(self, 'BTN_SELECT_' + str(idx))
            if sel_i < len(selection):
                # check type of selection
                self._active[btn] = selection[sel_i]
                selected = self.get_value(btn)
                self.set_component_text(btn, selected)
                self.show_component(btn)
            else:
                self._active[btn] = None
                self.hide_component(btn)

    def get_name(self, btn):
        if btn not in self._active:
            return None
        selection = self._active[btn]
        if isinstance(selection, str):
            return selection
        elif isinstance(selection, dict):
            return selection.get('name', '')
        elif isinstance(selection, (list, tuple)):
            return selection[0]
        return None

    def get_value(self, btn):
        if btn not in self._active:
            return None
        selection = self._active[btn]
        if isinstance(selection, str):
            return selection
        elif isinstance(selection, dict):
            return selection.get('value', '')
        elif isinstance(selection, (list, tuple)):
            return selection[1]
        return None

    # callback

    def callback_next(self, event, component, button_state):
        if button_state:
            return
        current_page = self._current_page + 1
        if (current_page * 12) > len(self._selection):
            current_page = 0
        self._current_page = current_page

        self.start_rec_cmd()
        self.load_selection()
        self.stop_rec_cmd(send_commands=True)

    def callback_select(self, event, component, button_state):
        if button_state:
            return
        if self._selection_callback_fnc:
            for x in self._active:
                if component == x:
                    self._selection_callback_fnc(self.get_name(x))
                    break
        if self._close_on_select:
            self.app.controller['navigation'].close_panel()

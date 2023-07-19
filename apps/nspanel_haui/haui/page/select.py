from ..mapping.color import COLORS
from ..helper.icon import get_icon
from . import HAUIPage


class PopupSelectPage(HAUIPage):

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # full width buttons
    BTN_SEL_FULL_1, BTN_SEL_FULL_2 = (7, 'bSelFull1'), (8, 'bSelFull2')
    BTN_SEL_FULL_3, BTN_SEL_FULL_4 = (9, 'bSelFull3'), (10, 'bSelFull4')
    # default buttons
    BTN_SEL_1, BTN_SEL_2, BTN_SEL_3 = (11, 'bSel1'), (12, 'bSel2'), (13, 'bSel3')
    BTN_SEL_4, BTN_SEL_5, BTN_SEL_6 = (14, 'bSel4'), (15, 'bSel5'), (16, 'bSel6')
    BTN_SEL_7, BTN_SEL_8, BTN_SEL_9 = (17, 'bSel7'), (18, 'bSel8'), (19, 'bSel9')
    BTN_SEL_10, BTN_SEL_11, BTN_SEL_12 = (20, 'bSel10'), (21, 'bSel11'), (22, 'bSel12')

    # panel

    def start_panel(self, panel):
        # set function buttons
        page_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_id': self.FNC_BTN_R_SEC,
            'fnc_name': 'next_page',
            'fnc_args': {
                'icon': self.ICO_NEXT_PAGE,
                'color': COLORS['component_accent'],
                'visible': False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, page_btn)
        # get params
        self._select_mode = panel.get('select_mode', [])
        self._selection = panel.get('selection', [])
        self._selected = panel.get('selected', '')
        self._close_on_select = panel.get('close_on_select', True)
        self._selection_callback_fnc = panel.get('selection_callback_fnc')
        self._close_callback_fnc = panel.get('close_callback_fnc')
        self._current_page = 0
        self._active = {}
        items_per_page = 12
        if self._select_mode == 'full':
            items_per_page = 4
        self._items_per_page = items_per_page
        for i in range(4):
            idx = i + 1
            btn = getattr(self, 'BTN_SEL_FULL_' + str(idx))
            self.add_component_callback(btn, self.callback_select)
        for i in range(12):
            idx = i + 1
            btn = getattr(self, 'BTN_SEL_' + str(idx))
            self.add_component_callback(btn, self.callback_select)

    def stop_panel(self, panel):
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
        self.set_selection()

    # misc

    def set_selection(self):
        selection = self._selection
        if len(selection) > self._items_per_page:
            # show header function button
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True)
        else:
            # hide header function button
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
        self._active = {}
        for i in range(self._items_per_page):
            idx = i + 1
            sel_i = (self._current_page * self._items_per_page) + i
            btn_name = 'BTN_SEL_FULL_' if self._select_mode == 'full' else 'BTN_SEL_'
            btn_name += str(idx)
            btn = getattr(self, btn_name)
            if sel_i < len(selection):
                # check type of selection
                self._active[btn] = selection[sel_i]
                sel_value = self.get_value(btn)
                sel_name = self.get_name(btn)
                if sel_name == self._selected:
                    self.set_component_text_color(btn, COLORS['component_accent'])
                self.set_component_text(btn, sel_value)
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

    def callback_function_component(self, fnc_id, fnc_name):
        if fnc_id != self.FNC_BTN_R_SEC:
            return

        current_page = self._current_page + 1
        if (current_page * self._items_per_page) > len(self._selection):
            current_page = 0
        self._current_page = current_page

        self.start_rec_cmd()
        self.set_selection()
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
            navigation = self.app.controller['navigation']
            navigation.close_panel()

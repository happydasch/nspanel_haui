from threading import Timer

from ..mapping.color import COLORS
from ..config import HAUIConfigPanel

from . import HAUIPage


class SelectPage(HAUIPage):
    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # full width buttons
    BTN_SEL_FULL_1, BTN_SEL_FULL_2 = (7, "bSelFull1"), (8, "bSelFull2")
    BTN_SEL_FULL_3, BTN_SEL_FULL_4 = (9, "bSelFull3"), (10, "bSelFull4")
    # default buttons
    BTN_SEL_1, BTN_SEL_2, BTN_SEL_3 = (11, "bSel1"), (12, "bSel2"), (13, "bSel3")
    BTN_SEL_4, BTN_SEL_5, BTN_SEL_6 = (14, "bSel4"), (15, "bSel5"), (16, "bSel6")
    BTN_SEL_7, BTN_SEL_8, BTN_SEL_9 = (17, "bSel7"), (18, "bSel8"), (19, "bSel9")
    BTN_SEL_10, BTN_SEL_11, BTN_SEL_12 = (20, "bSel10"), (21, "bSel11"), (22, "bSel12")

    ITEMS_PER_PAGE_DEFAULT = 12
    ITEMS_PER_PAGE_FULL = 4

    _select_mode = []
    _items = []
    _selected = None
    _multiple = False
    _multiple_delay = 1.5
    _multiple_timer = None
    _close_on_select = True
    _current_page = 0
    _active = {}  # active items currently being displayed
    _items_per_page = 0  # number of items per page
    _selection_callback_fnc = None
    _close_callback_fnc = None

    # panel

    def start_panel(self, panel: HAUIConfigPanel):
        # set function buttons
        page_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": self.ICO_NEXT_PAGE,
                "color": COLORS["component_accent"],
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            page_btn,
        )
        # get params
        self._select_mode = panel.get("select_mode", self._select_mode)
        self._items = panel.get("items", self._items)
        self._selected = panel.get("selected", self._selected)
        self._multiple = panel.get("multiple", self._multiple)
        self._multiple_delay = panel.get("multiple_delay", self._multiple_delay)
        self._close_on_select = panel.get("close_on_select", self._close_on_select)
        self._selection_callback_fnc = panel.get("selection_callback_fnc")
        self._close_callback_fnc = panel.get("close_callback_fnc")
        # prepare items
        items_per_page = self.ITEMS_PER_PAGE_DEFAULT
        if self._select_mode == "full":
            items_per_page = self.ITEMS_PER_PAGE_FULL
        self._items_per_page = items_per_page
        # set function components
        for i in range(self.ITEMS_PER_PAGE_DEFAULT):
            idx = i + 1
            btn = getattr(self, "BTN_SEL_" + str(idx))
            self.set_function_component(
                btn, btn[1], color=COLORS["component_active"], visible=False
            )
            self.add_component_callback(btn, self.callback_select)
        for i in range(self.ITEMS_PER_PAGE_FULL):
            idx = i + 1
            btn = getattr(self, "BTN_SEL_FULL_" + str(idx))
            self.set_function_component(
                btn, btn[1], color=COLORS["component_active"], visible=False
            )
            self.add_component_callback(btn, self.callback_select)
        # check if selection is list if multiple or string if not
        if self._multiple:
            if isinstance(self._selected, list):
                # make sure to use a new list
                self._selected = self._selected.copy()
            else:
                self._selected = list(self._selected)
        elif not self._multiple and not isinstance(self._selected, str):
            if isinstance(self._selected, list) and len(self._selected) > 0:
                self._selected = self._selected[0]
            else:
                self._selected = str(self._selected)

    def stop_panel(self, panel):
        if self._multiple_timer is not None:
            self._multiple_timer.run()
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def before_render_panel(self, panel):
        selection = self._items
        # check if a selection is provided
        navigation = self.app.controller["navigation"]
        if selection is None or len(selection) == 0:
            self.log("No selection provided, at least 1 selection item is required")
            navigation.close_panel()
            return False
        return True

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_items()

    # misc

    def _notify_selection_single(self):
        self._selection_callback_fnc(self._selected)
        # close on select
        if self._close_on_select:
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    def _notify_selection_multiple(self):
        self._start_selection_timer()

    def _start_selection_timer(self):
        self._stop_selection_timer()
        self._multiple_timer = Timer(
            self._multiple_delay, self._finish_selection_multiple
        )
        self._multiple_timer.daemon = True
        self._multiple_timer.start()

    def _stop_selection_timer(self):
        if self._multiple_timer is not None:
            self._multiple_timer.cancel()
            self._multiple_timer = None

    def _finish_selection_multiple(self):
        self._stop_selection_timer()
        self._selection_callback_fnc(self._selected)
        if self._close_on_select:
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    def set_items(self):
        selection = self._items
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
            btn_name = "BTN_SEL_FULL_" if self._select_mode == "full" else "BTN_SEL_"
            btn_name += str(idx)
            btn = getattr(self, btn_name)
            if sel_i < len(selection):
                # check type of selection
                self._active[btn] = selection[sel_i]
                sel_value = self.get_value(btn)
                sel_name = self.get_name(btn)
                color = COLORS["component_active"]
                # selected can also be a list
                if self._multiple and sel_value in self._selected:
                    color = COLORS["component_accent"]
                elif not self._multiple and sel_value == self._selected:
                    color = COLORS["component_accent"]
                self.update_function_component(
                    btn[1], text=sel_name, color=color, visible=True
                )
            else:
                self._active[btn] = None
                self.update_function_component(btn[1], visible=False)

    def get_value(self, btn):
        if btn not in self._active:
            return None
        selection = self._active[btn]
        if isinstance(selection, str):
            return selection
        elif isinstance(selection, dict):
            return selection.get("value", "")
        elif isinstance(selection, (list, tuple)):
            return selection[0]
        return None

    def get_name(self, btn):
        if btn not in self._active:
            return None
        selection = self._active[btn]
        if isinstance(selection, str):
            return selection
        elif isinstance(selection, dict):
            return selection.get("name", "")
        elif isinstance(selection, (list, tuple)):
            return selection[1]
        return None

    # callback

    def callback_function_component(self, fnc_id, fnc_name):
        if fnc_id != self.FNC_BTN_R_SEC:
            return
        current_page = self._current_page + 1
        if (current_page * self._items_per_page) >= len(self._items):
            current_page = 0
        self._current_page = current_page
        self.start_rec_cmd()
        self.set_items()
        self.stop_rec_cmd(send_commands=True)

    def callback_select(self, event, component, button_state):
        if button_state:
            return

        # updated selected
        for x in self._active:
            if component == x:
                value = self.get_value(x)
                if self._multiple:
                    if value in self._selected:
                        self._selected.remove(value)
                    else:
                        self._selected.append(value)
                else:
                    if value == self._selected:
                        self._selected = None
                    else:
                        self._selected = value
                break
        self.start_rec_cmd()
        self.set_items()
        self.stop_rec_cmd(send_commands=True)

        # selection callback
        if self._selection_callback_fnc:
            if not self._multiple:
                self._notify_selection_single()
            else:
                self._notify_selection_multiple()

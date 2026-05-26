from __future__ import annotations

from collections.abc import Callable
from threading import Timer
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from ..mapping.icons import ICO_NEXT_PAGE


class SelectPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="select",
        page_name="select",
        label="Selection List",
        description="Item selection panel with multi-page support.",
        is_system=True,
        sys_panel_default={
            "key": "popup_select",
            "show_in_navigation": False,
        },
        can_show_popup=True,
        icon="mdi:format-list-bulleted",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_sel_full_1=Component(8, "bSelFull1"),
        btn_sel_full_2=Component(9, "bSelFull2"),
        btn_sel_full_3=Component(10, "bSelFull3"),
        btn_sel_full_4=Component(11, "bSelFull4"),
        btn_sel_1=Component(12, "bSel1"),
        btn_sel_2=Component(13, "bSel2"),
        btn_sel_3=Component(14, "bSel3"),
        btn_sel_4=Component(15, "bSel4"),
        btn_sel_5=Component(16, "bSel5"),
        btn_sel_6=Component(17, "bSel6"),
        btn_sel_7=Component(18, "bSel7"),
        btn_sel_8=Component(19, "bSel8"),
        btn_sel_9=Component(20, "bSel9"),
        btn_sel_10=Component(21, "bSel10"),
        btn_sel_11=Component(22, "bSel11"),
        btn_sel_12=Component(23, "bSel12"),
    )

    ITEMS_PER_PAGE_DEFAULT = 12
    ITEMS_PER_PAGE_FULL = 4

    # panel

    def prepare(self) -> None:

        self._select_mode: list = []
        self._items: list = []
        self._selected: Any = None
        self._multiple = False
        self._multiple_delay = 1.5
        self._multiple_timer: Timer | None = None
        self._close_on_select = True
        self._current_page = 0
        self._active: dict = {}
        self._items_per_page = 0
        self._selection_callback_fnc: Callable[..., Any] | None = None
        self._close_callback_fnc = None

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        page_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": ICO_NEXT_PAGE,
                "color": self.get_color("component_accent"),
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            page_btn,
        )
        # get params
        self._select_mode = panel.get("select_mode", self._select_mode)
        self._items = panel.get("items", self._items)
        self._selected = panel.get("selected", self._selected)
        self._multiple = panel.get("multiple", self._multiple)
        self._multiple_delay = panel.get("multiple_delay", self._multiple_delay)
        self._close_on_select = panel.get("close_on_select", self._close_on_select)
        self._selection_callback_fnc = panel.get("selection_callback_fnc", None)
        self._close_callback_fnc = panel.get("close_callback_fnc", None)
        # prepare items
        items_per_page = self.ITEMS_PER_PAGE_DEFAULT
        if self._select_mode == "full":
            items_per_page = self.ITEMS_PER_PAGE_FULL
        self._items_per_page = items_per_page
        # set function components
        for i in range(self.ITEMS_PER_PAGE_DEFAULT):
            idx = i + 1
            btn = getattr(self.COMPONENTS, "btn_sel_" + str(idx))
            self.set_function_component(
                btn, btn[1], color=self.get_color("component_active"), visible=False
            )
            self.add_component_callback(btn, self.callback_select)
        for i in range(self.ITEMS_PER_PAGE_FULL):
            idx = i + 1
            btn = getattr(self.COMPONENTS, "btn_sel_full_" + str(idx))
            self.set_function_component(
                btn, btn[1], color=self.get_color("component_active"), visible=False
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

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        if self._multiple_timer is not None:
            self._multiple_timer.run()
        if self._close_callback_fnc:
            self._close_callback_fnc()

    def before_render_panel(self, panel: HAUIPanel) -> bool:
        selection = self._items
        # check if a selection is provided
        navigation = self.app.controller["navigation"]
        if selection is None or len(selection) == 0:
            self.log("No selection provided, at least 1 selection item is required")
            navigation.close_panel()
            return False
        return True

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, panel.get_title())
        self.set_items()

    # misc

    def _notify_selection_single(self) -> None:
        assert self._selection_callback_fnc is not None
        self._selection_callback_fnc(self._selected)
        # close on select
        if self._close_on_select:
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    def _notify_selection_multiple(self) -> None:
        self._start_selection_timer()

    def _start_selection_timer(self) -> None:
        self._stop_selection_timer()
        self._multiple_timer = Timer(self._multiple_delay, self._finish_selection_multiple)
        self._multiple_timer.daemon = True
        self._multiple_timer.start()

    def _stop_selection_timer(self) -> None:
        if self._multiple_timer is not None:
            self._multiple_timer.cancel()
            self._multiple_timer = None

    def _finish_selection_multiple(self) -> None:
        self._stop_selection_timer()
        assert self._selection_callback_fnc is not None
        self._selection_callback_fnc(self._selected)
        if self._close_on_select:
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    def set_items(self) -> None:
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
            btn_name = "btn_sel_full_" if self._select_mode == "full" else "btn_sel_"
            btn_name += str(idx)
            btn = getattr(self, btn_name)
            if sel_i < len(selection):
                # check type of selection
                self._active[btn] = selection[sel_i]
                sel_value = self.get_value(btn)
                sel_name = self.get_name(btn)
                color = self.get_color("component_active")
                # selected can also be a list
                if self._multiple and sel_value in self._selected:
                    color = self.get_color("component_accent")
                elif not self._multiple and sel_value == self._selected:
                    color = self.get_color("component_accent")
                self.update_function_component(btn[1], text=sel_name, color=color, visible=True)
            else:
                self._active[btn] = None
                self.update_function_component(btn[1], visible=False)

    def get_value(self, btn: tuple) -> str | None:
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

    def get_name(self, btn: tuple) -> str | None:
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

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id != self.FNC_BTN_R_SEC:
            return
        current_page = self._current_page + 1
        if (current_page * self._items_per_page) >= len(self._items):
            current_page = 0
        self._current_page = current_page
        with self.rec_cmd:
            self.set_items()

    def callback_select(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
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
        with self.rec_cmd:
            self.set_items()

        # selection callback
        if self._selection_callback_fnc:
            if not self._multiple:
                self._notify_selection_single()
            else:
                self._notify_selection_multiple()

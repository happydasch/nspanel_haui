from __future__ import annotations

import math
from typing import Any

from ..abstract.event import HAUIEvent
from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..features import CoverFeatures
from ..mapping.color import COLORS
from ..mapping.const import ESPRequest, ESPResponse
from ..mapping.descriptor import PageDescriptor, PageOption
from ..utils.icon import get_icon, get_icon_name_by_action
from ..utils.text import trim_text
from . import HAUIPage


class RowPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="row",
        page_name="row",
        label="Row",
        description="Row of entities with cover/action controls.",
        options=[
            PageOption(
                key="items",
                kind="item_list",
                label="Items",
                section="Items",
            ),
            PageOption(
                key="initial_page",
                kind="int",
                default=0,
                label="Initial page",
                section="Pagination",
            ),
        ],
    )

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # row entities
    R1_ICO, R1_NAME, R1_BTN_UP, R1_BTN_STOP, R1_BTN_DOWN = (
        (7, "r1Icon"),
        (8, "r1Name"),
        (9, "r1BtnUp"),
        (10, "r1BtnStop"),
        (11, "r1BtnDown"),
    )
    R1_TOGGLE, R1_SLIDER, R1_SLIDER_TXT, R1_BTN_TXT, R1_OVL = (
        (12, "r1Toggle"),
        (13, "r1Slider"),
        (14, "r1SliderTxt"),
        (15, "r1BtnText"),
        (16, "r1Overlay"),
    )
    R2_ICO, R2_NAME, R2_BTN_UP, R2_BTN_STOP, R2_BTN_DOWN = (
        (17, "r2Icon"),
        (18, "r2Name"),
        (19, "r2BtnUp"),
        (20, "r2BtnStop"),
        (21, "r2BtnDown"),
    )
    R2_TOGGLE, R2_SLIDER, R2_SLIDER_TXT, R2_BTN_TXT, R2_OVL = (
        (22, "r2Toggle"),
        (23, "r2Slider"),
        (24, "r2SliderTxt"),
        (25, "r2BtnText"),
        (26, "r2Overlay"),
    )
    R3_ICO, R3_NAME, R3_BTN_UP, R3_BTN_STOP, R3_BTN_DOWN = (
        (27, "r3Icon"),
        (28, "r3Name"),
        (29, "r3BtnUp"),
        (30, "r3BtnStop"),
        (31, "r3BtnDown"),
    )
    R3_TOGGLE, R3_SLIDER, R3_SLIDER_TXT, R3_BTN_TXT, R3_OVL = (
        (32, "r3Toggle"),
        (33, "r3Slider"),
        (34, "r3SliderTxt"),
        (35, "r3BtnText"),
        (36, "r3Overlay"),
    )
    R4_ICO, R4_NAME, R4_BTN_UP, R4_BTN_STOP, R4_BTN_DOWN = (
        (37, "r4Icon"),
        (38, "r4Name"),
        (39, "r4BtnUp"),
        (40, "r4BtnStop"),
        (41, "r4BtnDown"),
    )
    R4_TOGGLE, R4_SLIDER, R4_SLIDER_TXT, R4_BTN_TXT, R4_OVL = (
        (42, "r4Toggle"),
        (43, "r4Slider"),
        (44, "r4SliderTxt"),
        (45, "r4BtnText"),
        (46, "r4Overlay"),
    )
    R5_ICO, R5_NAME, R5_BTN_UP, R5_BTN_STOP, R5_BTN_DOWN = (
        (47, "r5Icon"),
        (48, "r5Name"),
        (49, "r5BtnUp"),
        (50, "r5BtnStop"),
        (51, "r5BtnDown"),
    )
    R5_TOGGLE, R5_SLIDER, R5_SLIDER_TXT, R5_BTN_TXT, R5_OVL = (
        (52, "r5Toggle"),
        (53, "r5Slider"),
        (54, "r5SliderTxt"),
        (55, "r5BtnText"),
        (56, "r5Overlay"),
    )
    # additional icons
    ICO_COVER_UP = get_icon("mdi:chevron-up")
    ICO_COVER_DOWN = get_icon("mdi:chevron-down")
    ICO_COVER_STOP = get_icon("mdi:stop")
    # definitions
    NUM_ROWS = 5
    LEN_NAME = 20

    # panel

    def start_page(self) -> None:
        self._items: list[HAUIItem] = []
        self._active_items: dict[tuple, HAUIItem | None] = {}
        self._active_handles: list = []
        self._current_page: int = 0
        self._pending_item_updates: set[str] = set()

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._items = panel.get_items()
        self._current_page = panel.get("initial_page", 0)
        # set function buttons
        show_in_nav = panel.show_in_navigation()
        nav_btn: dict = {
            "fnc_component": (
                self.BTN_FNC_RIGHT_SEC if show_in_nav else self.BTN_FNC_RIGHT_PRI
            ),
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": self.ICO_NEXT_PAGE,
                "color": COLORS["component_accent"],
                "visible": len(self._items) > self.NUM_ROWS,
            },
        }
        btn_right_1: tuple | dict
        btn_right_2: tuple | dict
        if show_in_nav:
            btn_right_1 = self.BTN_FNC_RIGHT_PRI
            btn_right_2 = nav_btn
        else:
            btn_right_1 = nav_btn
            btn_right_2 = self.BTN_FNC_RIGHT_SEC
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            btn_right_1,
            btn_right_2,
        )
        # set item overlay callbacks
        for i in range(self.NUM_ROWS):
            idx = i + 1
            ico = getattr(self, f"R{idx}_ICO")
            name = getattr(self, f"R{idx}_NAME")
            ovl = getattr(self, f"R{idx}_OVL")
            btn_text = getattr(self, f"R{idx}_BTN_TXT")
            btn_up = getattr(self, f"R{idx}_BTN_UP")
            btn_down = getattr(self, f"R{idx}_BTN_DOWN")
            btn_stop = getattr(self, f"R{idx}_BTN_STOP")
            toggle = getattr(self, f"R{idx}_TOGGLE")
            slider = getattr(self, f"R{idx}_SLIDER")
            slider_txt = getattr(self, f"R{idx}_SLIDER_TXT")
            self.set_function_component(ico, ico[1], "icon", row_index=i)
            self.set_function_component(name, name[1], "name", row_index=i)
            self.set_function_component(ovl, ovl[1], "overlay", row_index=i)
            self.set_function_component(
                btn_text, btn_text[1], "btn_text", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_up, btn_up[1], "btn_up", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_down, btn_down[1], "btn_down", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_stop, btn_stop[1], "btn_stop", visible=False, text="", row_index=i
            )
            self.set_function_component(
                toggle, toggle[1], "toggle", visible=False, value=0, row_index=i
            )
            self.set_function_component(
                slider, slider[1], "slider", visible=False, value=0, row_index=i
            )
            self.set_function_component(
                slider_txt,
                slider_txt[1],
                "slider_txt",
                visible=False,
                text="",
                row_index=i,
            )

    def stop_panel(self, panel: HAUIPanel) -> None:
        # cancel any pending debounced item-state updates
        self.debouncer.cancel("row_item_state")
        self._pending_item_updates.clear()
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_row_entries()

    # misc

    def set_row_entries(self) -> None:
        # check if there are any listener active and cancel them
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)
        # get current entities to display
        start = 0 + (self._current_page * self.NUM_ROWS)
        end = min(len(self._items), start + self.NUM_ROWS)
        if len(self._items) > start:
            items = self._items[start:end]
        else:
            items = []
        # set buttons
        item_ids = set()
        for i in range(self.NUM_ROWS):
            item = None
            idx = i + 1
            if i < len(items):
                item = items[i]
            # click events are captured by overlay, assign
            # entities to overlay
            ovl = getattr(self, f"R{idx}_OVL")
            self._active_items[ovl] = item
            # visibility of row entry
            visible = False
            if item is not None:
                # internal item
                if item.is_internal():
                    internal_type = item.get_internal_type()
                    if internal_type in ["navigate", "action"]:
                        visible = True
                # standard item
                else:
                    visible = True
                    item_ids.add(item.get_item_id())
            self.set_row_entry(idx, visible=visible)
        # create listener for active entities
        for item_id in item_ids:
            handle = self.add_item_listener(
                item_id, self.callback_item_state, attribute="all"
            )
            self._active_handles.append(handle)

    def set_row_entry(self, idx: int, visible: bool = True) -> None:
        # visibility of row entry components
        ovl = getattr(self, f"R{idx}_OVL")
        item = self._active_items[ovl]
        # detail visibility
        detail_visible = None
        if item is not None:
            detail_visible = self.get_item_display_type(item)
        # visibility
        if visible:
            # left part of item
            for n in ["ICO", "NAME", "OVL"]:
                item = getattr(self, f"R{idx}_{n}")
                self.update_function_component(item[1], visible=True)
            # detail part of item
            for n in [
                "BTN_TXT",
                "BTN_UP",
                "BTN_STOP",
                "BTN_DOWN",
                "TOGGLE",
                "SLIDER",
                "SLIDER_TXT",
            ]:
                item = getattr(self, f"R{idx}_{n}")
                show = False
                readonly = None
                color = None
                back_color = None
                back_color_pressed = None
                # check detail
                if detail_visible:
                    # 'BTN_UP', 'BTN_STOP', 'BTN_DOWN' cover control
                    if detail_visible == "cover":
                        if n in ["BTN_UP", "BTN_DOWN", "BTN_STOP"]:
                            show = True
                    # 'TOGGLE' on / off control
                    elif detail_visible == "toggle":
                        if n == "TOGGLE":
                            show = True
                    # 'SLIDER', 'SLIDER_TXT' value slider
                    elif detail_visible == "slider":
                        if n in ["SLIDER", "SLIDER_TXT"]:
                            show = True
                    # BTN_TXT
                    elif detail_visible == "button":
                        if n == "BTN_TXT":
                            show = True
                            readonly = False
                            color = COLORS["component_active"]
                            back_color = COLORS["component_background"]
                            back_color_pressed = COLORS["component_pressed"]
                    # 'BTN_TXT' will be used as default, text as disabled btn
                    elif n == "BTN_TXT":
                        show = True
                        readonly = True
                        color = COLORS["component"]
                        back_color = COLORS["background"]
                        back_color_pressed = COLORS["background"]
                # update component
                self.update_function_component(
                    item[1],
                    visible=show,
                    touch=not readonly,
                    color=color,
                    back_color=back_color,
                    back_color_pressed=back_color_pressed,
                )
                self.update_row_entry(idx)
        else:
            for n in [
                "ICO",
                "NAME",
                "OVL",
                "BTN_UP",
                "BTN_STOP",
                "BTN_DOWN",
                "TOGGLE",
                "SLIDER",
                "SLIDER_TXT",
                "BTN_TXT",
            ]:
                item = getattr(self, f"R{idx}_{n}")
                self.update_function_component(item[1], visible=False)

    def update_row_entries(self) -> None:
        items = self._active_items
        # row entries
        for idx in range(1, self.NUM_ROWS + 1):
            if idx > len(items):
                break
            self.update_row_entry(idx)

    def update_row_entry(self, idx: int) -> None:
        ovl = getattr(self, f"R{idx}_OVL")
        item = self._active_items[ovl]
        if item is None:
            return
        ico = getattr(self, f"R{idx}_ICO")
        name = getattr(self, f"R{idx}_NAME")
        self.update_function_component(name[1], text=trim_text(item.get_name(), self.LEN_NAME))
        self.update_function_component(ico[1], text=item.get_icon(), color=item.get_color())
        display_type = self.get_item_display_type(item)
        if display_type == "text":
            self.update_item_text(item, idx)
        elif display_type == "button":
            self.update_item_button(item, idx)
        elif display_type == "toggle":
            self.update_item_toggle(item, idx)
        elif display_type == "timer":
            self.update_item_timer(item, idx)
        elif display_type == "slider":
            self.update_item_slider(item, idx)
        elif display_type == "cover":
            self.update_item_cover(item, idx)

    # item detail

    def get_item_display_type(self, haui_item: HAUIItem) -> str:
        """Returns how the item should be displayed.

        Entities support different display types:
        - text (button with touch disabled)
        - button (button)
        - number (slider with number)
        - timer (button)
        - cover (3 buttons: up, stop, down)

        Args:
            haui_item (HAUIItem): item

        Returns:
            str: display type
        """
        item_type = haui_item.get_item_type()
        # default display type is text
        display_type = "text"
        # check for special cases
        if item_type == "cover":
            display_type = "cover"
        elif item_type in [
            "button",
            "input_button",
            "scene",
            "script",
            "lock",
            "vacuum",
        ]:
            display_type = "button"
        elif item_type in ["number", "input_number"]:
            display_type = "slider"
        elif item_type == "timer":
            display_type = "timer"
        elif item_type in ["switch", "input_boolean", "automation", "light"]:
            display_type = "toggle"

        return display_type

    def update_item_text(self, haui_item: HAUIItem, idx: int) -> None:
        item = getattr(self, f"R{idx}_BTN_TXT")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_button(self, haui_item: HAUIItem, idx: int) -> None:
        item = getattr(self, f"R{idx}_BTN_TXT")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_timer(self, haui_item: HAUIItem, idx: int) -> None:
        item = getattr(self, f"R{idx}_BTN_TXT")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_toggle(self, haui_item: HAUIItem, idx: int) -> None:
        toggle = getattr(self, f"R{idx}_TOGGLE")
        value = 0 if haui_item.get_item_state() == "off" else 1
        self.update_function_component(toggle[1], value=value)

    def update_item_slider(self, haui_item: HAUIItem, idx: int) -> None:
        slider = getattr(self, f"R{idx}_SLIDER")
        slider_txt = getattr(self, f"R{idx}_SLIDER_TXT")
        # get values needed for slider
        value = str(haui_item.get_item_state() or "0")
        minval = float(haui_item.get_item_attr("min", 0))
        maxval = float(haui_item.get_item_attr("max", 100))
        step = str(haui_item.get_item_attr("step", 1))
        dot_pos = 0 if float(step) >= 1 else step[::-1].find(".")
        scale_factor = int(10**dot_pos)
        # get internal values for slider
        i_value = int(value.replace(".", ""))
        i_minval = int(minval * scale_factor)
        i_maxval = int(maxval * scale_factor) - i_minval
        i_value = int(i_value - i_minval)
        # update display
        self.send_cmd(f"{slider[1]}.minval={0}")
        self.send_cmd(f"{slider[1]}.maxval={i_maxval}")
        self.update_function_component(slider[1], value=i_value)
        self.update_function_component(slider_txt[1], text=value)

    def update_item_cover(self, haui_item: HAUIItem, idx: int) -> None:
        btn_up = getattr(self, f"R{idx}_BTN_UP")
        btn_stop = getattr(self, f"R{idx}_BTN_STOP")
        btn_down = getattr(self, f"R{idx}_BTN_DOWN")
        icon_up = ""
        icon_stop = ""
        icon_down = ""
        icon_up_status = False
        icon_stop_status = False
        icon_down_status = False
        item_type = haui_item.get_item_type()
        item_state = haui_item.get_item_state()
        features = haui_item.get_item_attr("supported_features")
        pos = haui_item.get_item_attr("current_position")
        device_class = haui_item.get_item_attr("device_class", "window")

        if features & CoverFeatures.OPEN:  # SUPPORT_OPEN
            if pos != 100 and not (item_state == "open" and pos == "disable"):
                icon_up_status = True
            icon_up = get_icon_name_by_action(
                item_type=item_type, action="open", device_class=device_class
            ) or ""
            icon_up = get_icon(icon_up) or ""
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(icon_up_status)
        self.update_function_component(
            btn_up[1],
            visible=True,
            text=icon_up,
            color=color,
            color_pressed=color_pressed,
            back_color=back_color,
            back_color_pressed=back_color_pressed,
        )

        if features & CoverFeatures.STOP:  # SUPPORT_STOP
            icon_stop = get_icon_name_by_action(
                item_type=item_type, action="stop", device_class=device_class
            ) or ""
            icon_stop = get_icon(icon_stop) or ""
            if item_state not in ["open", "close"]:
                icon_stop_status = True
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(icon_stop_status)
        self.update_function_component(
            btn_stop[1],
            visible=True,
            text=icon_stop,
            color=color,
            color_pressed=color_pressed,
            back_color=back_color,
            back_color_pressed=back_color_pressed,
        )

        if features & CoverFeatures.CLOSE:  # SUPPORT_CLOSE
            if pos != 0 and not (item_state == "closed" and pos == "disable"):
                icon_down_status = True
            icon_down = get_icon_name_by_action(
                item_type=item_type, action="close", device_class=device_class
            ) or ""
            icon_down = get_icon(icon_down) or ""
        (
            color,
            color_pressed,
            back_color,
            back_color_pressed,
        ) = self.get_button_colors(icon_down_status)
        self.update_function_component(
            btn_down[1],
            visible=True,
            text=icon_down,
            color=color,
            color_pressed=color_pressed,
            back_color=back_color,
            back_color_pressed=back_color_pressed,
        )

    # callback

    def callback_item_state(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        item_ids = {
            haui_item.get_item_id()
            for haui_item in self._active_items.values()
            if haui_item is not None
        }
        if item not in item_ids:
            return
        # Coalesce rapid attribute updates into a single redraw to avoid
        # flooding the Nextion UART, which delays touch-event delivery.
        self._pending_item_updates.add(item)
        self.debouncer.call("row_item_state", self._flush_item_updates)

    def _flush_item_updates(self) -> None:
        # Swap pending set first so concurrent adds aren't lost on clear.
        pending = self._pending_item_updates
        if not pending:
            return
        self._pending_item_updates = set()
        with self.rec_cmd:
            idx = 0
            for haui_item in self._active_items.values():
                idx += 1
                if haui_item is None:
                    continue
                if haui_item.get_item_id() in pending:
                    self.update_row_entry(idx)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_name == "next_page":
            count_pages = math.ceil(len(self._items) / self.NUM_ROWS)
            self._current_page += 1
            if self._current_page >= count_pages:
                self._current_page = 0
            with self.rec_cmd:
                self.set_row_entries()

        items = self.get_function_components()
        item = items[fnc_id]
        i = item["fnc_args"].get("row_index", -1)
        if i < 0:
            return
        ovl = getattr(self, f"R{i + 1}_OVL")
        item = self._active_items[ovl]
        if item is None:
            return
        # row actions
        if fnc_name == "overlay":
            self.execute_item(item)
        elif fnc_name == "btn_text":
            item.execute()
        elif fnc_name == "toggle":
            item.call_item_service("toggle")
        elif fnc_name == "slider":
            self.send_esphome(ESPRequest.REQ_VAL, item["fnc_component"][1], force=True)
        elif fnc_name == "btn_up":
            item.call_item_service("open_cover")
        elif fnc_name == "btn_stop":
            item.call_item_service("stop_cover")
        elif fnc_name == "btn_down":
            item.call_item_service("close_cover")

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        # check for values for full and dimmed brightness
        if event.name == ESPResponse.RES_VAL:
            # parse json response, set brightness
            data = event.as_json()
            items = self.get_function_components()
            item = items[data["name"]]
            i = item["fnc_args"].get("row_index", -1)
            if i < 0:
                return
            ovl = getattr(self, f"R{i + 1}_OVL")
            item = self._active_items[ovl]
            if item is None:
                return
            step = str(item.get_item_attr("step", "1"))
            dot_pos = 0 if float(step) >= 1 else step[::-1].find(".")
            scale_factor = int(10**dot_pos)
            minval = float(item.get_item_attr("min", 0))
            i_minval = int(minval * scale_factor)
            n_value = (int(data["value"]) + i_minval) / scale_factor
            entity_object = item.get_item()
            if entity_object:
                entity_object.set_state(state=n_value)

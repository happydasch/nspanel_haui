from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import CoverFeatures
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_NEXT_PAGE
from ..utils.icon import get_icon, get_icon_name_by_action
from ..utils.text import trim_text


class RowPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="row",
        page_name="row",
        page_id=10,
        label=_("Row"),
        description=_("Row of entities with cover/action controls."),
        options=[
            PageOption(
                key="items",
                kind="item_list",
                description=_("Items displayed as a row with cover/action controls."),
                section=_("Rows"),
            ),
        ],
        icon="mdi:view-list-outline",
    )
    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        # r1
        r1_ico=Component(8, "r1Icon"),
        r1_name=Component(9, "r1Name"),
        r1_ovl=Component(10, "r1Overlay"),
        r1_btn_up=Component(11, "r1BtnUp"),
        r1_btn_stop=Component(12, "r1BtnStop"),
        r1_btn_down=Component(13, "r1BtnDown"),
        r1_slider=Component(14, "r1Slider"),
        r1_slider_txt=Component(15, "r1SliderTxt"),
        r1_btn_txt=Component(16, "r1BtnText"),
        r1_toggle=Component(17, "r1Toggle"),
        # r2
        r2_ico=Component(18, "r2Icon"),
        r2_name=Component(19, "r2Name"),
        r2_ovl=Component(20, "r2Overlay"),
        r2_btn_up=Component(21, "r2BtnUp"),
        r2_btn_stop=Component(22, "r2BtnStop"),
        r2_btn_down=Component(23, "r2BtnDown"),
        r2_slider=Component(24, "r2Slider"),
        r2_slider_txt=Component(25, "r2SliderTxt"),
        r2_btn_txt=Component(26, "r2BtnText"),
        r2_toggle=Component(27, "r2Toggle"),
        # r3
        r3_ico=Component(28, "r3Icon"),
        r3_name=Component(29, "r3Name"),
        r3_ovl=Component(30, "r3Overlay"),
        r3_btn_up=Component(31, "r3BtnUp"),
        r3_btn_stop=Component(32, "r3BtnStop"),
        r3_btn_down=Component(33, "r3BtnDown"),
        r3_slider=Component(34, "r3Slider"),
        r3_slider_txt=Component(35, "r3SliderTxt"),
        r3_btn_txt=Component(36, "r3BtnText"),
        r3_toggle=Component(37, "r3Toggle"),
        # r4
        r4_ico=Component(38, "r4Icon"),
        r4_name=Component(39, "r4Name"),
        r4_ovl=Component(40, "r4Overlay"),
        r4_btn_up=Component(41, "r4BtnUp"),
        r4_btn_stop=Component(42, "r4BtnStop"),
        r4_btn_down=Component(43, "r4BtnDown"),
        r4_slider=Component(44, "r4Slider"),
        r4_slider_txt=Component(45, "r4SliderTxt"),
        r4_btn_txt=Component(46, "r4BtnText"),
        r4_toggle=Component(47, "r4Toggle"),
        # r5
        r5_ico=Component(48, "r5Icon"),
        r5_name=Component(49, "r5Name"),
        r5_ovl=Component(50, "r5Overlay"),
        r5_btn_up=Component(51, "r5BtnUp"),
        r5_btn_stop=Component(52, "r5BtnStop"),
        r5_btn_down=Component(53, "r5BtnDown"),
        r5_slider=Component(54, "r5Slider"),
        r5_slider_txt=Component(55, "r5SliderTxt"),
        r5_btn_txt=Component(56, "r5BtnText"),
        r5_toggle=Component(57, "r5Toggle"),
    )
    # definitions
    NUM_ROWS = 5
    LEN_NAME = 20

    # panel

    def prepare(self) -> None:

        self._items: list[HAUIItem] = []
        self._active_items: dict[tuple, HAUIItem | None] = {}
        self._active_handles: list = []
        self._current_page: int = 0
        self._pending_item_updates: set[str] = set()

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._items = self._build_items_from_panel(panel, "items")
        # page position is navigation state, not a user option: it lives on
        # the panel (persists across visits) rather than being reset to a
        # configured initial page every time the panel opens.
        self._current_page = panel.get_state("current_page", 0)
        # set function buttons
        show_in_nav = panel.show_in_navigation()
        nav_btn: dict = {
            "fnc_component": (
                self.COMPONENTS.fnc_right_sec if show_in_nav else self.COMPONENTS.fnc_right_pri
            ),
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": ICO_NEXT_PAGE,
                "color": self.get_color("header_accent"),
                "visible": len(self._items) > self.NUM_ROWS,
            },
        }
        btn_right_1: tuple | dict
        btn_right_2: tuple | dict
        if show_in_nav:
            btn_right_1 = self.COMPONENTS.fnc_right_pri
            btn_right_2 = nav_btn
        else:
            btn_right_1 = nav_btn
            btn_right_2 = self.COMPONENTS.fnc_right_sec
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            btn_right_1,
            btn_right_2,
        )
        # set item overlay callbacks
        for i in range(self.NUM_ROWS):
            idx = i + 1
            ico = getattr(self.COMPONENTS, f"r{idx}_ico")
            name = getattr(self.COMPONENTS, f"r{idx}_name")
            ovl = getattr(self.COMPONENTS, f"r{idx}_ovl")
            btn_text = getattr(self.COMPONENTS, f"r{idx}_btn_txt")
            btn_up = getattr(self.COMPONENTS, f"r{idx}_btn_up")
            btn_down = getattr(self.COMPONENTS, f"r{idx}_btn_down")
            btn_stop = getattr(self.COMPONENTS, f"r{idx}_btn_stop")
            toggle = getattr(self.COMPONENTS, f"r{idx}_toggle")
            slider = getattr(self.COMPONENTS, f"r{idx}_slider")
            slider_txt = getattr(self.COMPONENTS, f"r{idx}_slider_txt")
            self.set_function_component(ico, ico[1], "icon", row_index=i)
            self.set_function_component(name, name[1], "name", row_index=i)
            self.set_function_component(ovl, ovl[1], "overlay", row_index=i, no_color=True)
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
            # row sliders are drag controls: suppress the swipe gesture
            # the drag produces, and register a read callback so the
            # slider value is read via a read request on release
            self.mark_drag_component(slider)
            self.add_component_callback(slider, self.process_row_slider, drag=True)
            self.add_read_callback(slider, self._make_row_slider_handler(slider))
            self.set_function_component(
                slider_txt,
                slider_txt[1],
                "slider_txt",
                visible=False,
                text="",
                row_index=i,
            )

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel any pending debounced item-state updates
        self.debouncer.cancel("row_item_state")
        self._pending_item_updates.clear()
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, panel.get_title())
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
            ovl = getattr(self.COMPONENTS, f"r{idx}_ovl")
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
            handle = self.add_item_listener(item_id, self.callback_item_state, attribute="all")
            self._active_handles.append(handle)

    def set_row_entry(self, idx: int, visible: bool = True) -> None:
        # visibility of row entry components
        ovl = getattr(self.COMPONENTS, f"r{idx}_ovl")
        item = self._active_items[ovl]
        # detail visibility
        detail_visible = None
        if item is not None:
            detail_visible = self.get_item_display_type(item)
        # visibility
        if visible:
            # left part of item
            for n in ["ico", "name", "ovl"]:
                item = getattr(self.COMPONENTS, f"r{idx}_{n}")
                self.update_function_component(item[1], visible=True)
            # detail part of item
            for n in [
                "btn_txt",
                "btn_up",
                "btn_stop",
                "btn_down",
                "toggle",
                "slider",
                "slider_txt",
            ]:
                item = getattr(self.COMPONENTS, f"r{idx}_{n}")
                show = False
                readonly = None
                color = None
                back_color = None
                back_color_pressed = None
                # check detail
                if detail_visible:
                    # 'btn_up', 'btn_stop', 'btn_down' cover control
                    if detail_visible == "cover":
                        if n in ["btn_up", "btn_down", "btn_stop"]:
                            show = True
                    # 'TOGGLE' on / off control
                    elif detail_visible == "toggle":
                        if n == "toggle":
                            show = True
                    # 'SLIDER', 'SLIDER_TXT' value slider
                    elif detail_visible == "slider":
                        if n in ["slider", "slider_txt"]:
                            show = True
                    # btn_txt
                    elif detail_visible == "button":
                        if n == "btn_txt":
                            show = True
                            readonly = False
                            color = self.get_color("component_active")
                            back_color = self.get_color("component_background")
                            back_color_pressed = self.get_color("component_pressed")
                    # 'btn_txt' will be used as default, text as disabled btn
                    elif n == "btn_txt":
                        show = True
                        readonly = True
                        color = self.get_color("component_text")
                        back_color = self.get_color("background")
                        back_color_pressed = self.get_color("background")
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
                "ico",
                "name",
                "ovl",
                "btn_up",
                "btn_stop",
                "btn_down",
                "toggle",
                "slider",
                "slider_txt",
                "btn_txt",
            ]:
                item = getattr(self.COMPONENTS, f"r{idx}_{n}")
                self.update_function_component(item[1], visible=False)

    def update_row_entries(self) -> None:
        items = self._active_items
        # row entries
        for idx in range(1, self.NUM_ROWS + 1):
            if idx > len(items):
                break
            self.update_row_entry(idx)

    def update_row_entry(self, idx: int) -> None:
        ovl = getattr(self.COMPONENTS, f"r{idx}_ovl")
        item = self._active_items[ovl]
        if item is None:
            return
        ico = getattr(self.COMPONENTS, f"r{idx}_ico")
        name = getattr(self.COMPONENTS, f"r{idx}_name")
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
        item = getattr(self.COMPONENTS, f"r{idx}_btn_txt")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_button(self, haui_item: HAUIItem, idx: int) -> None:
        item = getattr(self.COMPONENTS, f"r{idx}_btn_txt")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_timer(self, haui_item: HAUIItem, idx: int) -> None:
        item = getattr(self.COMPONENTS, f"r{idx}_btn_txt")
        self.update_function_component(item[1], text=haui_item.get_value())

    def update_item_toggle(self, haui_item: HAUIItem, idx: int) -> None:
        toggle = getattr(self.COMPONENTS, f"r{idx}_toggle")
        value = 0 if haui_item.get_item_state() == "off" else 1
        self.update_function_component(toggle[1], value=value)

    def update_item_slider(self, haui_item: HAUIItem, idx: int) -> None:
        slider = getattr(self.COMPONENTS, f"r{idx}_slider")
        slider_txt = getattr(self.COMPONENTS, f"r{idx}_slider_txt")
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
        self.set_slider_color(slider)
        self.update_function_component(slider_txt[1], text=value)

    def update_item_cover(self, haui_item: HAUIItem, idx: int) -> None:
        btn_up = getattr(self.COMPONENTS, f"r{idx}_btn_up")
        btn_stop = getattr(self.COMPONENTS, f"r{idx}_btn_stop")
        btn_down = getattr(self.COMPONENTS, f"r{idx}_btn_down")
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
            icon_up = (
                get_icon_name_by_action(
                    item_type=item_type, action="open", device_class=device_class
                )
                or ""
            )
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
            icon_stop = (
                get_icon_name_by_action(
                    item_type=item_type, action="stop", device_class=device_class
                )
                or ""
            )
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
            icon_down = (
                get_icon_name_by_action(
                    item_type=item_type, action="close", device_class=device_class
                )
                or ""
            )
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
            if self.panel is not None:
                self.panel.set_state("current_page", self._current_page)
            with self.rec_cmd:
                self.set_row_entries()

        items = self.get_function_components()
        fnc_item = items[fnc_id]
        i = fnc_item["fnc_args"].get("row_index", -1)
        if i < 0:
            return
        ovl = getattr(self.COMPONENTS, f"r{i + 1}_ovl")
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
        elif fnc_name == "btn_up":
            item.call_item_service("open_cover")
        elif fnc_name == "btn_stop":
            item.call_item_service("stop_cover")
        elif fnc_name == "btn_down":
            item.call_item_service("close_cover")

    # event

    def _make_row_slider_handler(self, component: Component) -> Callable[[int], None]:
        """Create a value-callback handler bound to *component*."""

        def handler(value: int) -> None:
            self._handle_row_slider_value(component, value)

        return handler

    def _handle_row_slider_value(self, component: Component, value: int) -> None:
        """Handle a row slider value from a read_response event.

        Args:
            component: The slider component whose value was read.
            value: The slider value (0-100).
        """
        if not self._in_read_callback:
            self.log(
                f"_handle_row_slider_value ({component.name}): value={value} ignored "
                f"(not from read_response — likely button_state leak)"
            )
            return
        self.log(f"Row slider value {value} for {component.name}")
        self.debug_log(f"Row slider value {value} from {component.name}")
        for _item_id, fnc_item in self._fnc_items.items():
            if fnc_item["fnc_component"] != component:
                continue
            i = fnc_item["fnc_args"].get("row_index", -1)
            if i < 0:
                return
            ovl = getattr(self.COMPONENTS, f"r{i + 1}_ovl")
            item = self._active_items.get(ovl)
            if item is None:
                return
            step = str(item.get_item_attr("step", "1"))
            dot_pos = 0 if float(step) >= 1 else step[::-1].find(".")
            scale_factor = int(10**dot_pos)
            minval = float(item.get_item_attr("min", 0))
            i_minval = int(minval * scale_factor)
            n_value = (value + i_minval) / scale_factor
            entity_object = item.get_item()
            if entity_object:
                entity_object.set_state(state=n_value)
            return

    def process_row_slider(self, event: HAUIEvent, component: Component, button_state: int) -> None:
        """Legacy callback retained for _callbacks compatibility."""
        self._handle_row_slider_value(component, button_state)

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)

from __future__ import annotations

from collections.abc import Callable

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..abstract.mixins.paged_items_mixin import PagedItemsMixin
from ..features import CoverFeatures
from ..mapping.const import InternalItemType
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_NEXT_PAGE, ICO_TOGGLE_OFF, ICO_TOGGLE_ON
from ..utils.icon import get_icon, get_icon_name_by_action
from ..utils.text import TextBox, fit_line, text_width

_NAME_BOXES = {
    "landscape": TextBox(220, 50, 2, 20),
    "portrait": TextBox(262, 26, 2, 20),
}
_VALUE_BOXES = {
    "landscape": TextBox(150, 50, 2, 15),
    "portrait": TextBox(192, 50, 2, 15),
}
_SLIDER_TEXT_BOXES = {
    "landscape": TextBox(50, 50, 2, 10),
    "portrait": TextBox(52, 42, 2, 10),
}


def _fit_with_suffix(text: str, font: int, box: TextBox, suffix: str) -> str:
    """Fit text while reserving room for a suffix that must remain visible."""
    room = TextBox(
        box.width - text_width(suffix, font),
        box.height,
        box.border,
        box.max_len - len(suffix.encode()),
    )
    return f"{fit_line([text], font, room)}{suffix}"


class RowPage(PagedItemsMixin, HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="row",
        page_name="row",
        page_id=10,
        label=_("Row"),
        description=_("Row of entities with cover/action controls."),
        category="grouping",
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
        # icon
        r1_ico=Component(8, "r1Icon"),
        r2_ico=Component(9, "r2Icon"),
        r3_ico=Component(10, "r3Icon"),
        r4_ico=Component(11, "r4Icon"),
        r5_ico=Component(12, "r5Icon"),
        # name
        r1_name=Component(13, "r1Name"),
        r2_name=Component(14, "r2Name"),
        r3_name=Component(15, "r3Name"),
        r4_name=Component(16, "r4Name"),
        r5_name=Component(17, "r5Name"),
        # overlay
        r1_ovl=Component(18, "r1Overlay"),
        r2_ovl=Component(19, "r2Overlay"),
        r3_ovl=Component(20, "r3Overlay"),
        r4_ovl=Component(21, "r4Overlay"),
        r5_ovl=Component(22, "r5Overlay"),
        #
        r1_btn_up=Component(23, "r1BtnUp"),
        r2_btn_up=Component(24, "r2BtnUp"),
        r3_btn_up=Component(25, "r3BtnUp"),
        r4_btn_up=Component(26, "r4BtnUp"),
        r5_btn_up=Component(27, "r5BtnUp"),
        #
        r1_btn_stop=Component(28, "r1BtnStop"),
        r2_btn_stop=Component(29, "r2BtnStop"),
        r3_btn_stop=Component(30, "r3BtnStop"),
        r4_btn_stop=Component(31, "r4BtnStop"),
        r5_btn_stop=Component(32, "r5BtnStop"),
        #
        r1_btn_down=Component(33, "r1BtnDown"),
        r2_btn_down=Component(34, "r2BtnDown"),
        r3_btn_down=Component(35, "r3BtnDown"),
        r4_btn_down=Component(36, "r4BtnDown"),
        r5_btn_down=Component(37, "r5BtnDown"),
        #
        r1_btn_txt=Component(38, "r1BtnText"),
        r2_btn_txt=Component(39, "r2BtnText"),
        r3_btn_txt=Component(40, "r3BtnText"),
        r4_btn_txt=Component(41, "r4BtnText"),
        r5_btn_txt=Component(42, "r5BtnText"),
        #
        r1_slider=Component(43, "r1Slider"),
        r2_slider=Component(44, "r2Slider"),
        r3_slider=Component(45, "r3Slider"),
        r4_slider=Component(46, "r4Slider"),
        r5_slider=Component(47, "r5Slider"),
        #
        r1_slider_txt=Component(48, "r1SliderTxt"),
        r2_slider_txt=Component(49, "r2SliderTxt"),
        r3_slider_txt=Component(50, "r3SliderTxt"),
        r4_slider_txt=Component(51, "r4SliderTxt"),
        r5_slider_txt=Component(52, "r5SliderTxt"),
        #
        r1_toggle=Component(53, "r1Toggle"),
        r2_toggle=Component(54, "r2Toggle"),
        r3_toggle=Component(55, "r3Toggle"),
        r4_toggle=Component(56, "r4Toggle"),
        r5_toggle=Component(57, "r5Toggle"),
    )
    # definitions
    NUM_ROWS = 5

    # panel

    _DEBOUNCE_KEY = "row_item_state"

    _ROW_SERVICES = {
        "toggle": "toggle",
        "btn_up": "open_cover",
        "btn_stop": "stop_cover",
        "btn_down": "close_cover",
    }

    def prepare(self) -> None:
        self._init_paging()

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._items = self._build_items_from_panel(panel, "items")
        # page position is navigation state, not a user option: it lives on
        # the panel (persists across visits) rather than being reset to a
        # configured initial page every time the panel opens.
        self._current_page = panel.get_state("current_page", 0)
        # set function buttons
        # Pagination sits on fnc_right_sec (inner, beside the title) so
        # fnc_right_pri stays free for auto-assignment: NEXT in navigation,
        # CLOSE on a stacked panel.  Only claim the slot when there actually
        # is more than one page; otherwise _auto_assign_fncs() can put the
        # notification indicator there.  When pagination does claim it,
        # auto-assign moves the notification indicator onto the idle button's
        # left-secondary slot on the home panel.
        btn_right_sec: tuple | dict = self.COMPONENTS.fnc_right_sec
        if len(self._items) > self.NUM_ROWS:
            btn_right_sec = {
                "fnc_component": self.COMPONENTS.fnc_right_sec,
                "fnc_name": "next_page",
                "fnc_args": {
                    "icon": ICO_NEXT_PAGE,
                    "color": self.get_color("header_accent"),
                    "visible": True,
                },
            }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            btn_right_sec,
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
            self.set_function_component(ico, ico.name, "icon", row_index=i)
            self.set_function_component(name, name.name, "name", row_index=i)
            self.set_function_component(ovl, ovl.name, "overlay", row_index=i, no_color=True)
            self.set_function_component(
                btn_text, btn_text.name, "btn_text", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_up, btn_up.name, "btn_up", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_down, btn_down.name, "btn_down", visible=False, text="", row_index=i
            )
            self.set_function_component(
                btn_stop, btn_stop.name, "btn_stop", visible=False, text="", row_index=i
            )
            self.set_function_component(
                toggle, toggle.name, "toggle", visible=False, value=0, row_index=i
            )
            self.set_function_component(
                slider, slider.name, "slider", visible=False, value=0, row_index=i
            )
            # row sliders are drag controls: bind_slider suppresses the swipe
            # gesture the drag produces and reads the value on release
            self.bind_slider(slider, self._make_row_slider_handler(slider))
            self.set_function_component(
                slider_txt,
                slider_txt.name,
                "slider_txt",
                visible=False,
                text="",
                row_index=i,
            )

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_title(panel.get_title())
        self.set_row_entries()

    # misc

    def set_row_entries(self) -> None:
        # check if there are any listener active and cancel them
        self._clear_item_listeners()
        # get current entities to display
        items = self._page_items(self.NUM_ROWS)
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
                    if internal_type in (
                        InternalItemType.NAVIGATE,
                        InternalItemType.ACTION,
                        InternalItemType.TEXT,
                    ):
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
                self.update_function_component(item.name, visible=True)
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
                color_pressed = None
                # the page paints the back colours (bco) while it loads
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
                            # dual-state icon on the page: pco is the off
                            # state, pco2 the on state
                            color = self.get_color("text_inactive")
                            color_pressed = self.get_color("component_active")
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
                            back_color_pressed = self.get_color("component_pressed")
                    # 'btn_txt' will be used as default, text as disabled btn
                    elif n == "btn_txt":
                        show = True
                        readonly = True
                        color = self.get_color("component_text")
                        back_color_pressed = self.get_color("background")
                # update component
                self.update_function_component(
                    item.name,
                    visible=show,
                    touch=not readonly,
                    color=color,
                    color_pressed=color_pressed,
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
                self.update_function_component(item.name, visible=False)

    def update_row_entry(self, idx: int) -> None:
        ovl = getattr(self.COMPONENTS, f"r{idx}_ovl")
        item = self._active_items[ovl]
        if item is None:
            return
        ico = getattr(self.COMPONENTS, f"r{idx}_ico")
        name = getattr(self.COMPONENTS, f"r{idx}_name")
        orientation = "portrait" if self.app.device.is_portrait else "landscape"
        self.update_function_component(
            name.name,
            text=fit_line([item.get_name()], 1, _NAME_BOXES[orientation]),
        )
        self.update_function_component(ico.name, text=item.get_icon(), color=item.get_color())
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
        self._update_item_value_cell(haui_item, idx, "component_text")

    def update_item_button(self, haui_item: HAUIItem, idx: int) -> None:
        self._update_item_value_cell(haui_item, idx, "component_active")

    def update_item_timer(self, haui_item: HAUIItem, idx: int) -> None:
        # The timer cell reuses the same rendering as the text cell.
        self._update_item_value_cell(haui_item, idx, "component_text")

    def _update_item_value_cell(self, haui_item: HAUIItem, idx: int, color_mode: str) -> None:
        item = getattr(self.COMPONENTS, f"r{idx}_btn_txt")
        self.update_function_component(
            item.name,
            text=self._value_cell_text(haui_item),
            color=self._value_cell_color(haui_item, color_mode),
        )

    def _item_stale(self, haui_item: HAUIItem) -> bool:
        """Whether the item's value is stale per the device's threshold.

        Returns:
            True when ``stale_data_seconds`` is configured and the item's
            entity has not updated within that window.
        """
        max_age = self.app.device.get("stale_data_seconds")
        try:
            max_age = int(max_age)
        except TypeError, ValueError:
            max_age = 0
        return haui_item.is_stale(max_age)

    def _value_cell_text(self, haui_item: HAUIItem) -> str:
        """Value text for a row cell, with a "…" suffix when stale."""
        text = haui_item.get_value()
        orientation = "portrait" if self.app.device.is_portrait else "landscape"
        box = _VALUE_BOXES[orientation]
        if text and self._item_stale(haui_item):
            return _fit_with_suffix(text, 1, box, " …")
        return fit_line([text], 1, box)

    def _value_cell_color(self, haui_item: HAUIItem, fresh_key: str) -> int:
        """Cell colour: dimmed while stale, restored to *fresh_key* otherwise."""
        if self._item_stale(haui_item):
            return self.get_color("text_inactive")
        return self.get_color(fresh_key)

    def update_item_toggle(self, haui_item: HAUIItem, idx: int) -> None:
        toggle = getattr(self.COMPONENTS, f"r{idx}_toggle")
        on = haui_item.get_item_state() != "off"
        # val picks the colour, but a dual-state button has one txt for both
        # states, so the icon is swapped too; one update sends val or txt, not
        # both, hence two calls
        self.update_function_component(toggle.name, value=int(on))
        self.update_function_component(toggle.name, text=ICO_TOGGLE_ON if on else ICO_TOGGLE_OFF)

    def update_item_slider(self, haui_item: HAUIItem, idx: int) -> None:
        slider = getattr(self.COMPONENTS, f"r{idx}_slider")
        slider_txt = getattr(self.COMPONENTS, f"r{idx}_slider_txt")
        # get values needed for slider
        state = haui_item.get_item_state()
        minval = float(haui_item.get_item_attr("min", 0))
        maxval = float(haui_item.get_item_attr("max", 100))
        step = str(haui_item.get_item_attr("step", 1))
        dot_pos = 0 if float(step) >= 1 else step[::-1].find(".")
        scale_factor = int(10**dot_pos)
        # the Nextion slider only holds integers: scale by the step's decimals
        i_minval = round(minval * scale_factor)
        i_maxval = round(maxval * scale_factor) - i_minval
        if state is None or state in ("unavailable", "unknown"):
            i_value = 0
            text = haui_item.translate_item_state()
        else:
            i_value = round(float(state) * scale_factor) - i_minval
            text = str(state)
        # update display
        self.send_cmd(f"{slider.name}.minval={0}")
        self.send_cmd(f"{slider.name}.maxval={i_maxval}")
        self.update_function_component(slider.name, value=i_value)
        self.set_slider_color(slider)
        stale = self._item_stale(haui_item)
        if stale:
            color = self.get_color("text_inactive")
        else:
            color = self.get_color("component_text")
        orientation = "portrait" if self.app.device.is_portrait else "landscape"
        box = _SLIDER_TEXT_BOXES[orientation]
        text = _fit_with_suffix(text, 0, box, " …") if stale and text else fit_line([text], 0, box)
        self.update_function_component(slider_txt.name, text=text, color=color)

    def update_item_cover(self, haui_item: HAUIItem, idx: int) -> None:
        item_type = haui_item.get_item_type()
        item_state = haui_item.get_item_state()
        pos = haui_item.get_item_attr("current_position")
        device_class = haui_item.get_item_attr("device_class", "window")
        can_open = pos != 100 and not (item_state == "open" and pos == "disable")
        can_close = pos != 0 and not (item_state == "closed" and pos == "disable")
        # a missing entity has no attributes, so it supports no features
        for name, flag, action, usable in (
            ("btn_up", CoverFeatures.OPEN, "open", can_open),
            ("btn_stop", CoverFeatures.STOP, "stop", item_state not in ["open", "closed"]),
            ("btn_down", CoverFeatures.CLOSE, "close", can_close),
        ):
            button = getattr(self.COMPONENTS, f"r{idx}_{name}")
            supported = haui_item.supports(flag)
            icon = ""
            if supported:
                icon_name = get_icon_name_by_action(
                    item_type=item_type, action=action, device_class=device_class
                )
                icon = get_icon(icon_name or "") or ""
            self.update_function_component(
                button.name,
                visible=True,
                text=icon,
                **self.button_color_args(supported and usable),
            )

    # callback

    def _update_entry(self, idx: int) -> None:
        self.update_row_entry(idx)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_name == "next_page":
            self._advance_page(self.NUM_ROWS)
            with self.rec_cmd:
                self.set_row_entries()
            return

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
        elif fnc_name in self._ROW_SERVICES:
            item.call_item_service(self._ROW_SERVICES[fnc_name])

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
        self.log(f"Row slider value {value} for {component.name}")
        self.log(f"Row slider value {value} from {component.name}", level="DEBUG")
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
            i_minval = round(minval * scale_factor)
            n_value = (value + i_minval) / scale_factor
            entity_object = item.get_item()
            if entity_object:
                entity_object.set_state(state=n_value)
            return

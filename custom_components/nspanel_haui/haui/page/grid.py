from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..abstract.mixins.paged_items_mixin import PagedItemsMixin
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_NEXT_PAGE
from ..utils.text import trim_text


class GridPage(PagedItemsMixin, HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="grid",
        page_name="grid",
        page_id=9,
        label=_("Grid"),
        description=_("Grid of up to 6 item tiles with pagination."),
        item_options=[
            PageOption(
                key="text_color",
                kind="color",
                label=_("Text color"),
                description=_("Color of the tile's icon and name."),
            ),
            PageOption(
                key="back_color",
                kind="color",
                label=_("Background color"),
                description=_("Background of the tile."),
            ),
            PageOption(
                key="color_pressed",
                kind="color",
                label=_("Pressed text color"),
                description=_("Icon and name color while the tile is pressed."),
            ),
            PageOption(
                key="back_color_pressed",
                kind="color",
                label=_("Pressed background color"),
                description=_("Background of the tile while it is pressed."),
            ),
            PageOption(
                key="power_color",
                kind="color",
                label=_("Power button color"),
                description=_("Color of the power button while the item is on."),
            ),
            PageOption(
                key="show_power_button",
                kind="bool",
                label=_("Show power button"),
                description=_("Show a power button on the tile that turns the item on or off."),
            ),
        ],
        options=[
            PageOption(
                key="items",
                kind="item_list",
                description=_("Items to display as tiles on the grid page."),
                section=_("Tiles"),
            ),
        ],
        icon="mdi:grid",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        g1_btn=Component(8, "g1Btn"),
        g1_ico=Component(9, "g1Icon"),
        g1_name=Component(10, "g1Name"),
        g1_ovl=Component(11, "g1Overlay"),
        g1_power=Component(12, "g1Power"),
        g2_btn=Component(13, "g2Btn"),
        g2_ico=Component(14, "g2Icon"),
        g2_name=Component(15, "g2Name"),
        g2_ovl=Component(16, "g2Overlay"),
        g2_power=Component(17, "g2Power"),
        g3_btn=Component(18, "g3Btn"),
        g3_ico=Component(19, "g3Icon"),
        g3_name=Component(20, "g3Name"),
        g3_ovl=Component(21, "g3Overlay"),
        g3_power=Component(22, "g3Power"),
        g4_btn=Component(23, "g4Btn"),
        g4_ico=Component(24, "g4Icon"),
        g4_name=Component(25, "g4Name"),
        g4_ovl=Component(26, "g4Overlay"),
        g4_power=Component(27, "g4Power"),
        g5_btn=Component(28, "g5Btn"),
        g5_ico=Component(29, "g5Icon"),
        g5_name=Component(30, "g5Name"),
        g5_ovl=Component(31, "g5Overlay"),
        g5_power=Component(32, "g5Power"),
        g6_btn=Component(33, "g6Btn"),
        g6_ico=Component(34, "g6Icon"),
        g6_name=Component(35, "g6Name"),
        g6_ovl=Component(36, "g6Overlay"),
        g6_power=Component(37, "g6Power"),
    )

    # definitions
    NUM_GRIDS = 6
    LEN_NAME = 15

    # panel

    _DEBOUNCE_KEY = "grid_item_state"

    def prepare(self) -> None:
        self._init_paging()
        self._item_mapping: list = []

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._items = self._build_items_from_panel(panel, "items")
        # page position is navigation state, not a user option: it lives on
        # the panel (persists across visits) rather than being reset to a
        # configured initial page every time the panel opens.
        self._current_page = panel.get_state("current_page", 0)
        # set function buttons
        # Pagination sits on fnc_right_sec when the panel is in navigation,
        # leaving fnc_right_pri for auto-assignment (NEXT on nav).  When the
        # panel is not in navigation (e.g. the home panel), pagination moves to
        # fnc_right_pri so fnc_right_sec stays free for the notification
        # indicator — matching the row page behaviour.
        show_in_nav = panel.show_in_navigation()
        # Only claim a right slot for pagination when there actually is more
        # than one page.  Otherwise the slot stays free so _auto_assign_fncs()
        # can put the notification indicator there — an invisible next_page
        # button used to occupy the slot and hide unread notifications.  When
        # pagination does claim right_sec (in navigation), auto-assign moves
        # the notification indicator onto the idle button's left-secondary
        # slot on the home panel.
        has_pagination = len(self._items) > self.NUM_GRIDS
        nav_btn: dict = {
            "fnc_component": (
                self.COMPONENTS.fnc_right_sec if show_in_nav else self.COMPONENTS.fnc_right_pri
            ),
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": ICO_NEXT_PAGE,
                "color": self.get_color("header_accent"),
                "visible": has_pagination,
            },
        }
        btn_right_1: tuple | dict
        btn_right_2: tuple | dict
        if show_in_nav:
            btn_right_1 = self.COMPONENTS.fnc_right_pri
            btn_right_2 = nav_btn if has_pagination else self.COMPONENTS.fnc_right_sec
        else:
            btn_right_1 = nav_btn if has_pagination else self.COMPONENTS.fnc_right_pri
            btn_right_2 = self.COMPONENTS.fnc_right_sec
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            btn_right_1,
            btn_right_2,
        )
        # set power and grid button callbacks
        power_btn_callbacks: dict = {}
        grid_ovl_callbacks: dict = {}
        for i in range(self.NUM_GRIDS):
            power = getattr(self.COMPONENTS, f"g{i + 1}_power")
            ovl = getattr(self.COMPONENTS, f"g{i + 1}_ovl")
            btn = getattr(self.COMPONENTS, f"g{i + 1}_btn")
            ico = getattr(self.COMPONENTS, f"g{i + 1}_ico")
            name = getattr(self.COMPONENTS, f"g{i + 1}_name")
            power_btn_callbacks[power] = self.callback_power_buttons
            grid_ovl_callbacks[ovl] = self.callback_grid_entries
            self.set_function_component(power, power[1], row_index=i, visible=False)
            self.set_function_component(ovl, ovl[1], row_index=i, visible=False, no_color=True)
            self.set_function_component(btn, btn[1], row_index=i, visible=False)
            self.set_function_component(ico, ico[1], row_index=i, visible=False)
            self.set_function_component(name, name[1], row_index=i, visible=False)
        self.on_release(power_btn_callbacks)
        self.on_release(grid_ovl_callbacks)

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, panel.get_title())
        self.set_grid_entries()

    # misc

    def is_power_visible(self, item: HAUIItem | None) -> bool:
        if item is not None and not item.is_internal():
            return bool(item.get("show_power_button", False))
        return False

    def is_item_active(self, item: HAUIItem) -> bool:
        active = False
        if not item.is_internal():
            active = item.get_item_state() in ["on", "playing"]
        return active

    def set_grid_entries(self) -> None:
        # check if there are any listener active and cancel them
        self._clear_item_listeners()
        # get current entities to display
        items = self._page_items(self.NUM_GRIDS)
        # set buttons
        item_ids = set()
        mapping = []
        for i in range(self.NUM_GRIDS):
            item = None
            if len(items) > i:
                item = items[i]
            # click events are captured by overlay, assign
            # entities to button overlay
            idx = i + 1
            ovl = getattr(self.COMPONENTS, f"g{idx}_ovl")
            power = getattr(self.COMPONENTS, f"g{idx}_power")
            self._active_items[ovl] = item
            # visibility of grid button
            visible = False
            if item is not None:
                # internal item
                if item.is_internal():
                    internal_type = item.get_internal_type()
                    if internal_type in ["navigate", "action", "text"]:
                        visible = True
                # standard item
                else:
                    visible = True
                    item_ids.add(item.get_item_id())
                # add mapping to
                mapping.append({"item": item, "ovl": ovl, "power": power})
            self.set_grid_entry(idx, visible=visible)
        self._item_mapping = mapping
        # create listener for active entities
        for item_id in item_ids:
            handle = self.add_item_listener(item_id, self.callback_item_state, attribute="all")
            self._active_handles.append(handle)

    def get_grid_colors(self, item: HAUIItem | None) -> tuple:
        # Default theme colors — no panel-level overrides.
        text_color = self.get_color("text")
        back_color = self.get_color("background")
        color_pressed = self.get_color("component_text")
        back_color_pressed = self.get_color("component_pressed")
        power_color = self.get_color("component_active")

        # Item-level overrides
        if item is not None:
            text_color = item.get("text_color", text_color)
            back_color = item.get("back_color", back_color)
            color_pressed = item.get("color_pressed", color_pressed)
            back_color_pressed = item.get("back_color_pressed", back_color_pressed)
            power_color = item.get("power_color", power_color)
            if not self.is_item_active(item):
                power_color = back_color_pressed

        return text_color, color_pressed, back_color, back_color_pressed, power_color

    def set_grid_entry(self, idx: int, visible: bool) -> None:
        # visibility of grid button components
        btn = getattr(self.COMPONENTS, f"g{idx}_btn")
        ico = getattr(self.COMPONENTS, f"g{idx}_ico")
        name = getattr(self.COMPONENTS, f"g{idx}_name")
        ovl = getattr(self.COMPONENTS, f"g{idx}_ovl")
        power = getattr(self.COMPONENTS, f"g{idx}_power")
        item = self._active_items[ovl]
        # power button, only show if requested and a item is set
        power_visible = self.is_power_visible(item) if item else False

        text_color, color_pressed, back_color, back_color_pressed, power_color = (
            self.get_grid_colors(item)
        )

        # update grid button
        if visible:
            power_args = {"visible": power_visible}
            ovl_args = {"visible": True}
            btn_args = {"visible": True}
            name_args = {"visible": True}
            ico_args = {"visible": True}
            if text_color is not None:
                btn_args["color"] = text_color
                name_args["color"] = text_color
            if power_visible and power_color is not None:
                power_args["color"] = power_color
            if color_pressed is not None:
                btn_args["color_pressed"] = color_pressed
                if power_visible:
                    power_args["color_pressed"] = color_pressed
            if back_color is not None:
                btn_args["back_color"] = back_color
                name_args["back_color"] = back_color
                ico_args["back_color"] = back_color
                if power_visible:
                    power_args["back_color"] = back_color
            if back_color_pressed is not None:
                btn_args["back_color_pressed"] = back_color_pressed
                if power_visible:
                    power_args["back_color_pressed"] = back_color_pressed
            self.update_function_component(ico[1], None, **ico_args)
            self.update_function_component(name[1], None, **name_args)
            self.update_function_component(btn[1], None, **btn_args)
            self.update_function_component(ovl[1], None, **ovl_args)
            self.update_grid_entry(idx)
            self.update_function_component(power[1], None, **power_args)
        else:
            for x in [btn, ico, name, ovl, power]:
                self.update_function_component(x[1], visible=False)

    def update_grid_entry(self, idx: int) -> None:
        # update a single button
        ovl = getattr(self.COMPONENTS, f"g{idx}_ovl")
        ico = getattr(self.COMPONENTS, f"g{idx}_ico")
        name = getattr(self.COMPONENTS, f"g{idx}_name")
        item = self._active_items[ovl]
        if item:
            self.set_component_text(name, trim_text(item.get_name(), self.LEN_NAME))
            self.set_component_text_color(ico, item.get_color())
            self.set_component_text(ico, item.get_icon())
            # make sure to redraw power if visible
            if self.is_power_visible(item):
                _, _, _, _, power_color = self.get_grid_colors(item)
                self.update_function_component(
                    getattr(self.COMPONENTS, f"g{idx}_power").name, visible=True, color=power_color
                )
            else:
                self.update_function_component(
                    getattr(self.COMPONENTS, f"g{idx}_power").name, visible=False
                )
        else:
            self.set_component_text(name, "")
            self.set_component_text_color(ico, self.get_color("text"))
            self.set_component_text(ico, "")

    # callback

    def _update_entry(self, idx: int) -> None:
        self.update_grid_entry(idx)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_name == "next_page":
            self._advance_page(self.NUM_GRIDS)
            with self.rec_cmd:
                self.set_grid_entries()

    def callback_power_buttons(self, event: HAUIEvent, component: Component) -> None:
        self.log(f"{self._item_mapping}")
        for mapping in self._item_mapping:
            haui_item = mapping["item"]
            state = haui_item.get_item_state()
            if mapping["power"] != component:
                continue
            if state not in ["off", "unavailable"]:
                self.turn_off_item(haui_item)
            elif state == "off":
                self.turn_on_item(haui_item)
            else:
                self.log(f"item {haui_item.get_item_id()} is not available")

    def callback_grid_entries(self, event: HAUIEvent, component: Component) -> None:
        if component not in self._active_items:
            return
        haui_item = self._active_items[component]
        if haui_item is None:
            return
        self.execute_item(haui_item)

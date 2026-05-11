from __future__ import annotations

import math
import random
from typing import Any

from ..abstract.event import HAUIEvent
from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..mapping.color import COLORS
from ..mapping.descriptor import PageDescriptor, PageOption
from ..utils.color import generate_color_palette, rgb565_to_rgb
from ..utils.text import trim_text
from . import HAUIPage


class GridPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="grid",
        page_name="grid",
        label="Grid",
        description="Grid of up to 6 item tiles with pagination.",
        item_options=[
            "color_mode",
            "color_seed",
            "text_color",
            "back_color",
            "color_pressed",
            "back_color_pressed",
            "power_color",
            "show_power_button",
        ],
        options=[
            PageOption(key="items", kind="item_list", label="Items", section="Items"),
            PageOption(
                key="initial_page",
                kind="int",
                default=0,
                label="Initial page",
                section="Pagination",
            ),
            PageOption(
                key="color_mode",
                section="Color Palette",
                kind="select",
                default="",
                label="Auto-color mode",
                choices=[
                    ("", "Off"),
                    ("pastel", "Pastel"),
                    ("light", "Light"),
                    ("lighten", "Lighten"),
                    ("vibrant", "Vibrant"),
                ],
            ),
            PageOption(
                key="color_seed",
                kind="color_seed",
                default=0,
                label="Auto-color seed (0 = random)",
                section="Color Palette",
            ),
            PageOption(key="text_color", kind="color", label="Text color", section="Appearance"),
            PageOption(
                key="back_color", kind="color", label="Background color", section="Appearance"
            ),
            PageOption(
                key="color_pressed",
                kind="color",
                label="Pressed text color",
                section="Appearance",
            ),
            PageOption(
                key="back_color_pressed",
                kind="color",
                label="Pressed background color",
                section="Appearance",
            ),
            PageOption(
                key="power_color",
                kind="color",
                label="Power button color",
                section="Appearance",
            ),
            PageOption(
                key="show_power_button",
                kind="bool",
                default=False,
                label="Show power button",
                section="Appearance",
            ),
        ],
    )

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # grid entities
    G1_BTN, G1_ICO, G1_NAME, G1_OVL, G1_POWER = (
        (7, "g1Btn"),
        (8, "g1Icon"),
        (9, "g1Name"),
        (10, "g1Overlay"),
        (11, "g1Power"),
    )
    G2_BTN, G2_ICO, G2_NAME, G2_OVL, G2_POWER = (
        (12, "g2Btn"),
        (13, "g2Icon"),
        (14, "g2Name"),
        (15, "g2Overlay"),
        (16, "g2Power"),
    )
    G3_BTN, G3_ICO, G3_NAME, G3_OVL, G3_POWER = (
        (17, "g3Btn"),
        (18, "g3Icon"),
        (19, "g3Name"),
        (20, "g3Overlay"),
        (21, "g3Power"),
    )
    G4_BTN, G4_ICO, G4_NAME, G4_OVL, G4_POWER = (
        (22, "g4Btn"),
        (23, "g4Icon"),
        (24, "g4Name"),
        (25, "g4Overlay"),
        (26, "g4Power"),
    )
    G5_BTN, G5_ICO, G5_NAME, G5_OVL, G5_POWER = (
        (27, "g5Btn"),
        (28, "g5Icon"),
        (29, "g5Name"),
        (30, "g5Overlay"),
        (31, "g5Power"),
    )
    G6_BTN, G6_ICO, G6_NAME, G6_OVL, G6_POWER = (
        (32, "g6Btn"),
        (33, "g6Icon"),
        (34, "g6Name"),
        (35, "g6Overlay"),
        (36, "g6Power"),
    )
    # definitions
    NUM_GRIDS = 6
    LEN_NAME = 15

    # panel

    def start_page(self) -> None:
        self._items: list[HAUIItem] = []
        self._active_items: dict[tuple, HAUIItem | None] = {}
        self._active_handles: list = []
        self._item_mapping: list = []
        self._current_page = 0
        self._color_seed = random.randint(0, 1000)
        self._pending_item_updates: set[str] = set()

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._items = panel.get_items()
        self._current_page = int(panel.get("initial_page", 0))
        self._color_seed = panel.get("color_seed", random.randint(0, 1000))
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
                "visible": len(self._items) > self.NUM_GRIDS,
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
        # set power and grid button callbacks
        for i in range(self.NUM_GRIDS):
            power = getattr(self, f"G{i + 1}_POWER")
            ovl = getattr(self, f"G{i + 1}_OVL")
            btn = getattr(self, f"G{i + 1}_BTN")
            ico = getattr(self, f"G{i + 1}_ICO")
            name = getattr(self, f"G{i + 1}_NAME")
            self.add_component_callback(power, self.callback_power_buttons)
            self.add_component_callback(ovl, self.callback_grid_entries)
            self.set_function_component(power, power[1], row_index=i, visible=False)
            self.set_function_component(ovl, ovl[1], row_index=i, visible=False)
            self.set_function_component(btn, btn[1], row_index=i, visible=False)
            self.set_function_component(ico, ico[1], row_index=i, visible=False)
            self.set_function_component(name, name[1], row_index=i, visible=False)

    def stop_panel(self, panel: HAUIPanel) -> None:
        # cancel any pending debounced item-state updates
        self.debouncer.cancel("grid_item_state")
        self._pending_item_updates.clear()
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_grid_entries(panel)

    # misc

    def is_power_visible(self, panel: HAUIPanel, item: HAUIItem) -> bool:
        power_visible = False
        if item is not None:
            power_visible = panel.get("show_power_button", False)
            if not item.is_internal():
                power_visible = item.get("show_power_button", power_visible)
        return power_visible

    def is_item_active(self, item: HAUIItem) -> bool:
        active = False
        if not item.is_internal():
            active = item.get_item_state() in ["on", "playing"]
        return active

    def set_grid_entries(self, panel: HAUIPanel) -> None:
        # check if there are any listener active and cancel them
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)
        # get current entities to display
        start = 0 + (int(self._current_page) * self.NUM_GRIDS)
        end = min(len(self._items), start + self.NUM_GRIDS)
        if len(self._items) > start:
            items = self._items[start:end]
        else:
            items = []
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
            ovl = getattr(self, f"G{idx}_OVL")
            power = getattr(self, f"G{idx}_POWER")
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
            self.set_grid_entry(idx, panel=panel, visible=visible)
        self._item_mapping = mapping
        # create listener for active entities
        for item_id in item_ids:
            handle = self.add_item_listener(
                item_id, self.callback_item_state, attribute="all"
            )
            self._active_handles.append(handle)

    def get_grid_colors(self, panel: HAUIPanel, item: HAUIItem | None, idx: int = 0) -> tuple:
        # colors for grid button
        color_pressed = panel.get("color_pressed", COLORS["text"])
        back_color_pressed = panel.get("back_color_pressed", COLORS["component_pressed"])
        power_color = panel.get("power_color", COLORS["component_active"])
        text_color = panel.get("text_color")
        back_color = panel.get("back_color")
        color_mode = panel.get("color_mode")
        color_seed = panel.get("color_seed", self._color_seed)
        # no background color check if color mode or set default
        if not back_color and color_mode:
            self.log(f"Using seed for grid: {color_seed}")
            colors = generate_color_palette(
                rgb565_to_rgb(COLORS["background"]), color_mode, color_seed, 6
            )
            back_color = colors[idx - 1]
            back_color_pressed = [int(x * 0.5) for x in back_color]
            # for light back colors use dark text color
            if color_mode in ["pastel", "light", "lighten"]:
                if not text_color:
                    text_color = COLORS["background"]
                color_pressed = COLORS["component_pressed"]
                power_color = COLORS["background"]
            elif color_mode in ["vibrant"]:
                if not text_color:
                    text_color = COLORS["component"]
                color_pressed = COLORS["component"]
                power_color = COLORS["component"]
        # text color
        if not text_color:
            text_color = COLORS["text"]
        # back color
        if not back_color:
            back_color = COLORS["background"]
        # item overrides (beat everything)
        if item is not None:
            color_mode = item.get("color_mode", color_mode)
            text_color = item.get("text_color", text_color)
            back_color = item.get("back_color", back_color)
            color_pressed = item.get("color_pressed", color_pressed)
            back_color_pressed = item.get("back_color_pressed", back_color_pressed)
            color_seed = item.get("color_seed", color_seed)
            power_color = item.get("power_color", power_color)
            if not self.is_item_active(item):
                power_color = back_color_pressed

        return text_color, color_pressed, back_color, back_color_pressed, power_color

    def set_grid_entry(self, idx: int, panel: HAUIPanel, visible: bool) -> None:
        # visibility of grid button components
        btn = getattr(self, f"G{idx}_BTN")
        ico = getattr(self, f"G{idx}_ICO")
        name = getattr(self, f"G{idx}_NAME")
        ovl = getattr(self, f"G{idx}_OVL")
        power = getattr(self, f"G{idx}_POWER")
        item = self._active_items[ovl]
        # power button, only show if requested and a item is set
        power_visible = self.is_power_visible(panel, item) if item else False

        text_color, color_pressed, back_color, back_color_pressed, power_color = (
            self.get_grid_colors(panel, item, idx)
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
            self.update_grid_entry(idx, panel)
            self.update_function_component(power[1], None, **power_args)
        else:
            for x in [btn, ico, name, ovl, power]:
                self.update_function_component(x[1], visible=False)

    def update_grid_entries(self, panel: HAUIPanel) -> None:
        items = self._active_items
        # grid buttons
        for idx in range(1, self.NUM_GRIDS + 1):
            if idx > len(items):
                break
            self.update_grid_entry(idx, panel)

    def update_grid_entry(self, idx: int, panel: HAUIPanel) -> None:
        # update a single button
        ovl = getattr(self, f"G{idx}_OVL")
        ico = getattr(self, f"G{idx}_ICO")
        name = getattr(self, f"G{idx}_NAME")
        item = self._active_items[ovl]
        if item:
            self.set_component_text(name, trim_text(item.get_name(), self.LEN_NAME))
            self.set_component_text_color(ico, item.get_color())
            self.set_component_text(ico, item.get_icon())
            # make sure to redraw power if visible
            if self.is_power_visible(panel, item):
                _, _, _, _, power_color = self.get_grid_colors(panel, item)
                self.update_function_component(
                    getattr(self, f"G{idx}_POWER")[1], visible=True, color=power_color
                )
            else:
                self.update_function_component(getattr(self, f"G{idx}_POWER")[1], visible=False)
        else:
            self.set_component_text(name, "")
            self.set_component_text_color(ico, COLORS["text"])
            self.set_component_text(ico, "")

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
        self.debouncer.call("grid_item_state", self._flush_item_updates)

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
                    if self.panel is not None:
                        self.update_grid_entry(idx, self.panel)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_name == "next_page":
            count_pages = math.ceil(len(self._items) / self.NUM_GRIDS)
            self._current_page += 1
            if self._current_page >= count_pages:
                self._current_page = 0
            with self.rec_cmd:
                if self.panel is not None:
                    self.set_grid_entries(self.panel)

    def callback_power_buttons(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
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

    def callback_grid_entries(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        if component not in self._active_items:
            return
        haui_item = self._active_items[component]
        if haui_item is None:
            return
        self.execute_item(haui_item)

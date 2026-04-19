import math
import random

from ..abstract.entity import HAUIEntity
from ..abstract.panel import HAUIPanel
from ..helper.color import generate_color_palette, rgb565_to_rgb
from ..helper.text import trim_text
from ..mapping.color import COLORS
from . import HAUIPage


class GridPage(HAUIPage):
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
        self._entities: list[HAUIEntity] = []
        self._active_entities: dict[tuple, HAUIEntity | None] = {}
        self._active_handles: list = []
        self._entity_mapping: list = []
        self._current_page = 0
        self._color_seed = random.randint(0, 1000)
        self._pending_entity_updates: set[str] = set()

    def start_panel(self, panel: HAUIPanel) -> None:
        # set vars
        self._entities = panel.get_entities()
        self._current_page = panel.get("initial_page", 0)
        self._color_seed = panel.get("color_seed", random.randint(0, 1000))
        # set function buttons
        mode = panel.get_mode()
        nav_btn: dict = {
            "fnc_component": (
                self.BTN_FNC_RIGHT_SEC if mode != "subpanel" else self.BTN_FNC_RIGHT_PRI
            ),
            "fnc_name": "next_page",
            "fnc_args": {
                "icon": self.ICO_NEXT_PAGE,
                "color": COLORS["component_accent"],
                "visible": len(self._entities) > self.NUM_GRIDS,
            },
        }
        btn_right_1: tuple | dict
        btn_right_2: tuple | dict
        if mode != "subpanel":
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
        # cancel any pending debounced entity-state updates
        self.debouncer.cancel("grid_entity_state")
        self._pending_entity_updates.clear()
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.set_grid_entries()

    # misc

    def is_power_visible(self, panel: HAUIPanel, entity: HAUIEntity) -> None:
        power_visible = False
        if entity is not None:
            power_visible = panel.get("show_power_button", False)
            if not entity.is_internal():
                power_visible = entity.get("show_power_button", power_visible)
        return power_visible

    def is_entity_active(self, entity: HAUIEntity) -> None:
        active = False
        if not entity.is_internal():
            active = entity.get_entity_state() in ["on", "playing"]
        return active

    def set_grid_entries(self) -> None:
        # check if there are any listener active and cancel them
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_entity_listener(handle)
        # get current entities to display
        start = 0 + (self._current_page * self.NUM_GRIDS)
        end = min(len(self._entities), start + self.NUM_GRIDS)
        if len(self._entities) > start:
            entities = self._entities[start:end]
        else:
            entities = []
        # set buttons
        entity_ids = set()
        mapping = []
        for i in range(self.NUM_GRIDS):
            entity = None
            if len(entities) > i:
                entity = entities[i]
            # click events are captured by overlay, assign
            # entities to button overlay
            idx = i + 1
            ovl = getattr(self, f"G{idx}_OVL")
            power = getattr(self, f"G{idx}_POWER")
            self._active_entities[ovl] = entity
            # visibility of grid button
            visible = False
            if entity is not None:
                # internal entity
                if entity.is_internal():
                    internal_type = entity.get_internal_type()
                    if internal_type in ["navigate", "action", "text"]:
                        visible = True
                # standard entity
                else:
                    visible = True
                    entity_ids.add(entity.get_entity_id())
                # add mapping to
                mapping.append({"entity": entity, "ovl": ovl, "power": power})
            self.set_grid_entry(idx, visible=visible)
        self._entity_mapping = mapping
        # create listener for active entities
        for entity_id in entity_ids:
            handle = self.add_entity_listener(
                entity_id, self.callback_entity_state, attribute="all"
            )
            self._active_handles.append(handle)

    def get_grid_colors(self, panel, entity, idx=0) -> tuple:
        # colors for grid button
        color_pressed = panel.get("color_pressed", COLORS["text"])
        back_color_pressed = panel.get(
            "back_color_pressed", COLORS["component_pressed"]
        )
        power_color = COLORS["component_active"]
        text_color = panel.get("text_color")
        back_color = panel.get("back_color")
        color_mode = panel.get("color_mode")
        color_seed = panel.get("color_seed", self._color_seed)
        if entity is not None:
            color_mode = entity.get("color_mode", color_mode)
            text_color = entity.get("text_color", text_color)
            back_color = entity.get("back_color", back_color)
            color_pressed = entity.get("color_pressed", color_pressed)
            back_color_pressed = entity.get("back_color_pressed", back_color_pressed)
            color_seed = entity.get("color_seed", color_seed)
            power_color = entity.get("power_color", power_color)
        # no background color check if color mode or set default
        if back_color is None and color_mode is not None:
            self.log(f"Using random seed for grid: {color_seed}")
            colors = generate_color_palette(
                rgb565_to_rgb(COLORS["background"]), color_mode, color_seed, 6
            )
            back_color = colors[idx - 1]
            back_color_pressed = [int(x * 0.5) for x in back_color]
            # for light back colors use dark text color
            if color_mode in ["pastel", "light", "lighten"]:
                if text_color is None:
                    text_color = COLORS["background"]
                color_pressed = COLORS["component_pressed"]
                power_color = COLORS["background"]
            elif color_mode in ["vibrant"]:
                if text_color is None:
                    text_color = COLORS["component"]
                color_pressed = COLORS["component"]
                power_color = COLORS["component"]
        # power color
        power_color = panel.get("power_color", power_color)
        if entity is not None:
            color_mode = entity.get("color_mode", color_mode)
            text_color = entity.get("text_color", text_color)
            back_color = entity.get("back_color", back_color)
            color_pressed = entity.get("color_pressed", color_pressed)
            back_color_pressed = entity.get("back_color_pressed", back_color_pressed)
            color_seed = entity.get("color_seed", color_seed)
            power_color = entity.get("power_color", power_color)
            if not self.is_entity_active(entity):
                power_color = back_color_pressed
        # text color
        if text_color is None:
            text_color = COLORS["text"]
        # back color
        if back_color is None:
            back_color = COLORS["background"]

        return text_color, color_pressed, back_color, back_color_pressed, power_color

    def set_grid_entry(self, idx, visible) -> None:
        # visibility of grid button components
        btn = getattr(self, f"G{idx}_BTN")
        ico = getattr(self, f"G{idx}_ICO")
        name = getattr(self, f"G{idx}_NAME")
        ovl = getattr(self, f"G{idx}_OVL")
        power = getattr(self, f"G{idx}_POWER")
        entity = self._active_entities[ovl]
        panel = self.panel
        # power button, only show if requested and a entity is set
        power_visible = self.is_power_visible(panel, entity)

        text_color, color_pressed, back_color, back_color_pressed, power_color = (
            self.get_grid_colors(panel, entity, idx)
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
            self.update_function_component(ico[1], **ico_args)
            self.update_function_component(name[1], **name_args)
            self.update_function_component(btn[1], **btn_args)
            self.update_function_component(ovl[1], **ovl_args)
            self.update_grid_entry(idx)
            self.update_function_component(power[1], **power_args)
        else:
            for x in [btn, ico, name, ovl, power]:
                self.update_function_component(x[1], visible=False)

    def update_grid_entries(self) -> None:
        entities = self._active_entities
        # grid buttons
        for idx in range(1, self.NUM_GRIDS + 1):
            if idx > len(entities):
                break
            self.update_grid_entry(idx)

    def update_grid_entry(self, idx) -> None:
        # update a single button
        ovl = getattr(self, f"G{idx}_OVL")
        ico = getattr(self, f"G{idx}_ICO")
        name = getattr(self, f"G{idx}_NAME")
        entity = self._active_entities[ovl]
        if entity:
            self.set_component_text(name, trim_text(entity.get_name(), self.LEN_NAME))
            self.set_component_text_color(ico, entity.get_color())
            self.set_component_text(ico, entity.get_icon())
            # make sure to redraw power if visible
            if self.is_power_visible(self.panel, entity):
                _, _, _, _, power_color = self.get_grid_colors(self.panel, entity)
                self.update_function_component(
                    getattr(self, f"G{idx}_POWER")[1], visible=True, color=power_color
                )
            else:
                self.update_function_component(
                    getattr(self, f"G{idx}_POWER")[1], visible=False
                )
        else:
            self.set_component_text(name, "")
            self.set_component_text_color(ico, COLORS["text"])
            self.set_component_text(ico, "")

    # callback

    def callback_entity_state(self, entity, attribute, old, new, kwargs) -> None:
        entity_ids = {
            haui_entity.get_entity_id()
            for haui_entity in self._active_entities.values()
            if haui_entity is not None
        }
        if entity not in entity_ids:
            return
        # Coalesce rapid attribute updates into a single redraw to avoid
        # flooding the Nextion UART, which delays touch-event delivery.
        self._pending_entity_updates.add(entity)
        self.debouncer.call("grid_entity_state", self._flush_entity_updates)

    def _flush_entity_updates(self) -> None:
        # Swap pending set first so concurrent adds aren't lost on clear.
        pending = self._pending_entity_updates
        if not pending:
            return
        self._pending_entity_updates = set()
        with self.rec_cmd:
            idx = 0
            for haui_entity in self._active_entities.values():
                idx += 1
                if haui_entity is None:
                    continue
                if haui_entity.get_entity_id() in pending:
                    self.update_grid_entry(idx)

    def callback_function_component(self, fnc_id, fnc_name) -> None:
        if fnc_name == "next_page":
            count_pages = math.ceil(len(self._entities) / self.NUM_GRIDS)
            self._current_page += 1
            if self._current_page >= count_pages:
                self._current_page = 0
            with self.rec_cmd:
                self.set_grid_entries()

    def callback_power_buttons(self, event, component, button_state) -> None:
        if button_state:
            return
        self.log(f"{self._entity_mapping}")
        for mapping in self._entity_mapping:
            haui_entity = mapping["entity"]
            state = haui_entity.get_entity_state()
            if mapping["power"] != component:
                continue
            if state not in ["off", "unavailable"]:
                self.turn_off_entity(haui_entity)
            elif state == "off":
                self.turn_on_entity(haui_entity)
            else:
                self.log(f"entity {haui_entity.get_entity_id()} is not available")

    def callback_grid_entries(self, event, component, button_state) -> None:
        if button_state:
            return
        if component not in self._active_entities:
            return
        haui_entity = self._active_entities[component]
        if haui_entity is None:
            return
        self.execute_entity(haui_entity)

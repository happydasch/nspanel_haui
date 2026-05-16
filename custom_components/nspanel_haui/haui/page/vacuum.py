from __future__ import annotations

from typing import Any

from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..features import VacuumFeatures
from ..mapping.color import COLORS
from ..mapping.descriptor import PageDescriptor, PageOption
from ..utils.icon import get_icon
from . import HAUIPage


class VacuumPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="vacuum",
        page_name="vacuum",
        label="Vacuum",
        description="Vacuum robot controls and status.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="vacuum",
                description="Vacuum robot entity for starting, stopping and returning to dock.",
                section="Vacuum",
            ),
            PageOption(
                key="items",
                kind="item_list",
                section="Secondary Items",
                description="Additional items to display below the vacuum controls (up to 6).",
                max_items=6,
            ),
        ],
        icon="mdi:robot-vacuum",
    )

    ICO_START = get_icon("mdi:play")
    ICO_PAUSE = get_icon("mdi:pause")
    ICO_STOP = get_icon("mdi:stop")
    ICO_LOCATE = get_icon("mdi:map-marker")
    ICO_HOME = get_icon("mdi:home")
    ICO_BATTERY = get_icon("mdi:battery")
    ICO_FAN = get_icon("mdi:fan")

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # control
    BTN_FAN, BTN_ACTION = (7, "bFan"), (8, "bAction")
    BTN_HOME, BTN_LOCATE = (9, "bHome"), (10, "bLocate")
    # info
    TXT_STATUS = (11, "tStatus")
    # entities
    BTN_ENTITY_1, BTN_ENTITY_2, BTN_ENTITY_3 = (
        (12, "bEntity1"),
        (13, "bEntity2"),
        (14, "bEntity3"),
    )
    BTN_ENTITY_4, BTN_ENTITY_5, BTN_ENTITY_6 = (
        (15, "bEntity4"),
        (16, "bEntity5"),
        (17, "bEntity6"),
    )

    NUM_ENTITIES = 6

    _title = ""
    _vacuum_item: HAUIItem | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        vacuum_battery = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_args": {
                "icon": self.ICO_BATTERY,
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            vacuum_battery,
        )
        # set item
        item = None
        entity_id = panel.get("item_id")
        if entity_id:
            item = HAUIItem(self.app, {"item": entity_id})
        items = self._build_items_from_panel(panel, "items")
        if len(items) > 0:
            first_item = items.pop(0)
            if item is None:
                item = first_item
        self._items = items
        self.set_vacuum_item(item)
        # set title
        title = panel.get_title(self.translate("Vacuum"))
        if item is not None:
            title = item.get_item_attr("friendly_name", title)
        self._title = title

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_vacuum_item()

    def stop_panel(self, panel: HAUIPanel) -> None:
        super().stop_panel(panel)

    # misc

    def set_vacuum_item(self, item: HAUIItem | None) -> None:
        self._vacuum_item = item
        if not item or not item.has_item_id():
            return
        # add listener
        self.add_item_listener(item.get_item_id(), self.callback_vacuum_entity)
        self.add_item_listener(item.get_item_id(), self.callback_vacuum_entity, attribute="status")
        # use features of vacuum
        features = item.get_item_attr("supported_features", 0)
        # fan button
        fan = False
        if features & VacuumFeatures.FAN_SPEED:
            fan = True
        self.set_function_component(
            self.BTN_FAN,
            self.BTN_FAN[1],
            "fan",
            color=COLORS["component_active"],
            icon=self.ICO_FAN,
            visible=fan,
        )
        # start/stop button
        action = False
        if features & VacuumFeatures.START:
            action = True
        self.set_function_component(
            self.BTN_ACTION,
            self.BTN_ACTION[1],
            "action",
            icon=self.ICO_START,
            visible=action,
        )
        # return home button
        return_home = False
        if features & VacuumFeatures.RETURN_HOME:
            return_home = True
        self.set_function_component(
            self.BTN_HOME,
            self.BTN_HOME[1],
            "return_home",
            icon=self.ICO_HOME,
            visible=return_home,
        )
        # locate button
        locate = False
        if features & VacuumFeatures.LOCATE:
            locate = True
        self.set_function_component(
            self.BTN_LOCATE,
            self.BTN_LOCATE[1],
            "locate",
            icon=self.ICO_LOCATE,
            visible=locate,
        )
        # item buttons
        total_items = len(self._items)
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ""
            color = COLORS["text"]
            item = None
            if i < total_items:
                item = self._items[i]
                icon = item.get_icon()
                color = item.get_color()
                visible = True
            component = getattr(self, f"BTN_ENTITY_{i + 1}")
            self.set_function_component(
                component,
                component[1],
                "item",
                item=item,
                icon=icon,
                color=color,
                visible=visible,
            )

    def update_vacuum_item(self) -> None:
        self.set_component_text(self.TXT_TITLE, self._title)
        if self._vacuum_item is None:
            return
        item = self._vacuum_item
        state = item.get_item_state()
        features = item.get_item_attr("supported_features", 0)
        # battery
        if features & VacuumFeatures.BATTERY:
            battery_icon = item.get_item_attr("battery_icon", self.ICO_BATTERY)
            self.update_function_component(
                self.FNC_BTN_R_SEC, icon=get_icon(battery_icon), visible=True
            )
        # status text
        status_text = self.translate_state(item.get_item_type(), state)
        self.set_component_text(self.TXT_STATUS, status_text)
        # pause/start/stop button
        active = False
        pause, start, stop = False, False, False
        icon = self.ICO_START
        if state in ["cleaning", "returning"]:
            start = False
            if features & VacuumFeatures.PAUSE:
                pause = True
            if features & VacuumFeatures.STOP:
                stop = True
        elif state in ["docked", "idle"]:
            if features & VacuumFeatures.START:
                start = True
        active = True
        if start:
            icon = self.ICO_START
        elif pause:
            icon = self.ICO_PAUSE
        elif stop:
            icon = self.ICO_STOP
        else:
            icon = self.ICO_START
            active = False
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.BTN_ACTION[1],
            touch=active,
            color=color,
            color_pressed=color_pressed,
            icon=icon,
            back_color_pressed=back_color_pressed,
        )
        # home button
        active = False
        if state != "docked":
            active = True
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.BTN_HOME[1],
            touch=active,
            color=color,
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )
        # locate button
        active = False
        if features & VacuumFeatures.LOCATE:
            active = True
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.BTN_LOCATE[1],
            touch=active,
            color=COLORS["component_accent"],
            color_pressed=color_pressed,
            back_color_pressed=back_color_pressed,
        )

    # callback

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if self._vacuum_item is None:
            return
        # header
        item = self._vacuum_item
        state = self._vacuum_item.get_item_state()
        # fan
        if fnc_name == "fan":
            navigation = self.app.controller["navigation"]
            current = item.get_item_attr("fan_speed", "")
            selection = item.get_item_attr("fan_speed_list", [])
            speeds = []
            for value in selection:
                name = self.translate_state("vacuum", value, attr="fan_speed")
                speeds.append({"name": name, "value": value})
            if len(speeds) > 0:
                navigation.open_popup(
                    "popup_select",
                    title=self.translate("Select Fan Speed"),
                    items=speeds,
                    selected=current,
                    selection_callback_fnc=self.callback_fan_speed,
                    close_on_select=True,
                )
        # start
        elif fnc_name == "action":
            if state in ["cleaning", "returning"]:
                if fnc_id == self.BTN_ACTION[1]:
                    item.call_item_service("pause")
                else:
                    item.call_item_service("stop")
            else:
                item.call_item_service("start")
        # locate
        elif fnc_name == "locate":
            item.call_item_service("locate")
        # return home
        elif fnc_name == "return_home":
            item.call_item_service("return_to_base")
        # item
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                item.execute()
        else:
            self.log(f"{fnc_id}, {fnc_name}")

    def callback_vacuum_entity(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if attribute in ["state", "status"]:
            with self.rec_cmd:
                self.update_vacuum_item()
        else:
            self.log(f"Unknown vacuum item attribute: {attribute}")

    def callback_fan_speed(self, selection: Any) -> None:
        self.log(f"Got fan speed selection: {selection}")
        self._vacuum_item.call_item_service("set_fan_speed", fan_speed=selection)

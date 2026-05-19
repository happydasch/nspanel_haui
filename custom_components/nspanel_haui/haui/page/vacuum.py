from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import VacuumFeatures
from ..mapping.color import COLORS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icons import (
    ICO_BATTERY,
    ICO_FAN,
    ICO_HOME,
    ICO_LOCATE,
    ICO_PAUSE,
    ICO_START,
    ICO_STOP,
)
from ..utils.icon import get_icon


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
        can_show_popup=True,
        icon="mdi:robot-vacuum",
    )

    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        title=Component(2, "tTitle"),
        btn_fan=Component(7, "bFan"),
        btn_action=Component(8, "bAction"),
        btn_home=Component(9, "bHome"),
        btn_locate=Component(10, "bLocate"),
        t_status=Component(11, "tStatus"),
        btn_entity_1=Component(12, "bEntity1"),
        btn_entity_2=Component(13, "bEntity2"),
        btn_entity_3=Component(14, "bEntity3"),
        btn_entity_4=Component(15, "bEntity4"),
        btn_entity_5=Component(16, "bEntity5"),
        btn_entity_6=Component(17, "bEntity6"),
    )

    NUM_ENTITIES = 6

    _title = ""
    _vacuum_item: HAUIItem | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        vacuum_battery = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_args": {
                "icon": ICO_BATTERY,
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
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
            self.COMPONENTS.btn_fan,
            self.COMPONENTS.btn_fan.name,
            "fan",
            color=COLORS["component_active"],
            icon=ICO_FAN,
            visible=fan,
        )
        # start/stop button
        action = False
        if features & VacuumFeatures.START:
            action = True
        self.set_function_component(
            self.COMPONENTS.btn_action,
            self.COMPONENTS.btn_action.name,
            "action",
            icon=ICO_START,
            visible=action,
        )
        # return home button
        return_home = False
        if features & VacuumFeatures.RETURN_HOME:
            return_home = True
        self.set_function_component(
            self.COMPONENTS.btn_home,
            self.COMPONENTS.btn_home.name,
            "return_home",
            icon=ICO_HOME,
            visible=return_home,
        )
        # locate button
        locate = False
        if features & VacuumFeatures.LOCATE:
            locate = True
        self.set_function_component(
            self.COMPONENTS.btn_locate,
            self.COMPONENTS.btn_locate.name,
            "locate",
            icon=ICO_LOCATE,
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
            component = getattr(self.COMPONENTS, f"btn_entity_{i + 1}")
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
        self.set_component_text(self.COMPONENTS.title, self._title)
        if self._vacuum_item is None:
            return
        item = self._vacuum_item
        state = item.get_item_state()
        features = item.get_item_attr("supported_features", 0)
        # battery
        if features & VacuumFeatures.BATTERY:
            battery_icon = item.get_item_attr("battery_icon", ICO_BATTERY)
            self.update_function_component(
                self.FNC_BTN_R_SEC, icon=get_icon(battery_icon), visible=True
            )
        # status text
        status_text = self.translate_state(item.get_item_type() or "", state or "")
        self.set_component_text(self.COMPONENTS.t_status, status_text)
        # pause/start/stop button
        active = False
        pause, start, stop = False, False, False
        icon = ICO_START
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
            icon = ICO_START
        elif pause:
            icon = ICO_PAUSE
        elif stop:
            icon = ICO_STOP
        else:
            icon = ICO_START
            active = False
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(active)
        self.update_function_component(
            self.COMPONENTS.btn_action.name,
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
            self.COMPONENTS.btn_home.name,
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
            self.COMPONENTS.btn_locate.name,
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
                navigation.open_panel(
                    SysPanelKey.POPUP_SELECT,
                    title=self.translate("Select Fan Speed"),
                    items=speeds,
                    selected=current,
                    selection_callback_fnc=self.callback_fan_speed,
                    close_on_select=True,
                )
        # start
        elif fnc_name == "action":
            if state in ["cleaning", "returning"]:
                if fnc_id == self.COMPONENTS.btn_action.name:
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
        if self._vacuum_item is None:
            return
        self.log(f"Got fan speed selection: {selection}")
        self._vacuum_item.call_item_service("set_fan_speed", fan_speed=selection)

from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import VacuumFeatures
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import (
    ICO_BATTERY,
    ICO_FAN,
    ICO_HOME,
    ICO_LOCATE,
    ICO_PAUSE,
    ICO_PLAY,
    ICO_STOP,
)
from ..utils.icon import get_icon

BATTERY_ICON_STEP = 10


def _battery_icon_name(level: Any) -> str:
    """Returns the MDI battery icon name for a level in percent.

    Battery sensors rarely set an ``icon`` attribute of their own — Home
    Assistant computes the battery icon at display time — so the level is
    mapped onto the MDI 10 % steps instead.

    Args:
        level (Any): Battery level in percent (number or numeric string)

    Returns:
        str: Icon name, e.g. ``mdi:battery-90``
    """
    try:
        pct = max(0.0, min(100.0, float(level)))
    except (TypeError, ValueError):
        return "mdi:battery"
    step = int(round(pct / BATTERY_ICON_STEP)) * BATTERY_ICON_STEP
    return f"mdi:battery-{step}"


class VacuumPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="vacuum",
        page_name="vacuum",
        page_id=15,
        label=_("Vacuum"),
        description=_("Vacuum robot controls and status."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="vacuum",
                description=_("Vacuum robot entity for starting, stopping and returning to dock."),
                section=_("Vacuum"),
            ),
            PageOption(
                key="battery_sensor",
                kind="item",
                domain="sensor",
                description=_(
                    "Optional sensor entity reporting the battery level. "
                    "Replaces the vacuum entity's deprecated battery attributes."
                ),
                section=_("Vacuum"),
            ),
            PageOption(
                key="items",
                kind="item_list",
                section=_("Secondary Items"),
                description=_("Additional items to display below the vacuum controls (up to 6)."),
                max_items=6,
            ),
        ],
        can_show_popup=True,
        icon="mdi:robot-vacuum",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_fan=Component(8, "bFan"),
        btn_action=Component(9, "bAction"),
        btn_home=Component(10, "bHome"),
        btn_locate=Component(11, "bLocate"),
        t_status=Component(12, "tStatus"),
        btn_entity_1=Component(13, "bEntity1"),
        btn_entity_2=Component(14, "bEntity2"),
        btn_entity_3=Component(15, "bEntity3"),
        btn_entity_4=Component(16, "bEntity4"),
        btn_entity_5=Component(17, "bEntity5"),
        btn_entity_6=Component(18, "bEntity6"),
    )

    NUM_ENTITIES = 6

    _SIMPLE_SERVICES = {"locate": "locate", "return_home": "return_to_base"}

    _title = ""
    _vacuum_item: HAUIItem | None = None
    _battery_item: HAUIItem | None = None

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
        item = self._resolve_panel_item(panel)
        self._items = self._build_items_from_panel(panel, "items")
        self.listen_items(self._items, self.update_item_buttons)
        # optional battery sensor: vacuum entities no longer report the
        # battery_level / battery_icon attributes (deprecated in Home Assistant)
        battery_sensor = panel.get("battery_sensor", None)
        if isinstance(battery_sensor, list):
            battery_sensor = battery_sensor[0] if battery_sensor else None
        self._battery_item = self._item_from_ref(battery_sensor)
        self.set_vacuum_item(item)
        # set title
        self._title = self._panel_title(panel, item, self.translate("Vacuum"))

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_vacuum_item()

    # misc

    def set_vacuum_item(self, item: HAUIItem | None) -> None:
        self._vacuum_item = item
        # the battery sensor is independent of the vacuum entity
        if self._battery_item is not None and self._battery_item.has_item_id():
            self.add_item_listener(
                self._battery_item.get_item_id(), self.callback_battery_entity
            )
        if not item or not item.has_item_id():
            return
        # add listener (vacuum entities report their activity as the state)
        self.add_item_listener(item.get_item_id(), self.callback_vacuum_entity)
        # fan button
        self.set_function_component(
            self.COMPONENTS.btn_fan,
            self.COMPONENTS.btn_fan.name,
            "fan",
            color=self.get_color("component_active"),
            icon=ICO_FAN,
            visible=item.supports(VacuumFeatures.FAN_SPEED),
        )
        for component, fnc_name, icon, flag in (
            (self.COMPONENTS.btn_action, "action", ICO_PLAY, VacuumFeatures.START),
            (self.COMPONENTS.btn_home, "return_home", ICO_HOME, VacuumFeatures.RETURN_HOME),
            (self.COMPONENTS.btn_locate, "locate", ICO_LOCATE, VacuumFeatures.LOCATE),
        ):
            self.set_function_component(
                component, component.name, fnc_name, icon=icon, visible=item.supports(flag)
            )
        self.update_item_buttons()

    def update_item_buttons(self) -> None:
        """Draw the secondary item buttons (icon and state colour)."""
        total_items = len(self._items)
        for i in range(self.NUM_ENTITIES):
            visible = False
            icon = ""
            color = self.get_color("text")
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
        self.update_battery()
        if self._vacuum_item is None:
            return
        item = self._vacuum_item
        state = item.get_item_state()
        # status text
        status_text = item.translate_item_state()
        self.set_component_text(self.COMPONENTS.t_status, status_text)
        # pause/start/stop button
        pause, start, stop = False, False, False
        if state in ["cleaning", "returning"]:
            pause = item.supports(VacuumFeatures.PAUSE)
            stop = item.supports(VacuumFeatures.STOP)
        # vacuum.start resumes a paused vacuum
        elif state in ["docked", "idle", "paused"]:
            start = item.supports(VacuumFeatures.START)
        active = True
        if start:
            icon = ICO_PLAY
        elif pause:
            icon = ICO_PAUSE
        elif stop:
            icon = ICO_STOP
        else:
            icon = ICO_PLAY
            active = False
        self.update_function_component(
            self.COMPONENTS.btn_action.name,
            touch=active,
            icon=icon,
            **self.button_color_args(active),
        )
        # home button
        active = state != "docked"
        self.update_function_component(
            self.COMPONENTS.btn_home.name, touch=active, **self.button_color_args(active)
        )
        # locate button
        active = item.supports(VacuumFeatures.LOCATE)
        self.update_function_component(
            self.COMPONENTS.btn_locate.name,
            touch=active,
            **{**self.button_color_args(active), "color": self.get_color("component_accent")},
        )

    def update_battery(self) -> None:
        """Updates the header battery icon.

        The icon comes from the configured battery sensor; without one no
        battery icon is shown.  The vacuum entity's ``battery_level`` /
        ``battery_icon`` attributes are deprecated in Home Assistant and are
        never read.
        """
        if self._battery_item is None or not self._battery_item.has_item_id():
            return
        icon = self._battery_item.get_item_attr("icon", None)
        if not icon:
            icon = _battery_icon_name(self._battery_item.get_item_state())
        if icon is None:
            return
        self.update_function_component(
            self.FNC_BTN_R_SEC, icon=get_icon(icon), visible=True
        )

    # callback

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if self._vacuum_item is None:
            return
        # header
        item = self._vacuum_item
        state = self._vacuum_item.get_item_state()
        if fnc_name == "fan":
            speeds = [
                {"name": self.translate_state("vacuum", value, attr="fan_speed"), "value": value}
                for value in item.get_item_attr("fan_speed_list", [])
            ]
            if len(speeds) > 0:
                self.app.controller["navigation"].open_panel(
                    SysPanelKey.POPUP_SELECT,
                    title=self.translate("Select Fan Speed"),
                    items=speeds,
                    selected=item.get_item_attr("fan_speed", ""),
                    selection_callback_fnc=self.callback_fan_speed,
                    close_on_select=True,
                )
        elif fnc_name == "action":
            if state in ["cleaning", "returning"]:
                # same preference as the icon: pause if supported, else stop
                item.call_item_service("pause" if item.supports(VacuumFeatures.PAUSE) else "stop")
            else:
                item.call_item_service("start")
        elif fnc_name in self._SIMPLE_SERVICES:
            item.call_item_service(self._SIMPLE_SERVICES[fnc_name])
        elif fnc_name == "item":
            item = self._fnc_items[fnc_id]["fnc_args"].get("item")
            if item is not None:
                self.execute_item(item)
        else:
            self.log(f"{fnc_id}, {fnc_name}")

    def callback_vacuum_entity(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if attribute == "state":
            with self.rec_cmd:
                self.update_vacuum_item()
        else:
            self.log(f"Unknown vacuum item attribute: {attribute}")

    def callback_battery_entity(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        if attribute == "state":
            with self.rec_cmd:
                self.update_battery()
        else:
            self.log(f"Unknown battery sensor attribute: {attribute}")

    def callback_fan_speed(self, selection: Any) -> None:
        if self._vacuum_item is None:
            return
        self.log(f"Got fan speed selection: {selection}")
        self._vacuum_item.call_item_service("set_fan_speed", fan_speed=selection)

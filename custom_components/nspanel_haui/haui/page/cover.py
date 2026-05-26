from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import CoverFeatures
from ..mapping.const import ESPRequest, ESPResponse
from ..mapping.descriptor import PageDescriptor, PageOption


class CoverPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="cover",
        page_name="cover",
        label="Cover",
        description="Cover item with open, close and position controls.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="cover",
                description="Cover entity for opening, closing and positioning window coverings.",
                section="Cover",
            ),
        ],
        can_show_popup=True,
        icon="mdi:blinds",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_up=Component(8, "bUp"),
        btn_stop=Component(9, "bStop"),
        btn_down=Component(10, "bDown"),
        h_vert_pos=Component(11, "hVertPos"),
        t_info=Component(12, "tInfo"),
    )

    _title = ""
    _cover_entity: HAUIItem | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set component callbacks
        self.add_component_callback(self.COMPONENTS.h_vert_pos, self.callback_cover_pos)
        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )
        # set cover function button callbacks
        for btn in [self.COMPONENTS.btn_up, self.COMPONENTS.btn_stop, self.COMPONENTS.btn_down]:
            self.add_component_callback(btn, self.callback_cover_buttons)
        # set item
        item: HAUIItem | None = None
        entity_id = panel.get("item_id")
        if entity_id:
            item = HAUIItem(self.app, {"item": entity_id})
        self.set_cover_item(item)

        # set title
        title = panel.get_title(self.translate("Cover"))
        if item is not None:
            title = item.get_item_attr("friendly_name", title)
        self._title = title
        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, self._title)
        self.update_cover_entity()

    # misc

    def set_cover_item(self, item: HAUIItem | None) -> None:
        self._cover_entity = item
        if not item or not item.has_item_id():
            return
        supported_features = item.get_item_attr("supported_features", 0)
        # add listener
        self.add_item_listener(item.get_item_id(), self.callback_cover_entity)

        self.add_item_listener(
            item.get_item_id(),
            self.callback_cover_entity,
            attribute="current_position",
        )
        # up button
        visible = False
        if supported_features & CoverFeatures.OPEN:
            visible = True
        self.set_function_component(
            self.COMPONENTS.btn_up,
            self.COMPONENTS.btn_up.name,
            visible=visible,
            color=self.get_color("component_active"),
        )
        # stop button
        visible = False
        if supported_features & CoverFeatures.STOP:
            visible = True
        self.set_function_component(
            self.COMPONENTS.btn_stop,
            self.COMPONENTS.btn_stop.name,
            visible=visible,
            color=self.get_color("component_active"),
        )
        # down button
        visible = False
        if supported_features & CoverFeatures.CLOSE:
            visible = True
        self.set_function_component(
            self.COMPONENTS.btn_down,
            self.COMPONENTS.btn_down.name,
            visible=visible,
            color=self.get_color("component_active"),
        )
        # slider
        visible = False
        if supported_features & CoverFeatures.SET_POSITION:
            visible = True
        self.set_function_component(
            self.COMPONENTS.h_vert_pos, self.COMPONENTS.h_vert_pos.name, visible=visible
        )

    def update_cover_entity(self) -> None:
        self.set_component_text(self.COMPONENTS.title, self._title)
        self.update_cover_controls()
        self.update_cover_info()

    def update_cover_info(self) -> None:
        if self._cover_entity is None:
            return
        item = self._cover_entity
        current_position = item.get_item_attr("current_position", 0)
        self.set_component_text(self.COMPONENTS.t_info, f"{current_position}%")

    def update_cover_controls(self) -> None:
        if self._cover_entity is None:
            return
        item = self._cover_entity
        state = item.get_item_state()
        supported_features = item.get_item_attr("supported_features", 0)
        current_position = item.get_item_attr("current_position", 0)

        # up button
        if supported_features & CoverFeatures.OPEN:
            touch_enabled = current_position < 100
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.COMPONENTS.btn_up.name,
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.COMPONENTS.btn_up.name, visible=False)
        # stop button
        if supported_features & CoverFeatures.STOP:
            touch_enabled = state in ["opening", "closing"]
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.COMPONENTS.btn_stop.name,
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.COMPONENTS.btn_stop.name, visible=False)
        # down button
        if supported_features & CoverFeatures.CLOSE:
            touch_enabled = current_position > 0
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.COMPONENTS.btn_down.name,
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.COMPONENTS.btn_down.name, visible=False)
        # slider
        if supported_features & CoverFeatures.SET_POSITION:
            self.set_component_value(self.COMPONENTS.h_vert_pos, current_position)
            self.update_function_component(self.COMPONENTS.h_vert_pos.name, visible=True)
        else:
            self.update_function_component(self.COMPONENTS.h_vert_pos.name, visible=False)

    # callback

    def callback_cover_entity(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        if attribute in ["state", "current_position"]:
            with self.rec_cmd:
                self.update_cover_entity()
        else:
            self.log(f"Unknown cover item attribute: {attribute}")

    def callback_cover_pos(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got cover pos press: {component}-{button_state}")
        self.send_esphome(ESPRequest.REQ_VAL, self.COMPONENTS.h_vert_pos.name, force=True)

    def callback_cover_buttons(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if self._cover_entity is None:
            return
        if component == self.COMPONENTS.btn_up:
            self._cover_entity.call_item_service("open_cover")
        elif component == self.COMPONENTS.btn_stop:
            self._cover_entity.call_item_service("stop_cover")
        elif component == self.COMPONENTS.btn_down:
            self._cover_entity.call_item_service("close_cover")

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        # requested values
        if event.name == ESPResponse.RES_VAL:
            data = event.as_json()
            name = data.get("name", "")
            value = int(data.get("value", 0))
            if name == self.COMPONENTS.h_vert_pos.name:
                self.process_cover_pos(value)

    def process_cover_pos(self, pos: int) -> None:
        if self._cover_entity is not None:
            self._cover_entity.call_item_service("set_cover_position", position=pos)

from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import CoverFeatures
from ..mapping.descriptor import PageDescriptor, PageOption, _


class CoverPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="cover",
        page_name="cover",
        page_id=18,
        label=_("Cover"),
        description=_("Cover item with open, close and position controls."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="cover",
                description=_(
                    "Cover entity for opening, closing and positioning window coverings."
                ),
                section=_("Cover"),
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
        self.bind_slider(self.COMPONENTS.h_vert_pos, self.process_cover_pos)
        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )
        # set cover button callbacks
        self.on_release(
            {
                self.COMPONENTS.btn_up: self.callback_cover_up,
                self.COMPONENTS.btn_stop: self.callback_cover_stop,
                self.COMPONENTS.btn_down: self.callback_cover_down,
            }
        )
        item = self._resolve_panel_item(panel)
        self.set_cover_item(item)

        # set title
        self._title = self._panel_title(panel, item, self.translate("Cover"))
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
        # add listener
        self.add_item_listener(item.get_item_id(), self.callback_cover_entity)

        self.add_item_listener(
            item.get_item_id(),
            self.callback_cover_entity,
            attribute="current_position",
        )
        for component, flag in (
            (self.COMPONENTS.btn_up, CoverFeatures.OPEN),
            (self.COMPONENTS.btn_stop, CoverFeatures.STOP),
            (self.COMPONENTS.btn_down, CoverFeatures.CLOSE),
        ):
            self.set_function_component(
                component,
                component.name,
                visible=item.supports(flag),
                color=self.get_color("component_active"),
            )
        # slider
        self.set_function_component(
            self.COMPONENTS.h_vert_pos,
            self.COMPONENTS.h_vert_pos.name,
            visible=item.supports(CoverFeatures.SET_POSITION),
        )

    def update_cover_entity(self) -> None:
        self.set_component_text(self.COMPONENTS.title, self._title)
        self.update_cover_controls()
        self.update_cover_info()

    def update_cover_info(self) -> None:
        if self._cover_entity is None:
            return
        item = self._cover_entity
        current_position = item.get_item_attr("current_position")
        if current_position is None:
            # covers without position support only report open/closed
            info = item.translate_item_state()
        else:
            info = f"{current_position}%"
        self.set_component_text(self.COMPONENTS.t_info, info)

    def update_cover_controls(self) -> None:
        if self._cover_entity is None:
            return
        item = self._cover_entity
        state = item.get_item_state()
        current_position = item.get_item_attr("current_position")
        # covers without position support only report open/closed
        if current_position is None:
            fully_open = state == "open"
            fully_closed = state == "closed"
        else:
            fully_open = current_position >= 100
            fully_closed = current_position <= 0

        for component, flag, touch_enabled in (
            (self.COMPONENTS.btn_up, CoverFeatures.OPEN, not fully_open),
            (self.COMPONENTS.btn_stop, CoverFeatures.STOP, state in ["opening", "closing"]),
            (self.COMPONENTS.btn_down, CoverFeatures.CLOSE, not fully_closed),
        ):
            self.update_supported_component(
                component.name,
                item.supports(flag),
                touch=touch_enabled,
                **self.button_color_args(touch_enabled),
            )
        # slider
        if item.supports(CoverFeatures.SET_POSITION):
            self.set_slider_color(self.COMPONENTS.h_vert_pos, show_toggle=False)
            # an unavailable cover reports no position
            if current_position is not None:
                self.set_component_value(self.COMPONENTS.h_vert_pos, value=current_position)
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

    def callback_cover_up(self, event: HAUIEvent, component: Component) -> None:
        if self._cover_entity is not None:
            self._cover_entity.call_item_service("open_cover")

    def callback_cover_stop(self, event: HAUIEvent, component: Component) -> None:
        if self._cover_entity is not None:
            self._cover_entity.call_item_service("stop_cover")

    def callback_cover_down(self, event: HAUIEvent, component: Component) -> None:
        if self._cover_entity is not None:
            self._cover_entity.call_item_service("close_cover")

    # event

    def process_cover_pos(self, pos: int) -> None:
        self.log(f"Slider cover position value {pos}")
        if self._cover_entity is not None:
            self._cover_entity.call_item_service("set_cover_position", position=pos)

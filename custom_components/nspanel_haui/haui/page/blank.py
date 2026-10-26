from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, _


class BlankPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="blank",
        page_name="blank",
        page_id=1,
        label=_("Blank"),
        description=_("Blank page usable as the idle page."),
        is_system=True,
        sys_panel_default={
            "key": SysPanelKey.SYS_BLANK,
            "show_in_navigation": False,
        },
        icon="mdi:circle-outline",
        has_header=False,
    )

    # Not merged from HAUIPage: the blank page has no header buttons.
    COMPONENTS = ComponentRegistry(
        h_blank=Component(1, "hBlank"),
    )

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        self.add_component_callback(self.COMPONENTS.h_blank, self.callback_blank)

    # callback

    def callback_blank(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log("Blank callback")

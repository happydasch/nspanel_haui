from __future__ import annotations

from ..abstract.component import Component
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor


class BlankPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="blank",
        page_name="blank",
        label="Blank",
        description="Blank/idle page used for sleep state.",
        is_system=True,
        sys_panel_default={
            "key": "sys_blank",
            "show_in_navigation": False,
        },
        icon="mdi:circle-outline",
    )

    COMPONENTS = HAUIPage.COMPONENTS.merge(
        h_blank=Component(1, "hBlank"),
    )

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        self.add_component_callback(self.COMPONENTS.h_blank, self.callback_blank)

    # callback

    def callback_blank(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log("Blank callback")

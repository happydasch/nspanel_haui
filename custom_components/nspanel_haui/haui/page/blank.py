from __future__ import annotations

from ..abstract.event import HAUIEvent
from ..abstract.panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from . import HAUIPage


class BlankPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="blank",
        page_name="blank",
        label="Blank",
        description="Blank/idle page used for sleep state.",
        is_system=True,
        icon="mdi:circle-outline",
    )

    H_BLANK = (1, "hBlank")

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        self.add_component_callback(self.H_BLANK, self.callback_blank)

    # callback

    def callback_blank(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log("Blank callback")

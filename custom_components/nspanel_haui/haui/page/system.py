from __future__ import annotations

from ..abstract.panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from . import HAUIPage


class SystemPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system",
        page_name="system",
        label="System",
        description="System status and connection screen.",
        is_system=True,
        icon="mdi:cog-outline",
    )

    # qr code with url
    QR_URL = (1, "qrUrl")
    # spinner animation
    H_SPINNER = (2, "hSpinner")
    # text components
    TXT_TITLE = (3, "tTitle")
    TXT_MSG1 = (4, "tMsg1")
    TXT_MSG2 = (5, "tMsg2")

    # panel

    def render_panel(self, panel: HAUIPanel) -> None:
        # update default text
        self.set_title(self.translate("Waiting for Connection"))
        self.set_message(
            self.translate("This is taking longer than usual,"),
            self.translate("please check your configuration"),
        )

    def after_render_panel(self, panel: HAUIPanel, rendered: bool) -> None:
        # open home panel
        navigation = self.app.controller["navigation"]
        navigation.open_home_panel()

    # misc

    def set_title(self, title: str) -> None:
        self.set_component_text(self.TXT_TITLE, title)

    def set_message(self, text_1: str, text_2: str) -> None:
        self.set_component_text(self.TXT_MSG1, text_1)
        self.set_component_text(self.TXT_MSG2, text_2)

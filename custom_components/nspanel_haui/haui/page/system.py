from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, _


class SystemPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system",
        page_name="system",
        page_id=0,
        label=_("System"),
        description=_("System status and connection screen."),
        is_system=True,
        sys_panel_default={
            "key": "sys_system",
            "show_in_navigation": False,
        },
        icon="mdi:cog-outline",
        has_header=False,
    )

    COMPONENTS = ComponentRegistry(
        qr_url=Component(1, "qrUrl"),
        h_spinner=Component(2, "hSpinner"),
        title=Component(3, "tTitle"),
        t_msg1=Component(4, "tMsg1"),
        t_msg2=Component(5, "tMsg2"),
    )

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
        self.set_component_text(self.COMPONENTS.title, title)

    def set_message(self, text_1: str, text_2: str) -> None:
        self.set_component_text(self.COMPONENTS.t_msg1, text_1)
        self.set_component_text(self.COMPONENTS.t_msg2, text_2)

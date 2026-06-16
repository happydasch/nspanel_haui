from __future__ import annotations

from typing import TYPE_CHECKING

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icons import ICO_KEY, ICO_WIFI, ICO_ZOOM

if TYPE_CHECKING:
    from ...ha_adapter import ItemProxy


class QRPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="qr",
        page_name="qr",
        label="QR Code",
        description="Display a QR code alongside item info.",
        options=[
            PageOption(
                key="essid",
                kind="str",
                default="",
                label="WiFi SSID",
                description="WiFi network name (SSID).",
                section="Network",
            ),
            PageOption(
                key="password",
                kind="str",
                default="",
                label="WiFi password",
                description="WiFi network password.",
                section="Network",
            ),
            PageOption(
                key="start_big_qr",
                kind="bool",
                default=False,
                label="Show big code",
                description="Start with a big QR code.",
                section="Display",
            ),
            PageOption(
                key="show_info",
                kind="bool",
                default=True,
                label="Show network info",
                description="When no custom items are configured, show SSID/password"
                " as text alongside the QR code.",
                section="Display",
            ),
            PageOption(
                key="items",
                kind="item_list",
                label="Text items",
                description="Custom items shown beside the QR code (max 2).",
                section="Items",
                max_items=2,
            ),
        ],
        icon="mdi:qrcode",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        qr_code_big=Component(8, "qrCodeBig"),
        qr_code=Component(9, "qrCode"),
        q1_icon=Component(10, "q1Icon"),
        q1_title=Component(11, "q1Title"),
        q1_text=Component(12, "q1Text"),
        q1_text_add=Component(13, "q1TextAdd"),
        q2_icon=Component(14, "q2Icon"),
        q2_title=Component(15, "q2Title"),
        q2_text=Component(16, "q2Text"),
        q2_text_add=Component(17, "q2TextAdd"),
    )

    # panel

    def prepare(self) -> None:
        self.auto_dimming: ItemProxy
        self.auto_page: ItemProxy
        self._use_auto_dimming: bool
        self._use_auto_page: bool
        self._is_big: bool = False
        self._has_text: bool = False

    def start_panel(self, panel: HAUIPanel) -> None:
        name = self.app.device.get_name()
        self.on_release(self.COMPONENTS.qr_code, self.callback_qr_code)
        self.on_release(self.COMPONENTS.qr_code_big, self.callback_qr_code_big)
        self.auto_dimming = self.app.get_item(f"switch.{name}_use_auto_dimming")
        self.auto_page = self.app.get_item(f"switch.{name}_use_auto_page")
        self._use_auto_dimming = self.auto_dimming.get_state()
        self._use_auto_page = self.auto_page.get_state()

        # Compute initial state
        essid = panel.get("essid", "")
        password = panel.get("password", "")
        qr_code = f"WIFI:S:{essid};T:WPA;P:{password};;" if essid else ""
        items = self._build_items_from_panel(panel, "items")
        self._has_text = panel.get("show_info", True) or bool(items)
        self._is_big = panel.get("start_big_qr", False)

        # Add zoom button on right secondary only — leave nav buttons alone
        zoom_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "zoom",
            "fnc_args": {
                "icon": ICO_ZOOM,
                "color": self.get_color("header_accent"),
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            zoom_btn,
        )

        with self.rec_cmd:
            # Set text on both QR components so whichever is shown after a
            # zoom toggle already has its content.
            self.set_component_text(self.COMPONENTS.qr_code, qr_code)
            self.set_component_text(self.COMPONENTS.qr_code_big, qr_code)
            # Render Q1/Q2 content in the same batch as visibility so the
            # Nextion never paints empty/stale slots between batches.
            if panel.get("show_info", True):
                self._render_text(panel)
            elif items:
                self._render_items(items)
            self._apply_zoom_state()

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # restore old dimming values
        if self._use_auto_dimming and self.auto_dimming:
            self.auto_dimming.turn_on()
        if self._use_auto_page and self.auto_page:
            self.auto_page.turn_on()

    def render_panel(self, panel: HAUIPanel) -> None:
        essid = panel.get("essid", "")
        password = panel.get("password", "")
        qr_code = f"WIFI:S:{essid};T:WPA;P:{password};;" if essid else ""
        self.set_component_text(self.COMPONENTS.qr_code, qr_code)
        self.set_component_text(self.COMPONENTS.qr_code_big, qr_code)
        if panel.get("show_info", True):
            self._render_text(panel)
        else:
            items = self._build_items_from_panel(panel, "items")
            if items:
                self._render_items(items)
        self._apply_zoom_state()

    # Visibility

    def _apply_zoom_state(self) -> None:
        """Show/hide QR and Q1/Q2 components based on current _is_big state.

        Ordering: hide outgoing components first, then show incoming ones, to
        avoid unnecessary Nextion compositing passes between transitions.
        """
        if self._is_big:
            # Hide Q elements first, then show the big QR
            for component in (
                self.COMPONENTS.q1_icon,
                self.COMPONENTS.q1_title,
                self.COMPONENTS.q1_text,
                self.COMPONENTS.q1_text_add,
                self.COMPONENTS.q2_icon,
                self.COMPONENTS.q2_title,
                self.COMPONENTS.q2_text,
                self.COMPONENTS.q2_text_add,
            ):
                self.hide_component(component)
            self.hide_component(self.COMPONENTS.qr_code)
            self.show_component(self.COMPONENTS.qr_code_big)
            self.update_function_component(
                self.FNC_BTN_R_SEC, visible=True, color=self.get_color("header_accent")
            )
        else:
            # Hide big QR first, then show normal QR + Q elements.
            # No send_cmd("ref") needed — the Nextion compositor handles
            # visibility changes without a full repaint, avoiding flicker.
            self.hide_component(self.COMPONENTS.qr_code_big)
            self.show_component(self.COMPONENTS.qr_code)
            self.update_function_component(
                self.FNC_BTN_R_SEC, visible=True, color=self.get_color("component_text")
            )
            for component in (
                self.COMPONENTS.q1_icon,
                self.COMPONENTS.q1_title,
                self.COMPONENTS.q1_text,
                self.COMPONENTS.q1_text_add,
                self.COMPONENTS.q2_icon,
                self.COMPONENTS.q2_title,
                self.COMPONENTS.q2_text,
                self.COMPONENTS.q2_text_add,
            ):
                if self._has_text:
                    self.show_component(component)
                else:
                    self.hide_component(component)

    # Content rendering

    def _render_items(self, items: list) -> None:
        """Render up to 2 items into Q1/Q2 slots."""
        max_len = 20
        for i in range(2):
            if len(items) <= i:
                break
            idx = i + 1
            item = items[i]
            q_icon = getattr(self.COMPONENTS, f"q{idx}_icon")
            q_title = getattr(self.COMPONENTS, f"q{idx}_title")
            q_text = getattr(self.COMPONENTS, f"q{idx}_text")
            q_text_add = getattr(self.COMPONENTS, f"q{idx}_text_add")
            self.set_component_text(q_icon, item.get_icon())
            self.set_component_text(q_title, item.get_name())
            value = item.get_value()
            value_add = ""
            if len(value) > max_len:
                value_add = value[max_len - 1 :]
                value = value[: max_len - 1]
            self.set_component_text(q_text, value)
            self.set_component_text(q_text_add, value_add)

    def _render_text(self, panel: HAUIPanel) -> None:
        """Fill Q1/Q2 slots with SSID and password text alongside the QR code.

        Note: caller (set_panel) wraps render_panel in rec_cmd, so no need for a
        separate rec_cmd here.
        """
        self.set_component_text(self.COMPONENTS.title, panel.get_title())
        self.set_component_text(self.COMPONENTS.q1_icon, ICO_WIFI)
        self.set_component_text(self.COMPONENTS.q1_title, "SSID")
        essid = panel.get("essid", "") or ""
        self.set_component_text(self.COMPONENTS.q1_text, str(essid))
        self.set_component_text(self.COMPONENTS.q1_text_add, "")
        self.set_component_text(self.COMPONENTS.q2_icon, ICO_KEY)
        self.set_component_text(self.COMPONENTS.q2_title, "Password")
        password = panel.get("password", "") or ""
        self.set_component_text(self.COMPONENTS.q2_text, str(password))
        self.set_component_text(self.COMPONENTS.q2_text_add, "")

    # Callbacks

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        self.log(f"Got function component press: {fnc_id}")
        if fnc_name == "zoom":
            self._is_big = not self._is_big
            with self.rec_cmd:
                self._apply_zoom_state()

    def callback_qr_code(self, event: HAUIEvent, component: Component) -> None:
        if not self.panel:
            return
        if not self.auto_page or not self.auto_dimming:
            return
        self.log(f"Got qr code press: {component}")
        with self.rec_cmd:
            self._is_big = True
            self._apply_zoom_state()
            self.auto_dimming.turn_off()
            self.auto_page.turn_off()

    def callback_qr_code_big(self, event: HAUIEvent, component: Component) -> None:
        if not self.panel:
            return
        if not self.auto_page or not self.auto_dimming:
            return
        with self.rec_cmd:
            self._is_big = False
            self._apply_zoom_state()
            if self._use_auto_dimming:
                self.auto_dimming.turn_on()
            if self._use_auto_page:
                self.auto_page.turn_on()

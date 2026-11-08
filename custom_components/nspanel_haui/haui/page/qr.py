from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_KEY, ICO_WIFI, ICO_ZOOM


class QRPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="qr",
        page_name="qr",
        page_id=11,
        label=_("QR"),
        description=_("Display a QR code alongside item info."),
        options=[
            PageOption(
                key="essid",
                kind="str",
                default="",
                label=_("WiFi SSID"),
                description=_("WiFi network name (SSID)."),
                section=_("Network"),
            ),
            PageOption(
                key="password",
                kind="str",
                default="",
                label=_("WiFi password"),
                description=_("WiFi network password."),
                section=_("Network"),
            ),
            PageOption(
                key="start_big_qr",
                kind="bool",
                default=False,
                label=_("Show big code"),
                description=_("Start with a big QR code."),
                section=_("Display"),
            ),
            PageOption(
                key="show_info",
                kind="bool",
                default=True,
                label=_("Show network info"),
                description=_(
                    "When no custom items are configured, show SSID/password as text alongside the QR code."  # noqa: E501
                ),
                section=_("Display"),
            ),
            PageOption(
                key="items",
                kind="item_list",
                label=_("Text items"),
                description=_("Custom items shown beside the QR code (max 2)."),
                section=_("Items"),
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
        self._is_big: bool = False
        self._has_text: bool = False

    def start_panel(self, panel: HAUIPanel) -> None:
        self.on_release(self.COMPONENTS.qr_code, self.callback_qr_code)
        self.on_release(self.COMPONENTS.qr_code_big, self.callback_qr_code_big)

        # Compute initial state
        essid = panel.get("essid", "")
        password = panel.get("password", "")
        qr_code = f"WIFI:S:{essid};T:WPA;P:{password};;" if essid else ""
        items = self._build_items_from_panel(panel, "items")
        self.listen_items(items, lambda: self._render_items(items))
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

        # Set text on both QR components so whichever is shown after a
        # zoom toggle already has its content.
        self.set_title(panel.get_title())
        self.set_component_text(self.COMPONENTS.qr_code, qr_code)
        self.set_component_text(self.COMPONENTS.qr_code_big, qr_code)
        # Render Q1/Q2 content in the same batch as visibility so the
        # Nextion never paints empty/stale slots between batches.
        if items:
            self._render_items(items)
        elif panel.get("show_info", True):
            self._render_text(panel)
        self._apply_zoom_state()

    def suspends_auto_page(self) -> bool:
        """Keep the enlarged code on screen while it is being scanned."""
        return self._is_big

    def render_panel(self, panel: HAUIPanel) -> None:
        essid = panel.get("essid", "")
        password = panel.get("password", "")
        qr_code = f"WIFI:S:{essid};T:WPA;P:{password};;" if essid else ""
        self.set_title(panel.get_title())
        self.set_component_text(self.COMPONENTS.qr_code, qr_code)
        self.set_component_text(self.COMPONENTS.qr_code_big, qr_code)
        items = self._build_items_from_panel(panel, "items")
        if items:
            self._render_items(items)
        elif panel.get("show_info", True):
            self._render_text(panel)
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

    def _set_info_text_colors(self) -> None:
        """Use the device text palette instead of the QR page's dark-only HMI defaults."""
        for idx in (1, 2):
            self.set_component_text_color(
                getattr(self.COMPONENTS, f"q{idx}_title"), self.get_color("text")
            )
            for part in ("text", "text_add"):
                self.set_component_text_color(
                    getattr(self.COMPONENTS, f"q{idx}_{part}"), self.get_color("text_inactive")
                )

    def _render_items(self, items: list) -> None:
        """Render up to 2 items into Q1/Q2 slots."""
        self._set_info_text_colors()
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
        self._set_info_text_colors()
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
            self._set_big(not self._is_big)

    def callback_qr_code(self, event: HAUIEvent, component: Component) -> None:
        if not self.panel:
            return
        self.log(f"Got qr code press: {component}")
        self._set_big(True)

    def callback_qr_code_big(self, event: HAUIEvent, component: Component) -> None:
        if not self.panel:
            return
        self._set_big(False)

    def _set_big(self, big: bool) -> None:
        self._is_big = big
        with self.rec_cmd:
            self._apply_zoom_state()

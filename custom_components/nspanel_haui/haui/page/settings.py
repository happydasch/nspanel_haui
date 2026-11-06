from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...ha_adapter import ItemProxy

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, _


class SettingsPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system_settings",
        page_name="settings",
        page_id=3,
        label=_("Settings"),
        description=_("Display brightness and system settings."),
        is_system=True,
        sys_panel_default={
            "key": SysPanelKey.SYS_SETTINGS,
            "show_in_navigation": False,
            "show_home_button": False,
        },
        can_show_popup=True,
        icon="mdi:tune",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        t_brght_title=Component(8, "tBrghtTitle"),
        t_brght_ico=Component(9, "tBrghtIco"),
        h_brght=Component(10, "hBrght"),
        t_brght_pct=Component(11, "tBrghtPct"),
        t_brght_dim_ico=Component(12, "tBrghtDimIco"),
        h_brght_dim=Component(13, "hBrghtDim"),
        t_brght_dim_pct=Component(14, "tBrghtDimPct"),
    )

    def prepare(self) -> None:
        self.auto_dimming: ItemProxy | None = None
        self.brightness_full_entity: ItemProxy | None = None
        self.brightness_dimmed_entity: ItemProxy | None = None
        self._use_auto_dimming = False
        self._handle_brightness_full: str | None = None
        self._handle_brightness_dimmed: str | None = None
        self._full_brightness: int | None = None
        self._dimmed_brightness: int | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        auto_dimming_id = self.find_esphome_entity_id("switch", "Use Auto-Dimming")
        self.auto_dimming = self.app.get_item(auto_dimming_id) if auto_dimming_id else None
        self._use_auto_dimming = (
            self.auto_dimming is not None and self.auto_dimming.get_state() == "on"
        )
        if self.auto_dimming is not None:
            self.auto_dimming.turn_off()

        brightness_full_id = self.find_esphome_entity_id("number", "Brightness Full")
        self.brightness_full_entity = (
            self.app.get_item(brightness_full_id) if brightness_full_id else None
        )
        brightness_dimmed_id = self.find_esphome_entity_id("number", "Brightness Dimmed")
        self.brightness_dimmed_entity = (
            self.app.get_item(brightness_dimmed_id) if brightness_dimmed_id else None
        )
        self._handle_brightness_full = (
            self.brightness_full_entity.listen_state(self.callback_brightness)
            if self.brightness_full_entity is not None
            else None
        )
        self._handle_brightness_dimmed = (
            self.brightness_dimmed_entity.listen_state(self.callback_brightness)
            if self.brightness_dimmed_entity is not None
            else None
        )
        self._full_brightness = (
            self._parse_brightness(self.brightness_full_entity.get_state())
            if self.brightness_full_entity is not None
            else None
        )
        self._dimmed_brightness = (
            self._parse_brightness(self.brightness_dimmed_entity.get_state())
            if self.brightness_dimmed_entity is not None
            else None
        )

        # display components
        self.bind_slider(self.COMPONENTS.h_brght, self.process_brightness_full)
        self.bind_slider(self.COMPONENTS.h_brght_dim, self.process_brightness_dim)

        # not in navigation: up and close, the secondary slots as the panel sets
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # remove existing handles
        if self._handle_brightness_full is not None:
            self.app.cancel_listen_state(self._handle_brightness_full)
        if self._handle_brightness_dimmed is not None:
            self.app.cancel_listen_state(self._handle_brightness_dimmed)
        if self._use_auto_dimming and self.auto_dimming is not None:
            self.auto_dimming.turn_on()

    def render_panel(self, panel: HAUIPanel) -> None:
        title = panel.get_title(self.translate("Settings"))
        self.set_title(title)
        self.set_component_text(
            self.COMPONENTS.t_brght_title, self.translate("Full and Dimmed Brightness:")
        )
        if self.brightness_full_entity is not None:
            brightness_full_state = self.brightness_full_entity.get_state()
            if brightness_full_state is not None and brightness_full_state != "unavailable":
                self.set_brightness_full_slider(int(float(brightness_full_state)))
        if self.brightness_dimmed_entity is not None:
            brightness_dimmed_state = self.brightness_dimmed_entity.get_state()
            if brightness_dimmed_state is not None and brightness_dimmed_state != "unavailable":
                self.set_brightness_dim_slider(int(float(brightness_dimmed_state)))

    # misc

    def _parse_brightness(self, state: Any) -> int | None:
        if state is None or state == "unavailable":
            return None
        return int(float(state))

    def set_brightness_full_slider(self, value: int) -> None:
        self.set_slider_color(self.COMPONENTS.h_brght)
        self.set_component_value(self.COMPONENTS.h_brght, value)
        self.send_cmd(f"click {self.COMPONENTS.t_brght_pct.name},0")

    def set_brightness_dim_slider(self, value: int) -> None:
        self.set_slider_color(self.COMPONENTS.h_brght_dim)
        self.set_component_value(self.COMPONENTS.h_brght_dim, value)
        self.send_cmd(f"click {self.COMPONENTS.t_brght_dim_pct.name},0")

    # callback

    def callback_brightness(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        self.log(f"Got brightness callback: {item}.{attribute}:{new}")
        # callback from ha
        if (
            self.brightness_full_entity is not None
            and item == self.brightness_full_entity.entity_id
        ):
            value = self._parse_brightness(new)
            if value is not None:
                if self._full_brightness != value:
                    self._full_brightness = value
                self.set_brightness_full_slider(value)
        elif (
            self.brightness_dimmed_entity is not None
            and item == self.brightness_dimmed_entity.entity_id
        ):
            value = self._parse_brightness(new)
            if value is not None:
                if self._dimmed_brightness != value:
                    self._dimmed_brightness = value
                self.set_brightness_dim_slider(value)

    # event

    def process_brightness_full(self, value: int) -> None:
        if self.brightness_full_entity is None:
            return
        self.log(f"Slider full brightness value {value}")
        if self._full_brightness != value:
            self._full_brightness = value
            self.brightness_full_entity.set_state(state=value)

    def process_brightness_dim(self, value: int) -> None:
        if self.brightness_dimmed_entity is None:
            return
        self.log(f"Slider dimmed brightness value {value}")
        if self._dimmed_brightness != value:
            self._dimmed_brightness = value
            self.brightness_dimmed_entity.set_state(state=value)

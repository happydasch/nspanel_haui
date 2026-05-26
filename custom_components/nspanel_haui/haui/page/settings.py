from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPRequest, ESPResponse
from ..mapping.descriptor import PageDescriptor


class SettingsPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system_settings",
        page_name="settings",
        label="Settings",
        description="Display brightness and system settings.",
        is_system=True,
        sys_panel_default={
            "key": "sys_settings",
            "show_in_navigation": False,
            "show_home_button": False,
        },
        can_show_popup=True,
        icon="mdi:tune",
    )

    COMPONENTS = ComponentRegistry(
        title=Component(2, "tTitle"),
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        t_brght_title=Component(7, "tBrghtTitle"),
        t_brght_ico=Component(8, "tBrghtIco"),
        h_brght=Component(9, "hBrght"),
        t_brght_pct=Component(10, "tBrghtPct"),
        t_brght_dim_ico=Component(11, "tBrghtDimIco"),
        h_brght_dim=Component(12, "hBrghtDim"),
        t_brght_dim_pct=Component(13, "tBrghtDimPct"),
    )

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        name = self.app.device.get_name()

        # auto dimming component
        self.auto_dimming = self.app.get_item(f"switch.{name}_use_auto_dimming")
        self._use_auto_dimming = self.auto_dimming.get_state()
        self.auto_dimming.turn_off()

        # brightness components
        self.brightness_full_entity = self.app.get_item(f"number.{name}_brightness_full")
        self.brightness_dimmed_entity = self.app.get_item(f"number.{name}_brightness_dimmed")
        self._handle_brightness_full = self.brightness_full_entity.listen_state(
            self.callback_brightness
        )
        self._handle_brightness_dimmed = self.brightness_dimmed_entity.listen_state(
            self.callback_brightness
        )
        self._full_brightness = self.brightness_full_entity.get_state()
        self._dimmed_brightness = self.brightness_dimmed_entity.get_state()

        # display components
        self.add_component_callback(self.COMPONENTS.h_brght, self.callback_slider_brightness)
        self.add_component_callback(self.COMPONENTS.h_brght_dim, self.callback_slider_brightness)

        # set function buttons
        with self.rec_cmd:
            self.set_function_component(
                self.COMPONENTS.fnc_left_pri, self.FNC_BTN_L_PRI,
                fnc_name=self.FNC_TYPE_NAV_UP,
            )
            self.set_function_component(
                self.COMPONENTS.fnc_right_pri, self.FNC_BTN_R_PRI,
                fnc_name=self.FNC_TYPE_NAV_CLOSE,
            )
            # left and right secondary buttons are unused (hidden, no callback)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # remove existing handles
        if self._handle_brightness_full:
            self.app.cancel_listen_state(self._handle_brightness_full)
        if self._handle_brightness_dimmed:
            self.app.cancel_listen_state(self._handle_brightness_dimmed)
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()

    def render_panel(self, panel: HAUIPanel) -> None:
        title = panel.get_title(self.translate("Settings"))
        self.set_component_text(self.COMPONENTS.title, title)
        self.set_component_text(
            self.COMPONENTS.t_brght_title, self.translate("Full and Dimmed Brightness:")
        )
        # update settings
        brightness_full_state = self.brightness_full_entity.get_state()
        if brightness_full_state is not None and brightness_full_state != "unavailable":
            brightness_full = int(float(brightness_full_state))
            self.set_brightness_full_slider(brightness_full)
        brightness_dimmed_state = self.brightness_dimmed_entity.get_state()
        if brightness_dimmed_state is not None and brightness_dimmed_state != "unavailable":
            brightness_dimmed = int(float(brightness_dimmed_state))
            self.set_brightness_dim_slider(brightness_dimmed)

    # misc

    def set_brightness_full_slider(self, value: int) -> None:
        self.set_component_value(self.COMPONENTS.h_brght, value)
        self.send_cmd(f"click {self.COMPONENTS.t_brght_pct[1]},0")

    def set_brightness_dim_slider(self, value: int) -> None:
        self.set_component_value(self.COMPONENTS.h_brght_dim, value)
        self.send_cmd(f"click {self.COMPONENTS.t_brght_dim_pct[1]},0")

    # callback

    def callback_slider_brightness(
        self, event: HAUIEvent, component: tuple, button_state: int
    ) -> None:
        self.log(f"Got slider brightness press: {component}-{button_state}")
        if button_state:
            return
        self.send_esphome(ESPRequest.REQ_VAL, component[1], force=True)

    def callback_brightness(
        self, item: str, attribute: str, old: Any, new: Any, **cb_args: Any
    ) -> None:
        self.log(f"Got brightness callback: {item}.{attribute}:{new}")
        # callback from ha
        if self.brightness_full_entity and item == self.brightness_full_entity.entity_id:
            if new.isnumeric():
                if self._full_brightness != new:
                    self._full_brightness = new
                self.set_brightness_full_slider(new)
        elif self.brightness_dimmed_entity and item == self.brightness_dimmed_entity.entity_id:
            if new.isnumeric():
                if self._dimmed_brightness != new:
                    self._dimmed_brightness = new
                self.set_brightness_dim_slider(new)

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        # check for values for full and dimmed brightness
        if event.name == ESPResponse.RES_VAL:
            # parse json response, set brightness
            data = event.as_json()
            if data.get("name", "") == self.COMPONENTS.h_brght[1]:
                if self._full_brightness != data["value"]:
                    self._full_brightness = data["value"]
                    self.brightness_full_entity.set_state(state=data["value"])
            elif data.get("name", "") == self.COMPONENTS.h_brght_dim[1]:
                if self._dimmed_brightness != data["value"]:
                    self._dimmed_brightness = data["value"]
                    self.brightness_dimmed_entity.set_state(state=data["value"])

from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from ..version import get_version


class AboutPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system_about",
        page_name="about",
        label="About",
        description="Device info and version details.",
        is_system=True,
        sys_panel_default={
            "key": "sys_about",
            "show_in_navigation": False,
            "show_home_button": False,
        },
        can_show_popup=True,
        icon="mdi:information-outline",
    )

    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        title=Component(2, "tTitle"),
        t_about_1=Component(7, "tAbout1"),
        t_about_2=Component(8, "tAbout2"),
        t_device_name=Component(9, "tDeviceName"),
        t_ip=Component(10, "tIP"),
        t_tft_vers=Component(11, "tTftVers"),
        t_tft_vers_val=Component(12, "tTftVersVal"),
        t_yaml_vers=Component(13, "tYamlVers"),
        t_yaml_vers_val=Component(14, "tYamlVersVal"),
        t_ad_vers=Component(15, "tADVers"),
        t_ad_vers_val=Component(16, "tADVersVal"),
    )

    _title = ""

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        with self.rec_cmd:
            # set function buttons
            self.set_function_buttons(
                self.COMPONENTS.fnc_left_pri,
                self.COMPONENTS.fnc_left_sec,
                self.COMPONENTS.fnc_right_pri,
                self.COMPONENTS.fnc_right_sec,
            )

            # title
            self._title = panel.get_title(self.translate("NSPanel HAUI"))
            self.set_component_text(self.COMPONENTS.title, self._title)

    def render_panel(self, panel: HAUIPanel) -> None:
        name = self.app.device.get_name()
        ip_address = self.app.device.device_info.get("ip", "127.0.0.1")
        tft_version = self.app.device.device_info.get("tft_version", "0.0.0")
        yaml_version = self.app.device.device_info.get("yaml_version", "0.0.0")
        ad_version = get_version()
        # about text
        self.set_component_text(
            self.COMPONENTS.t_about_1,
            self.translate("Versatile wall panel for HomeAssistant based"),
        )
        self.set_component_text(
            self.COMPONENTS.t_about_2, self.translate("smart homes with a custom UI Design.")
        )
        # name
        self.set_component_text(self.COMPONENTS.t_device_name, name)
        # ip address
        self.set_component_text(self.COMPONENTS.t_ip, f"{ip_address}")
        # tft version
        self.set_component_text(self.COMPONENTS.t_tft_vers, self.translate("TFT-Version:"))
        self.set_component_text(self.COMPONENTS.t_tft_vers_val, tft_version)
        # yaml version
        self.set_component_text(self.COMPONENTS.t_yaml_vers, self.translate("YAML-Version:"))
        self.set_component_text(self.COMPONENTS.t_yaml_vers_val, yaml_version)
        # ad version
        self.set_component_text(self.COMPONENTS.t_ad_vers, self.translate("AD-Version:"))
        self.set_component_text(self.COMPONENTS.t_ad_vers_val, ad_version)

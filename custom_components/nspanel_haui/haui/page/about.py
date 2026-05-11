from ..abstract.panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from ..version import get_version
from . import HAUIPage


class AboutPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="system_about",
        page_name="about",
        label="About",
        description="Device info and version details.",
        is_system=True,
    )

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # about text
    TXT_ABOUT_1, TXT_ABOUT_2 = (7, "tAbout1"), (8, "tAbout2")
    # about vars
    TXT_NAME, TXT_IP = (9, "tDeviceName"), (10, "tIP")
    TXT_TFT_VERS, TXT_TFT_VERS_VAL = (11, "tTftVers"), (12, "tTftVersVal")
    TXT_YAML_VERS, TXT_YAML_VERS_VAL = (13, "tYamlVers"), (14, "tYamlVersVal")
    TXT_AD_VERS, TXT_AD_VERS_VAL = (15, "tADVers"), (16, "tADVersVal")

    _title = ""

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        with self.rec_cmd:
            # set function buttons
            self.set_function_buttons(
                self.BTN_FNC_LEFT_PRI,
                self.BTN_FNC_LEFT_SEC,
                self.BTN_FNC_RIGHT_PRI,
                self.BTN_FNC_RIGHT_SEC,
            )

            # title
            self._title = panel.get_title(self.translate("NSPanel HAUI"))
            self.set_component_text(self.TXT_TITLE, self._title)

    def render_panel(self, panel: HAUIPanel) -> None:
        name = self.app.device.device_info.get("friendly_name", self.app.device.get_name())
        ip_address = self.app.device.device_info.get("ip", "127.0.0.1")
        tft_version = self.app.device.device_info.get("tft_version", "0.0.0")
        yaml_version = self.app.device.device_info.get("yaml_version", "0.0.0")
        ad_version = get_version()
        # about text
        self.set_component_text(
            self.TXT_ABOUT_1,
            self.translate("Versatile wall panel for HomeAssistant based"),
        )
        self.set_component_text(
            self.TXT_ABOUT_2, self.translate("smart homes with a custom UI Design.")
        )
        # name
        self.set_component_text(self.TXT_NAME, name)
        # ip address
        self.set_component_text(self.TXT_IP, f"{ip_address}")
        # tft version
        self.set_component_text(self.TXT_TFT_VERS, self.translate("TFT-Version:"))
        self.set_component_text(self.TXT_TFT_VERS_VAL, tft_version)
        # yaml version
        self.set_component_text(self.TXT_YAML_VERS, self.translate("YAML-Version:"))
        self.set_component_text(self.TXT_YAML_VERS_VAL, yaml_version)
        # ad version
        self.set_component_text(self.TXT_AD_VERS, self.translate("AD-Version:"))
        self.set_component_text(self.TXT_AD_VERS_VAL, ad_version)

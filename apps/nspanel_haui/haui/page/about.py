from . import HAUIPage
import haui.version


class AboutPage(HAUIPage):

    # common components
    BTN_STATE_BTN_LEFT, BTN_STATE_BTN_RIGHT = (2, 'bBtnStateLeft'), (3, 'bBtnStateRight')
    BTN_NAV_CLOSE, TXT_TITLE = (4, 'bNavClose'), (5, 'tTitle')
    # About Text
    TXT_ABOUT_1, TXT_ABOUT_2 = (6, 'tAbout1'), (7, 'tAbout2')
    # About Vars
    TXT_DEVICE_NAME, TXT_IP = (8, 'tDeviceName'), (9, 'tIP')
    TXT_TFT_VERS, TXT_TFT_VERS_VAL = (10, 'tTftVers'), (11, 'tTftVersVal')
    TXT_YAML_VERS, TXT_YAML_VERS_VAL = (12, 'tYamlVers'), (13, 'tYamlVersVal')
    TXT_AD_VERS, TXT_AD_VERS_VAL = (14, 'tADVers'), (15, 'tADVersVal')
    TXT_PROJECT_URL, PIC_APPS = (16, 'tProjectUrl'), (17, 'pApps')

    # panel

    def start_panel(self, panel):
        panel._config['nav_panel'] = False
        self.set_button_state_buttons(self.BTN_STATE_BTN_LEFT, self.BTN_STATE_BTN_RIGHT)
        self.set_close_nav_button(self.BTN_NAV_CLOSE)

    def render_panel(self, panel):
        device_name = self.app.device.device_vars.get('device_friendly_name', '')
        ip_address = self.app.device.device_vars.get('device_ip', '127.0.0.1')
        tft_version = self.app.device.device_vars.get('tft_version', '0.0.0')
        yaml_version = self.app.device.device_vars.get('yaml_version', '0.0.0')
        ad_version = haui.version.__version__

        # about text
        self.set_component_text(self.TXT_ABOUT_1, self.translate('Wall-Panel for HomeAssistant based Smart'))
        self.set_component_text(self.TXT_ABOUT_2, self.translate('Homes in Lovelace UI Design.'))

        # common vars
        self._title = panel.get_title(self.translate('About NSPanel HAUI'))
        self.set_component_text(self.TXT_TITLE, self._title)
        # device_name
        self.set_component_text(self.TXT_DEVICE_NAME, device_name)
        # tft version
        self.set_component_text(self.TXT_TFT_VERS, self.translate('TFT-Version:'))
        self.set_component_text(self.TXT_TFT_VERS_VAL, tft_version)
        # yaml version
        self.set_component_text(self.TXT_YAML_VERS, self.translate('YAML-Version:'))
        self.set_component_text(self.TXT_YAML_VERS_VAL, yaml_version)
        # ad version
        self.set_component_text(self.TXT_AD_VERS, self.translate('AD-Version:'))
        self.set_component_text(self.TXT_AD_VERS_VAL, ad_version)
        # ip address
        ip_text = self.translate('IP:')
        self.set_component_text(self.TXT_IP, f'{ip_text} {ip_address}')
        # project url
        self.set_component_text(self.TXT_PROJECT_URL, 'https://github.com/happydasch/nspanel_haui')

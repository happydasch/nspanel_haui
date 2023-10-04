from distutils.version import LooseVersion

import threading
import json
import requests

from ..helper.text import trim_text
from ..mapping.color import COLORS
from ..const import ESP_EVENT, ESP_REQUEST, ESP_RESPONSE
from ..base import HAUIPart


class HAUIUpdateController(HAUIPart):

    """
    Update Controller
    - check for display tft version
    """

    RELEASES_URL = 'https://api.github.com/repos/happydasch/nspanel_haui/releases'

    def __init__(self, app, config):
        """ Initialize for update controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f'Creating Update Controller with config: {config}')
        self._timer = None  # timer for update check by interval
        self._connected_timer = None  # timer for update check on connected
        self._device_info = None
        self._req_await = False
        self._update_url = None
        self._interval = 0

    # internal

    def _start_timer(self, interval):
        if self._timer is not None:
            return
        self._interval = interval
        self._timer = threading.Timer(interval, self.callback_timer)
        self._timer.daemon = True
        self._timer.start()

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _restart_timer(self):
        self._stop_timer()
        self._start_timer(self._interval)

    def _start_connected_timer(self, interval):
        self._connected_timer = threading.Timer(
            interval, lambda: self.request_device_info(True))
        self._connected_timer.start()

    def _stop_connected_timer(self):
        if self._connected_timer is not None:
            self._connected_timer.cancel()
            self._connected_timer = None

    # part

    def start_part(self):
        """ Starts the part.
        """
        interval = self.get('update_interval', 0)
        if interval > 0:
            self._start_timer(interval)

    def stop_part(self):
        """ Stops the part.
        """
        self._stop_timer()
        self._stop_connected_timer()

    # public

    def request_device_info(self, check_for_update=True):
        """ Sends a device info request to the panel.

        Args:
            check_for_update (bool, optional): Should the controller check for updates. Defaults to True.
        """
        self.log('Sending device_info request')
        self.send_mqtt(ESP_REQUEST['req_device_info'])
        self._req_await = check_for_update

    def check_required_tft_version(self):
        """ Checks if the required tft version is installed.
        """
        if self._device_info is None:
            self.log('No device info available')
            return
        device_info = self._device_info
        required_version = device_info.get('required_tft_version')
        installed_version = device_info.get('tft_version')
        if required_version is None or installed_version is None:
            # notify about unknown versions
            msg = self.translate('Got unknown TFT-Version information.')
        elif LooseVersion(required_version) > LooseVersion(installed_version):
            # notify about outdated tft version
            msg = self.translate('Your TFT-version is outdated.')
        else:
            # everything is fine (installed version is newer or equal to required version)
            return
        # append check for update text
        msg += '\r\n'
        msg += self.translate('Do you want to check for a update?')
        # open notification
        navigation = self.app.controller['navigation']
        navigation.open_popup(
            'popup_notify',
            icon='mdi:message-question',
            title=self.translate('Outdated TFT-Version'),
            btn_left_color=COLORS['component_active'],
            btn_right_color=COLORS['component_active'],
            btn_right_back_color=COLORS['component_pressed'],
            btn_left=self.translate('Cancel'),
            btn_right=self.translate('Check'),
            open_prev_on_close=False,
            button_callback_fnc=self.callback_check_response,
            notification=msg)

    def check_for_update(self):
        """ Checks for updates.
        """
        if self._device_info is None:
            self.log('No device info available')
            return False
        device_info = self._device_info
        try:
            resp = requests.get(self.RELEASES_URL, timeout=5)
            json_decoded = resp.json()
        except requests.exceptions.RequestException:
            self.log('Could not get release info')
            return False
        self.log('Checking for update')
        # get the latest release
        latest_release = None
        for release in json_decoded:
            if latest_release is None:
                temp_version = None
            else:
                temp_version = LooseVersion(latest_release['tag_name'])
            new_version = LooseVersion(release['tag_name'])
            if temp_version is None or new_version > temp_version:
                latest_release = release
        # check latest release against currently installed version
        if latest_release is None:
            self.log('No release available')
            return False
        current_version = LooseVersion(device_info['tft_version'])
        latest_version = LooseVersion(latest_release['tag_name'])
        if current_version >= latest_version:
            self.log('No update available')
            return False
        # check for availability of tft file
        tft_filename = self.get('tft_filename')
        assets = latest_release['assets']
        tft_file_asset = None
        for asset in assets:
            if asset['name'] == tft_filename:
                tft_file_asset = asset
        if tft_file_asset is None:
            self.log('No tft file available')
            return False
        self._update_url = tft_file_asset['browser_download_url'].replace('https', 'http')
        # notify about the new release
        name = latest_release['name']
        description = latest_release['body']
        # notify about new release (or update if autoupdate)
        if self.get('auto_update', False):
            self.run_update_display()
        else:
            msg = name
            msg += '\r\n'
            msg += trim_text(description, 200)
            msg += '\r\n'
            msg += self.translate('Current Version:')
            msg += ' ' + str(device_info['tft_version'])
            msg += '\r\n'
            msg += self.translate('New Version:')
            msg += ' ' + str(new_version)
            msg += '\r\n'
            msg += self.translate('Do you want to update?')
            # open notification
            navigation = self.app.controller['navigation']
            navigation.open_popup(
                'popup_notify',
                icon='mdi:message-question',
                title=self.translate('Update available'),
                btn_left_color=COLORS['component_active'],
                btn_right_color=COLORS['component_active'],
                btn_right_back_color=COLORS['component_pressed'],
                btn_left=self.translate('Cancel'),
                btn_right=self.translate('Update'),
                button_callback_fnc=self.callback_update_response,
                notification=msg)
        return True

    def run_update_display(self):
        if self._update_url is None:
            self.log('No update url available')
            return
        # run update
        device_name = self.app.device.get('device_name', 'nspanel_haui')
        self.app.call_service(
            f'esphome/{device_name}_upload_tft_url',
            url=self._update_url)

    # callback

    def callback_check_response(self, btn_left, btn_right):
        navigation = self.app.controller['navigation']
        if btn_right:
            navigation.close_panel(False)
            self._stop_connected_timer()
            update = self.check_for_update()
            if update:
                return
            msg = self.translate('There is no update available')
            # open notification
            navigation = self.app.controller['navigation']
            navigation.open_popup(
                'popup_notify',
                icon='mdi:message-alert',
                title=self.translate('No update found'),
                btn_right_color=COLORS['component_active'],
                btn_right=self.translate('Close'),
                notification=msg)
        else:
            navigation.close_panel()

    def callback_update_response(self, btn_left, btn_right):
        if btn_right:
            self.run_update_display()

    def callback_timer(self):
        self._restart_timer()
        self.request_device_info(True)

    # event

    def process_event(self, event):
        """ Process events.

        Args:
            event (HAUIEvent): Event
        """
        if event.name == ESP_EVENT['connected']:
            self._stop_connected_timer()
            # request device infos when device connects
            if self.get('check_on_connect', False):
                delay_interval = self.get('on_connect_delay', 30)
                self.log(f'Checking for update on connect in {delay_interval} seconds')
                self._start_connected_timer(delay_interval)
            # always request device infos when device is connected
            # so a check for outdated tft version can be done quicker
            # than first update check
            self.request_device_info(False)

        # device info is received, check for update with device info
        if event.name == ESP_RESPONSE['res_device_info']:
            device_info = json.loads(event.value)
            self._device_info = device_info
            self.app.device.set_device_vars(device_info, append=True)
            self.check_required_tft_version()
            # only if update controller requested the value
            if self._req_await:
                self.check_for_update()

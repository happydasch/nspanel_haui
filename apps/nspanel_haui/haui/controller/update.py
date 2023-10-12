import threading
import json
import requests

from pkg_resources import parse_version  # https://peps.python.org/pep-0386/

from ..helper.text import trim_text
from ..mapping.color import COLORS
from ..const import ESP_EVENT, ESP_REQUEST, ESP_RESPONSE
from ..base import HAUIPart


class HAUIUpdateController(HAUIPart):

    """
    Update Controller

    The update controller is used to check for updates and to install them. The controller
    checks for the currently installed tft version and compares it to the versions available
    on github.

    It supports the following features:

    - check for version mismatch of installed tft version and required tft version
        (this is always active and cannot be disabled, this check is done when connecting)

    - check for updates on a regular basis and either ask user for update if there
        is a update available or install update automatically
        (this is only active if the update check interval is bigger 0)
    """

    # hard-coded url for haui relases on github
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
        self._timer_delay = None  # timer to delay update check on connected event
        self._interval = 0  # update check interval
        self._interval_delay = 0  # on connect check delay
        self._req_fetch = False  # is being used to identify release info request
        self._req_await = False  # is being used to identify device info request
        self._release_infos = []  # store latest release infos

    # internal timers for version checks

    def _start_timer(self):
        if self._timer is not None or self._interval == 0:
            return
        self._timer = threading.Timer(self._interval, self.callback_timer)
        self._timer.daemon = True
        self._timer.start()

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _restart_timer(self):
        self._stop_timer()
        self._start_timer()

    def _start_timer_delay(self):
        self._timer_delay = threading.Timer(
            self._interval_delay,
            lambda: self.request_device_info(True))
        self._timer_delay.start()

    def _stop_timer_delay(self):
        if self._timer_delay is not None:
            self._timer_delay.cancel()
            self._timer_delay = None

    # part

    def start_part(self):
        """ Starts the part.
        """
        self._interval = self.get('update_interval', 0)
        self._interval_delay = self.get('on_connect_delay', 30)
        self._start_timer()

    def stop_part(self):
        """ Stops the part.
        """
        self._stop_timer()
        self._stop_timer_delay()

    # device

    def request_device_info(self, check_for_update=True):
        """ Sends a device info request to the panel.

        This will generate a mqtt response which will later be processed.

        Args:
            check_for_update (bool, optional): Should the controller check for updates. Defaults to True.
        """
        self.log('Sending device_info request')
        self.send_mqtt(ESP_REQUEST['req_device_info'])
        self._req_await = check_for_update

    # update

    def _update_release_infos(self):
        """ Updates the release informations.
        """
        if self._req_fetch:
            return
        self._req_fetch = True
        try:
            resp = requests.get(self.RELEASES_URL, timeout=5)
            json_decoded = resp.json()
        except requests.exceptions.RequestException:
            self.log('Could not fetch release informations')
            json_decoded = []
        self._release_infos = json_decoded
        self._req_fetch = False

    def _get_latest_release(self):
        """ Returns the latest available release dict.

        Returns:
            None|dict: Release info
        """
        latest_release = None
        for release in self._release_infos:
            if latest_release is None:
                temp_version = None
            else:
                temp_version = parse_version(latest_release['tag_name'])
            new_version = parse_version(release['tag_name'])
            if temp_version is None or new_version > temp_version:
                latest_release = release
        return latest_release

    def _get_update_url(self, release_info):
        """ Returns the update url to the tft file from given release.

        Args:
            release_info (dict): Release info

        Returns:
            None|str: Update url
        """
        if release_info is None:
            return None
        tft_filename = self.get('tft_filename')
        assets = release_info['assets']
        tft_file_asset = None
        for asset in assets:
            if asset['name'] == tft_filename:
                tft_file_asset = asset
        if tft_file_asset is None:
            return None
        return tft_file_asset['browser_download_url']

    def _is_update_available(self):
        """ Returns if a update is available.

        Returns:
            bool: True if an update is available, False if not
        """
        device_info = self.app.device.device_info
        if device_info is None:
            return False
        latest_release = self._get_latest_release()
        current_version = parse_version(device_info['tft_version'])
        latest_version = parse_version(latest_release['tag_name'])
        if current_version < latest_version:
            return True
        return False

    def run_update_display(self):
        """ Runs the update process for the display.
        """
        latest_release = self._get_latest_release()
        if latest_release is None:
            self.log('No release info available')
            return
        update_url = self._get_update_url(latest_release)
        if update_url is None:
            self.log('No update url available')
            return
        # run update
        device_name = self.app.device.get('device_name', 'nspanel_haui')
        self.app.call_service(f'esphome/{device_name}_upload_tft_url', url=update_url)

    def check_installed_version(self):
        """ Checks on connect if a update is available.
        """
        device_info = self.app.device.device_info
        required_version = device_info.get('required_tft_version')
        installed_version = device_info.get('tft_version')
        if required_version is None or installed_version is None:
            # notify about unknown versions
            msg = self.translate('Got unknown TFT-Version information.')
        elif parse_version(required_version) > parse_version(installed_version):
            # notify about outdated tft version
            msg = self.translate('Your TFT-version is outdated.')
        else:
            # everything is fine (installed version is newer or equal to required version)
            return
        self._stop_timer_delay()  # ensure there is no delay on connect timer
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
            close_on_button=False,
            button_callback_fnc=self.callback_version_response,
            notification=msg)

    def check_for_update(self):
        """ Checks if a update is available.
        """
        self._stop_timer_delay()
        self._update_release_infos()
        latest_release = self._get_latest_release()
        if not self._is_update_available() or latest_release is None:
            return
        name = latest_release['name']
        description = latest_release['body']
        # notify about new release (or update if autoupdate)
        if self.get('auto_update', False):
            self.run_update_display()
        # open notification
        else:
            device_info = self.app.device.device_info
            navigation = self.app.controller['navigation']
            msg = name
            msg += '\r\n'
            msg += trim_text(description, 200)
            msg += '\r\n\r\n'
            msg += self.translate('Version:')
            msg += f' {device_info["tft_version"]} -> {latest_release["tag_name"]}'
            msg += '\r\n\r\n'
            msg += self.translate('Do you want to update?')
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
                close_on_button=False,
                notification=msg)

    # callback

    def callback_version_response(self, btn_left, btn_right):
        """ Callback method for check update response.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
        """
        self.log("Callback version response")
        navigation = self.app.controller['navigation']
        if btn_right:
            self.request_device_info(True)
        navigation.close_panel()

    def callback_update_response(self, btn_left, btn_right):
        """ Callback method for update to new version response.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
        """
        self.log("Callback update response")
        navigation = self.app.controller['navigation']
        if btn_left:
            navigation.close_panel()
        if btn_right:
            msg = self.translate('Please wait while the update is starting')
            navigation.open_popup(
                'popup_notify',
                icon='mdi:message-cog',
                title=self.translate('Starting Update'),
                notification=msg)
            self.run_update_display()

    def callback_timer(self):
        """ Callback method for timer.
        """
        self.request_device_info(True)
        self._restart_timer()

    # event

    def process_event(self, event):
        """ Process events.

        Args:
            event (HAUIEvent): Event
        """

        # on connect
        if event.name == ESP_EVENT['connected']:
            self._stop_timer_delay()
            # request device infos when device connects
            if self.get('check_on_connect', False):
                delay_interval = self.get('on_connect_delay', 30)
                self.log(f'Checking for update on connect in {delay_interval} seconds')
                self._start_timer_delay()
            # always request device infos when device is connected
            # so a check for outdated tft version can be done faster
            # than first update check
            self.request_device_info(False)

        # device info received, check for update using device info
        if event.name == ESP_RESPONSE['res_device_info']:
            device_info = json.loads(event.value)
            self.app.device.set_device_info(device_info, append=True)
            # check the required tft version defined on the esp
            # to match currently installed version on the display
            if not self._req_await:
                self.check_installed_version()
            # only if update interval is bigger than 0 and update controller
            # requested the value
            elif self._req_await and self._interval > 0:
                threading.Thread(target=self.check_for_update, daemon=True).start()
                self._req_await = False

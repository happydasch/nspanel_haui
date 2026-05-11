from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import requests
from packaging.version import InvalidVersion, Version, parse

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.base import HAUIBase
from ..abstract.event import HAUIEvent
from ..mapping.color import COLORS
from ..mapping.const import ESPAction, ESPEvent, ESPRequest, ESPResponse
from ..utils.text import trim_text


class HAUIUpdateController(HAUIBase):
    """Update Controller

    The update controller is used to check for updates and to install them. The controller
    checks for the currently installed tft version and compares it to the versions available
    on github.

    It supports the following features:

    - check for version mismatch of installed tft version and required tft version
        (this is always active and cannot be disabled, this check is done when connecting)

    - check for updates on a regular basis and either ask user for update if there
        is a update available or install update automatically
        (this is only active if the update check interval is bigger 0)

    - check for initial display upload if the panel is connected
        (this can be deactivated by configuration)
    """

    # hard-coded url for haui relases on github
    RELEASES_URL = "https://api.github.com/repos/happydasch/nspanel_haui/releases"

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for update controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.debug_log(f"Creating Update Controller with config: {config}")
        self._timer = None  # timer for update check by interval
        self._timer_delay = None  # timer to delay update check on connected event
        self._interval = 0  # update check interval
        self._interval_delay = 0  # on connect check delay
        self._req_fetch = False  # is being used to identify release info request
        self._release_infos: list[dict[str, Any]] = []  # store latest release infos

    # internal timers for version checks

    def _start_timer(self) -> None:
        if self._timer is not None or self._interval == 0:
            return
        self._timer = self.app.run_every(
            self._timer_callback, f"now+{self._interval}", self._interval
        )

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self.app.cancel_timer(self._timer)
            self._timer = None

    def _restart_timer(self) -> None:
        self._stop_timer()
        self._start_timer()

    def _timer_callback(self, kwargs: dict[str, Any]) -> None:
        self.callback_timer()

    def _start_timer_delay(self) -> None:
        self._timer_delay = self.app.run_in(self._timer_delay_callback, self._interval_delay)

    def _stop_timer_delay(self) -> None:
        if self._timer_delay is not None:
            self.app.cancel_timer(self._timer_delay)
            self._timer_delay = None

    def _timer_delay_callback(self, kwargs: dict[str, Any]) -> None:
        self.check_installed_version()

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self._interval = self.get("update_interval")
        self._interval_delay = self.get("on_connect_delay")
        self._start_timer()

    def stop_part(self) -> None:
        """Stops the part."""
        self._stop_timer()
        self._stop_timer_delay()

    # device

    def request_device_info(self, check_for_update: bool = True) -> None:
        """Sends a device info request to the panel.

        This will generate an ESPHome response which will later be processed.

        Args:
            check_for_update (bool, optional): Whether to check for updates. Defaults to True.
        """
        self.log("Sending device_info request")
        self.send_esphome(ESPRequest.REQ_DEVICE_INFO)

    # update

    def _parse_version(self, version: str) -> Version:
        """Parses the given version string and returns a Version object.

        Args:
            version (str): Version string

        Returns:
            Version: parsed Version
        """
        try:
            vers = parse(version)
        except InvalidVersion:
            vers = Version("0.0.0")
        return vers

    def _update_release_infos(self) -> None:
        """Updates the release informations."""
        if self._req_fetch:
            return
        self._req_fetch = True
        try:
            resp = requests.get(self.RELEASES_URL, timeout=5)
            json_decoded = resp.json()
            if not isinstance(json_decoded, list):
                self.log("Unexpected response from GitHub API", level="WARNING")
                json_decoded = []
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch release info from {self.RELEASES_URL}: {exc}"
            ) from exc
        self._release_infos = json_decoded
        self._req_fetch = False

    def _get_latest_release(self) -> dict[str, Any] | None:
        """Returns the latest available release dict.

        Returns:
            None|dict: Release info
        """
        latest_release = None
        for release in self._release_infos:
            if latest_release is None:
                temp_version = None
            else:
                temp_version = self._parse_version(latest_release["tag_name"])
            new_version = self._parse_version(release["tag_name"])
            if temp_version is None or new_version > temp_version:
                latest_release = release
        return latest_release

    def _get_update_url(self, release_info: dict[str, Any] | None) -> str | None:
        """Returns the update url to the tft file from given release.

        Args:
            release_info (dict): Release info

        Returns:
            None|str: Update url
        """
        if release_info is None:
            return None
        tft_filename = self.get("tft_filename")
        assets = release_info["assets"]
        tft_file_asset = None
        for asset in assets:
            if asset["name"] == tft_filename:
                tft_file_asset = asset
        if tft_file_asset is None:
            return None
        return tft_file_asset["browser_download_url"]

    def _is_update_available(self) -> bool:
        """Returns if a update is available.

        Returns:
            bool: True if an update is available, False if not
        """
        device_info = self.app.device.device_info
        latest_release = self._get_latest_release()
        if device_info is None or latest_release is None:
            return False
        current_tft = device_info.get("tft_version")
        if current_tft is None:
            return False
        current_version = self._parse_version(current_tft)
        latest_version = self._parse_version(latest_release["tag_name"])
        if current_version < latest_version:
            return True
        return False

    def run_update_display(self) -> None:
        """Runs the update process for the display."""
        latest_release = self._get_latest_release()
        if latest_release is None:
            self.log("No release info available")
            return
        update_url = self._get_update_url(latest_release)
        if update_url is None:
            self.log("No update url available")
            return
        # run update
        self.app.controller["esphome"].esphome.publish(ESPAction.UPLOAD_TFT_URL, update_url)

    def check_installed_version(self) -> None:
        """Checks on connect if a update is available."""
        device_info = self.app.device.device_info
        installed_version = device_info.get("tft_version")
        required_version = device_info.get("yaml_version")
        self.log(
            f"Checking installed version: required={required_version} installed={installed_version}"
        )
        if required_version is None or installed_version is None:
            # notify about unknown versions
            msg = self.translate("Got unknown TFT-Version information.")
        else:
            # check for outdated versions

            v_req = self._parse_version(required_version)
            v_inst = self._parse_version(installed_version)
            if v_req <= v_inst:
                self.log("Installed TFT version is up to date")
                return
            # invalid or unknown version installed
            if self.get("auto_install", True) and v_inst == Version("0.0.0"):
                if self.app.device.connected:
                    self.log(
                        f"Invalid version installed: {installed_version}, auto install display"
                    )
                    self.run_update_display()
                    return
            # notify about outdated tft version
            msg = self.translate("Your TFT-version is outdated.")
        self._stop_timer_delay()  # ensure there is no delay on connect timer
        msg += "\r\n"
        msg += self.translate("Do you want to check for a update?")
        # open notification
        navigation = self.app.controller["navigation"]
        navigation.open_popup(
            "popup_notify",
            icon="mdi:message-question",
            title=self.translate("Outdated TFT-Version"),
            btn_left_color=COLORS["component_active"],
            btn_right_color=COLORS["component_active"],
            btn_right_back_color=COLORS["component_pressed"],
            btn_left=self.translate("Cancel"),
            btn_right=self.translate("Check"),
            close_on_button=False,
            button_callback_fnc=self.callback_version_response,
            notification=msg,
        )

    def check_for_update(self) -> None:
        """Checks if a update is available."""
        self._update_release_infos()
        latest_release = self._get_latest_release()
        if not self._is_update_available() or latest_release is None:
            return
        name = latest_release["name"]
        description = latest_release["body"]
        # notify about new release (or update if autoupdate)
        if self.get("auto_update", False):
            self.run_update_display()
            return
        # open notification
        else:
            device_info = self.app.device.device_info
            navigation = self.app.controller["navigation"]
            msg = name
            msg += "\r\n"
            msg += trim_text(description, 200)
            msg += "\r\n\r\n"
            msg += self.translate("Version:")
            msg += f" {device_info.get('tft_version', '0.0.0')} -> {latest_release['tag_name']}"
            msg += "\r\n\r\n"
            msg += self.translate("Do you want to update?")
            navigation.open_popup(
                "popup_notify",
                icon="mdi:message-question",
                title=self.translate("Update available"),
                btn_left_color=COLORS["component_active"],
                btn_right_color=COLORS["component_active"],
                btn_right_back_color=COLORS["component_pressed"],
                btn_left=self.translate("Cancel"),
                btn_right=self.translate("Update"),
                button_callback_fnc=self.callback_update_response,
                close_on_button=False,
                notification=msg,
            )

    # callback

    def callback_version_response(self, btn_left: bool, btn_right: bool) -> None:
        """Callback method for check update response.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
        """
        self.log("Callback version response")
        navigation = self.app.controller["navigation"]
        if btn_right:
            self.check_for_update()
        navigation.close_panel()

    def callback_update_response(self, btn_left: bool, btn_right: bool) -> None:
        """Callback method for update to new version response.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
        """
        self.log("Callback update response")
        navigation = self.app.controller["navigation"]
        if btn_left:
            navigation.close_panel()
        if btn_right:
            msg = self.translate("Please wait while the update is starting")
            navigation.open_popup(
                "popup_notify",
                icon="mdi:message-cog",
                title=self.translate("Starting Update"),
                notification=msg,
            )
            self.run_update_display()

    def callback_timer(self) -> None:
        """Callback method for timer."""
        self.check_for_update()
        self._restart_timer()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process events.

        Args:
            event (HAUIEvent): Event
        """

        # on connect
        if event.name == ESPEvent.CONNECTED:
            self._stop_timer_delay()
            # schedule delayed update check if configured
            if self.get("check_on_connect", False):
                delay_interval = self.get("on_connect_delay")
                self.log(f"Checking for update on connect in {delay_interval} seconds")
                self._start_timer_delay()

        # device info received (device_version, yaml_version)
        if event.name == ESPResponse.RES_DEVICE_INFO:
            device_info = json.loads(event.value)
            self.app.device.set_device_info(device_info, append=True)

        # device state received (includes yaml_version, tft_version)
        if event.name == ESPResponse.RES_DEVICE_STATE:
            device_state = json.loads(event.value)
            self.app.device.set_device_info(device_state, append=True)


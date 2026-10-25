from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import requests
from packaging.version import InvalidVersion, Version, parse

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPAction, ESPResponse, SysPanelKey
from ..utils.text import trim_text

# TFT update states reported to the editor.  There is no byte-level progress
# signal from the display, so only coarse transitions are exposed:
# idle -> checking -> installing -> done, or error at any point.
UPDATE_STATE_IDLE = "idle"
UPDATE_STATE_CHECKING = "checking"
UPDATE_STATE_INSTALLING = "installing"
UPDATE_STATE_ERROR = "error"
UPDATE_STATE_DONE = "done"


class HAUIUpdateController(HAUIBase):
    """Update Controller

    Keeps the display's TFT file at the version the firmware needs.

    - On every connect (after ``on_connect_delay`` seconds) the installed TFT
      version is compared with the firmware's ``yaml_version``. An older TFT is
      replaced with the TFT of the GitHub release with that version: right away
      when ``auto_install`` is on (the default), otherwise after the user
      confirms on the display.
    - Optionally (``check_on_connect`` or ``update_interval`` > 0) the display
      shows a notice when a newer release exists. It never installs that TFT: it
      has to match the integration and the firmware, so it follows once those are
      updated.
    """

    # hard-coded url for haui releases on github; a page holds every release
    RELEASES_URL = "https://api.github.com/repos/happydasch/nspanel_haui/releases?per_page=100"

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for update controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.debug_log(f"Creating Update Controller with config: {config}")
        self._timer: str | None = None  # timer for update check by interval
        self._timer_delay: str | None = None  # delays the TFT check after a connect
        self._interval = 0  # update check interval
        self._req_fetch = False  # is being used to identify release info request
        self._release_infos: list[dict[str, Any]] = []  # store latest release infos
        # TFT update state for the editor (Panel Doctor / update workflow).
        self._update_state = UPDATE_STATE_IDLE
        self._update_version: str | None = None
        self._update_started_at: datetime.datetime | None = None
        self._update_last_error: str | None = None

    # internal timers for version checks

    def _start_timer(self) -> None:
        if self._timer is not None or self._interval == 0:
            return
        self._timer = self.app.run_every(
            self._timer_callback, f"now+{self._interval}", self._interval
        )

    def _stop_timer(self) -> None:
        self._cancel_timer("_timer")

    def _restart_timer(self) -> None:
        self._stop_timer()
        self._start_timer()

    def _timer_callback(self, kwargs: dict[str, Any]) -> None:
        self.callback_timer()

    def _start_timer_delay(self) -> None:
        self._timer_delay = self.app.run_in(
            self._timer_delay_callback, self.get("on_connect_delay")
        )

    def _stop_timer_delay(self) -> None:
        self._cancel_timer("_timer_delay")

    def _timer_delay_callback(self, kwargs: dict[str, Any]) -> None:
        self._timer_delay = None
        self.check_installed_version()
        if self.get("check_on_connect", False):
            self.check_for_update()

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self._interval = self.get("update_interval")
        self._start_timer()

    def stop_part(self) -> None:
        """Stops the part."""
        self._stop_timer()
        self._stop_timer_delay()

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
        finally:
            self._req_fetch = False
        self._release_infos = json_decoded

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

    def _find_release(self, version: str) -> dict[str, Any] | None:
        """Returns the release whose tag is ``version`` (``v`` prefix ignored)."""
        wanted = self._parse_version(version)
        for release in self._release_infos:
            if self._parse_version(release["tag_name"]) == wanted:
                return release
        return None

    def _get_tft_filename(self) -> str:
        """Resolve the TFT asset filename for this device's display model.

        ``update.tft_filename`` remains an explicit override; when it is left
        at the generic default, the device's ``display_model`` decides which
        release asset to install (EU and US-landscape share the landscape
        TFT, the US portrait model needs the rotated one).
        """
        from ..device_config import tft_filename_for_model
        from ..mapping.const import DEFAULT_CONFIG

        configured = self.get("tft_filename")
        default = DEFAULT_CONFIG["update"].get("tft_filename", "nspanel_haui.tft")
        if configured and configured != default:
            return configured
        return tft_filename_for_model(self.app.device.display_model)

    def _get_update_url(self, release_info: dict[str, Any] | None) -> str | None:
        """Returns the update url to the tft file from given release.

        Args:
            release_info (dict): Release info

        Returns:
            None|str: Update url
        """
        if release_info is None:
            return None
        tft_filename = self._get_tft_filename()
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

    def run_update_display(self, version: str) -> None:
        """Installs the TFT file of the GitHub release ``version`` on the display.

        Args:
            version (str): Release version, the firmware's ``yaml_version``
        """
        self._set_update_state(UPDATE_STATE_CHECKING, version=version)
        try:
            self._update_release_infos()
        except RuntimeError as exc:
            self.log(f"TFT update failed: {exc}", level="ERROR")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=str(exc))
            return
        update_url = self._get_update_url(self._find_release(version))
        if update_url is None:
            msg = f"No GitHub release {version} with {self._get_tft_filename()}; TFT not updated"
            self.log(msg, level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=msg)
            return
        self.log(f"Installing TFT {version} from {update_url}")
        self._set_update_state(UPDATE_STATE_INSTALLING, version=version)
        self.app.controller["esphome"].esphome.publish(ESPAction.UPLOAD_TFT_URL, update_url)

    def install_tft(self, version: str | None = None) -> None:
        """Trigger a TFT install from the editor.

        Installs the TFT of the GitHub release ``version``; when ``version`` is
        omitted the firmware's ``yaml_version`` (the version the firmware needs)
        is installed.  The update runs on the device worker, so this method must
        be called via ``app.async_run_on_worker``.

        Args:
            version (str | None): Release version to install
        """
        if not self.app.device.connected:
            self.log("Cannot install the TFT while the device is disconnected", level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, error="device disconnected")
            return
        if version is None:
            version = (self.app.device.device_info or {}).get("yaml_version")
        if not version:
            self.log(
                "No yaml_version reported by the firmware; cannot install the TFT",
                level="WARNING",
            )
            self._set_update_state(UPDATE_STATE_ERROR, error="no yaml_version reported")
            return
        self.run_update_display(version)

    # update state (for the editor / Panel Doctor)

    def _set_update_state(
        self, state: str, version: str | None = None, error: str | None = None
    ) -> None:
        """Record a transition of the TFT update state.

        The display gives no byte-level progress, so only coarse transitions
        are tracked.  ``idle`` clears the recorded error; ``installing`` stamps
        the start time; other transitions keep the previous timestamp.

        Args:
            state (str): New update state
            version (str | None): Version being installed / requested
            error (str | None): Error message when moving to ``error``
        """
        if version is not None:
            self._update_version = version
        if state == UPDATE_STATE_IDLE:
            self._update_last_error = None
        if state == UPDATE_STATE_INSTALLING:
            self._update_started_at = datetime.datetime.now(tz=datetime.UTC)
        if error is not None:
            self._update_last_error = error
        self._update_state = state
        self.log(f"TFT update state: {state}")

    def get_update_state(self) -> dict[str, Any]:
        """Return the current TFT update state for the device status payload.

        Returns:
            dict: ``state`` (idle/checking/installing/error/done), ``version``,
            ``started_at`` (ISO timestamp or None) and ``last_error``
        """
        return {
            "state": self._update_state,
            "version": self._update_version,
            "started_at": (
                self._update_started_at.isoformat() if self._update_started_at else None
            ),
            "last_error": self._update_last_error,
        }

    def _mark_done_if_installed(self) -> None:
        """Mark the TFT update ``done`` once the display reports the requested version.

        The display gives no byte-level progress; the install is considered
        complete when the firmware reports a ``tft_version`` that is at least
        the requested one (the display re-sends it after rebooting into the new
        TFT).  Called from the periodic version check and from device-state
        events.  Does nothing when no version was requested (auto checks do not
        flip the state).
        """
        if self._update_state not in (UPDATE_STATE_CHECKING, UPDATE_STATE_INSTALLING):
            return
        requested = self._update_version
        installed = (self.app.device.device_info or {}).get("tft_version")
        if (
            requested
            and installed
            and self._parse_version(installed) >= self._parse_version(requested)
        ):
            self._set_update_state(UPDATE_STATE_DONE, version=requested)

    def check_installed_version(self) -> None:
        """Updates the TFT when it is older than the version the firmware needs."""
        if not self.app.device.connected:
            return
        device_info = self.app.device.device_info
        installed_version = device_info.get("tft_version")
        required_version = device_info.get("yaml_version")
        self.log(
            f"Checking installed version: required={required_version} installed={installed_version}"
        )
        if not required_version:
            self.log("The firmware reported no yaml_version; TFT not checked", level="WARNING")
            return
        # no or an invalid TFT version parses as 0.0.0, so it is updated too
        if self._parse_version(required_version) <= self._parse_version(installed_version or ""):
            self.log("Installed TFT version is up to date")
            self._mark_done_if_installed()
            return
        if self.get("auto_install", True):
            self.log(f"TFT {installed_version!r} is older than {required_version}, installing")
            self.run_update_display(required_version)
            return
        msg = self.translate("Your TFT-version is outdated.")
        msg += "\r\n"
        msg += self.translate("Do you want to update?")
        navigation = self.app.controller["navigation"]
        navigation.open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon="mdi:message-question",
            title=self.translate("Outdated TFT-Version"),
            btn_left_color=self.get_color("component_active"),
            btn_right_color=self.get_color("component_active"),
            btn_right_back_color=self.get_color("component_pressed"),
            btn_left=self.translate("Cancel"),
            btn_right=self.translate("Update"),
            close_on_button=False,
            button_callback_fnc=lambda left, right: self.callback_update_response(
                left, right, required_version
            ),
            notification=msg,
        )

    def check_for_update(self) -> None:
        """Shows a notice on the display when a newer release than the TFT exists."""
        self._update_release_infos()
        latest_release = self._get_latest_release()
        if not self._is_update_available() or latest_release is None:
            return
        device_info = self.app.device.device_info
        msg = latest_release["name"]
        msg += "\r\n"
        msg += trim_text(latest_release["body"], 200)
        msg += "\r\n\r\n"
        msg += self.translate("Version:")
        msg += f" {device_info.get('tft_version', '0.0.0')} -> {latest_release['tag_name']}"
        msg += "\r\n\r\n"
        msg += self.translate("Update the integration and the ESPHome firmware to install it.")
        msg += "\r\n\r\n"
        msg += self.translate("Review the upgrade guide before updating.")
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon="mdi:message-alert",
            title=self.translate("Update available"),
            notification=msg,
        )

    # callback

    def on_connection_changed(self, connected: bool) -> None:
        """Schedules the TFT check on connect and cancels it on disconnect.

        Called by the app once the connection handshake is complete, so the
        device info holds ``tft_version`` and ``yaml_version``.

        Args:
            connected (bool): Connection state
        """
        self._stop_timer_delay()
        if connected:
            self.log(f"Checking the TFT version in {self.get('on_connect_delay')} seconds")
            self._start_timer_delay()
        else:
            # An install in progress cannot report back while disconnected.
            if self._update_state not in (UPDATE_STATE_IDLE, UPDATE_STATE_DONE):
                self._set_update_state(UPDATE_STATE_IDLE)

    def callback_update_response(self, btn_left: bool, btn_right: bool, version: str) -> None:
        """Callback for the outdated-TFT prompt: installs ``version`` on confirm.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
            version (str): TFT version to install
        """
        self.log("Callback update response")
        navigation = self.app.controller["navigation"]
        if btn_left:
            navigation.close_panel()
        if btn_right:
            msg = self.translate("Please wait while the update is starting")
            navigation.open_panel(
                SysPanelKey.POPUP_NOTIFY,
                icon="mdi:message-cog",
                title=self.translate("Starting Update"),
                notification=msg,
            )
            self.run_update_display(version)

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

        # device info received (device_version, yaml_version)
        if event.name == ESPResponse.RES_DEVICE_INFO:
            device_info = event.as_json()
            self.app.device.set_device_info(device_info, append=True)

        # device state received (includes yaml_version, tft_version)
        if event.name == ESPResponse.RES_DEVICE_STATE:
            device_state = event.as_json()
            self.app.device.set_device_info(device_state, append=True)
            self._mark_done_if_installed()

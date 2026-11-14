from __future__ import annotations

import copy
import datetime
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypedDict

from packaging.version import Version, parse

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI
    from .notification import Notification

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import (
    DEFAULT_CONFIG,
    ESPAction,
    ESPRequest,
    ESPResponse,
    PopupPanelKey,
)
from ..utils.text import strip_markdown, trim_text
from . import release_source
from .release_source import (
    FirmwareInstallRequest,
    FirmwareManifestInfo,
    UpdateFetchInputs,
    UpdateFetchRequest,
)

# The update model mirrors Home Assistant's own version comparison
# (``AwesomeVersion``, see ``homeassistant.components.update.entity``) so the
# hub's decision and the HAUI update entities can never disagree.  ``awesomeversion``
# ships with Home Assistant; the packaging fallback only covers a bare
# environment without it (production and CI always take the AwesomeVersion
# branch, because requirements-dev.txt pins homeassistant, which depends on it).
try:
    from awesomeversion import AwesomeVersion, AwesomeVersionCompareException
except ImportError:  # pragma: no cover - Home Assistant always ships awesomeversion
    AwesomeVersion = None  # type: ignore[assignment,misc]
    AwesomeVersionCompareException = Exception  # type: ignore[assignment,misc]


def _version_is_newer_cmp(latest: str, installed: str) -> bool:
    """Whether ``latest`` is strictly newer than ``installed`` (HA semantics).

    Raises:
        AwesomeVersionCompareException: When the versions cannot be compared
    """
    if AwesomeVersion is None:  # pragma: no cover - packaging fallback
        return parse(latest) > parse(installed)
    return bool(AwesomeVersion(latest) > installed)


# TFT update states reported to the editor.  There is no byte-level progress
# signal from the display, so only coarse transitions are exposed:
# idle -> checking -> installing -> done, or error at any point.
UPDATE_STATE_IDLE = "idle"
UPDATE_STATE_CHECKING = "checking"
UPDATE_STATE_INSTALLING = "installing"
UPDATE_STATE_ERROR = "error"
UPDATE_STATE_DONE = "done"

# Fired on every TFT version or update state change; the "HAUI Display" update
# entity (``update.py``) renders it.
DISPLAY_UPDATE_EVENT = "nspanel_haui.display_update_changed"

# TFT install timing.  The portrait upload takes ~13 minutes, so the install
# timeout must be generous; the verification window on reconnect (the upload
# reboots the device) only re-reads the state a few times before failing.
INSTALL_TIMEOUT_SECONDS = 20 * 60
DEVICE_STATE_REFRESH_SECONDS = 15
VERIFY_REFRESH_SECONDS = 60
VERIFY_MAX_REFRESHES = 2

# Firmware update.  The hub reads the firmware manifest at the device's
# ``firmware_manifest_url`` (by default the one of the ``firmware_update_channel``:
# the latest stable GitHub release, or the newest dev prerelease) and, when it
# names a newer version, flashes its image with the firmware's
# ``install_firmware_url`` action; the display TFT the new firmware's manifest
# ships follows after the reboot.  A failed automatic install is retried after
# the policy's ``retry_interval``, at most ``max_attempts`` times per version
# (``_AutoAttempt``).
# The device downloads and flashes the image, then reboots.  An install that
# has not ended in a reconnect after this long failed without a reboot.
FIRMWARE_INSTALL_TIMEOUT_SECONDS = 10 * 60
# Fired on every firmware version or install state change; the "HAUI Firmware"
# update entity (``update.py``) renders it.
FIRMWARE_UPDATE_EVENT = "nspanel_haui.firmware_update_changed"
# How far the editor may put off a scheduled automatic firmware install.
DEFER_SECONDS = (3600, 86400)
# What an install usually takes, for the editor's time estimate: the device
# reports no byte progress (the transfer blocks its main loop), only steps.
FIRMWARE_EXPECTED_SECONDS = 3 * 60
TFT_EXPECTED_SECONDS = 15 * 60


class _AutoAttempt(TypedDict):
    """The automatic install attempts of one kind (``firmware``, ``tft``) for one version."""

    version: str | None
    attempts: int
    last_at: datetime.datetime | None
    failed: bool


class _Progress(TypedDict):
    """The step an install is at: ``scheduled``, ``starting``, ``transferring``,
    ``verifying``, ``done`` or ``failed``."""

    phase: str
    phase_started_at: str
    started_at: str | None
    expected_seconds: int


class _AutoSnapshot(TypedDict):
    attempts: int
    max_attempts: int
    next_attempt_at: str | None
    stopped_reason: str | None


class _DisplayUpdateSnapshot(TypedDict):
    installed_version: str | None
    latest_version: str | None
    available: bool
    state: str
    version: str | None
    started_at: str | None
    last_error: str | None
    update_reason: str | None
    auto: _AutoSnapshot
    progress: _Progress | None


class _FirmwareUpdateSnapshot(TypedDict):
    installed_version: str | None
    latest_version: str | None
    available: bool
    reason: str | None
    installing: bool
    last_error: str | None
    auto: _AutoSnapshot
    scheduled: dict[str, str] | None
    skipped_version: str | None
    progress: _Progress | None


class UpdateSnapshot(TypedDict):
    """Canonical update state shared by the API and Home Assistant entities."""

    device: str
    connected: bool
    enabled: bool
    display: _DisplayUpdateSnapshot
    firmware: _FirmwareUpdateSnapshot


# check_error of a check a newer one replaced before it finished
CHECK_SUPERSEDED = "check superseded"


def _with_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """The update settings ``config`` gives, the rest at their declared default."""
    return {**copy.deepcopy(DEFAULT_CONFIG["update"]), **config}


class HAUIUpdateController(HAUIBase):
    """Update Controller

    Keeps the display's TFT file at the version the firmware's manifest ships
    (``manifest.tft``; a manifest without a ``tft`` block — a local test
    release names none — needs no display update), and offers/installs the firmware the
    manifest at ``firmware_manifest_url`` names.

    - On every connect (after ``on_connect_delay`` seconds) the installed TFT
      version is compared with the TFT the firmware's manifest ships. An older
      TFT is replaced right away when ``auto_install`` is on (the default),
      otherwise after the user confirms on the display.
    - Optionally (``check_on_connect`` or ``update_interval`` > 0) the display
      shows a notice when a newer GitHub release exists; the TFT installs only
      via the firmware's manifest, so the notice keeps pointing at the
      integration/firmware update that ships the matching TFT.

    Network I/O never runs on the device worker: every check and install
    fetches its inputs with ``release_source`` on the adapter's I/O pool
    (``start_async_*``) and applies the result back on the worker.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for update controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller; a setting it leaves out takes
                its ``DEFAULT_CONFIG["update"]`` default
        """
        super().__init__(app, _with_defaults(config))
        self.log(f"Creating Update Controller with config: {config}", level="DEBUG")
        self._timer: str | None = None  # timer for update check by interval
        self._timer_delay: str | None = None  # delays the TFT check after a connect
        self._interval = 0  # update check interval
        self._release_infos: list[dict[str, Any]] = []  # store latest release infos
        # TFT update state for the editor (Panel Doctor / update workflow).
        self._update_state = UPDATE_STATE_IDLE
        self._update_version: str | None = None
        self._update_started_at: datetime.datetime | None = None
        self._update_last_error: str | None = None
        # #63: the handshake reads ``tft_version`` ~1s after boot, before the
        # display reported it.  The bookkeeping below re-reads device state on
        # demand and treats an unknown version / unconfirmed install as "not
        # outdated", so an empty snapshot is never mistaken for an outdated TFT
        # (which reinstalled the TFT after every reboot).
        self._pending_state_check = False
        self._state_check_timer: str | None = None
        self._install_verify_timer: str | None = None
        self._install_verify_refreshes = 0
        self._install_timeout_timer: str | None = None
        self._last_install_version: str | None = None
        self._last_install_at: datetime.datetime | None = None
        self._last_install_confirmed = False
        # yaml_version for which a TFT installed by hand (another release or a
        # URL) is kept.  The automatic check would otherwise replace an older
        # TFT right after the reboot that ends its own install.  In memory
        # only: a Home Assistant restart or a new firmware version lifts it.
        self._manual_tft_firmware: str | None = None
        # Release notices are advisory and shown at most once per selected
        # release for this controller/channel.
        self._last_notified_release: str | None = None
        # The manifest read last (``version``, ``url``, ``md5``) and the URL it
        # was read from; None when the read failed, with the reason in
        # ``_firmware_manifest_error``.
        self._firmware_manifest: FirmwareManifestInfo | None = None
        self._firmware_manifest_url: str | None = None
        self._firmware_manifest_error: str | None = None
        self._tft_manifest: FirmwareManifestInfo | None = None
        self._tft_manifest_url: str | None = None
        self._tft_manifest_error: str | None = None
        # Firmware install bookkeeping.  The install runs on the device and
        # ends in a reboot, so a reconnect means the attempt finished — either
        # way.  While it is in flight the TFT install waits, because the reboot
        # would abort an upload.
        self._firmware_installing = False
        self._firmware_install_version: str | None = None
        self._firmware_install_at: datetime.datetime | None = None
        self._firmware_install_error: str | None = None
        self._firmware_install_timer: str | None = None
        # the queued "installing" notice, removed when the install ends
        self._firmware_install_notice: Notification | None = None
        # A firmware installed by hand (another release or a URL) pauses the
        # automatic firmware update, which would otherwise reinstall the latest
        # release on the next check.  In memory only: a Home Assistant restart
        # or installing the offered update ends it.
        self._manual_firmware = False
        # Automatic install attempts per kind; reset by a success, a manual
        # install, a newer version or a Home Assistant restart (in memory).
        self._auto_attempts: dict[str, _AutoAttempt] = {}
        # An automatic firmware install waiting out ``install_delay``:
        # ``{"version", "starts_at"}``; the editor can start it now or defer it.
        self._scheduled: dict[str, Any] | None = None
        self._scheduled_timer: str | None = None
        # Set while a hub rollout (``hub/rollout.py``) owns this device's installs.
        self._rollout_hold = False
        # How the last firmware install ended: None while none ended since it
        # started (or the next check), True for success, False for a failure.
        self._firmware_install_ok: bool | None = None
        # The step each kind is at, and since when (``_progress``).
        self._phase_since: dict[str, tuple[str, datetime.datetime]] = {}
        self._async_check_id = 0
        self._async_catalog_id = 0
        self._async_install_id = 0
        self._lifecycle_generation = 0

    # internal timers for version checks
    def _updates_enabled(self) -> bool:
        """Whether this device permits update checks and installs."""
        return bool(self.get("enabled"))

    def _start_timer(self) -> None:
        if not self._updates_enabled() or self._timer is not None or self._interval == 0:
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
        if not self._updates_enabled():
            return
        self.start_async_check(
            allow_auto_install=self.get("check_on_connect"),
            include_notice=self.get("check_on_connect"),
            check_tft=True,
        )

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self._interval = self.get("update_interval")
        self._start_timer()
        if self._updates_enabled():
            self.start_async_check(allow_auto_install=False, include_notice=False)
        else:
            self.publish_display_update()
            self.publish_firmware_update()

    def reload_options(self, config: dict[str, Any]) -> None:
        """Apply updated options without interrupting an active installation.

        Config saves reload the app's settings while an OTA or TFT upload may
        still be running. Checks are reconfigured, while active installs and
        their verification timers remain owned by the in-flight operation.
        """
        previous_channel = self.get("firmware_update_channel")
        self.config = _with_defaults(config)
        if previous_channel != self.get("firmware_update_channel"):
            self._last_notified_release = None
        self._interval = self.get("update_interval")
        if self._scheduled and self._scheduled["version"] == self.get("skipped_firmware_version"):
            self._drop_schedule()
        if not self._updates_enabled():
            self._drop_schedule()
            self._stop_timer()
            self._stop_timer_delay()
            self._async_check_id += 1
            self._cancel_timer("_state_check_timer")
            self._pending_state_check = False
            self._async_catalog_id += 1
            self._async_install_id += 1
            self.publish_display_update()
            self.publish_firmware_update()
            return
        self._restart_timer()
        self.start_async_check(allow_auto_install=False, include_notice=False)

    def stop_part(self) -> None:
        """Stops the part."""
        self._lifecycle_generation += 1
        self._async_check_id += 1
        self._async_catalog_id += 1
        self._async_install_id += 1
        self._stop_timer()
        self._stop_timer_delay()
        self._cancel_timer("_state_check_timer")
        self._pending_state_check = False
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")
        self._cancel_timer("_firmware_install_timer")
        self._drop_schedule()
        self._firmware_installing = False

    # update

    def _try_parse_version(self, version: str | None) -> Version | None:
        """Strictly parse ``version``, returning None for empty/invalid values.

        An empty ``tft_version`` (the display reports it only after boot) is
        *unknown*, not ``0.0.0`` — treating it as an old version is exactly
        what reinstalled the TFT after every reboot.
        """
        return release_source.parse_version(version)

    def _version_is_newer(self, latest: str | None, installed: str | None) -> bool | None:
        """Whether ``latest`` is strictly newer than ``installed``.

        Uses the same comparison Home Assistant applies to update entities
        (``AwesomeVersion``), so the hub never offers — or auto-installs —
        a firmware Home Assistant itself would consider older.  Returns None
        when either side does not parse as a version, or AwesomeVersion cannot
        compare them: an *unknown* version is never a reason to install.  A
        final release is newer than its dev builds (``0.4.5`` over
        ``0.4.5.dev3``).  AwesomeVersion sorts a ``+local`` build
        (``0.4.5.dev3+g<sha>``, published before dev versions dropped the
        segment) above the final release and later plain dev builds, and the
        hub mirrors that rather than disagree with the entity.
        """
        if latest is None or installed is None:
            return None
        if self._try_parse_version(latest) is None or self._try_parse_version(installed) is None:
            return None
        try:
            return _version_is_newer_cmp(latest, installed)
        except AwesomeVersionCompareException:
            # Home Assistant falls back to "update available" here; the hub
            # treats an incomparable version as unknown instead (see above).
            return None

    def _get_latest_release(self) -> dict[str, Any] | None:
        """Return the newest fetched release of the configured channel."""
        channel = str(self.get("firmware_update_channel"))
        return release_source.latest_release(self._release_infos, channel)

    def _is_update_available(self) -> bool:
        """Returns if a update is available.

        Compares the installed firmware (``yaml_version``) with the newest
        GitHub release; both must parse, and the comparison follows Home
        Assistant's own semantics (see ``_version_is_newer``).  The release is
        a firmware release, so the display TFT (``tft_version``) never
        participates: an up-to-date display must not hide a firmware update,
        nor a stale display invent one.

        Returns:
            bool: True if an update is available, False if not
        """
        device_info = self.app.device.device_info
        latest_release = self._get_latest_release()
        if device_info is None or latest_release is None:
            return False
        return (
            self._version_is_newer(latest_release.get("tag_name"), device_info.get("yaml_version"))
            is True
        )

    # firmware update

    def _same_version(self, first: str | None, second: str | None) -> bool:
        """Whether two version strings name the same version (``v`` prefix ignored)."""
        return release_source.same_version(first, second)

    def _required_tft_version(self, device_info: dict[str, Any]) -> str | None:
        """Return the TFT version explicitly declared by the firmware."""
        version = device_info.get("tft_required_version")
        return version if isinstance(version, str) and version else None

    def _get_tft_manifest(self) -> FirmwareManifestInfo | None:
        """Return the manifest chosen for this firmware's required TFT."""
        return self._tft_manifest or self._firmware_manifest

    def _tft_update_reason(self) -> str | None:
        """Explain why the manifest cannot provide the firmware-required TFT."""
        device_info = self.app.device.device_info or {}
        required = self._required_tft_version(device_info)
        if required is None:
            return None
        manifest = self._get_tft_manifest()
        if manifest is None:
            return self._tft_manifest_error or self._firmware_manifest_error
        manifest_tft = manifest.get("tft_version") or None
        if self._same_version(required, manifest_tft):
            if manifest.get("tft_url"):
                return None
            return self._tft_manifest_error or self.translate("No TFT asset for this display")
        shown_manifest = manifest_tft or self.translate("none")
        return (
            self.translate("TFT required by firmware: {required}; manifest provides: {manifest}.")
            .replace("{required}", required)
            .replace("{manifest}", shown_manifest)
        )

    def _firmware_variant_compatible(self, manifest_variant: str | None) -> bool:
        """Whether the manifest's firmware may be installed on this panel.

        Both sides must report the same known variant.  A device whose
        firmware does not report its variant (pre-0.4.4 builds) and a
        manifest without a ``variant`` both fail closed: flashing the
        universal release image onto a custom build — whose OTA and API
        credentials differ from the public universal ones — must never
        happen, not even when the user only gets the upgrade *offered*.
        """
        device_variant = (self.app.device.device_info or {}).get("firmware_variant")
        return (
            bool(device_variant) and bool(manifest_variant) and (device_variant == manifest_variant)
        )

    def _firmware_variant_mismatch_reason(self) -> str | None:
        """Explain why the manifest's firmware is not offered on this panel.

        Returns:
            str | None: A user-facing reason, or None when the manifest is
            compatible (or there is no manifest to judge).
        """
        if self._firmware_manifest is None:
            return None
        manifest_variant = self._firmware_manifest.get("variant")
        if self._firmware_variant_compatible(manifest_variant):
            return None
        device_variant = (self.app.device.device_info or {}).get("firmware_variant")
        if not device_variant:
            return (
                "The panel's firmware does not report its build variant; flash the "
                "offered release once manually (ESPHome or Install firmware → From URL) "
                "and the hub can update it afterwards"
            )
        if not manifest_variant:
            return (
                "The firmware manifest names no build variant; point "
                "firmware_manifest_url at the manifest of a recent release"
            )
        return (
            f"The firmware manifest offers the {manifest_variant!r} build but this "
            f"panel runs the {device_variant!r} one; they are not interchangeable"
        )

    def _invalid_installed_reason(self) -> str | None:
        """Explain an unparseable ``yaml_version`` reported by the panel.

        Home Assistant's update entity falls back to "update available" when it
        cannot compare two versions, so an invalid installed version would make
        it offer the manifest's firmware on every check.  The hub withholds the
        offer instead and reports the installed version as unknown.

        Returns:
            str | None: A user-facing reason, or None when the version parses
        """
        installed = (self.app.device.device_info or {}).get("yaml_version")
        if self._try_parse_version(installed) is not None:
            return None
        if not installed:
            return "The panel has not reported its firmware version yet"
        return (
            f"The panel reports an invalid firmware version {installed!r}; "
            "Home Assistant cannot compare it (it would offer an update on every "
            "check), so the hub withholds the offer. Reinstall the firmware with a "
            "parseable version (a release or a next-patch X.Y.(Z+1).devN build)"
        )

    def _firmware_update_reason(self) -> str | None:
        """Explain why the manifest's firmware is not offered on this panel.

        Returns:
            str | None: A user-facing reason, or None when the manifest offers
            this panel an update (or there is no manifest to judge).
        """
        if self._firmware_manifest is None:
            return None
        return self._firmware_variant_mismatch_reason() or self._invalid_installed_reason()

    def _firmware_update_available(self) -> bool:
        """True when the manifest offers a newer firmware for *this* panel.

        A newer version alone is not enough: the manifest's build variant must
        match the one the device reports (and the installed version must parse),
        or the update is withheld entirely.  The comparison follows Home
        Assistant's own semantics (``_version_is_newer``), so the hub never
        offers a firmware the HAUI Firmware entity would not offer either.
        """
        installed = (self.app.device.device_info or {}).get("yaml_version")
        return self._version_is_newer(self._firmware_update_version(), installed) is True

    def _firmware_update_version(self) -> str | None:
        """Return the firmware version the manifest offers this panel.

        None when there is no manifest, its build variant does not match the
        panel's, the installed version does not parse, or the manifest's own
        version does not parse: a custom build must never be shown the
        universal release as an update, and an unparseable version must not
        reach Home Assistant's comparison (which would offer the update on
        every check — the HAUI Firmware entity reports no compatible release
        then).
        """
        if self._firmware_manifest is None or self._firmware_update_reason() is not None:
            return None
        version = self._firmware_manifest["version"]
        if self._try_parse_version(version) is None:
            # An unparsable manifest version must not surface as ``latest``:
            # Home Assistant falls back to "update available" when it cannot
            # compare two versions, so an incomparable latest would read as an
            # update on every check.
            return None
        return version

    def _firmware_install_due(self) -> bool:
        """Whether an automatic firmware install should be started now.

        Returns:
            bool: True when ``firmware_auto_update`` is on, no firmware was
            installed by hand, no install or TFT upload is in flight, the
            retry policy allows another attempt (``_auto_attempt_allowed``)
            and the manifest offers a newer firmware.
        """
        if not self._updates_enabled() or not self.get("firmware_auto_update"):
            return False
        if not self.app.device.connected:
            return False
        if self._manual_firmware:
            return False
        if self._update_state == UPDATE_STATE_INSTALLING:
            return False  # never reboot the device mid TFT upload
        if self._firmware_installing:
            return False
        if self._rollout_hold:
            return False
        version = self._firmware_update_version()
        if version and version == self.get("skipped_firmware_version"):
            return False
        if not self._auto_attempt_allowed("firmware", version):
            return False
        return self._firmware_update_available()

    def _start_firmware_install(
        self, url: str, md5: str, label: str, manual: bool
    ) -> dict[str, Any]:
        """Flash the image at ``url`` with the firmware's ``install_firmware_url`` action.

        Args:
            url (str): http(s) URL of the OTA app image
            md5 (str): md5 of the image
            label (str): Version (or URL) shown and logged for the install
            manual (bool): Whether the install pauses the automatic update

        Returns:
            dict: The update state, see ``get_update_state``
        """
        if not self._updates_enabled():
            self._firmware_install_error = "Updates are disabled for this device"
            self.publish_firmware_update()
            return self.get_update_state()
        if self._update_state == UPDATE_STATE_INSTALLING:
            # A TFT upload can start while the firmware is fetched; the
            # firmware install would reboot the device in the middle of it.
            self._firmware_install_error = "Cannot install firmware during a TFT upload"
            self.log(self._firmware_install_error, level="WARNING")
            self.publish_firmware_update()
            return self.get_update_state()
        self._firmware_install_ok = None
        if manual:
            self._auto_attempts.pop("firmware", None)
            self._drop_schedule()
        else:
            self._record_auto_attempt("firmware", label)
        published = self.app.controller["esphome"].esphome.publish(
            ESPAction.INSTALL_FIRMWARE_URL, {"url": url, "md5sum": md5}
        )
        if not published:
            self._firmware_install_ok = False
            self._record_auto_result("firmware", False)
            self._firmware_install_error = (
                "Could not send the firmware install command; the panel's firmware needs "
                "the install_firmware_url action (0.4.3 and later), so flash the latest "
                "firmware first"
            )
            self.log(self._firmware_install_error, level="ERROR")
            return self.get_update_state()
        self._firmware_installing = True
        self._firmware_install_version = label
        self._firmware_install_at = datetime.datetime.now(tz=datetime.UTC)
        self._firmware_install_error = None
        self._manual_firmware = manual
        self._cancel_timer("_firmware_install_timer")
        self._firmware_install_timer = self.app.run_in(
            self._firmware_install_timer_callback, FIRMWARE_INSTALL_TIMEOUT_SECONDS
        )
        self.log(f"Firmware install of {label} started")
        self._notify_firmware_install(label)
        self.publish_firmware_update()
        return self.get_update_state()

    # the waiting period of an automatic firmware install

    def _schedule_firmware_install(self) -> None:
        """Start the due automatic firmware install after the policy's ``install_delay``.

        A version already scheduled keeps its start time (a later check does not
        push it back); ``install_delay`` 0 starts the install right away.
        """
        manifest = self._firmware_manifest
        if manifest is None:
            return
        delay = int(self.get("install_delay"))
        if delay <= 0:
            self._start_firmware_install(
                manifest["url"], manifest["md5"], manifest["version"], manual=False
            )
            return
        if self._scheduled is not None and self._scheduled["version"] == manifest["version"]:
            return
        self._arm_schedule(manifest["version"], delay)
        self.log(f"Firmware {manifest['version']} installs automatically in {delay} seconds")

    def _arm_schedule(self, version: str, delay: int) -> None:
        self._cancel_timer("_scheduled_timer")
        self._scheduled = {
            "version": version,
            "starts_at": datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=delay),
        }
        self._scheduled_timer = self.app.run_in(self._scheduled_timer_callback, delay)
        self.publish_firmware_update()

    def _drop_schedule(self) -> None:
        """Forget the scheduled automatic install, if any."""
        self._cancel_timer("_scheduled_timer")
        if self._scheduled is not None:
            self._scheduled = None
            self.publish_firmware_update()

    def _scheduled_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._scheduled_timer = None
        self._start_scheduled_install()

    def _start_scheduled_install(self) -> None:
        """Start the scheduled install if every guard still allows it."""
        scheduled = self._scheduled
        self._drop_schedule()
        manifest = self._firmware_manifest
        if scheduled is None or manifest is None or manifest["version"] != scheduled["version"]:
            return
        if not self._firmware_install_due():
            self.log(f"Scheduled firmware install of {scheduled['version']} is no longer due")
            return
        self._start_firmware_install(
            manifest["url"], manifest["md5"], manifest["version"], manual=False
        )

    def control_scheduled(self, action: str, seconds: int | None = None) -> dict[str, Any]:
        """Act on the scheduled automatic firmware install from the editor.

        Args:
            action: ``install_now`` starts it now; ``defer`` moves its start.
            seconds: For ``defer``: 3600 or 86400.

        Returns:
            dict: The update state, see ``get_update_state``

        Raises:
            ValueError: No install is scheduled, an unknown action, or another
                defer duration.
        """
        if self._scheduled is None:
            raise ValueError("No automatic firmware install is scheduled")
        if action == "install_now":
            self._start_scheduled_install()
        elif action == "defer":
            if seconds not in DEFER_SECONDS:
                raise ValueError(f"Defer by one of {DEFER_SECONDS} seconds, not {seconds!r}")
            self._arm_schedule(self._scheduled["version"], seconds)
            self.log(f"Firmware {self._scheduled['version']} install deferred by {seconds} seconds")
        else:
            raise ValueError(f"Unknown update control action {action!r}")
        return self.get_update_state()

    def set_rollout_hold(self, hold: bool) -> None:
        """Hold automatic firmware installs while a hub rollout owns this device.

        A hold drops the scheduled install and schedules none until released.
        """
        self._rollout_hold = hold
        if hold:
            self._drop_schedule()

    def _firmware_install_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._firmware_install_timer = None
        if not self._firmware_installing:
            return
        self._firmware_installing = False
        self._drop_firmware_install_notice()
        self._firmware_install_error = (
            f"Firmware install of {self._firmware_install_version} did not finish: the panel "
            "did not reboot. See the device's ESPHome log for the download or flash error."
        )
        self.log(self._firmware_install_error, level="ERROR")
        self._firmware_install_ok = False
        self._record_auto_result("firmware", False)
        self.publish_firmware_update()

    def _finish_firmware_install(self) -> None:
        """Check the firmware version the device reconnected with after an install.

        A reconnect without a reboot means the install failed (``_rebooted_since``).
        A release install names its version; when the device still reports
        another ``yaml_version``, the image was not flashed.  A URL install
        names no version and is taken as finished once the device rebooted.
        """
        self._firmware_installing = False
        self._cancel_timer("_firmware_install_timer")
        self._drop_firmware_install_notice()
        label = self._firmware_install_version
        if not self._rebooted_since(self._firmware_install_at):
            self._firmware_install_error = (
                f"Firmware install of {label} failed: the panel did not reboot. See the "
                "device's ESPHome log for the download or flash error."
            )
            self.log(self._firmware_install_error, level="ERROR")
            self._firmware_install_ok = False
            self._record_auto_result("firmware", False)
            return
        installed = (self.app.device.device_info or {}).get("yaml_version")
        if self._try_parse_version(label) is not None and not self._same_version(label, installed):
            self._firmware_install_error = (
                f"Firmware install of {label} failed: the panel still runs {installed}"
            )
            self.log(self._firmware_install_error, level="ERROR")
            self._firmware_install_ok = False
            self._record_auto_result("firmware", False)
            return
        self._firmware_install_ok = True
        self._record_auto_result("firmware", True)
        self.log(f"Device reconnected after installing firmware {label}")

    def _notify_firmware_install(self, version: str | None) -> None:
        """Tell the user on the display that a firmware update is installing.

        The notice is a queued notification, so it never replaces one the user
        is reading; it leaves the queue when the install ends.
        """
        msg = self.translate(
            "A new firmware release is installing. The display updates after the device reboots."
        )
        msg += "\r\n\r\n"
        msg += self.translate("Version:")
        msg += f" {version}"
        self._drop_firmware_install_notice()
        self._firmware_install_notice = self.app.controller["notification"].add_notification(
            self.translate("Update"),
            msg,
            icon="mdi:package-down",
            force_show=True,
            sound="",
        )

    def _drop_firmware_install_notice(self) -> None:
        """Remove the install notice from the queue once the install ended."""
        if self._firmware_install_notice is not None:
            self.app.controller["notification"].remove_notification(self._firmware_install_notice)
            self._firmware_install_notice = None

    def publish_firmware_update(self) -> None:
        """Fire the firmware versions and install state for the "HAUI Firmware" entity."""
        snapshot = self.get_update_snapshot()
        self.app.fire_event(
            FIRMWARE_UPDATE_EVENT,
            {
                "device": snapshot["device"],
                "connected": snapshot["connected"],
                "enabled": snapshot["enabled"],
                "installed_version": snapshot["firmware"]["installed_version"],
                "latest_version": snapshot["firmware"]["latest_version"],
                "installing": snapshot["firmware"]["installing"],
                "reason": snapshot["firmware"]["reason"],
                "last_error": snapshot["firmware"]["last_error"],
            },
        )

    def run_update_display(self, version: str) -> dict[str, Any]:
        """Installs the TFT file the firmware manifest ships for this display model.

        The manifest is the single TFT source: the release workflow names the
        display TFT of the release in its ``tft`` block, and the asset for the
        device's ``display_model`` is resolved against the manifest URL.  A
        manifest without a ``tft`` block (a local test release names none)
        installs nothing; the TFT then comes from a URL (``install_tft_url``).
        Uses the manifest the last check loaded (``start_async_check``).

        Args:
            version (str): TFT version required by the firmware's ``tft_version``
            substitution; it must equal the version the manifest's TFT block names

        Returns:
            dict: The update state after the attempt (``get_update_state()``);
            the caller can check ``state == UPDATE_STATE_ERROR`` and read
            ``last_error`` to report the outcome to the user.
        """
        if not self._updates_enabled():
            self._set_update_state(
                UPDATE_STATE_ERROR,
                version=version,
                error="Updates are disabled for this device",
            )
            return self.get_update_state()
        self._set_update_state(UPDATE_STATE_CHECKING, version=version)
        manifest = self._get_tft_manifest()
        tft_version = manifest.get("tft_version") if manifest is not None else None
        tft_url = manifest.get("tft_url") if manifest is not None else None
        if manifest is None or not tft_url or self._try_parse_version(tft_version) is None:
            msg = (
                f"The firmware manifest at {self._tft_manifest_url or self._firmware_manifest_url} "
                f"ships no TFT for version {version}. "
                "Install the TFT from a URL instead"
                if manifest is not None
                else str(
                    self._tft_manifest_error
                    or self._firmware_manifest_error
                    or self.translate("Firmware manifest unavailable")
                )
            )
            self.log(msg, level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=msg)
            return self.get_update_state()
        if not self._same_version(version, tft_version):
            msg = (
                f"The firmware manifest ships the {tft_version} TFT, not one for "
                f"{version}; the display TFT follows the manifest. Install the TFT "
                "from a URL to use another version"
            )
            self.log(msg, level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=msg)
            return self.get_update_state()
        self.log(f"Installing TFT {version} from {tft_url}")
        return self._start_tft_upload(tft_url, version)

    def _start_tft_upload(self, url: str, version: str | None) -> dict[str, Any]:
        """Send the TFT at ``url`` to the device and track the install.

        Args:
            url (str): TFT file the device downloads and flashes
            version (str | None): Expected TFT version; None for a URL install

        Returns:
            dict: The update state after the attempt (``get_update_state()``)
        """
        if not self._updates_enabled():
            self._set_update_state(
                UPDATE_STATE_ERROR, version=version, error="Updates are disabled for this device"
            )
            return self.get_update_state()
        if self._firmware_installing:
            # A firmware install can start while the TFT is resolved; its
            # reboot would cut the upload off.
            self._set_update_state(
                UPDATE_STATE_ERROR,
                version=version,
                error=self.translate("Cannot install TFT during a firmware update"),
            )
            return self.get_update_state()
        published = self.app.controller["esphome"].esphome.publish(ESPAction.UPLOAD_TFT_URL, url)
        if not published:
            msg = "Could not send the TFT upload command; check the ESPHome connection"
            self.log(msg, level="ERROR")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=msg)
            self._cancel_timer("_install_timeout_timer")
            return self.get_update_state()
        # Record the attempt so the confirm check treats the install as
        # in-flight: an upload that reboots the device reads back an empty
        # tft_version, and that must not be mistaken for "outdated" (which
        # used to reinstall the TFT after every reboot).
        self._last_install_version = version
        self._last_install_at = datetime.datetime.now(tz=datetime.UTC)
        self._last_install_confirmed = False
        self._set_update_state(UPDATE_STATE_INSTALLING, version=version)
        self._start_install_timeout_timer()
        return self.get_update_state()

    def install_tft(self, version: str | None = None) -> dict[str, Any]:
        """Trigger a TFT install from the editor.

        Installs the TFT the firmware manifest ships (the release's ``tft``
        block for this device's display model); when ``version`` is omitted the
        manifest's TFT version — the one the firmware needs — is installed.
        A manifest without a ``tft`` block (a local test release names none)
        installs nothing; install the TFT from a URL for those.  Uses the
        manifest the last check loaded; ``start_async_tft_install`` loads it
        first.

        Args:
            version (str | None): Manifest TFT version to install

        Returns:
            dict: The update state after the attempt; ``state`` is
            ``UPDATE_STATE_ERROR`` when the install could not start (see
            ``last_error``).
        """
        if not self._updates_enabled():
            self._set_update_state(
                UPDATE_STATE_ERROR, version=version, error="Updates are disabled for this device"
            )
            return self.get_update_state()
        if not self.app.device.connected:
            self.log("Cannot install the TFT while the device is disconnected", level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, error="device disconnected")
            return self.get_update_state()
        device_info = self.app.device.device_info or {}
        firmware_version = device_info.get("yaml_version")
        required = self._required_tft_version(device_info)
        if version is None:
            version = required
        if not version:
            self.log(
                "No TFT version requirement reported by the firmware; cannot install the TFT",
                level="WARNING",
            )
            self._set_update_state(UPDATE_STATE_ERROR, error="no TFT version requirement reported")
            return self.get_update_state()
        # A manual retry starts a fresh attempt: it must not be blocked by the
        # "install not confirmed" guard left over from a previous attempt, and
        # it gives the automatic install its attempts back.
        self._last_install_confirmed = False
        self._last_install_at = None
        self._auto_attempts.pop("tft", None)
        result = self.run_update_display(version)
        if result["state"] == UPDATE_STATE_INSTALLING:
            matches = self._same_version(version, required)
            self._manual_tft_firmware = None if matches else firmware_version
        return result

    def start_async_tft_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Resolve the TFT manifest off-worker before starting the display upload."""
        if not self._updates_enabled():
            self._set_update_state(
                UPDATE_STATE_ERROR,
                version=version,
                error="Updates are disabled for this device",
            )
            on_complete(self.get_update_state())
            return
        if not self.app.device.connected:
            on_complete(self.install_tft(version))
            return
        if self._update_state == UPDATE_STATE_INSTALLING:
            on_complete(self.get_update_state())
            return
        if self._firmware_installing:
            self._set_update_state(
                UPDATE_STATE_ERROR,
                version=version,
                error=self.translate("Cannot install TFT during a firmware update"),
            )
            on_complete(self.get_update_state())
            return
        if url is not None:
            on_complete(self.install_tft_url(url))
            return
        self.start_async_check(
            allow_auto_install=False,
            include_notice=False,
            include_tft_source=True,
            require_connected=False,
            on_complete=lambda check: self._answer_once(
                on_complete,
                lambda message: {
                    **self.get_update_state(),
                    "state": UPDATE_STATE_ERROR,
                    "last_error": f"TFT install request failed: {message}",
                },
                lambda answer: answer(self._install_tft_after_check(check, version)),
            ),
        )

    @staticmethod
    def _answer_once(
        on_complete: Callable[[dict[str, Any]], None],
        failed: Callable[[str], dict[str, Any]],
        work: Callable[[Callable[[dict[str, Any]], None]], None],
    ) -> None:
        """Run ``work(answer)`` so that ``on_complete`` is answered even when it raises.

        The editor and the update entity wait for ``on_complete`` after the
        off-worker gap. When ``work`` raises before answering they get
        ``failed(message)``; the exception still reaches the worker's log.
        """
        answered = False

        def answer(result: dict[str, Any]) -> None:
            nonlocal answered
            answered = True
            on_complete(result)

        try:
            work(answer)
        except Exception as exc:
            if not answered:
                on_complete(failed(str(exc)))
            raise

    def _install_tft_after_check(
        self, check: dict[str, Any], version: str | None
    ) -> dict[str, Any]:
        """Install the TFT with the manifest the check loaded.

        A superseded check loaded nothing: a newer check is still fetching,
        and the manifest held now may belong to another URL or channel.
        """
        if check["check_error"] == CHECK_SUPERSEDED:
            return {
                **self.get_update_state(),
                "state": UPDATE_STATE_ERROR,
                "last_error": self.translate("Install request superseded"),
            }
        if self._get_tft_manifest() is None:
            return self._set_missing_manifest_error_for_tft(version)
        return self.install_tft(version)

    def _set_missing_manifest_error_for_tft(self, version: str | None) -> dict[str, Any]:
        """Record a manifest fetch failure without retrying synchronously."""
        message = (
            self._tft_manifest_error
            or self._firmware_manifest_error
            or self.translate("Firmware manifest unavailable")
        )
        self._set_update_state(UPDATE_STATE_ERROR, version=version, error=message)
        return self.get_update_state()

    def _loaded_tft_releases(self) -> dict[str, Any]:
        """List the TFT versions the loaded manifest lets this panel install.

        The TFT comes from the firmware manifest (one update path), so the
        only selectable version is the manifest's TFT, and only when it is the
        one the firmware needs; a manifest without a ``tft`` block lists none
        and the From URL path stays available.

        Returns:
            dict: ``releases`` (the manifest's TFT version, if any),
            ``required`` (the firmware's ``tft_required_version``) and
            ``error`` (why nothing can be installed, or None)
        """
        required = self._required_tft_version(self.app.device.device_info or {})
        manifest = self._get_tft_manifest()
        version = manifest.get("tft_version") if manifest is not None else None
        matches_required = required is None or self._same_version(required, version)
        releases = [version] if manifest and manifest.get("tft_url") and matches_required else []
        error = (
            None
            if releases
            else self._tft_update_reason()
            or self._tft_manifest_error
            or self._firmware_manifest_error
        )
        return {"releases": releases, "required": required, "error": error}

    def install_tft_url(self, url: str) -> dict[str, Any]:
        """Install the TFT file at ``url`` instead of the manifest's.

        For custom or development TFT builds.  The file carries no version the
        hub can check, so the install counts as done once the device reboots
        after the upload and the display reports any version.  The TFT is kept
        until the firmware's ``yaml_version`` changes (see
        ``_manual_tft_firmware``).  Call via ``app.async_run_on_worker``.

        Args:
            url (str): http(s) URL of the ``.tft`` file

        Returns:
            dict: The update state after the attempt; ``state`` is
            ``UPDATE_STATE_ERROR`` when the install could not start.
        """
        if not self.app.device.connected:
            self.log("Cannot install the TFT while the device is disconnected", level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, error="device disconnected")
            return self.get_update_state()
        self.log(f"Installing TFT from {url}")
        # _set_update_state keeps the previous version when given None; a URL
        # install must not be confirmed against an earlier release's version.
        self._update_version = None
        self._auto_attempts.pop("tft", None)
        result = self._start_tft_upload(url, None)
        if result["state"] == UPDATE_STATE_INSTALLING:
            self._manual_tft_firmware = (self.app.device.device_info or {}).get("yaml_version")
        return result

    # update state (for the editor / Panel Doctor)

    def _set_update_state(
        self, state: str, version: str | None = None, error: str | None = None
    ) -> None:
        """Record a transition of the TFT update state.

        The display gives no byte-level progress, so only coarse transitions
        are tracked.  Every state but ``error`` clears the recorded error (the
        update entity shows it first); ``installing`` stamps the start time;
        other transitions keep the previous timestamp.

        Args:
            state (str): New update state
            version (str | None): Version being installed / requested
            error (str | None): Error message when moving to ``error``
        """
        if version is not None:
            self._update_version = version
        if state == UPDATE_STATE_INSTALLING:
            self._update_started_at = datetime.datetime.now(tz=datetime.UTC)
        self._update_last_error = error if state == UPDATE_STATE_ERROR else None
        self._update_state = state
        self.log(f"TFT update state: {state}")
        self.publish_display_update()

    def get_update_snapshot(self) -> UpdateSnapshot:
        """Return the complete controller-owned update state for one device."""
        device_info = self.app.device.device_info or {}
        enabled = self._updates_enabled()
        tft_manifest = self._get_tft_manifest()
        manifest_tft = tft_manifest.get("tft_version") if tft_manifest is not None else None
        installed_tft = device_info.get("tft_version") or None
        tft_reason = (
            None if enabled else "Updates are disabled for this device"
        ) or self._tft_update_reason()
        installed_firmware = device_info.get("yaml_version") or None
        firmware_reason = (
            None if enabled else "Updates are disabled for this device"
        ) or self._firmware_update_reason()
        return {
            "device": self.app.device.get_name(),
            "connected": self.app.device.connected,
            "enabled": enabled,
            "display": {
                "installed_version": installed_tft,
                "latest_version": (
                    manifest_tft
                    if enabled and manifest_tft and tft_reason is None
                    else installed_tft
                ),
                "available": (
                    enabled
                    and tft_reason is None
                    and self._version_is_newer(manifest_tft, installed_tft) is True
                ),
                "state": self._update_state,
                "version": self._update_version,
                "started_at": (
                    self._update_started_at.isoformat() if self._update_started_at else None
                ),
                "last_error": self._update_last_error,
                "update_reason": tft_reason,
                "auto": self._auto_snapshot("tft"),
                "progress": self._progress("tft"),
            },
            "firmware": {
                "installed_version": installed_firmware,
                "latest_version": (
                    self._firmware_update_version() if enabled else installed_firmware
                ),
                "available": enabled and self._firmware_update_available(),
                "reason": firmware_reason,
                "installing": self._firmware_installing,
                "last_error": self._firmware_install_error,
                "auto": self._auto_snapshot("firmware"),
                "scheduled": (
                    {
                        "version": self._scheduled["version"],
                        "starts_at": self._scheduled["starts_at"].isoformat(),
                    }
                    if self._scheduled is not None
                    else None
                ),
                "skipped_version": self.get("skipped_firmware_version") or None,
                "progress": self._progress("firmware"),
            },
        }

    def publish_display_update(self) -> None:
        """Fire the TFT versions and update state for the "HAUI Display" entity.

        The latest version is the TFT the firmware manifest ships; without a
        ``tft`` block (a local test release names none) there is no display update, so
        the installed TFT is reported instead — the entity then shows itself up
        to date instead of offering an install the manifest cannot serve.
        """
        snapshot = self.get_update_snapshot()
        self.app.fire_event(
            DISPLAY_UPDATE_EVENT,
            {
                "device": snapshot["device"],
                "connected": snapshot["connected"],
                "enabled": snapshot["enabled"],
                "installed_version": snapshot["display"]["installed_version"],
                "latest_version": snapshot["display"]["latest_version"],
                "state": snapshot["display"]["state"],
                "last_error": snapshot["display"]["last_error"],
                "update_reason": snapshot["display"]["update_reason"],
            },
        )

    def get_update_state(self) -> dict[str, Any]:
        """Return the current TFT update state for the device status payload.

        Returns:
            dict: ``state`` (idle/checking/installing/error/done), ``version``,
            ``started_at`` (ISO timestamp or None) and ``last_error``
        """
        snapshot = self.get_update_snapshot()
        display = snapshot["display"]
        firmware = snapshot["firmware"]
        return {
            "enabled": snapshot["enabled"],
            "state": display["state"],
            "version": display["version"],
            "started_at": display["started_at"],
            "last_error": display["last_error"],
            "tft_update_reason": display["update_reason"],
            "tft_update_available": display["available"],
            "firmware_update_available": firmware["available"],
            "firmware_update_version": firmware["latest_version"],
            "firmware_update_reason": firmware["reason"],
            "firmware_installing": firmware["installing"],
            "firmware_install_error": firmware["last_error"],
            "firmware_auto": firmware["auto"],
            "tft_auto": display["auto"],
            "firmware_scheduled": firmware["scheduled"],
            "firmware_skipped_version": firmware["skipped_version"],
            "firmware_progress": firmware["progress"],
            "tft_progress": display["progress"],
        }

    def _mark_done_if_installed(self) -> None:
        """Mark the TFT update ``done`` once the display reports the requested version.

        The display gives no byte-level progress; the install is considered
        complete when the firmware reports a ``tft_version`` that is at least
        the requested one (the display re-sends it after rebooting into the new
        TFT).  Called from the periodic version check and from device-state
        events.  A URL install requests no version: it is complete once the
        display reports any version during the verification window that starts
        when the device reconnects after the upload's reboot.
        """
        if self._update_state not in (UPDATE_STATE_CHECKING, UPDATE_STATE_INSTALLING):
            return
        requested = self._update_version
        installed = (self.app.device.device_info or {}).get("tft_version")
        installed_v = self._try_parse_version(installed)
        if installed_v is None:
            return
        requested_v = self._try_parse_version(requested)
        if requested_v is None:
            if self._install_verify_timer is None:
                return  # no reboot yet: the upload has not finished
        elif self._version_is_newer(requested, installed) is True:
            return  # the display still reports an older TFT
        self._set_update_state(UPDATE_STATE_DONE, version=requested)
        self._auto_attempts.pop("tft", None)
        self._last_install_confirmed = True
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")

    def _unconfirmed_install_waits(self, required_version: str) -> bool:
        """Whether an unconfirmed install of ``required_version`` holds off the next one.

        An install the display never confirmed failed (or is still in flight).
        It counts as a failed attempt; the automatic install tries again once
        the retry policy allows (``_auto_attempt_allowed``), and until then the
        failure is reported with when the next attempt follows.
        """
        if not self._recent_unconfirmed_install(required_version):
            return False
        self._record_auto_result("tft", False, at=self._last_install_at)
        # The install is still the one in flight (its verification window may
        # be running): it fails now, and a retry waits for a later check.
        in_flight = self._update_state == UPDATE_STATE_INSTALLING
        if (
            not in_flight
            and self.get("auto_install")
            and self._auto_attempt_allowed("tft", required_version)
        ):
            return False
        stopped = self._auto_snapshot("tft")["stopped_reason"]
        self._set_install_failed(
            stopped
            or "TFT install was not confirmed; press Install TFT to retry now, or the "
            "automatic install tries again after the retry interval"
        )
        return True

    # automatic install attempts (the retry policy)

    def _retry_interval(self) -> int:
        return int(self.get("retry_interval"))

    def _max_attempts(self) -> int:
        return int(self.get("max_attempts"))

    def _record_auto_attempt(self, kind: str, version: str | None) -> None:
        """Count an automatic install of ``version`` that starts now."""
        record = self._auto_attempts.get(kind)
        if record is None or record["version"] != version:
            record = {"version": version, "attempts": 0, "last_at": None, "failed": False}
            self._auto_attempts[kind] = record
        record["attempts"] += 1
        record["last_at"] = datetime.datetime.now(tz=datetime.UTC)
        record["failed"] = False

    def _record_auto_result(self, kind: str, ok: bool, at: datetime.datetime | None = None) -> None:
        """Record how the last install of ``kind`` ended.

        A success clears the record. A failure marks it; a failed install that
        was not automatic (a manual one, or one from before a restart) counts
        as one attempt started ``at`` (now when not given), so the automatic
        install waits the retry interval before it tries the version again.
        """
        if ok:
            self._auto_attempts.pop(kind, None)
            return
        record = self._auto_attempts.get(kind)
        if record is None:
            version = self._update_version if kind == "tft" else self._firmware_install_version
            record = {
                "version": version,
                "attempts": 1,
                "last_at": at or datetime.datetime.now(tz=datetime.UTC),
                "failed": True,
            }
            self._auto_attempts[kind] = record
        record["failed"] = True

    def _auto_attempt_allowed(self, kind: str, version: str | None) -> bool:
        """Whether the retry policy lets an automatic install of ``version`` start now.

        A version without attempts may start. After a failure the next attempt
        waits ``retry_interval`` seconds, and after ``max_attempts`` attempts the
        automatic install of that version stops.
        """
        record = self._auto_attempts.get(kind)
        if record is None or record["version"] != version:
            return True
        if record["attempts"] >= self._max_attempts():
            return False
        if record["last_at"] is None:
            return True
        age = datetime.datetime.now(tz=datetime.UTC) - record["last_at"]
        return age.total_seconds() >= self._retry_interval()

    def _auto_snapshot(self, kind: str) -> _AutoSnapshot:
        """The retry state of ``kind`` for the editor."""
        record = self._auto_attempts.get(kind)
        max_attempts = self._max_attempts()
        if record is None:
            return {
                "attempts": 0,
                "max_attempts": max_attempts,
                "next_attempt_at": None,
                "stopped_reason": None,
            }
        stopped = record["failed"] and record["attempts"] >= max_attempts
        next_at = None
        if record["failed"] and not stopped and record["last_at"] is not None:
            next_at = (
                record["last_at"] + datetime.timedelta(seconds=self._retry_interval())
            ).isoformat()
        return {
            "attempts": record["attempts"],
            "max_attempts": max_attempts,
            "next_attempt_at": next_at,
            "stopped_reason": (
                f"Automatic install of {record['version']} stopped after "
                f"{record['attempts']} failed attempts. Install it by hand or wait for a "
                "newer version."
                if stopped
                else None
            ),
        }

    # step progress

    def _firmware_phase(self) -> str | None:
        if self._firmware_installing:
            return "transferring" if not self.app.device.connected else "starting"
        if self._scheduled is not None:
            return "scheduled"
        if self._firmware_install_ok is True:
            return "done"
        if self._firmware_install_ok is False:
            return "failed"
        return None

    def _display_phase(self) -> str | None:
        state = self._update_state
        if state == UPDATE_STATE_CHECKING:
            return "starting"
        if state == UPDATE_STATE_INSTALLING:
            if not self.app.device.connected:
                return "transferring"
            return "verifying" if self._install_verify_timer is not None else "starting"
        if state == UPDATE_STATE_DONE:
            return "done"
        if state == UPDATE_STATE_ERROR:
            return "failed"
        return None

    def _progress(self, kind: str) -> _Progress | None:
        """The step the ``firmware`` or ``tft`` install is at, for the editor.

        Each change of step stamps when it began, so the editor can show how
        long the current step has run.
        """
        if kind == "firmware":
            phase = self._firmware_phase()
            started = self._firmware_install_at if phase != "scheduled" else None
            expected = FIRMWARE_EXPECTED_SECONDS
        else:
            phase = self._display_phase()
            started = self._update_started_at
            expected = TFT_EXPECTED_SECONDS
        if phase is None:
            self._phase_since.pop(kind, None)
            return None
        known = self._phase_since.get(kind)
        if known is None or known[0] != phase:
            known = (phase, datetime.datetime.now(tz=datetime.UTC))
            self._phase_since[kind] = known
        return {
            "phase": phase,
            "phase_started_at": known[1].isoformat(),
            "started_at": started.isoformat() if started else None,
            "expected_seconds": expected,
        }

    def _recent_unconfirmed_install(self, version: str | None) -> bool:
        """True when ``version`` was installed and the display never confirmed it.

        Such an install may still be in flight (the upload reboots the device,
        so confirming takes time) or have failed (the display never reported
        the new version).  Either way it must not be auto-reinstalled, or a
        display that cannot report its version would be uploaded to forever.
        """
        return (
            self._last_install_version == version
            and not self._last_install_confirmed
            and self._last_install_at is not None
        )

    def _set_install_failed(self, message: str) -> None:
        """Mark the in-flight install as failed and stop its timers."""
        self.log(message, level="ERROR")
        self._record_auto_result("tft", False)
        self._set_update_state(
            UPDATE_STATE_ERROR, version=self._last_install_version, error=message
        )
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")

    def _install_missing_tft(
        self, required_version: str, installed_version: str | None, firmware_version: str | None
    ) -> None:
        """Install the required TFT automatically, or ask when ``auto_install`` is off."""
        if self._manual_tft_firmware is not None and self._manual_tft_firmware == firmware_version:
            self.log(
                f"Keeping the TFT installed by hand ({installed_version!r}) until the "
                f"firmware changes from {firmware_version}"
            )
            return
        if self._firmware_installing:
            # A firmware install reboots the device; a TFT upload now would be
            # cut off mid-transfer.  The version check runs again after the
            # reconnect, when the new firmware's tft_version decides the TFT.
            self.log("Firmware update in flight; TFT install deferred until it finishes")
            return
        if self.get("auto_install"):
            if not self._auto_attempt_allowed("tft", required_version):
                self.log(f"Automatic TFT install of {required_version} waits for its retry policy")
                self.publish_display_update()
                return
            self.log(f"TFT {installed_version!r} is older than {required_version}, installing")
            self._record_auto_attempt("tft", required_version)
            if self.run_update_display(required_version)["state"] == UPDATE_STATE_ERROR:
                self._record_auto_result("tft", False)
            return
        msg = self.translate("Your TFT-version is outdated.")
        msg += "\r\n"
        msg += self.translate("Do you want to update?")
        navigation = self.app.controller["navigation"]
        navigation.open_panel(
            PopupPanelKey.POPUP_NOTIFY,
            icon="mdi:message-question",
            title=self.translate("TFT"),
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

    def _request_device_state(self) -> None:
        """Ask the firmware to republish its device state.

        The boot handshake reads ``tft_version`` before the display answered,
        and the firmware only republishes the state on ``req_device_state``
        (plus — newer firmware — when the display finally reports the version).
        The explicit request is what turns a stale/empty snapshot into real data.
        """
        self.send_esphome(ESPRequest.REQ_DEVICE_STATE, "", force=True)

    def _start_state_check_timer(self) -> None:
        """Start the fallback that evaluates the version if the refresh is lost."""
        self._state_check_timer = self.app.run_in(
            self._state_check_timer_callback, DEVICE_STATE_REFRESH_SECONDS
        )

    def _state_check_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._state_check_timer = None
        self._evaluate_installed_version(self.app.device.device_info or {}, refresh_answered=False)

    def _evaluate_installed_version(
        self, device_info: dict[str, Any], refresh_answered: bool = True
    ) -> None:
        """Decide whether the TFT needs an install based on ``device_info``.

        ``refresh_answered`` is False when the state refresh timed out.  A
        lost response is fail-safe: an *unknown* installed version is then
        never auto-installed, because the display may simply still be reading
        it.  Known versions are evaluated either way.
        """
        firmware_version = device_info.get("yaml_version")
        if not self._updates_enabled():
            return
        required_version = self._required_tft_version(device_info)
        installed_version = device_info.get("tft_version")
        if required_version is None:
            self.log("The firmware did not report a required TFT version; TFT not checked")
            return
        required = self._try_parse_version(required_version)
        if required is None:
            msg = f"invalid tft_required_version {required_version!r}"
            self.log(
                "The firmware reported an invalid tft_required_version; TFT not checked",
                level="WARNING",
            )
            self._set_update_state(UPDATE_STATE_ERROR, version=self._update_version, error=msg)
            return
        # The manifest only has the TFT asset for its declared TFT version.
        # It must match the version this firmware requires, which can differ
        # from ``yaml_version`` on firmware-only releases. A manifest without
        # ``tft`` cannot serve a display update; in that case the display keeps
        # its current TFT.
        manifest = self._get_tft_manifest()
        manifest_tft = manifest.get("tft_version") if manifest is not None else None
        manifest_tft_url = manifest.get("tft_url") if manifest is not None else None
        if (
            self._try_parse_version(manifest_tft) is None
            or not self._same_version(required_version, manifest_tft)
            or not manifest_tft_url
        ):
            reason = self._tft_update_reason()
            self.log(
                reason or "The firmware manifest cannot provide the required TFT",
                level="WARNING",
            )
            self.publish_display_update()
            return
        installed = self._try_parse_version(installed_version)
        if not refresh_answered and installed is None:
            self.log(
                "Could not read the installed TFT version (no device-state answer); not installing",
                level="WARNING",
            )
            return
        if installed is not None:
            self.log(
                f"Checking installed version: required={required_version} "
                f"installed={installed_version}"
            )
            newer = self._version_is_newer(required_version, installed_version)
            if newer is False:
                self.log("Installed TFT version is up to date")
                self._auto_attempts.pop("tft", None)
                self._mark_done_if_installed()
                self._last_install_confirmed = True
                self._cancel_timer("_install_verify_timer")
                self._cancel_timer("_install_timeout_timer")
                return
            if newer is None:
                # Parseable under packaging but AwesomeVersion (which Home
                # Assistant uses) cannot compare them: treat as unknown, never
                # install on a guess.
                self.log(
                    f"TFT versions {required_version!r} and {installed_version!r} "
                    "cannot be compared; not installing",
                    level="WARNING",
                )
                return
            if self._unconfirmed_install_waits(required_version):
                return
            self._install_missing_tft(required_version, installed_version, firmware_version)
            return
        # The refresh answered but the display still has no version.
        if self._install_verify_timer is not None:
            # A reconnect right after an install: the bounded verification
            # window owns the outcome.  Re-read once more instead of guessing.
            self.log("TFT version still unknown after reconnect; verifying the install")
            self._request_device_state()
            return
        if self._unconfirmed_install_waits(required_version):
            return
        self.log(f"TFT version unknown, installing {required_version}")
        self._install_missing_tft(required_version, installed_version, firmware_version)

    # install timing (the upload reboots the device, so confirmation is async)

    def _start_install_timeout_timer(self) -> None:
        """Start the overall install timeout (covers the slow portrait upload)."""
        self._cancel_timer("_install_timeout_timer")
        self._install_timeout_timer = self.app.run_in(
            self._install_timeout_timer_callback, INSTALL_TIMEOUT_SECONDS
        )

    def _install_timeout_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._install_timeout_timer = None
        if self._update_state != UPDATE_STATE_INSTALLING:
            return
        self._set_install_failed(
            "TFT install timed out; the display never reported the new version"
        )

    def _rebooted_since(self, started_at: datetime.datetime | None) -> bool:
        """Whether the device booted after an install sent at ``started_at``.

        A TFT upload or firmware install blocks the device until it ends: a
        finished one reboots it, a failed one lets it run on, and either way
        it then reconnects.  The connection handshake's ``uptime`` tells the
        two apart; without the check a failed URL install counted as done.

        Args:
            started_at (datetime.datetime | None): When the install was sent

        Returns:
            bool: False when the device ran through the whole install or the
            handshake does not provide enough information to confirm a reboot.
        """
        uptime = (self.app.device.device_info or {}).get("uptime")
        if uptime is None or started_at is None:
            self.log(
                "The handshake reports no uptime; cannot tell whether the install rebooted "
                "the device",
                level="WARNING",
            )
            return False
        try:
            uptime_seconds = float(uptime)
        except TypeError, ValueError:
            self.log(
                "The handshake reports an invalid uptime; install reboot is unconfirmed",
                level="WARNING",
            )
            return False
        elapsed = datetime.datetime.now(tz=datetime.UTC) - started_at
        return uptime_seconds < elapsed.total_seconds()

    def _start_install_verification(self) -> None:
        """Verify an install that was in flight when the device reconnected.

        The upload ends in a reboot, so a reconnect while ``installing`` is
        expected.  Start a bounded refresh window: re-read the state a few
        times, then fail so the editor can offer a manual retry.  A matching
        version flips the state to ``done`` via ``_mark_done_if_installed``.
        """
        self._install_verify_refreshes = 0
        self._request_device_state()
        self._start_install_verify_timer()

    def _start_install_verify_timer(self) -> None:
        self._cancel_timer("_install_verify_timer")
        self._install_verify_timer = self.app.run_in(
            self._install_verify_timer_callback, VERIFY_REFRESH_SECONDS
        )

    def _install_verify_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._install_verify_timer = None
        if self._update_state != UPDATE_STATE_INSTALLING:
            return  # done or errored in the meantime
        if self._install_verify_refreshes >= VERIFY_MAX_REFRESHES:
            self._set_install_failed(
                "TFT install was not confirmed within the timeout; press Install TFT to retry"
            )
            return
        self._install_verify_refreshes += 1
        self._request_device_state()
        self._start_install_verify_timer()

    def check_installed_version(self) -> None:
        """Updates the TFT when it is older than the firmware-reported ``tft_required_version``.

        The firmware publishes ``tft_version`` only in response to
        ``req_device_state``; the handshake reads it before the display
        answered.  When the version is unknown — or a recent install is still
        unconfirmed — a fresh device-state read is requested instead of acting
        on the possibly-empty boot snapshot.  This is what stops the reboot
        loop where an empty version was compared as ``0.0.0`` and reinstalled.
        """
        if not self.app.device.connected:
            return
        device_info = self.app.device.device_info or {}
        installed_version = device_info.get("tft_version")
        required_version = self._required_tft_version(device_info)
        self.log(
            f"Checking installed version: required={required_version} installed={installed_version}"
        )
        if self._pending_state_check or self._state_check_timer is not None:
            return  # a refresh is already in flight
        if installed_version or self._recent_unconfirmed_install(required_version):
            # The display already reported a version (or a recent install is
            # waiting for confirmation): evaluate right away.
            self._evaluate_installed_version(device_info)
            return
        # Version unknown: ask the device before drawing any conclusion.
        self._pending_state_check = True
        self._request_device_state()
        self._start_state_check_timer()

    def _check_result(
        self, check_error: str | None, latest_release: str | None = None
    ) -> dict[str, Any]:
        """Return an update check's result: the update state plus the release check."""
        return {
            **self.get_update_state(),
            "latest_release": latest_release,
            "check_error": check_error,
        }

    def start_async_check(
        self,
        force_refresh: bool = False,
        *,
        allow_auto_install: bool = True,
        include_notice: bool = True,
        check_tft: bool = False,
        include_tft_source: bool = False,
        require_connected: bool = True,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Fetch update inputs off-worker and apply them in the worker callback.

        The worker only captures configuration before submission. Network I/O
        runs on the adapter's bounded I/O pool; all controller/device state is
        applied by ``_complete_async_check`` after ``submit_off_worker``
        dispatches its callback back to this worker.

        Args:
            force_refresh: Bypass the shared GitHub release cache
            allow_auto_install: Whether the check may start a configured
                automatic firmware install
            include_notice: Fetch the release catalog and show the advisory
                notice for a newer release
            check_tft: Check the installed TFT against the firmware's requirement
            include_tft_source: Look up the installed firmware's own manifest
                when the channel's manifest lacks the required TFT
            require_connected: Refuse the check while the device is disconnected
            on_complete: Receives ``get_update_state()`` plus ``latest_release``
                and ``check_error`` (why the release check failed, or None)
        """
        done = on_complete or (lambda _result: None)
        if not self._updates_enabled():
            done(self._check_result("Updates are disabled for this device"))
            return
        if require_connected and not self.app.device.connected:
            done(self._check_result("device disconnected"))
            return

        self._async_check_id += 1
        request_id = self._async_check_id
        lifecycle = self._lifecycle_generation
        firmware_info = self.app.device.device_info or {}
        required_tft_version = self._required_tft_version(firmware_info)
        request = UpdateFetchRequest(
            manifest_override=str(self.get("firmware_manifest_url") or ""),
            channel=str(self.get("firmware_update_channel")),
            force=force_refresh,
            include_releases=include_notice,
            include_tft_source=(
                include_tft_source or check_tft or required_tft_version is not None
            ),
            firmware_version=firmware_info.get("yaml_version"),
            required_tft_version=required_tft_version,
            display_model=self.app.device.display_model,
        )
        self.app.submit_off_worker(
            release_source.fetch_update_inputs,
            request,
            on_done=lambda inputs, error: self._complete_async_check(
                request_id,
                lifecycle,
                inputs,
                error,
                allow_auto_install,
                include_notice,
                check_tft,
                done,
            ),
        )

    def _complete_async_check(
        self,
        request_id: int,
        lifecycle: int,
        inputs: UpdateFetchInputs | None,
        error: BaseException | None,
        allow_auto_install: bool,
        include_notice: bool,
        check_tft: bool,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Apply fetched update inputs on the device worker and finish the check."""
        if lifecycle != self._lifecycle_generation or request_id != self._async_check_id:
            on_complete(self._check_result(CHECK_SUPERSEDED))
            return
        if not self._updates_enabled():
            on_complete(self._check_result("Updates are disabled for this device"))
            return
        try:
            result = self._apply_check_inputs(
                inputs, error, allow_auto_install, include_notice, check_tft
            )
        except Exception as exc:
            # The editor or the update entity waits for this answer; the
            # exception still reaches the worker's log.
            on_complete(self._check_result(f"Update check failed: {exc}"))
            raise
        on_complete(result)

    def _apply_check_inputs(
        self,
        inputs: UpdateFetchInputs | None,
        error: BaseException | None,
        allow_auto_install: bool,
        include_notice: bool,
        check_tft: bool,
    ) -> dict[str, Any]:
        """Adopt what a check fetched and act on it; returns the check result."""
        if error is not None or inputs is None:
            inputs = release_source.failed_update_inputs(
                str(error) if error else "Update check failed"
            )
        if inputs["release_warning"]:
            self.log(inputs["release_warning"], level="WARNING")
        self._release_infos = inputs["releases"]
        if self._firmware_install_ok:
            self._firmware_install_ok = None
        if self._apply_manifests(inputs):
            self.publish_display_update()
            self.publish_firmware_update()
        if allow_auto_install and self._firmware_manifest and self._firmware_install_due():
            self._schedule_firmware_install()
        if check_tft and self.app.device.connected:
            if self._get_tft_manifest() is None:
                self.log(
                    "TFT requirement check deferred because the firmware manifest is unavailable",
                    level="WARNING",
                )
            else:
                self.check_installed_version()

        latest_release = self._get_latest_release()
        # A firmware install in flight already tells the user what is coming;
        # the advisory would only replace its popup.
        if (
            include_notice
            and latest_release is not None
            and not self._firmware_installing
            and self._is_update_available()
        ):
            self._notify_firmware_release(latest_release)
        return self._check_result(
            inputs["release_error"], latest_release["tag_name"] if latest_release else None
        )

    def _apply_manifests(self, inputs: UpdateFetchInputs) -> bool:
        """Adopt the firmware and TFT manifests a check fetched.

        A failed read clears the manifest instead of keeping the previous one:
        after the URL changed, the old manifest would offer a firmware the
        panel is no longer meant to follow.  Without a manifest of its own for
        the required TFT, the TFT follows the firmware manifest.

        Returns:
            bool: Whether anything the update entities show changed
        """
        before = (
            self._firmware_manifest,
            self._firmware_manifest_error,
            self._firmware_manifest_url,
            self._tft_manifest,
            self._tft_manifest_url,
        )
        self._firmware_manifest_url = inputs["manifest_url"]
        manifest = inputs["manifest"]
        if isinstance(manifest, dict) and self._firmware_manifest_url:
            try:
                self._firmware_manifest = release_source.parse_firmware_manifest(
                    manifest,
                    self._firmware_manifest_url,
                    self.app.device.display_model,
                )
                self._firmware_manifest_error = None
            except RuntimeError as exc:
                self._firmware_manifest = None
                self._firmware_manifest_error = str(exc)
        else:
            self._firmware_manifest = None
            self._firmware_manifest_error = inputs["manifest_error"]
        self._tft_manifest = inputs["tft_manifest"]
        self._tft_manifest_url = inputs["tft_manifest_url"]
        self._tft_manifest_error = inputs["tft_manifest_error"]
        if self._tft_manifest is None and self._firmware_manifest is not None:
            self._tft_manifest = self._firmware_manifest
            self._tft_manifest_url = self._firmware_manifest_url
            self._tft_manifest_error = self._firmware_manifest_error
        return before != (
            self._firmware_manifest,
            self._firmware_manifest_error,
            self._firmware_manifest_url,
            self._tft_manifest,
            self._tft_manifest_url,
        )

    def start_async_list_tft_releases(self, on_complete: Callable[[dict[str, Any]], None]) -> None:
        """Load the TFT picker manifest without blocking the device worker."""
        if not self._updates_enabled():
            on_complete(
                {"releases": [], "required": None, "error": "Updates are disabled for this device"}
            )
            return
        self.start_async_check(
            allow_auto_install=False,
            include_notice=False,
            include_tft_source=True,
            require_connected=False,
            on_complete=lambda check: self._answer_once(
                on_complete,
                lambda message: {"releases": [], "required": None, "error": message},
                lambda answer: answer(self._list_tft_releases_after_check(check)),
            ),
        )

    def _list_tft_releases_after_check(self, check: dict[str, Any]) -> dict[str, Any]:
        """List the TFT versions the manifest the check loaded offers."""
        if check["check_error"] == CHECK_SUPERSEDED:
            # a superseded check loaded no manifest to list from
            return {"releases": [], "required": None, "error": "request superseded"}
        return self._loaded_tft_releases()

    def start_async_list_firmware_releases(
        self, on_complete: Callable[[dict[str, Any]], None]
    ) -> None:
        """Load release candidates and their compatibility manifests off-worker."""
        if not self._updates_enabled():
            on_complete({"releases": [], "error": "Updates are disabled for this device"})
            return
        self._async_catalog_id += 1
        request_id = self._async_catalog_id
        lifecycle = self._lifecycle_generation
        variant = (self.app.device.device_info or {}).get("firmware_variant")

        def _done(result: Any, error: BaseException | None) -> None:
            if lifecycle != self._lifecycle_generation or request_id != self._async_catalog_id:
                on_complete({"releases": [], "error": "request superseded"})
            elif error is not None:
                on_complete({"releases": [], "error": str(error)})
            else:
                on_complete(result)

        self.app.submit_off_worker(
            release_source.fetch_firmware_release_candidates, variant, on_done=_done
        )

    def start_async_firmware_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Install the offered firmware, another release or the image at a URL.

        Without ``version`` and ``url`` it installs the firmware the manifest
        at ``firmware_manifest_url`` (or the ``firmware_update_channel``)
        offers, when it is newer than the one the device runs; the manual
        install is not disabled by the ``firmware_auto_update`` setting.
        ``version`` installs that manifest version, or else the GitHub release
        ``version`` (one with an over-the-air image, older ones included);
        ``url`` installs an OTA app image.  Installing anything but the
        manifest's firmware pauses the automatic firmware update until Home
        Assistant restarts or the offered update is installed.  Refuses to
        reboot during a TFT upload.

        The artifacts are resolved off-worker, then the install starts on the
        worker; ``on_complete`` receives the update state, with
        ``firmware_install_error`` set when the install could not start.
        """
        if not self._updates_enabled():
            self._report_firmware_install_error("Updates are disabled for this device", on_complete)
            return
        if not self.app.device.connected:
            self._report_firmware_install_error("Device is disconnected", on_complete)
            return
        if self._update_state == UPDATE_STATE_INSTALLING:
            self._report_firmware_install_error(
                "Cannot install firmware during a TFT upload", on_complete
            )
            return
        if self._firmware_installing:
            on_complete(self.get_update_state())
            return

        self._async_install_id += 1
        request_id = self._async_install_id
        lifecycle = self._lifecycle_generation
        request = FirmwareInstallRequest(
            version=version,
            url=url,
            manifest_override=str(self.get("firmware_manifest_url") or ""),
            channel=str(self.get("firmware_update_channel")),
        )
        self.app.submit_off_worker(
            release_source.fetch_firmware_install_inputs,
            request,
            on_done=lambda result, error: self._answer_once(
                on_complete,
                lambda message: {
                    **self.get_update_state(),
                    "firmware_install_error": f"Firmware install request failed: {message}",
                },
                lambda answer: self._complete_async_firmware_install(
                    request_id, lifecycle, version, url, result, error, answer
                ),
            ),
        )

    def _report_firmware_install_error(
        self, message: str, on_complete: Callable[[dict[str, Any]], None]
    ) -> None:
        """Record why a firmware install did not start and report the update state."""
        self._firmware_install_error = message
        self.log(f"Firmware install failed: {message}", level="WARNING")
        self.publish_firmware_update()
        on_complete(self.get_update_state())

    def _release_variant_error(self, version: str, manifest_variant: str) -> str:
        """Explain why the release ``version`` cannot be flashed onto this panel's build."""
        device_variant = (self.app.device.device_info or {}).get("firmware_variant")
        tip = (
            "; the variants are not interchangeable"
            if manifest_variant
            else "; its manifest names no variant"
        )
        return (
            f"Release {version} is a {manifest_variant or 'unknown-variant'} build but this "
            f"panel runs {device_variant or 'an unknown build'}{tip}"
        )

    def _complete_async_firmware_install(
        self,
        request_id: int,
        lifecycle: int,
        version: str | None,
        url: str | None,
        result: dict[str, Any] | None,
        error: BaseException | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Apply fetched artifact metadata and send the install action on-worker."""
        if lifecycle != self._lifecycle_generation or request_id != self._async_install_id:
            on_complete(
                {
                    **self.get_update_state(),
                    "firmware_install_error": self.translate("Install request superseded"),
                }
            )
            return
        failure = str(error) if error is not None else (result or {}).get("error")
        if failure == "Firmware manifest unavailable":
            failure = self.translate("Firmware manifest unavailable")
        if failure or result is None:
            self._report_firmware_install_error(failure or "Firmware install failed", on_complete)
            return

        if url is not None:
            on_complete(
                self._start_firmware_install(
                    result["url"], result["md5"], result["version"], manual=True
                )
            )
            return

        manifest_url = result["manifest_url"]
        try:
            manifest_info = release_source.parse_firmware_manifest(
                result["manifest"], manifest_url, self.app.device.display_model
            )
        except RuntimeError as exc:
            self._report_firmware_install_error(str(exc), on_complete)
            return

        is_offered = bool(result["offered"])
        if is_offered:
            self._firmware_manifest_url = manifest_url
            self._firmware_manifest = manifest_info
            self._firmware_manifest_error = None
        if not self._firmware_variant_compatible(manifest_info["variant"]):
            self._report_firmware_install_error(
                (self._firmware_variant_mismatch_reason() if is_offered else None)
                or self._release_variant_error(
                    version or manifest_info["version"], manifest_info["variant"]
                ),
                on_complete,
            )
            return
        if version is None and not self._firmware_update_available():
            self._report_firmware_install_error(
                self._firmware_update_reason() or self.translate("No firmware update is available"),
                on_complete,
            )
            return
        if version is not None and not self._same_version(version, manifest_info["version"]):
            self._report_firmware_install_error(
                self.translate("Release {version} manifest names {manifest}")
                .replace("{version}", version)
                .replace("{manifest}", manifest_info["version"]),
                on_complete,
            )
            return

        on_complete(
            self._start_firmware_install(
                manifest_info["url"],
                manifest_info["md5"],
                manifest_info["version"],
                manual=not is_offered,
            )
        )

    def _notify_firmware_release(self, latest_release: dict[str, Any]) -> None:
        """Show a deduplicated advisory for a newer integration release."""
        release_tag = latest_release["tag_name"]
        if release_tag == self._last_notified_release:
            return
        # GitHub reports null for a release without a title or notes; its
        # release page then shows the tag as the title.
        msg = latest_release["name"] or release_tag
        msg += "\r\n"
        msg += trim_text(strip_markdown(latest_release["body"] or ""), 200)
        msg += "\r\n\r\n"
        msg += self.translate("Firmware release:")
        msg += f" {release_tag}"
        msg += "\r\n\r\n"
        msg += self.translate("Firmware and display installs use the configured firmware manifest.")
        msg += "\r\n\r\n"
        # Queued, so it never replaces a notification the user is reading.
        self.app.controller["notification"].add_notification(
            self.translate("Update"),
            msg,
            icon="mdi:message-alert",
            force_show=True,
            sound="",
        )
        self._last_notified_release = release_tag

    # callback

    def on_connection_changed(self, connected: bool) -> None:
        """Schedules the TFT check on connect and cancels it on disconnect.

        Called by the app once the connection handshake is complete, so the
        device info holds ``tft_version``, ``tft_required_version`` and
        ``yaml_version``.

        A disconnect while ``installing`` is expected — the upload ends in a
        reboot — so that state is kept (the install timeout started at install
        time covers the case where the device never reconnects; the bounded
        verification window on reconnect covers the upload-completed case).
        A reconnect without a reboot means the upload failed, which fails the
        install right away (``_rebooted_since``).

        Args:
            connected (bool): Connection state
        """
        self._stop_timer_delay()
        if connected:
            if self._firmware_installing:
                # A firmware install ends in a reboot; a reconnect means the
                # attempt finished.  Clear the flag so the TFT check can run —
                # when the install failed, yaml_version still matches the
                # installed TFT and nothing happens.
                self._finish_firmware_install()
            if self._updates_enabled():
                self.log(f"Checking the TFT version in {self.get('on_connect_delay')} seconds")
                self._start_timer_delay()
            if self._update_state == UPDATE_STATE_INSTALLING:
                if self._rebooted_since(self._last_install_at):
                    self._start_install_verification()
                else:
                    self._set_install_failed(
                        "TFT upload failed: the panel did not reboot after the upload. "
                        "See the device's ESPHome log for the download or flash error."
                    )
        else:
            self._cancel_timer("_state_check_timer")
            self._cancel_timer("_install_verify_timer")
            self._pending_state_check = False
            self._install_verify_refreshes = 0
            if self._update_state not in (UPDATE_STATE_IDLE, UPDATE_STATE_INSTALLING):
                self._set_update_state(UPDATE_STATE_IDLE)
        self.publish_display_update()
        self.publish_firmware_update()

    def callback_update_response(self, btn_left: bool, btn_right: bool, version: str) -> None:
        """Callback for the outdated-TFT prompt: installs ``version`` on confirm.

        Args:
            btn_left (bool): Left button state
            btn_right (bool): Right button state
            version (str): TFT version to install
        """
        self.log("Callback update response")
        if not self._updates_enabled():
            return
        navigation = self.app.controller["navigation"]
        if btn_left:
            navigation.close_panel()
        if btn_right:
            msg = self.translate("Please wait while the update is starting")
            navigation.open_panel(
                PopupPanelKey.POPUP_NOTIFY,
                icon="mdi:message-cog",
                title=self.translate("Updating"),
                notification=msg,
            )
            self.run_update_display(version)

    def callback_timer(self) -> None:
        """Start the periodic check without holding the device worker on HTTP."""
        if not self._updates_enabled():
            return
        self.start_async_check()
        self._restart_timer()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process events.

        Args:
            event (HAUIEvent): Event
        """

        # device state received (includes yaml_version, tft_required_version and tft_version)
        if event.name == ESPResponse.RES_DEVICE_STATE:
            device_state = event.as_json()
            self.app.device.set_device_info(device_state, append=True)
            if self._pending_state_check:
                # A version-check refresh answered: evaluate with the fresh
                # snapshot instead of the (possibly empty) boot handshake one.
                self._pending_state_check = False
                self._cancel_timer("_state_check_timer")
                self._evaluate_installed_version(self.app.device.device_info or {})
            self._mark_done_if_installed()
            self.publish_display_update()
            self.publish_firmware_update()

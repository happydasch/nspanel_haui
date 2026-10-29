from __future__ import annotations

import datetime
import hashlib
import threading
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import requests
from packaging.version import InvalidVersion, Version, parse

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPAction, ESPRequest, ESPResponse, SysPanelKey
from ..utils.text import trim_text

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
# ``firmware_manifest_url`` (by default the one of the latest GitHub release)
# and, when it names a newer version, flashes its image with the firmware's
# ``install_firmware_url`` action; the TFT the new firmware needs follows after
# the reboot.  A failed automatic install is retried at most once an hour.
FIRMWARE_RETRY_SECONDS = 60 * 60
# The device downloads and flashes the image, then reboots.  An install that
# has not ended in a reconnect after this long failed without a reboot.
FIRMWARE_INSTALL_TIMEOUT_SECONDS = 10 * 60
# Fired on every firmware version or install state change; the "HAUI Firmware"
# update entity (``update.py``) renders it.
FIRMWARE_UPDATE_EVENT = "nspanel_haui.firmware_update_changed"

# Another firmware release or a custom build is flashed by the same action.  A
# release qualifies when it ships the OTA app image and the manifest holding
# its md5; ``nspanel_haui.bin`` is the full factory image, which an
# over-the-air update must never write.
FIRMWARE_OTA_ASSET = "nspanel_haui_ota.bin"
FIRMWARE_MANIFEST_ASSET = "firmware-manifest.json"
# The firmware build variants that the release manifest and the device state
# identify each other with.  The release workflow builds the prebuilt image
# from ``esphome/nspanel_haui_universal.yaml`` and its manifest says
# ``universal``; an ``install.yaml``/``nspanel_haui_dev.yaml`` build reports
# ``custom``.  The hub refuses to offer or install a manifest whose variant
# does not match the one the device reports (and treats both unknowns as
# incompatible): flashing the universal image onto a custom build would
# silently replace the user's credentials with the public universal ones.
FIRMWARE_VARIANT_UNIVERSAL = "universal"
FIRMWARE_VARIANT_CUSTOM = "custom"
# App partition size of the shipped partition table, and the first byte of an
# ESP32 app image (a factory image starts with 0xFF padding instead).
FIRMWARE_MAX_BYTES = 0x1C0000
ESP_IMAGE_MAGIC = 0xE9

# Hub-level release cache.  Every device has its own controller, but the
# GitHub releases page is identical for all of them; without a shared cache a
# hub with N devices spends N unauthenticated requests per interval against
# GitHub's 60 requests/hour/IP limit.  The cache lives at module level so it is
# shared across controller instances; a manual check bypasses the TTL.
RELEASE_CACHE_TTL_SECONDS = 60 * 60
_release_cache: tuple[float, list[dict[str, Any]]] | None = None
# Controllers run on separate worker threads, so the cache check + fetch is
# serialized: the first controller fetches and the rest reuse its result.
_release_cache_lock = threading.Lock()


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
        self.log(f"Creating Update Controller with config: {config}", level="DEBUG")
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
        # The manifest read last (``version``, ``url``, ``md5``) and the URL it
        # was read from; None when the read failed.
        self._firmware_manifest: dict[str, str] | None = None
        self._firmware_manifest_url: str | None = None
        # Firmware install bookkeeping.  The install runs on the device and
        # ends in a reboot, so a reconnect means the attempt finished — either
        # way.  While it is in flight the TFT install waits, because the reboot
        # would abort an upload.
        self._firmware_installing = False
        self._firmware_install_version: str | None = None
        self._firmware_install_at: datetime.datetime | None = None
        self._firmware_install_error: str | None = None
        self._firmware_install_timer: str | None = None
        # A firmware installed by hand (another release or a URL) pauses the
        # automatic firmware update, which would otherwise reinstall the latest
        # release on the next check.  In memory only: a Home Assistant restart
        # or installing the offered update ends it.
        self._manual_firmware = False

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
        if self.get("check_on_connect", False):
            self.check_for_update()
        self.check_installed_version()

    # part

    def start_part(self) -> None:
        """Starts the part."""
        self._interval = self.get("update_interval")
        self._start_timer()
        # On start and whenever a config reload changed the URL, so the HAUI
        # Firmware entity shows what the configured manifest offers right away.
        if self.get("firmware_manifest_url") != self._firmware_manifest_url:
            self._refresh_firmware_manifest()

    def stop_part(self) -> None:
        """Stops the part."""
        self._stop_timer()
        self._stop_timer_delay()
        self._cancel_timer("_state_check_timer")
        self._pending_state_check = False
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")
        self._cancel_timer("_firmware_install_timer")
        self._firmware_installing = False

    # update

    def _try_parse_version(self, version: str | None) -> Version | None:
        """Strictly parse ``version``, returning None for empty/invalid values.

        An empty ``tft_version`` (the display reports it only after boot) is
        *unknown*, not ``0.0.0`` — treating it as an old version is exactly
        what reinstalled the TFT after every reboot.
        """
        if not version:
            return None
        try:
            return parse(version)
        except InvalidVersion:
            return None

    def _update_release_infos(self, force: bool = False) -> None:
        """Updates the release informations.

        The GitHub releases page is the same for every device, so the response
        is cached at module level and shared across controller instances.  A
        hub with several panels therefore makes one request per TTL instead of
        one per device, staying well inside GitHub's unauthenticated rate
        limit.  ``force`` bypasses the cache for a user-initiated refresh; a
        failed request falls back to stale cached data when it exists.
        """
        global _release_cache

        if self._req_fetch:
            return

        with _release_cache_lock:
            if not force and _release_cache is not None:
                cached_at, cached_infos = _release_cache
                if time.monotonic() - cached_at < RELEASE_CACHE_TTL_SECONDS:
                    self._release_infos = cached_infos
                    return

            self._req_fetch = True
            cacheable = False
            try:
                resp = requests.get(self.RELEASES_URL, timeout=5)
                try:
                    json_decoded = resp.json()
                except ValueError as exc:
                    # GitHub rate-limit / proxy responses are HTML, not JSON.
                    if _release_cache is not None:
                        self._release_infos = _release_cache[1]
                        self.log(
                            "GitHub returned a non-JSON response; using cached release info",
                            level="WARNING",
                        )
                        return
                    raise RuntimeError(
                        f"GitHub returned a non-JSON response for {self.RELEASES_URL}: {exc}"
                    ) from exc
                if not isinstance(json_decoded, list):
                    # Rate-limit errors come back as a JSON object, not a list.
                    # Prefer stale cached data over caching a failure for an hour.
                    if _release_cache is not None:
                        self._release_infos = _release_cache[1]
                        self.log(
                            "Unexpected response from GitHub API; using cached release info",
                            level="WARNING",
                        )
                        return
                    self.log("Unexpected response from GitHub API", level="WARNING")
                    json_decoded = []
                else:
                    cacheable = True
            except requests.exceptions.RequestException as exc:
                if _release_cache is not None:
                    self._release_infos = _release_cache[1]
                    self.log(
                        f"Release info fetch failed ({exc}); using cached release info",
                        level="WARNING",
                    )
                    return
                raise RuntimeError(
                    f"Failed to fetch release info from {self.RELEASES_URL}: {exc}"
                ) from exc
            finally:
                self._req_fetch = False
            self._release_infos = json_decoded
            if cacheable:
                _release_cache = (time.monotonic(), json_decoded)

    def _get_latest_release(self) -> dict[str, Any] | None:
        """Returns the latest available release dict.

        Releases whose tag does not parse as a version are skipped, so an
        odd tag can neither break the comparison nor surface as ``0.0.0``.

        Returns:
            None|dict: Release info
        """
        latest_release = None
        latest_version: Version | None = None
        for release in self._release_infos:
            version = self._try_parse_version(release.get("tag_name"))
            if version is None:
                continue
            if latest_version is None or version > latest_version:
                latest_release = release
                latest_version = version
        return latest_release

    def _find_release(self, version: str) -> dict[str, Any] | None:
        """Returns the release whose tag is ``version`` (``v`` prefix ignored)."""
        wanted = self._try_parse_version(version)
        if wanted is None:
            return None
        for release in self._release_infos:
            if self._try_parse_version(release.get("tag_name")) == wanted:
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
        current_version = self._try_parse_version(device_info.get("tft_version"))
        latest_version = self._try_parse_version(latest_release.get("tag_name"))
        if current_version is None or latest_version is None:
            return False
        return current_version < latest_version

    # firmware update

    def _read_firmware_manifest(self, url: str) -> dict[str, str]:
        """Read the firmware manifest at ``url``.

        The manifest uses the ESPHome web-tools schema the release workflow
        writes (``version`` and ``builds[0].ota`` with ``path`` and ``md5``);
        a relative ``path`` is resolved against the manifest URL.  The
        optional ``variant`` names the build variant the image was compiled
        from (``universal`` for the release image, ``custom`` for a build
        from ``install.yaml``); a manifest without one is treated as unknown.

        Returns:
            dict: ``version``, ``url`` (of the OTA app image), ``md5`` and
            ``variant`` ("" when the manifest names none)

        Raises:
            RuntimeError: When the manifest cannot be read
        """
        try:
            manifest = requests.get(url, timeout=10).json()
            ota = manifest["builds"][0]["ota"]
            return {
                "version": str(manifest["version"]),
                "url": urljoin(url, ota["path"]),
                "md5": ota["md5"],
                "variant": str(manifest.get("variant") or ""),
            }
        except (requests.exceptions.RequestException, ValueError, LookupError, TypeError) as exc:
            raise RuntimeError(f"Could not read the firmware manifest {url}: {exc}") from exc

    def _refresh_firmware_manifest(self) -> None:
        """Read the manifest at ``firmware_manifest_url`` and publish the result.

        A failed read clears the manifest instead of keeping the previous one:
        after the URL changed, the old manifest would offer a firmware the
        panel is no longer meant to follow.
        """
        url = self.get("firmware_manifest_url")
        self._firmware_manifest_url = url
        try:
            if not url:
                raise RuntimeError("No firmware manifest URL is configured")
            self._firmware_manifest = self._read_firmware_manifest(url)
        except RuntimeError as exc:
            self._firmware_manifest = None
            self.log(f"Firmware update check failed: {exc}", level="WARNING")
        self.publish_firmware_update()

    def _same_version(self, first: str | None, second: str | None) -> bool:
        """Whether two version strings name the same version (``v`` prefix ignored)."""
        first_v = self._try_parse_version(first)
        return first_v is not None and first_v == self._try_parse_version(second)

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
        return bool(device_variant) and bool(manifest_variant) and device_variant == manifest_variant

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

    def _firmware_update_available(self) -> bool:
        """True when the manifest offers a newer firmware for *this* panel.

        A newer version alone is not enough: the manifest's build variant must
        match the one the device reports, or the update is withheld entirely.
        """
        latest = self._try_parse_version(self._firmware_update_version())
        installed = self._try_parse_version(
            (self.app.device.device_info or {}).get("yaml_version")
        )
        return latest is not None and installed is not None and latest > installed

    def _firmware_update_version(self) -> str | None:
        """Return the firmware version the manifest offers this panel.

        None when there is no manifest or its build variant does not match the
        panel's: a custom build must never be shown the universal release as an
        update (the HAUI Firmware entity reports no compatible release then).
        """
        if self._firmware_manifest is None:
            return None
        if not self._firmware_variant_compatible(self._firmware_manifest.get("variant")):
            return None
        return self._firmware_manifest["version"]

    def _firmware_install_due(self) -> bool:
        """Whether an automatic firmware install should be started now.

        Returns:
            bool: True when ``firmware_auto_update`` is on, no firmware was
            installed by hand, no install or TFT upload is in flight, the last
            attempt is more than ``FIRMWARE_RETRY_SECONDS`` ago and the
            manifest offers a newer firmware.
        """
        if not self.get("firmware_auto_update", False):
            return False
        if self._manual_firmware:
            return False
        if self._update_state == UPDATE_STATE_INSTALLING:
            return False  # never reboot the device mid TFT upload
        if self._firmware_installing:
            return False
        if self._firmware_install_at is not None:
            age = datetime.datetime.now(tz=datetime.UTC) - self._firmware_install_at
            if age.total_seconds() < FIRMWARE_RETRY_SECONDS:
                return False
        return self._firmware_update_available()

    def list_firmware_releases(self) -> dict[str, Any]:
        """List the GitHub releases whose firmware installs over the air, newest first.

        Only releases whose manifest's build variant matches the panel's are
        listed: a custom ``install.yaml`` build must never be handed the
        universal image by the picker.  A device that reports no variant (or a
        release whose manifest cannot be read / names no variant) is left out —
        the editor still offers the explicit **From URL** path for those.

        For the editor's firmware install picker.  Call via
        ``app.async_run_on_worker``.

        Returns:
            dict: ``releases`` (release tags) and ``error`` (why the release
            list could not be fetched, or None)
        """
        try:
            self._update_release_infos()
        except RuntimeError as exc:
            return {"releases": [], "error": str(exc)}
        device_variant = (self.app.device.device_info or {}).get("firmware_variant")
        releases = []
        if device_variant:
            for release in self._release_infos:
                version = self._try_parse_version(release.get("tag_name"))
                names = {asset.get("name") for asset in release.get("assets", [])}
                if version is None or {FIRMWARE_OTA_ASSET, FIRMWARE_MANIFEST_ASSET} > names:
                    continue
                manifest_url = next(
                    (
                        asset["browser_download_url"]
                        for asset in release.get("assets", [])
                        if asset.get("name") == FIRMWARE_MANIFEST_ASSET
                    ),
                    None,
                )
                if manifest_url is None:
                    continue
                try:
                    manifest = self._read_firmware_manifest(manifest_url)
                except RuntimeError:
                    continue  # unreadable manifest: fail closed for this release
                if manifest.get("variant") != device_variant:
                    continue
                releases.append((version, release["tag_name"]))
        releases.sort(reverse=True)
        return {"releases": [tag for _version, tag in releases], "error": None}

    def _release_firmware(self, version: str) -> tuple[str, str]:
        """Return the OTA image URL and md5 of the GitHub release ``version``.

        Only releases whose manifest's build variant matches the panel's are
        installable: an explicit release pick on a custom build must not flash
        the universal image either.

        Raises:
            RuntimeError: When the release, its manifest or its image is missing,
                or the release's build variant does not match the panel's
        """
        self._update_release_infos()
        release = self._find_release(version)
        if release is None:
            # The cache may predate the release, as for the TFT.
            self._update_release_infos(force=True)
            release = self._find_release(version)
        if release is None:
            raise RuntimeError(f"No GitHub release {version}")
        manifest_url = next(
            (
                asset["browser_download_url"]
                for asset in release.get("assets", [])
                if asset.get("name") == FIRMWARE_MANIFEST_ASSET
            ),
            None,
        )
        if manifest_url is None:
            raise RuntimeError(
                f"Release {version} ships no over-the-air firmware ({FIRMWARE_MANIFEST_ASSET})"
            )
        manifest = self._read_firmware_manifest(manifest_url)
        if not self._firmware_variant_compatible(manifest.get("variant")):
            raise RuntimeError(
                "Release {version} is a {variant} build but this panel runs {device}{tip}".format(
                    version=version,
                    variant=manifest.get("variant") or "unknown-variant",
                    device=(self.app.device.device_info or {}).get("firmware_variant")
                    or "an unknown build",
                    tip=(
                        "; the variants are not interchangeable"
                        if manifest.get("variant")
                        else "; its manifest names no variant"
                    ),
                )
            )
        return manifest["url"], manifest["md5"]

    def _url_firmware_md5(self, url: str) -> str:
        """Download the firmware image at ``url`` and return its md5.

        The device downloads the file itself; the hub reads it first for the
        md5 the flash action needs, and to refuse a factory image or a file
        that does not fit the app partition before the device touches it.

        Raises:
            RuntimeError: When the file cannot be read or is no app image
        """
        digest = hashlib.md5(usedforsecurity=False)
        size = 0
        first = b""
        try:
            with requests.get(url, timeout=30, stream=True) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(chunk_size=65536):
                    if not first:
                        first = chunk[:1]
                    size += len(chunk)
                    if size > FIRMWARE_MAX_BYTES:
                        raise RuntimeError(
                            f"{url} is larger than the {FIRMWARE_MAX_BYTES} byte app partition"
                        )
                    digest.update(chunk)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Could not download {url}: {exc}") from exc
        if first != bytes([ESP_IMAGE_MAGIC]):
            raise RuntimeError(
                f"{url} is no ESP32 app image; use the OTA image "
                f"({FIRMWARE_OTA_ASSET} or firmware.ota.bin), not the factory image"
            )
        return digest.hexdigest()

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
        published = self.app.controller["esphome"].esphome.publish(
            ESPAction.INSTALL_FIRMWARE_URL, {"url": url, "md5sum": md5}
        )
        if not published:
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

    def _firmware_install_timer_callback(self, kwargs: dict[str, Any]) -> None:
        self._firmware_install_timer = None
        if not self._firmware_installing:
            return
        self._firmware_installing = False
        self._firmware_install_error = (
            f"Firmware install of {self._firmware_install_version} did not finish: the panel "
            "did not reboot. See the device's ESPHome log for the download or flash error."
        )
        self.log(self._firmware_install_error, level="ERROR")
        self.publish_firmware_update()

    def _finish_firmware_install(self) -> None:
        """Check the firmware version the device reconnected with after an install.

        A release install names its version; when the device still reports
        another ``yaml_version``, the image was not flashed.  A URL install
        names no version and is taken as finished.
        """
        self._firmware_installing = False
        self._cancel_timer("_firmware_install_timer")
        label = self._firmware_install_version
        installed = (self.app.device.device_info or {}).get("yaml_version")
        if self._try_parse_version(label) is not None and not self._same_version(
            label, installed
        ):
            self._firmware_install_error = (
                f"Firmware install of {label} failed: the panel still runs {installed}"
            )
            self.log(self._firmware_install_error, level="ERROR")
            return
        self.log(f"Device reconnected after installing firmware {label}")

    def install_firmware(
        self, version: str | None = None, url: str | None = None
    ) -> dict[str, Any]:
        """Install the offered firmware, another release or the image at a URL.

        Without ``version`` and ``url`` it installs the firmware the manifest
        at ``firmware_manifest_url`` offers, when it is newer than the one the
        device runs; the manual install is not disabled by the
        ``firmware_auto_update`` setting.  ``version`` installs that manifest
        version, or else the GitHub release ``version`` (one with an
        over-the-air image, older ones included); ``url`` installs an OTA app
        image.  Installing anything but the manifest's firmware pauses the
        automatic firmware update until Home Assistant restarts or the offered
        update is installed.  Refuses to reboot during a TFT upload.

        Args:
            version (str | None): Version to install
            url (str | None): http(s) URL of an OTA app image

        Returns:
            dict: Current update status, with ``firmware_install_error`` set when
            the firmware install could not be started.
        """
        if not self.app.device.connected:
            self._firmware_install_error = "Device is disconnected"
            return self.get_update_state()
        if self._update_state == UPDATE_STATE_INSTALLING:
            self._firmware_install_error = "Cannot install firmware during a TFT upload"
            return self.get_update_state()
        if self._firmware_installing:
            return self.get_update_state()
        self._firmware_install_error = None
        if url is None:
            self._refresh_firmware_manifest()
            manifest = self._firmware_manifest
            if version is None:
                if manifest is None:
                    self._firmware_install_error = (
                        f"Could not read the firmware manifest {self.get('firmware_manifest_url')}"
                    )
                    return self.get_update_state()
                if not self._firmware_update_available():
                    self._firmware_install_error = (
                        self._firmware_variant_mismatch_reason()
                        or "No firmware update is available"
                    )
                    return self.get_update_state()
            if manifest is not None and (
                version is None or self._same_version(version, manifest["version"])
            ):
                return self._start_firmware_install(
                    manifest["url"], manifest["md5"], manifest["version"], manual=False
                )
        try:
            if url is not None:
                md5 = self._url_firmware_md5(url)
            elif version is not None:
                url, md5 = self._release_firmware(version)
            else:
                raise RuntimeError("Pass a version or a URL")
        except RuntimeError as exc:
            self._firmware_install_error = str(exc)
            self.log(f"Firmware install failed: {exc}", level="ERROR")
            return self.get_update_state()
        return self._start_firmware_install(url, md5, version or url, manual=True)

    def _notify_firmware_install(self, version: str | None) -> None:
        """Tell the user on the display that a firmware update is installing."""
        msg = self.translate(
            "A new firmware release is installing. The display updates after "
            "the device reboots."
        )
        msg += "\r\n\r\n"
        msg += self.translate("Version:")
        msg += f" {version}"
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon="mdi:package-down",
            title=self.translate("Firmware update"),
            notification=msg,
        )

    def publish_firmware_update(self) -> None:
        """Fire the firmware versions and install state for the "HAUI Firmware" entity."""
        self.app.fire_event(
            FIRMWARE_UPDATE_EVENT,
            {
                "device": self.app.device.get_name(),
                "connected": self.app.device.connected,
                "installed_version": (self.app.device.device_info or {}).get("yaml_version")
                or None,
                "latest_version": self._firmware_update_version(),
                "installing": self._firmware_installing,
            },
        )

    def run_update_display(self, version: str) -> dict[str, Any]:
        """Installs the TFT file of the GitHub release ``version`` on the display.

        Args:
            version (str): Release version, the firmware's ``yaml_version``

        Returns:
            dict: The update state after the attempt (``get_update_state()``);
            the caller can check ``state == UPDATE_STATE_ERROR`` and read
            ``last_error`` to report the outcome to the user.
        """
        self._set_update_state(UPDATE_STATE_CHECKING, version=version)
        try:
            self._update_release_infos()
            update_url = self._get_update_url(self._find_release(version))
            if update_url is None:
                # The shared cache can predate the release the firmware was
                # just updated to: a firmware install skips the release fetch,
                # so the TFT check after its reboot would miss the new release.
                self._update_release_infos(force=True)
                update_url = self._get_update_url(self._find_release(version))
        except RuntimeError as exc:
            self.log(f"TFT update failed: {exc}", level="ERROR")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=str(exc))
            return self.get_update_state()
        if update_url is None:
            msg = f"No GitHub release {version} with {self._get_tft_filename()}; TFT not updated"
            self.log(msg, level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, version=version, error=msg)
            return self.get_update_state()
        self.log(f"Installing TFT {version} from {update_url}")
        return self._start_tft_upload(update_url, version)

    def _start_tft_upload(self, url: str, version: str | None) -> dict[str, Any]:
        """Send the TFT at ``url`` to the device and track the install.

        Args:
            url (str): TFT file the device downloads and flashes
            version (str | None): Expected TFT version; None for a URL install

        Returns:
            dict: The update state after the attempt (``get_update_state()``)
        """
        published = self.app.controller["esphome"].esphome.publish(
            ESPAction.UPLOAD_TFT_URL, url
        )
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

        Installs the TFT of the GitHub release ``version``; when ``version`` is
        omitted the firmware's ``yaml_version`` (the version the firmware needs)
        is installed.  Another release, older ones included, is kept until the
        firmware's ``yaml_version`` changes (see ``_manual_tft_firmware``).  The
        update runs on the device worker, so this method must be called via
        ``app.async_run_on_worker``.

        Args:
            version (str | None): Release version to install

        Returns:
            dict: The update state after the attempt; ``state`` is
            ``UPDATE_STATE_ERROR`` when the install could not start (see
            ``last_error``).
        """
        if not self.app.device.connected:
            self.log("Cannot install the TFT while the device is disconnected", level="WARNING")
            self._set_update_state(UPDATE_STATE_ERROR, error="device disconnected")
            return self.get_update_state()
        required = (self.app.device.device_info or {}).get("yaml_version")
        if version is None:
            version = required
        if not version:
            self.log(
                "No yaml_version reported by the firmware; cannot install the TFT",
                level="WARNING",
            )
            self._set_update_state(UPDATE_STATE_ERROR, error="no yaml_version reported")
            return self.get_update_state()
        # A manual retry starts a fresh attempt: it must not be blocked by the
        # "install not confirmed" guard left over from a previous attempt.
        self._last_install_confirmed = False
        self._last_install_at = None
        result = self.run_update_display(version)
        if result["state"] == UPDATE_STATE_INSTALLING:
            matches = self._try_parse_version(version) == self._try_parse_version(required)
            self._manual_tft_firmware = None if matches else required
        return result

    def list_tft_releases(self) -> dict[str, Any]:
        """List the GitHub releases that ship this device's TFT, newest first.

        For the editor's TFT install picker.  Call via
        ``app.async_run_on_worker``.

        Returns:
            dict: ``releases`` (release tags), ``required`` (the firmware's
            ``yaml_version``) and ``error`` (why the release list could not be
            fetched, or None)
        """
        required = (self.app.device.device_info or {}).get("yaml_version")
        try:
            self._update_release_infos()
        except RuntimeError as exc:
            return {"releases": [], "required": required, "error": str(exc)}
        releases = []
        for release in self._release_infos:
            version = self._try_parse_version(release.get("tag_name"))
            if version is not None and self._get_update_url(release) is not None:
                releases.append((version, release["tag_name"]))
        releases.sort(reverse=True)
        tags = [tag for _version, tag in releases]
        return {"releases": tags, "required": required, "error": None}

    def install_tft_url(self, url: str) -> dict[str, Any]:
        """Install the TFT file at ``url`` instead of a GitHub release.

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
        self.publish_display_update()

    def publish_display_update(self) -> None:
        """Fire the TFT versions and update state for the "HAUI Display" entity."""
        device_info = self.app.device.device_info or {}
        self.app.fire_event(
            DISPLAY_UPDATE_EVENT,
            {
                "device": self.app.device.get_name(),
                "connected": self.app.device.connected,
                "installed_version": device_info.get("tft_version") or None,
                "latest_version": device_info.get("yaml_version") or None,
                "state": self._update_state,
                "last_error": self._update_last_error,
            },
        )

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
            "firmware_update_available": self._firmware_update_available(),
            "firmware_update_version": self._firmware_update_version(),
            "firmware_installing": self._firmware_installing,
            "firmware_install_error": self._firmware_install_error,
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
        elif installed_v < requested_v:
            return
        self._set_update_state(UPDATE_STATE_DONE, version=requested)
        self._last_install_confirmed = True
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")

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
        self._set_update_state(
            UPDATE_STATE_ERROR, version=self._last_install_version, error=message
        )
        self._cancel_timer("_install_verify_timer")
        self._cancel_timer("_install_timeout_timer")

    def _install_missing_tft(self, required_version: str, installed_version: str | None) -> None:
        """Install the required TFT automatically, or ask when ``auto_install`` is off."""
        if self._manual_tft_firmware == required_version:
            self.log(
                f"Keeping the TFT installed by hand ({installed_version!r}) until the "
                f"firmware changes from {required_version}"
            )
            return
        if self._firmware_installing:
            # A firmware install reboots the device; a TFT upload now would be
            # cut off mid-transfer.  The version check runs again after the
            # reconnect, when the new firmware's yaml_version decides the TFT.
            self.log("Firmware update in flight; TFT install deferred until it finishes")
            return
        if self.get("auto_install", True):
            self.log(
                f"TFT {installed_version!r} is older than {required_version}, installing"
            )
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
        self._evaluate_installed_version(
            self.app.device.device_info or {}, refresh_answered=False
        )

    def _evaluate_installed_version(
        self, device_info: dict[str, Any], refresh_answered: bool = True
    ) -> None:
        """Decide whether the TFT needs an install based on ``device_info``.

        ``refresh_answered`` is False when the state refresh timed out.  A
        lost response is fail-safe: an *unknown* installed version is then
        never auto-installed, because the display may simply still be reading
        it.  Known versions are evaluated either way.
        """
        required_version = device_info.get("yaml_version")
        installed_version = device_info.get("tft_version")
        required = self._try_parse_version(required_version)
        if required is None or not isinstance(required_version, str):
            msg = f"invalid yaml_version {required_version!r}"
            self.log(
                "The firmware reported an invalid yaml_version; TFT not checked",
                level="WARNING",
            )
            self._set_update_state(
                UPDATE_STATE_ERROR, version=self._update_version, error=msg
            )
            return
        installed = self._try_parse_version(installed_version)
        if not refresh_answered and installed is None:
            self.log(
                "Could not read the installed TFT version (no device-state answer); "
                "not installing",
                level="WARNING",
            )
            return
        if installed is not None:
            self.log(
                f"Checking installed version: required={required_version} "
                f"installed={installed_version}"
            )
            if installed >= required:
                self.log("Installed TFT version is up to date")
                self._mark_done_if_installed()
                self._last_install_confirmed = True
                self._cancel_timer("_install_verify_timer")
                self._cancel_timer("_install_timeout_timer")
                return
            if self._recent_unconfirmed_install(required_version):
                self._set_install_failed(
                    "TFT install was not confirmed; press Install TFT to retry "
                    "(auto-reinstall is disabled while unconfirmed)"
                )
                return
            self._install_missing_tft(required_version, installed_version)
            return
        # The refresh answered but the display still has no version.
        if self._install_verify_timer is not None:
            # A reconnect right after an install: the bounded verification
            # window owns the outcome.  Re-read once more instead of guessing.
            self.log(
                "TFT version still unknown after reconnect; verifying the install"
            )
            self._request_device_state()
            return
        if self._recent_unconfirmed_install(required_version):
            self._set_install_failed(
                "TFT install was not confirmed; press Install TFT to retry "
                "(auto-reinstall is disabled while unconfirmed)"
            )
            return
        self.log(f"TFT version unknown, installing {required_version}")
        self._install_missing_tft(required_version, installed_version)

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
        """Updates the TFT when it is older than the version the firmware needs.

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
        required_version = device_info.get("yaml_version")
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

    def manual_check_for_update(self) -> dict[str, Any]:
        """Trigger a user-initiated update check from the editor.

        A manual retry must not be suppressed by leftover failure state from an
        earlier install attempt, and it should bypass the hub-level release
        cache so the user gets a fresh GitHub answer.  It also runs the TFT
        version check, which otherwise only runs after a connect, so an
        outdated TFT is installed (or, with ``auto_install`` off, offered).
        Runs on the device worker, so call via ``app.async_run_on_worker``.

        Returns:
            dict: The check result, see ``check_for_update``.
        """
        if not self.app.device.connected:
            self.log("Cannot check for updates while the device is disconnected", level="WARNING")
            return {
                **self.get_update_state(),
                "latest_release": None,
                "check_error": "device disconnected",
            }
        # A running upload keeps its bookkeeping: resetting it would let the
        # TFT check below start a second upload on top of it.
        installing = self._update_state == UPDATE_STATE_INSTALLING
        if not installing:
            self._last_install_at = None
            self._last_install_confirmed = False
            if self._update_state == UPDATE_STATE_ERROR:
                self._update_last_error = None
                self._set_update_state(UPDATE_STATE_IDLE)
        result = self.check_for_update(force_refresh=True)
        if not installing:
            self.check_installed_version()
            result.update(self.get_update_state())
        return result

    def check_for_update(self, force_refresh: bool = False) -> dict[str, Any]:
        """Check the firmware manifest and the latest TFT release independently.

        Returns:
            dict: ``get_update_state()`` plus ``latest_release`` (tag of the
            newest GitHub release, None when the release check did not run)
            and ``check_error`` (why the GitHub release check failed, or None).
        """
        # Firmware availability comes from the firmware manifest, not from the
        # TFT version. Check it first: a panel can have the newest TFT and
        # still need a newer ESPHome firmware release.
        self._refresh_firmware_manifest()
        manifest = self._firmware_manifest
        if manifest is not None and self._firmware_install_due():
            state = self._start_firmware_install(
                manifest["url"], manifest["md5"], manifest["version"], manual=False
            )
            if state["firmware_installing"]:
                return {**state, "latest_release": None, "check_error": None}

        try:
            self._update_release_infos(force=force_refresh)
        except RuntimeError as exc:
            # A GitHub API failure must not interfere with the independent
            # firmware manifest check above.
            self.log(f"Update check failed: {exc}", level="WARNING")
            return {**self.get_update_state(), "latest_release": None, "check_error": str(exc)}
        latest_release = self._get_latest_release()
        result = {
            **self.get_update_state(),
            "latest_release": latest_release["tag_name"] if latest_release else None,
            "check_error": None,
        }
        if not self._is_update_available() or latest_release is None:
            return result

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
        return result

    # callback

    def on_connection_changed(self, connected: bool) -> None:
        """Schedules the TFT check on connect and cancels it on disconnect.

        Called by the app once the connection handshake is complete, so the
        device info holds ``tft_version`` and ``yaml_version``.

        A disconnect while ``installing`` is expected — the upload ends in a
        reboot — so that state is kept (the install timeout started at install
        time covers the case where the device never reconnects; the bounded
        verification window on reconnect covers the upload-completed case).

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
            self.log(f"Checking the TFT version in {self.get('on_connect_delay')} seconds")
            self._start_timer_delay()
            if self._update_state == UPDATE_STATE_INSTALLING:
                self._start_install_verification()
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
            if self._pending_state_check:
                # A version-check refresh answered: evaluate with the fresh
                # snapshot instead of the (possibly empty) boot handshake one.
                self._pending_state_check = False
                self._cancel_timer("_state_check_timer")
                self._evaluate_installed_version(self.app.device.device_info or {})
            self._mark_done_if_installed()

        if event.name in (ESPResponse.RES_DEVICE_INFO, ESPResponse.RES_DEVICE_STATE):
            self.publish_display_update()
            self.publish_firmware_update()

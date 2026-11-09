"""Fetch and resolve firmware artifacts without controller state.

Everything here is blocking I/O or pure parsing: the update controller hands
it to the adapter's I/O pool (``app.submit_off_worker``) and applies the
result back on its device worker.  The GitHub release catalog is the one piece
of shared state, cached at module level for every device's controller.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any, TypedDict
from urllib.parse import urljoin

import requests
from packaging.version import InvalidVersion, Version, parse

from ..mapping.const import FIRMWARE_MANIFEST_URL, FirmwareUpdateChannel

# hard-coded url for haui releases on github; a page holds every release
RELEASES_URL = "https://api.github.com/repos/happydasch/nspanel_haui/releases?per_page=100"
# A release can be flashed over the air when it ships the OTA app image and the
# manifest holding its md5; ``nspanel_haui.bin`` is the full factory image,
# which an over-the-air update must never write.
FIRMWARE_OTA_ASSET = "nspanel_haui_ota.bin"
FIRMWARE_MANIFEST_ASSET = "firmware-manifest.json"
# App partition size of the shipped partition table, and the first byte of an
# ESP32 app image (a factory image starts with 0xFF padding instead).
FIRMWARE_MAX_BYTES = 0x1C0000
ESP_IMAGE_MAGIC = 0xE9
# The release catalog is identical for every device; without a shared cache a
# hub with N devices spends N unauthenticated requests per interval against
# GitHub's 60 requests/hour/IP limit.  A manual check bypasses the TTL.
RELEASE_CACHE_TTL_SECONDS = 60 * 60

_release_cache: tuple[float, list[dict[str, Any]]] | None = None
# Controllers fetch from separate worker threads, so the cache check + fetch is
# serialized: the first controller fetches and the rest reuse its result.
_release_cache_lock = threading.Lock()


class FirmwareManifestInfo(TypedDict):
    """A validated firmware manifest, resolved for one display model."""

    version: str
    url: str
    md5: str
    variant: str
    # Empty when the manifest ships no TFT for the display model.
    tft_version: str
    tft_url: str


class UpdateFetchInputs(TypedDict):
    """Everything one update check fetched; each ``*_error`` explains a missing part."""

    releases: list[dict[str, Any]]
    release_error: str | None
    # Set when a failed refresh fell back to the cached catalog.
    release_warning: str | None
    manifest_url: str | None
    manifest: Any
    manifest_error: str | None
    tft_manifest: FirmwareManifestInfo | None
    tft_manifest_url: str | None
    tft_manifest_error: str | None


@dataclass(frozen=True, slots=True)
class ReleaseCatalog:
    releases: list[dict[str, Any]]
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateFetchRequest:
    manifest_override: str
    channel: str
    force: bool
    include_releases: bool = True
    include_tft_source: bool = False
    firmware_version: str | None = None
    required_tft_version: str | None = None
    display_model: str | None = None


@dataclass(frozen=True, slots=True)
class FirmwareInstallRequest:
    version: str | None
    url: str | None
    manifest_override: str
    channel: str


def fetch_json(url: str, timeout: float) -> Any:
    """GET ``url`` and decode its JSON body.

    Raises:
        requests.exceptions.RequestException: On a network/HTTP failure.
        ValueError: When the body is not JSON (GitHub rate-limit pages are HTML).
    """
    return requests.get(url, timeout=timeout).json()


def parse_version(value: Any) -> Version | None:
    """Parse ``value`` as a version; None for an empty, non-string or invalid value."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return parse(value)
    except InvalidVersion:
        return None


def same_version(first: Any, second: Any) -> bool:
    """Whether two version strings name the same version (``v`` prefix ignored)."""
    first_version = parse_version(first)
    return first_version is not None and first_version == parse_version(second)


def manifest_asset_url(release: dict[str, Any]) -> str | None:
    """Return the download URL of the firmware manifest a release ships, if any."""
    for asset in release.get("assets", []):
        if asset.get("name") == FIRMWARE_MANIFEST_ASSET:
            url = asset.get("browser_download_url")
            return url if isinstance(url, str) and url else None
    return None


def latest_release(
    releases: list[dict[str, Any]], channel: str, asset: str | None = None
) -> dict[str, Any] | None:
    """Return the newest release the update ``channel`` follows.

    Stable excludes GitHub-marked prereleases and prerelease version tags; the
    dev channel considers them.  Releases whose tag does not parse as a version
    are skipped, so an odd tag can neither break the comparison nor surface as
    ``0.0.0``.

    Args:
        releases: The release catalog
        channel: A ``FirmwareUpdateChannel`` value
        asset: Only consider releases that ship an asset of this name
    """
    newest: tuple[Version, dict[str, Any]] | None = None
    for release in releases:
        version = parse_version(release.get("tag_name"))
        if version is None:
            continue
        if channel != FirmwareUpdateChannel.DEV and (
            release.get("prerelease") or version.is_prerelease
        ):
            continue
        if asset is not None and not any(
            item.get("name") == asset for item in release.get("assets", [])
        ):
            continue
        if newest is None or version > newest[0]:
            newest = (version, release)
    return newest[1] if newest else None


def find_release(releases: list[dict[str, Any]], version: str) -> dict[str, Any] | None:
    """Return the release whose tag names ``version`` (``v`` prefix ignored)."""
    wanted = parse_version(version)
    if wanted is None:
        return None
    return next(
        (release for release in releases if parse_version(release.get("tag_name")) == wanted),
        None,
    )


def fetch_release_catalog(force: bool = False) -> ReleaseCatalog:
    """Fetch the shared release catalog, using stale data when a refresh fails.

    Raises:
        requests.exceptions.RequestException: When the fetch fails and nothing is cached.
        ValueError: When GitHub answers with no JSON and nothing is cached.
    """
    global _release_cache
    with _release_cache_lock:
        if not force and _release_cache is not None:
            cached_at, cached_releases = _release_cache
            if time.monotonic() - cached_at < RELEASE_CACHE_TTL_SECONDS:
                return ReleaseCatalog(cached_releases)

        try:
            releases = fetch_json(RELEASES_URL, 5)
        except requests.exceptions.RequestException as exc:
            if _release_cache is not None:
                return ReleaseCatalog(
                    _release_cache[1],
                    f"Release info fetch failed ({exc}); using cached release info",
                )
            raise
        except ValueError:
            if _release_cache is not None:
                return ReleaseCatalog(
                    _release_cache[1],
                    "GitHub returned a non-JSON response; using cached release info",
                )
            raise

        if not isinstance(releases, list):
            # Rate-limit errors come back as a JSON object, not a list.  Stale
            # data beats caching a failure for an hour.
            if _release_cache is not None:
                return ReleaseCatalog(
                    _release_cache[1],
                    "Unexpected response from GitHub API; using cached release info",
                )
            return ReleaseCatalog([], "Unexpected response from GitHub API")

        _release_cache = (time.monotonic(), releases)
        return ReleaseCatalog(releases)


def _load_catalog(force: bool) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Return the release catalog, the error that left it empty, and a stale-cache warning."""
    try:
        catalog = fetch_release_catalog(force)
    except (requests.exceptions.RequestException, ValueError) as exc:
        return [], f"Failed to fetch release info: {exc}", None
    return catalog.releases, None, catalog.warning


def parse_firmware_manifest(
    manifest: Any, url: str, display_model: str | None
) -> FirmwareManifestInfo:
    """Validate decoded manifest data and resolve its artifacts for ``display_model``.

    Paths resolve against ``url``.  The TFT is the ``tft.assets`` entry of the
    display model (``eu`` for an unknown model); without one the TFT fields
    stay empty.

    Raises:
        RuntimeError: When the manifest lacks its OTA build
    """
    try:
        ota = manifest["builds"][0]["ota"]
        info: FirmwareManifestInfo = {
            "version": str(manifest["version"]),
            "url": urljoin(url, ota["path"]),
            "md5": ota["md5"],
            "variant": str(manifest.get("variant") or ""),
            "tft_version": "",
            "tft_url": "",
        }
        tft = manifest.get("tft")
        if isinstance(tft, dict):
            assets = tft.get("assets")
            asset = None
            if isinstance(assets, dict):
                model = str(display_model or "").lower()
                if model not in ("eu", "us"):
                    model = "eu"
                asset = assets.get(model)
            tft_path: Any = asset.get("path") if isinstance(asset, dict) else asset
            if isinstance(tft_path, str) and tft_path:
                info["tft_url"] = urljoin(url, tft_path)
                tft_version = tft.get("version")
                if isinstance(tft_version, str) and tft_version:
                    info["tft_version"] = tft_version
        return info
    except (LookupError, TypeError) as exc:
        raise RuntimeError(f"Could not read the firmware manifest {url}: {exc}") from exc


def _installed_firmware_tft_manifest(
    releases: list[dict[str, Any]],
    firmware_version: str | None,
    required_tft_version: str,
    display_model: str | None,
) -> tuple[FirmwareManifestInfo | None, str | None, str | None]:
    """Find the installed firmware's manifest when the update channel lacks its TFT.

    The selected channel may point at a newer/stable manifest that does not
    carry the TFT an installed dev firmware requires; the release named like
    ``yaml_version`` is then the TFT source.  Its build variant does not
    matter: a release ships only the universal image, but the TFT is the same
    for a custom build.

    Returns:
        The manifest, its URL, and why it cannot serve the TFT (each may be None)
    """
    release = find_release(releases, firmware_version) if firmware_version else None
    manifest_url = manifest_asset_url(release) if release is not None else None
    if manifest_url is None:
        return None, None, None
    try:
        info = parse_firmware_manifest(fetch_json(manifest_url, 10), manifest_url, display_model)
    except (requests.exceptions.RequestException, ValueError, RuntimeError) as exc:
        return None, manifest_url, str(exc)
    if not same_version(info["version"], firmware_version):
        return None, manifest_url, "installed firmware manifest names a different version"
    if not same_version(info["tft_version"], required_tft_version):
        return None, manifest_url, None
    return info, manifest_url, None


def _channel_manifest_url(
    request: UpdateFetchRequest, releases: list[dict[str, Any]], release_error: str | None
) -> tuple[str | None, str | None]:
    """Return the manifest URL the device follows, or why there is none.

    ``manifest_override`` wins unless it is the shipped default (the stable
    channel's URL).  The dev channel has no fixed URL: it follows the newest
    release in the catalog that ships a manifest, dev prereleases included.
    """
    explicit = request.manifest_override.strip()
    if explicit and explicit != FIRMWARE_MANIFEST_URL:
        return explicit, None
    if request.channel != FirmwareUpdateChannel.DEV:
        return FIRMWARE_MANIFEST_URL, None
    if release_error:
        return None, release_error
    release = latest_release(releases, request.channel, FIRMWARE_MANIFEST_ASSET)
    url = manifest_asset_url(release) if release is not None else None
    if url is None:
        return None, f"No GitHub release ships a {FIRMWARE_MANIFEST_ASSET}"
    return url, None


def failed_update_inputs(message: str) -> UpdateFetchInputs:
    """Return the inputs of a check whose whole fetch stage failed with ``message``."""
    return {
        "releases": [],
        "release_error": message,
        "release_warning": None,
        "manifest_url": None,
        "manifest": None,
        "manifest_error": message,
        "tft_manifest": None,
        "tft_manifest_url": None,
        "tft_manifest_error": message,
    }


def fetch_update_inputs(request: UpdateFetchRequest) -> UpdateFetchInputs:
    """Fetch the release catalog and the manifests one update check needs."""
    releases: list[dict[str, Any]] = []
    release_error: str | None = None
    release_warning: str | None = None
    if request.include_releases or request.channel == FirmwareUpdateChannel.DEV:
        releases, release_error, release_warning = _load_catalog(request.force)

    manifest_url, manifest_error = _channel_manifest_url(request, releases, release_error)
    manifest: Any = None
    if manifest_url is not None:
        try:
            manifest = fetch_json(manifest_url, 10)
        except (requests.exceptions.RequestException, ValueError) as exc:
            manifest_error = f"Could not read the firmware manifest {manifest_url}: {exc}"

    tft_manifest: FirmwareManifestInfo | None = None
    tft_manifest_url: str | None = None
    tft_manifest_error: str | None = None
    if isinstance(manifest, dict) and manifest_url:
        try:
            tft_manifest = parse_firmware_manifest(manifest, manifest_url, request.display_model)
            tft_manifest_url = manifest_url
        except RuntimeError as exc:
            tft_manifest_error = str(exc)

    required = request.required_tft_version
    serves_required = (
        tft_manifest is not None
        and bool(tft_manifest["tft_url"])
        and same_version(tft_manifest["tft_version"], required)
    )
    if request.include_tft_source and required and not serves_required:
        if not releases:
            releases, catalog_error, release_warning = _load_catalog(request.force)
            release_error = release_error or catalog_error
        fallback, fallback_url, fallback_error = _installed_firmware_tft_manifest(
            releases, request.firmware_version, required, request.display_model
        )
        if fallback is not None:
            tft_manifest, tft_manifest_url, tft_manifest_error = fallback, fallback_url, None
        elif fallback_error:
            tft_manifest_error = fallback_error

    return {
        "releases": releases,
        "release_error": release_error,
        "release_warning": release_warning,
        "manifest_url": manifest_url,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "tft_manifest": tft_manifest,
        "tft_manifest_url": tft_manifest_url,
        "tft_manifest_error": tft_manifest_error,
    }


def fetch_firmware_release_candidates(device_variant: str | None) -> dict[str, Any]:
    """List the releases this device's build variant can flash over the air, newest first.

    A release qualifies when it ships the OTA image and a manifest naming the
    device's variant; an unreadable manifest leaves its release out.  A device
    that reports no variant gets none (the editor keeps the From URL path).

    Raises:
        RuntimeError: When the release catalog cannot be fetched
    """
    if not device_variant:
        return {"releases": [], "error": None}
    try:
        releases = fetch_release_catalog().releases
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise RuntimeError(f"Failed to fetch release info: {exc}") from exc

    versions: list[tuple[Version, str]] = []
    for release in releases:
        version = parse_version(release.get("tag_name"))
        manifest_url = manifest_asset_url(release)
        names = {asset.get("name") for asset in release.get("assets", [])}
        if version is None or manifest_url is None or FIRMWARE_OTA_ASSET not in names:
            continue
        try:
            manifest = parse_firmware_manifest(fetch_json(manifest_url, 10), manifest_url, None)
        except requests.exceptions.RequestException, RuntimeError, ValueError:
            continue
        if manifest["variant"] == device_variant:
            versions.append((version, release["tag_name"]))
    versions.sort(reverse=True)
    return {"releases": [tag for _version, tag in versions], "error": None}


def download_image_md5(url: str) -> str:
    """Download the OTA image at ``url`` and return its md5.

    The device downloads the file itself; the hub reads it first for the md5
    the flash action needs, and to refuse a factory image or a file that does
    not fit the app partition before the device touches it.

    Raises:
        RuntimeError: When the file cannot be read or is no app image
    """
    digest = hashlib.md5(usedforsecurity=False)
    size = 0
    first = b""
    try:
        with requests.get(url, timeout=30, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=65536):
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


def fetch_firmware_install_inputs(request: FirmwareInstallRequest) -> dict[str, Any]:
    """Resolve what a firmware install flashes.

    Returns:
        ``{"error"}`` when nothing can be installed; ``{"url", "md5",
        "version"}`` for a URL install (the image was checked); otherwise
        ``{"manifest", "manifest_url", "offered"}``, where ``offered`` tells
        the channel's manifest apart from another release's.
    """
    if request.url is not None:
        try:
            md5 = download_image_md5(request.url)
        except RuntimeError as exc:
            return {"error": str(exc)}
        return {"url": request.url, "md5": md5, "version": request.version or request.url}

    # The catalog is only needed for another release (or to resolve the dev
    # channel), so the offered firmware installs without a GitHub request.
    inputs = fetch_update_inputs(
        UpdateFetchRequest(
            manifest_override=request.manifest_override,
            channel=request.channel,
            force=True,
            include_releases=False,
        )
    )
    manifest, manifest_url = inputs["manifest"], inputs["manifest_url"]
    if manifest is None or manifest_url is None:
        return {
            "error": inputs["manifest_error"]
            or inputs["release_error"]
            or "Firmware manifest unavailable"
        }
    offered_version = manifest.get("version") if isinstance(manifest, dict) else None
    if request.version is None or same_version(request.version, offered_version):
        return {"manifest": manifest, "manifest_url": manifest_url, "offered": True}

    releases, release_error = inputs["releases"], inputs["release_error"]
    if not releases and release_error is None:
        releases, release_error, _warning = _load_catalog(True)
    release = find_release(releases, request.version)
    if release is None:
        return {"error": release_error or f"No GitHub release {request.version}"}
    release_manifest_url = manifest_asset_url(release)
    if release_manifest_url is None:
        return {
            "error": (
                f"Release {request.version} ships no over-the-air firmware "
                f"({FIRMWARE_MANIFEST_ASSET})"
            )
        }
    try:
        release_manifest = fetch_json(release_manifest_url, 10)
    except (requests.exceptions.RequestException, ValueError) as exc:
        return {"error": f"Could not read the firmware manifest {release_manifest_url}: {exc}"}
    return {"manifest": release_manifest, "manifest_url": release_manifest_url, "offered": False}

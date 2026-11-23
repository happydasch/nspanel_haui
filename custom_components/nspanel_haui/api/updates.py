"""TFT and firmware updates: installs, local uploads, release lists and update checks.

Every install runs through the device's update controller
(``NSPanelHAUI.async_install_tft`` / ``async_install_firmware``), which fetches
manifests and images off the device worker.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..const import DOMAIN
from ..haui.controller.release_source import ESP_IMAGE_MAGIC, FIRMWARE_MAX_BYTES
from ..hub.storage import empty_store, panel_store
from ..update_url import tft_url_problem
from .common import (
    ALL_DEVICES,
    ApiError,
    api_errors,
    body_device,
    device_app,
    for_each_app,
    json_object,
    query_device,
    running_apps,
    running_device_app,
    text_field,
)
from .panel_edits import edit_panels

_LOGGER = logging.getLogger(__name__)

_UPDATE_UPLOAD_TTL = 60 * 60
_TFT_UPLOAD_MAX_BYTES = 16 * 1024 * 1024
_UPLOAD_MAX_BYTES = {"tft": _TFT_UPLOAD_MAX_BYTES, "firmware": FIRMWARE_MAX_BYTES}
_STAGED_UPLOAD_MAX_BYTES = 64 * 1024 * 1024
_STAGED_UPLOAD_MAX_COUNT = 16
_UPLOADS_KEY = f"{DOMAIN}_update_uploads"

# Starts an install on one app: ``(app, version, url) -> update state``.
_StartInstall = Callable[[Any, str | None, str | None], Awaitable[Any]]


@dataclass(slots=True)
class _StagedUpdate:
    content: bytes
    expires_at: float


def _staged_updates(hass: Any) -> dict[str, _StagedUpdate]:
    """Return the in-memory, bounded-lifetime update artifact registry."""
    return hass.data.setdefault(_UPLOADS_KEY, {})


def _prune_staged_updates(artifacts: dict[str, _StagedUpdate]) -> None:
    now = time.monotonic()
    for token, artifact in tuple(artifacts.items()):
        if artifact.expires_at <= now:
            del artifacts[token]


async def _expire_staged_update(hass: Any, token: str, expires_at: float) -> None:
    """Release staged bytes even if no later API request arrives."""
    await asyncio.sleep(max(0, expires_at - time.monotonic()))
    artifact = _staged_updates(hass).get(token)
    if artifact is not None and artifact.expires_at == expires_at:
        del _staged_updates(hass)[token]


def _stage_update(hass: Any, image: bytes) -> str:
    """Keep ``image`` for ``_UPDATE_UPLOAD_TTL`` seconds and return its download token.

    Raises:
        ApiError: When the staging area is full
    """
    artifacts = _staged_updates(hass)
    _prune_staged_updates(artifacts)
    total_bytes = sum(len(artifact.content) for artifact in artifacts.values())
    if (
        len(artifacts) >= _STAGED_UPLOAD_MAX_COUNT
        or total_bytes + len(image) > _STAGED_UPLOAD_MAX_BYTES
    ):
        raise ApiError("Too many update files are currently staged; try again shortly", 429)
    token = secrets.token_urlsafe(32)
    expires_at = time.monotonic() + _UPDATE_UPLOAD_TTL
    artifacts[token] = _StagedUpdate(image, expires_at)
    hass.async_create_task(_expire_staged_update(hass, token, expires_at))
    return token


def _artifact_base_url(hass: Any) -> str | None:
    """Use only Home Assistant's configured internal URL for device downloads."""
    value = getattr(hass.config, "internal_url", None)
    if not isinstance(value, str) or not value:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return None
    return value.rstrip("/")


def _validate_update_artifact(kind: str, filename: str, content: bytes) -> str | None:
    """Return why a local update image cannot be installed, or None when it can."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    suffix = name.rpartition(".")[2].lower() if "." in name else ""
    if kind == "tft":
        if suffix != "tft":
            return "The display file must have a .tft extension"
        if len(content) < 16 or not content.startswith(b"\x00\x01DN2E"):
            return "The file is not a valid Nextion TFT image"
    else:
        if suffix != "bin":
            return "The firmware file must have a .bin extension"
        if not content or content[0] != ESP_IMAGE_MAGIC:
            return "The firmware file is not an ESPHome OTA app image"
    return None


async def _read_upload(request: Any, max_bytes: int) -> bytes:
    """Read the uploaded file, refusing it as soon as it exceeds ``max_bytes``.

    Raises:
        ApiError: When the file is too large
    """
    if request.content_length is not None and request.content_length > max_bytes:
        raise ApiError("The uploaded file exceeds the device limit", 413)
    content = bytearray()
    async for chunk in request.content.iter_chunked(64 * 1024):
        if len(content) + len(chunk) > max_bytes:
            raise ApiError("The uploaded file exceeds the device limit", 413)
        content.extend(chunk)
    return bytes(content)


def _tft_install_error(result: Any) -> str | None:
    """Return why a TFT install did not start, or None when it started.

    Only the state counts: ``last_error`` survives from an earlier attempt.
    """
    if isinstance(result, dict) and result.get("state") == "error":
        return result.get("last_error") or "TFT update failed"
    return None


def _firmware_install_error(result: Any) -> str | None:
    """Return why a firmware install did not start, or None when it started."""
    return result.get("firmware_install_error") if isinstance(result, dict) else None


async def _start_tft_install(app: Any, version: str | None, url: str | None) -> Any:
    return await app.async_install_tft(version, url)


async def _start_firmware_install(app: Any, version: str | None, url: str | None) -> Any:
    return await app.async_install_firmware(version, url)


@dataclass(frozen=True, slots=True)
class _InstallRequest:
    device: str
    version: str | None
    url: str | None


def _install_request(body: dict[str, Any], what: str) -> _InstallRequest:
    """Read ``device``, ``version`` and ``url`` of an install request body.

    Raises:
        ApiError: When a version and a URL are both given, a URL install
            addresses every device, or the URL is no http(s) URL
    """
    install = _InstallRequest(
        device=body_device(body),
        version=text_field(body.get("version"), "version") or None,
        url=text_field(body.get("url"), "url") or None,
    )
    if install.url is not None:
        if install.version is not None:
            raise ApiError("Pass either a version or a URL, not both", 400)
        if install.device == ALL_DEVICES:
            raise ApiError("A URL install needs a single device", 400)
        if not install.url.startswith(("http://", "https://")):
            raise ApiError(f"The {what} URL must start with http:// or https://", 400)
    return install


async def _install(
    view: HomeAssistantView,
    apps: dict[str, Any],
    install: _InstallRequest,
    action: str,
    start: _StartInstall,
    install_error: Callable[[Any], str | None],
) -> web.Response:
    """Start an install on one device or on every device and build the response.

    A single device answers 502 with the controller's reason when the install
    could not start (disconnected, nothing to install, unreadable manifest)
    instead of a success that never installs anything.
    """
    if install.device != ALL_DEVICES:
        app = device_app(apps, install.device)
        result = await start(app, install.version, install.url)
        message = install_error(result)
        if message:
            raise ApiError(message, 502)
        return view.json({"status": "ok", "devices_updated": [install.device], "update": result})

    async def run(name: str, app: Any) -> str | None:
        message = install_error(await start(app, install.version, None))
        if message:
            _LOGGER.warning("Could not %s on device '%s': %s", action, name, message)
        return message

    updated, failed = await for_each_app(apps, action, run)
    return view.json({"status": "ok", "devices_updated": updated, "failed": failed})


class DeviceUpdateUploadView(HomeAssistantView):
    """Accept a local update image and immediately hand its staged URL to the device."""

    url = "/api/nspanel_haui/update_upload/{entry_id}/{kind}"
    name = "api:nspanel_haui:update_upload"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str, kind: str) -> web.Response:
        """Stream, validate, stage, and install one local TFT or firmware image."""
        if kind not in _UPLOAD_MAX_BYTES:
            raise ApiError("Update type must be tft or firmware", 400)
        device_name = query_device(request)
        if not device_name or device_name == ALL_DEVICES:
            raise ApiError("A local file install needs a single device", 400)
        hass = request.app["hass"]
        app = running_device_app(hass, entry_id, device_name)
        base_url = _artifact_base_url(hass)
        if base_url is None:
            raise ApiError(
                "Set Home Assistant's internal URL to an address reachable by the NSPanel", 400
            )

        image = await _read_upload(request, _UPLOAD_MAX_BYTES[kind])
        validation_error = _validate_update_artifact(kind, request.query.get("filename", ""), image)
        if validation_error:
            raise ApiError(validation_error, 400)

        token = _stage_update(hass, image)
        download_url = f"{base_url}/api/nspanel_haui/update_artifact/{token}"
        start, install_error = (
            (_start_tft_install, _tft_install_error)
            if kind == "tft"
            else (_start_firmware_install, _firmware_install_error)
        )
        try:
            result = await start(app, None, download_url)
        except Exception as exc:
            _staged_updates(hass).pop(token, None)
            _LOGGER.exception("Failed to start uploaded %s update for '%s'", kind, device_name)
            raise ApiError(str(exc) or f"Failed to start {kind} update", 502) from exc
        update_error = install_error(result)
        if update_error:
            _staged_updates(hass).pop(token, None)
            raise ApiError(update_error, 502)

        return self.json({"status": "ok", "devices_updated": [device_name], "update": result})


class DeviceUpdateArtifactView(HomeAssistantView):
    """Serve a short-lived staged update image to HA and the NSPanel device."""

    url = "/api/nspanel_haui/update_artifact/{token}"
    name = "api:nspanel_haui:update_artifact"
    requires_auth = False

    def _artifact(self, request: web.Request) -> _StagedUpdate | None:
        hass = request.app["hass"]
        artifacts = _staged_updates(hass)
        _prune_staged_updates(artifacts)
        return artifacts.get(request.match_info["token"])

    @staticmethod
    def _unsatisfiable(size: int) -> web.Response:
        return web.Response(status=416, headers={"Content-Range": f"bytes */{size}"})

    def _response(
        self, request: web.Request, artifact: _StagedUpdate, *, head: bool = False
    ) -> web.Response:
        content = artifact.content
        size = len(content)
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Content-Type": "application/octet-stream",
        }
        range_header = request.headers.get("Range")
        status = 200
        start, end = 0, size - 1
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match or not any(match.groups()):
                return self._unsatisfiable(size)
            first, last = match.groups()
            if not first:
                suffix_length = int(last)
                if suffix_length <= 0:
                    return self._unsatisfiable(size)
                start = max(0, size - suffix_length)
            else:
                start = int(first)
                if last:
                    end = min(int(last), size - 1)
            if start >= size or start > end:
                return self._unsatisfiable(size)
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"

        headers["Content-Length"] = str(end - start + 1)
        body = b"" if head else content[start : end + 1]
        return web.Response(status=status, headers=headers, body=body)

    async def get(self, request: web.Request, token: str) -> web.Response:
        """Return the complete image or the requested byte range."""
        artifact = self._artifact(request)
        if artifact is None:
            return web.Response(status=404)
        return self._response(request, artifact)

    async def head(self, request: web.Request, token: str) -> web.Response:
        """Return image headers for clients that probe before downloading."""
        artifact = self._artifact(request)
        if artifact is None:
            return web.Response(status=404)
        return self._response(request, artifact, head=True)


class DeviceUpdateTftView(HomeAssistantView):
    """Install the TFT of one device or of every device."""

    url = "/api/nspanel_haui/update_tft/{entry_id}"
    name = "api:nspanel_haui:update_tft"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Install the TFT of one device, or of every device, from the firmware manifest.

        The body's optional ``device`` defaults to ``*``. An optional
        ``version`` names the TFT other than the manifest's default, and an
        optional ``url`` (single device only) installs that image instead.
        """
        install = _install_request(await json_object(request), "TFT")
        if install.url is not None:
            # A URL the panel cannot install is refused before the long
            # transfer; a local upload stages bytes through its own view.
            problem = await tft_url_problem(request.app["hass"], install.url)
            if problem:
                raise ApiError(problem, 502)
        apps = running_apps(request.app["hass"], entry_id)
        return await _install(
            self, apps, install, "install the TFT", _start_tft_install, _tft_install_error
        )


class DeviceUpdateFirmwareView(HomeAssistantView):
    """Install the firmware of one device or of every device."""

    url = "/api/nspanel_haui/update_firmware/{entry_id}"
    name = "api:nspanel_haui:update_firmware"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Install the firmware offered to a device, or one ``version``/``url`` names.

        Without a body field the device re-reads its firmware manifest and
        installs the newer firmware it names, even when automatic installs are
        off. An optional ``version`` (a GitHub release, older ones included) or
        ``url`` (an OTA app image, single device only) installs that image
        instead.
        """
        install = _install_request(await json_object(request), "firmware")
        apps = running_apps(request.app["hass"], entry_id)
        return await _install(
            self,
            apps,
            install,
            "install firmware",
            _start_firmware_install,
            _firmware_install_error,
        )


class DeviceTftReleasesView(HomeAssistantView):
    """List the TFT versions a device can install."""

    url = "/api/nspanel_haui/tft_releases/{entry_id}"
    name = "api:nspanel_haui:tft_releases"
    requires_auth = True

    @require_admin
    @api_errors
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the TFT versions the ``device`` query param can install.

        ``releases`` is the manifest's TFT version, ``required`` the firmware's
        ``tft_required_version``, and ``error`` carries a failed lookup.
        """
        app = running_device_app(request.app["hass"], entry_id, query_device(request))
        return self.json(await app.async_list_tft_releases())


class DeviceFirmwareReleasesView(HomeAssistantView):
    """List the GitHub releases whose firmware installs over the air."""

    url = "/api/nspanel_haui/firmware_releases/{entry_id}"
    name = "api:nspanel_haui:firmware_releases"
    requires_auth = True

    @require_admin
    @api_errors
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the releases the ``device`` query param can flash over the air."""
        app = running_device_app(request.app["hass"], entry_id, query_device(request))
        return self.json(await app.async_list_firmware_releases())


class DeviceUpdateCheckView(HomeAssistantView):
    """Run a manual update check on one device or on every device."""

    url = "/api/nspanel_haui/check_update/{entry_id}"
    name = "api:nspanel_haui:check_update"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Check the device the body names, or every device, for updates.

        Update inputs are fetched off the worker and applied in order by each
        device's worker.
        """
        device_name = body_device(await json_object(request))
        apps = running_apps(request.app["hass"], entry_id)

        if device_name != ALL_DEVICES:
            app = device_app(apps, device_name)
            result = await app.async_check_for_update()
            return self.json(
                {
                    "status": "ok",
                    "devices_checked": [device_name],
                    "results": {device_name: result},
                }
            )

        results: dict[str, dict[str, Any]] = {}

        async def check(name: str, app: Any) -> None:
            results[name] = await app.async_check_for_update()

        checked, failed = await for_each_app(apps, "check for updates", check)
        return self.json(
            {"status": "ok", "devices_checked": checked, "failed": failed, "results": results}
        )


class UpdateControlView(HomeAssistantView):
    """Act on a device's scheduled automatic firmware install: start now, defer or skip."""

    url = "/api/nspanel_haui/update_control/{entry_id}"
    name = "api:nspanel_haui:update_control"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Body ``{device, action, seconds?}``.

        ``install_now`` and ``defer`` (``seconds`` 3600 or 86400) act on the
        scheduled install. ``skip`` stores the offered firmware version in the
        device settings, so automatic installs pass over it, even after a
        restart; a manual install or a newer version is not affected.
        """
        hass = request.app["hass"]
        body = await json_object(request)
        device = text_field(body.get("device"), "device")
        if not device:
            raise ApiError("Body must name a device", 400)
        action = body.get("action")
        if action in ("install_now", "defer"):
            app = running_device_app(hass, entry_id, device)
            try:
                result = await app.async_update_control(action, body.get("seconds"))
            except ValueError as exc:
                raise ApiError(str(exc), 400) from exc
            return self.json({"status": "ok", "update": result})
        if action != "skip":
            raise ApiError(f"Unknown update control action {action!r}", 400)
        async with edit_panels(hass, entry_id) as edit:
            app = running_device_app(hass, entry_id, device)
            state = await app.async_update_state()
            version = (
                state.get("firmware_update_version")
                if state.get("firmware_update_available")
                else None
            )
            if not version:
                raise ApiError("No firmware update is offered to skip", 400)
            data = await edit.load()
            stored = data.get("devices", {}).get(device)
            if stored is None:
                raise ApiError(f'Device "{device}" not found', 404)
            stored.setdefault("config", {}).setdefault("update", {})["skipped_firmware_version"] = (
                version
            )
            pushed = await edit.save(data, devices=(device,))
        return self.json(
            {
                "status": "ok",
                "skipped_version": version,
                **pushed,
            }
        )


async def _offered_devices(hass: Any, entry_id: str, apps: dict[str, Any]) -> list[str]:
    """Return the connected devices with an offered update, in the editor's order."""
    data = await panel_store(hass, entry_id).async_load() or empty_store()
    order = [name for name in data.get("device_order", []) if name in apps]
    order += [name for name in apps if name not in order]
    offered = []
    for name in order:
        snapshot = await apps[name].async_update_snapshot()
        if snapshot["connected"] and (
            snapshot["firmware"]["available"] or snapshot["display"]["available"]
        ):
            offered.append(name)
    return offered


class RolloutView(HomeAssistantView):
    """Fleet's *Install updates*: one device at a time, stopping at the first failure."""

    url = "/api/nspanel_haui/rollout/{entry_id}"
    name = "api:nspanel_haui:rollout"
    requires_auth = True

    @require_admin
    @api_errors
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the rollout, idle when none ran since Home Assistant started."""
        from ..hub.rollout import rollout_snapshot

        return self.json({"rollout": rollout_snapshot(request.app["hass"], entry_id)})

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Start a rollout on every device that has an offered update, or on those named.

        Body ``{devices?: [...]}``; without it the default is every connected
        device with an offered update, in the editor's device order.
        """
        from ..hub.rollout import async_get_rollout

        hass = request.app["hass"]
        body = await json_object(request)
        apps = running_apps(hass, entry_id)
        devices = body.get("devices")
        if devices is None:
            devices = await _offered_devices(hass, entry_id, apps)
        if not isinstance(devices, list) or not devices:
            raise ApiError("No device has an update to install", 400)
        try:
            rollout = await async_get_rollout(hass, entry_id).async_start(devices)
        except ValueError as exc:
            raise ApiError(str(exc), 400) from exc
        return self.json({"status": "ok", "rollout": rollout})

    @require_admin
    @api_errors
    async def delete(self, request: web.Request, entry_id: str) -> web.Response:
        """Cancel the queued devices of a running rollout, or dismiss a finished one."""
        from ..hub.rollout import async_get_rollout

        rollout = async_get_rollout(request.app["hass"], entry_id)
        snapshot = await rollout.async_cancel() if rollout.running else rollout.dismiss()
        return self.json({"status": "ok", "rollout": snapshot})


class RolloutDeviceView(HomeAssistantView):
    """Cancel one queued device of the rollout."""

    url = "/api/nspanel_haui/rollout/{entry_id}/{device}"
    name = "api:nspanel_haui:rollout_device"
    requires_auth = True

    @require_admin
    @api_errors
    async def delete(self, request: web.Request, entry_id: str, device: str) -> web.Response:
        """Cancel ``device`` if it is still queued; the installing device finishes."""
        from ..hub.rollout import async_get_rollout

        rollout = async_get_rollout(request.app["hass"], entry_id)
        return self.json({"status": "ok", "rollout": await rollout.async_cancel(device)})

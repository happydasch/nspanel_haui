"""REST API for NSPanel HAUI panel configuration.

Exposes panel CRUD endpoints for the frontend HAUI Editor.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from .const import DOMAIN
from .esphome_helpers import lookup_device_registry_name, read_network_entities
from .haui.config_models import validate_panels
from .storage import empty_device, empty_store, enabled_device_names, panel_store

_LOGGER = logging.getLogger(__name__)


def _error(view: HomeAssistantView, message: str, status_code: int):
    """Build the ``{"status": "error", "message": ...}`` response used by all views."""
    return view.json({"status": "error", "message": message}, status_code=status_code)


def _get_apps(hass: Any, entry_id: str) -> Any:
    """Return what hass.data holds for a config entry: the apps dict, or None if not set up."""
    return hass.data.get(DOMAIN, {}).get(entry_id)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def _query_device(request: Any) -> str:
    """Return the stripped ``device`` query param ('' when absent)."""
    return (request.query.get("device") or "").strip()


async def _validate_or_400(view: HomeAssistantView, hass: Any, data: dict, what: str):
    """Validate panel data in the executor; return an error response, or None when valid."""
    try:
        # Pydantic model validation does importlib.metadata I/O, which must
        # not block the event loop.
        await hass.async_add_executor_job(validate_panels, data)
    except Exception as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        return _error(view, str(exc), 400)
    return None


async def _push_panels(hass: Any, entry_id: str, data: dict) -> dict:
    """Apply saved panel data to the running apps; returns the JSON response body.

    Reloads the entry when the set of enabled devices changed (notify entities
    are created per running device at setup) or no apps are running; otherwise
    rebuilds each device's runtime config the way setup does and applies it on
    the app's worker.
    """
    from . import _build_config_dict

    apps = _get_apps(hass, entry_id)

    if apps is None:
        # Entry not yet set up; nothing to push to
        return {"status": "ok"}

    if not isinstance(apps, dict):
        # None is handled above; an app object instead of the devices dict is
        # the pre-multi-device store format and has nothing to push to.
        return {"status": "ok"}

    if not apps:
        # Entry set up without running apps; fall back to reload
        _LOGGER.info(
            "No running apps for entry %s; triggering config entry reload",
            entry_id,
        )
        await hass.config_entries.async_reload(entry_id)
        return {"status": "ok", "reloaded": True}

    entry = hass.config_entries.async_get_entry(entry_id)
    # Same rule as setup, so a store-only device (removed with "keep config")
    # doesn't force a reload on every save.
    if set(enabled_device_names(entry.data, data)) != set(apps):
        hass.config_entries.async_schedule_reload(entry_id)
        return {"status": "ok", "reloaded": True}

    for device_name, app in apps.items():
        if app.device_config:
            try:
                cfg = _build_config_dict(entry.data, data, device_name=device_name)
                await app.async_run_on_worker(app.reload_config, cfg)
            except Exception:
                _LOGGER.exception(
                    "Failed to push panel update to device '%s' for entry %s",
                    device_name,
                    entry_id,
                )

    return {"status": "ok"}


def _strip_empty_configs(dev_data: dict) -> dict:
    """Remove None-valued keys from config for a cleaner YAML export."""
    config = dict(dev_data.get("config", {}))
    cleaned = {k: v for k, v in config.items() if v is not None}
    result: dict = {}
    if cleaned:
        result["config"] = cleaned
    result["panels"] = list(dev_data.get("panels", []))
    return result


class TranslationsView(HomeAssistantView):
    """REST API view returning translation data for the frontend editor."""

    url = "/api/nspanel_haui/translations/{language}"
    name = "api:nspanel_haui:translations"
    requires_auth = True

    async def get(self, request, language: str):
        """Return translation data for a language code.

        Query param ``flat`` (optional, defaults to ``1``) controls whether the
        response is a flat ``{text_key: translation}`` mapping.  When ``0`` the
        full JSON structure (including ``component`` section) is returned.

        Falls back to English when the requested language is not available.
        """
        from .haui.utils.text import get_translations

        hass = request.app["hass"]
        flat = request.query.get("flat", "1")
        try:
            translations = await hass.async_add_executor_job(get_translations, language)
        except ValueError as exc:
            return _error(self, str(exc), 400)

        if flat == "1" or flat is True:
            return self.json(translations.get("text", {}))
        return self.json(translations)


class DeviceStatusView(HomeAssistantView):
    """REST API view returning live device status."""

    url = "/api/nspanel_haui/status/{entry_id}"
    name = "api:nspanel_haui:status"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return live device status for a config entry.

        Query param ``device`` (optional) restricts the response to a single
        device.  When omitted an aggregate dict is returned, including both
        enabled and disabled devices (status for disabled devices is read
        directly from HA entities).
        """
        hass = request.app["hass"]
        apps = _get_apps(hass, entry_id)

        if apps is None:
            apps = {}

        device_name = _query_device(request)
        if device_name:
            app = apps.get(device_name)
            if app is not None:
                return self.json(app.get_device_status())
            # Device may be disabled or pending — read from HA entities
            status = await self._build_entity_status(hass, entry_id, device_name)
            if status is not None:
                return self.json(status)
            return self.json(
                {"error": f"device {device_name!r} not found"},
                status_code=404,
            )

        # ── Build status for all known devices ──
        # Enabled devices use their NSPanelHAUI instance.
        # Disabled devices get a minimal status from HA entities.
        entry = hass.config_entries.async_get_entry(entry_id)
        all_devices = entry.data.get("devices", []) if entry else []
        result: dict[str, dict] = {}

        for dev in all_devices:
            dev_name = dev.get("name", "")
            if not dev_name:
                continue
            app = apps.get(dev_name)
            if app is not None:
                result[dev_name] = app.get_device_status()
            else:
                status = await self._build_entity_status(hass, entry_id, dev_name)
                if status is not None:
                    result[dev_name] = status

        return self.json({"devices": result})

    @staticmethod
    def _build_minimal_device_info(hass: Any, dev_name: str) -> dict | None:
        """Build minimal status from HA entities for a device without a running app."""
        nw = read_network_entities(hass, dev_name)

        # If none of the WiFi entities exist, the device may not be a real ESPHome device
        if not nw["ip"] and not nw["ssid"] and nw["rssi"] is None:
            return None

        return {
            "connected": False,
            "connection_state": "disabled",
            "current_page": "",
            "device_info": {
                "name": dev_name,
                "tft_version": "",
                "yaml_version": "",
                "ip": nw["ip"],
                "ssid": nw["ssid"],
                "rssi": nw["rssi"],
                "last_panel_update": None,
                "last_connection": None,
            },
        }

    @staticmethod
    async def _build_entity_status(hass: Any, entry_id: str, dev_name: str) -> dict | None:
        """Build status for a device from HA entities, running in executor if needed."""
        return await hass.async_add_executor_job(
            DeviceStatusView._build_minimal_device_info, hass, dev_name
        )


class PanelTypesView(HomeAssistantView):
    """REST API view returning panel type descriptors for the frontend editor."""

    url = "/api/nspanel_haui/panel_types"
    name = "api:nspanel_haui:panel_types"
    requires_auth = True

    async def get(self, request):
        """Return JSON descriptors for all user-visible panel types.

        Query param ``language`` (optional, defaults to ``"en"``) controls the
        locale for pre-translating string fields.
        """
        from .haui.mapping.panel import get_user_panel_type_descriptors

        lang = request.query.get("language", "en")
        hass = request.app["hass"]
        descriptors = await hass.async_add_executor_job(get_user_panel_type_descriptors, lang)
        return self.json(descriptors)


class ColorDefaultsView(HomeAssistantView):
    """REST API view returning built-in color defaults for the frontend editor."""

    url = "/api/nspanel_haui/color_defaults"
    name = "api:nspanel_haui:color_defaults"
    requires_auth = True

    async def get(self, request):
        """Return the COLORS dict as JSON (single source of truth from color.py)."""
        from .haui.mapping.color import COLORS

        return self.json(COLORS)


class PanelConfigView(HomeAssistantView):
    """REST API view for per-entry panel configuration."""

    url = "/api/nspanel_haui/panels/{entry_id}"
    name = "api:nspanel_haui:panels"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return the panel store data for a config entry.

        Query param ``language`` (optional, defaults to ``"en"``) controls the
        locale for pre-translating system panel string fields.
        """
        hass = request.app["hass"]
        lang = request.query.get("language", "en")
        store = panel_store(hass, entry_id)
        data = await store.async_load()
        result = data or empty_store()
        from .haui.mapping.panel import get_system_panel_entries

        result["system_panels"] = await hass.async_add_executor_job(get_system_panel_entries, lang)

        # Enrich each device with friendly_name from HA device registry.
        # Always refresh — the stored value (if any) may be stale since users
        # can change a device's name via HA Settings → Devices & Services.
        for dev_key, dev_data in result.get("devices", {}).items():
            friendly_name = lookup_device_registry_name(hass, dev_key)
            dev_data["friendly_name"] = friendly_name

        return self.json(result)

    @require_admin
    async def post(self, request, entry_id: str):
        """Save panel store data for a config entry."""
        hass = request.app["hass"]
        data = await request.json()
        # GET adds these for display; they are not part of the store.
        data.pop("system_panels", None)
        for dev_data in data.get("devices", {}).values():
            dev_data.pop("friendly_name", None)

        error = await _validate_or_400(self, hass, data, "Panel config")
        if error is not None:
            return error

        # Stamp each device with the save timestamp (server-side, not from frontend)
        now_iso = _now_iso()
        for dev_data in data.get("devices", {}).values():
            dev_data["last_panel_update"] = now_iso

        await panel_store(hass, entry_id).async_save(data)
        return self.json(await _push_panels(hass, entry_id, data))


class DeviceConfigView(HomeAssistantView):
    """REST API view for adding/removing devices per config entry."""

    url = "/api/nspanel_haui/devices/{entry_id}"
    name = "api:nspanel_haui:devices"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return discovered ESPHome HAUI devices available for adding.

        Returns a list of discovered devices with ``name``, ``friendly_name``,
        and ``esphome_device_id`` keys.
        """
        hass = request.app["hass"]
        from .esphome_helpers import discover_esphome_devices

        discovered = await discover_esphome_devices(hass)
        return self.json({"devices": discovered})

    @require_admin
    async def post(self, request, entry_id: str):
        """Add one or more devices to the config entry and panel store.

        Accepts a batch body ``{devices: [{name, enabled, esphome_device_id}, ...]}``.

        After adding, reloads the config entry so app instances start for
        newly-enabled devices.
        """
        hass = request.app["hass"]
        body = await request.json()

        devices_to_add = body.get("devices") if isinstance(body, dict) else None
        if not isinstance(devices_to_add, list):
            return _error(self, "Body must be {'devices': [...]}", 400)

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return _error(self, "Config entry not found", 404)

        from .esphome_helpers import hub_device_entry
        from .haui.device_config import find_store_device

        existing_names = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        new_devices: list[dict] = []
        enabled_by_name: dict[str, bool] = {}

        for dev_spec in devices_to_add:
            name = (dev_spec.get("name") or "").strip()
            if not name or name in existing_names:
                continue
            new_devices.append(hub_device_entry({**dev_spec, "name": name}))
            # Default to enabled — the user explicitly opted in by clicking Add.
            enabled_by_name[name] = dev_spec.get("enabled", True)
            existing_names.add(name)

        if not new_devices:
            return self.json(
                {"status": "ok", "devices_added": [], "message": "No new devices to add"}
            )
        names_added = list(enabled_by_name)

        # The entry holds only identity; settings, including ``enabled``, live
        # in the panel store. A device re-added after a keep-config removal
        # keeps its stored settings.
        store = panel_store(hass, entry_id)
        panels_data = await store.async_load() or empty_store()
        store_devices = panels_data.setdefault("devices", {})
        for name, enabled in enabled_by_name.items():
            store_dev = find_store_device(store_devices, name)
            if store_dev is None:
                store_dev = store_devices[name] = empty_device()
            store_dev.setdefault("config", {})["enabled"] = enabled
        await store.async_save(panels_data)

        # The entry's update listener reloads it, starting apps for the new device(s).
        new_data = {
            **entry.data,
            "devices": [*entry.data.get("devices", []), *new_devices],
            "removed_devices": [
                n for n in entry.data.get("removed_devices", []) if n not in names_added
            ],
        }
        hass.config_entries.async_update_entry(entry, data=new_data)

        return self.json({"status": "ok", "devices_added": names_added})

    @require_admin
    async def delete(self, request, entry_id: str):
        """Remove a device from the config entry, optionally keeping panel config.

        Query param ``name`` identifies the device.  JSON body may carry an
        optional ``keep_config`` boolean - when true the panel store is left
        untouched so that panel definitions survive device removal.
        """
        hass = request.app["hass"]
        name = (request.query.get("name") or "").strip()
        if not name:
            return _error(self, "Device name is required", 400)

        data = await request.json()
        keep_config = data.get("keep_config", False) if data else False

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return _error(self, "Config entry not found", 404)

        # Always remove from config_entry.data["devices"]
        existing_in_ce = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        if name not in existing_in_ce:
            return _error(self, f'Device "{name}" not found', 404)

        # Remove from panel store only when keep_config is False
        if not keep_config:
            store = panel_store(hass, entry_id)
            panels_data = await store.async_load() or empty_store()
            had_in_store = name in panels_data.get("devices", {})
            if had_in_store:
                panels_data.get("devices", {}).pop(name, None)
                await store.async_save(panels_data)
                _LOGGER.debug("Removed device %s from panel store for %s", name, entry_id)

        # The entry's update listener reloads it, stopping the device's app.
        new_data = dict(entry.data)
        new_data["devices"] = [d for d in new_data.get("devices", []) if d.get("name") != name]
        # Keeps auto-add from adding the device straight back while ESPHome still has it.
        new_data["removed_devices"] = [*entry.data.get("removed_devices", []), name]
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.debug("Removed device %s from config_entry.data for %s", name, entry_id)

        return self.json({"status": "ok", "kept_config": keep_config})


class DeviceYamlView(HomeAssistantView):
    """REST API view for YAML import/export of per-device configuration."""

    url = "/api/nspanel_haui/yaml/{entry_id}"
    name = "api:nspanel_haui:yaml"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Export device configuration as YAML.

        Query param ``device`` (optional) restricts export to a single device.
        When omitted all devices are included.
        """
        hass = request.app["hass"]
        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
        devices = data.get("devices", {})

        device_name = _query_device(request)

        if device_name:
            if device_name not in devices:
                return _error(self, f'Device "{device_name}" not found', 404)
            export = _strip_empty_configs(devices[device_name])
        else:
            export = {name: _strip_empty_configs(dev_data) for name, dev_data in devices.items()}

        import yaml

        yaml_str = yaml.dump(export, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return web.Response(text=yaml_str, content_type="application/x-yaml")

    @require_admin
    async def post(self, request, entry_id: str):
        """Import device configuration from YAML.

        Query param ``device`` specifies which device to update (required).
        The YAML body should contain the device's ``config`` and ``panels``.

        When devices already exist they are **replaced**; when absent they are
        added.  Other devices in the store are left untouched.
        """
        hass = request.app["hass"]
        device_name = _query_device(request)
        if not device_name:
            return _error(self, "Query param 'device' is required", 400)

        import yaml

        body = await request.text()
        try:
            parsed: dict = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            return _error(self, f"Invalid YAML: {exc}", 400)

        if not isinstance(parsed, dict):
            return _error(self, "YAML root must be a mapping", 400)

        # The YAML must expose the device's ``config`` and/or ``panels``
        # directly; wrapped-under-device-name imports are no longer accepted.
        if "config" not in parsed and "panels" not in parsed:
            return _error(
                self,
                "YAML must contain a 'config' and/or 'panels' mapping for the device",
                400,
            )
        device_data = parsed

        config = device_data.get("config", {})
        if not isinstance(config, dict):
            return _error(self, "'config' must be a mapping", 400)

        panels = device_data.get("panels", [])
        if not isinstance(panels, list):
            return _error(self, "'panels' must be a list", 400)

        # Validate against known config fields - strip unknown keys
        from .haui.device_config import DEVICE_CONFIG_FIELDS

        known_config = {k: config.get(k) for k in DEVICE_CONFIG_FIELDS if k in config}
        error = await _validate_or_400(
            self,
            hass,
            {"devices": {device_name: {"config": known_config, "panels": panels}}},
            "YAML import",
        )
        if error is not None:
            return error

        store = panel_store(hass, entry_id)
        store_data = await store.async_load() or empty_store()
        store_data.setdefault("devices", {})[device_name] = {
            "config": known_config,
            "panels": panels,
            "last_panel_update": _now_iso(),
        }
        await store.async_save(store_data)

        return self.json({**await _push_panels(hass, entry_id, store_data), "device": device_name})


class IconSearchView(HomeAssistantView):
    """REST API view providing MDI icon names for the frontend icon picker."""

    url = "/api/nspanel_haui/icons"
    name = "api:nspanel_haui:icons"
    requires_auth = True

    # Cache the icon list after first load
    _icons: list[str] | None = None

    async def get(self, request):
        """Return filtered list of MDI icon names.

        Query param ``q`` (optional) filters by substring match on the icon
        name (case-insensitive).  When omitted returns all icon names, which
        the icon picker fetches once and searches client-side.
        """
        if IconSearchView._icons is None:
            from .haui.mapping.icon_names import ICON_NAMES

            IconSearchView._icons = ICON_NAMES

        query = (request.query.get("q") or "").strip().lower()
        if query:
            results = [name for name in IconSearchView._icons if query in name]
        else:
            results = IconSearchView._icons

        return self.json(results)


class DeviceUpdateDisplayView(HomeAssistantView):
    """REST API endpoint to trigger display refresh on one or all devices."""

    url = "/api/nspanel_haui/update_display/{entry_id}"
    name = "api:nspanel_haui:update_display"
    requires_auth = True

    @require_admin
    async def post(self, request, entry_id: str):
        """Refresh the display for the specified device (or all devices).

        JSON body may carry an optional ``device`` field (device name, or ``*``
        for all devices).  When omitted defaults to ``*``.
        """
        hass = request.app["hass"]
        body = await request.json() or {}
        device_name = (body.get("device") or "*").strip()

        apps = _get_apps(hass, entry_id)

        if not isinstance(apps, dict):
            return _error(self, "No running devices", 400)

        if device_name and device_name != "*":
            app = apps.get(device_name)
            if app is None:
                return _error(self, f'Device "{device_name}" not found', 404)
            await app.async_run_on_worker(app.update_display)
            return self.json({"status": "ok", "devices_updated": [device_name]})

        # Update all devices
        updated: list[str] = []
        for dname, dapp in apps.items():
            try:
                await dapp.async_run_on_worker(dapp.update_display)
                updated.append(dname)
            except Exception:
                _LOGGER.exception("Failed to update display for device '%s'", dname)

        return self.json({"status": "ok", "devices_updated": updated})


class FirmwareDownloadView(HomeAssistantView):
    """REST API view returning the latest release's firmware (.bin) asset URL."""

    url = "/api/nspanel_haui/firmware"
    name = "api:nspanel_haui:firmware"
    requires_auth = True

    @require_admin
    async def get(self, request):
        """Return the prebuilt firmware download link of the latest release.

        Releases may carry a ``nspanel_haui.bin`` asset (name-agnostic build)
        in addition to the TFT files.  Returns ``{"url": null}`` when the
        latest release has no binary asset, so the editor can show a plain
        build-from-YAML hint instead of a dead link.  When the GitHub API is
        unreachable an error response is returned instead, so the editor does
        not mistake a network problem for a missing asset.
        """
        from .haui.controller.update import HAUIUpdateController

        # The update controller already caches release info on the worker; for
        # this small, user-initiated lookup do a fresh, short fetch here so the
        # link always reflects the very latest release.
        def _fetch() -> list | None:
            try:
                resp = requests.get(HAUIUpdateController.RELEASES_URL, timeout=5)
                json_decoded = resp.json()
            except (requests.exceptions.RequestException, ValueError):
                # Network failure, a non-JSON body (GitHub rate limit page), …
                return None
            return json_decoded if isinstance(json_decoded, list) else None

        releases = await asyncio.to_thread(_fetch)
        if not releases:
            # None = the GitHub API could not be reached; [] = it returned no
            # releases.  Both are environment problems, not "the release lacks
            # a binary" — report them as such so the editor does not claim the
            # release ships no firmware.
            return _error(
                self,
                "Could not reach the GitHub API; check the Home Assistant host's network access",
                502,
            )

        # Releases are returned newest-first; the first binary-bearing release
        # is the right one to link (semver tags are the release convention).
        for release in releases:
            for asset in release.get("assets", []):
                # one universal binary serves every display model
                if asset.get("name") == "nspanel_haui.bin":
                    return self.json(
                        {
                            "url": asset["browser_download_url"],
                            "version": release.get("tag_name"),
                        }
                    )
        return self.json({"url": None, "version": None})


class DeviceUpdateTftView(HomeAssistantView):
    """REST API endpoint to trigger a TFT install on one or all devices."""

    url = "/api/nspanel_haui/update_tft/{entry_id}"
    name = "api:nspanel_haui:update_tft"
    requires_auth = True

    @require_admin
    async def post(self, request, entry_id: str):
        """Install the TFT for the specified device (or all devices).

        JSON body may carry an optional ``device`` field (device name, or ``*``
        for all devices; default ``*``) and an optional ``version`` (the GitHub
        release version to install; when omitted the version the firmware needs,
        its ``yaml_version``, is installed).  The install runs on the device's
        worker thread.
        """
        hass = request.app["hass"]
        body = await request.json() or {}
        device_name = (body.get("device") or "*").strip()
        version = (body.get("version") or "").strip() or None

        apps = _get_apps(hass, entry_id)

        if not isinstance(apps, dict):
            return _error(self, "No running devices", 400)

        if device_name and device_name != "*":
            app = apps.get(device_name)
            if app is None:
                return _error(self, f'Device "{device_name}" not found', 404)
            result = await app.async_run_on_worker(app.install_tft, version)
            if isinstance(result, dict) and result.get("state") == "error":
                # The controller records *why* the install could not start
                # (device disconnected, no yaml_version, no matching release,
                # GitHub fetch failure).  Surface that to the editor instead of
                # a success response that never installs anything.
                return _error(
                    self,
                    result.get("last_error") or "TFT update failed",
                    502,
                )
            return self.json(
                {"status": "ok", "devices_updated": [device_name], "update": result}
            )

        # Update all devices
        updated: list[str] = []
        failed: list[dict[str, str]] = []
        for dname, dapp in apps.items():
            try:
                result = await dapp.async_run_on_worker(dapp.install_tft, version)
                if isinstance(result, dict) and result.get("state") == "error":
                    failed.append(
                        {"name": dname, "error": result.get("last_error") or "TFT update failed"}
                    )
                    _LOGGER.warning(
                        "Failed to install TFT for device '%s': %s",
                        dname,
                        result.get("last_error"),
                    )
                else:
                    updated.append(dname)
            except Exception:
                _LOGGER.exception("Failed to install TFT for device '%s'", dname)
                failed.append({"name": dname, "error": "install failed"})

        return self.json({"status": "ok", "devices_updated": updated, "failed": failed})

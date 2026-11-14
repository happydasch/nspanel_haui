"""Panel and device configuration: the panel store, devices, YAML import/export."""

from __future__ import annotations

import copy
import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..haui.config_models import PanelValidationError, validate_device_config, validate_panels
from ..haui.device_config import DEVICE_CONFIG_FIELDS
from ..hub.esphome_helpers import lookup_device_registry_name
from ..hub.storage import (
    async_remove_device,
    empty_device,
    empty_store,
    enabled_device_names,
    migrate_device_config_keys,
    normalize_device_order,
    panel_store,
)
from .common import (
    ApiError,
    api_errors,
    ensure_known_theme_ids,
    error,
    get_apps,
    json_object,
    now_iso,
    query_device,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_panels(hass: Any, data: dict, what: str, previous: dict | None = None) -> None:
    """Validate panel data in the executor.

    Args:
        hass: Home Assistant
        data: The panel data to save
        what: Names the data in the log
        previous: The stored data the save replaces; unchanged panels skip the
            option rules (see ``validate_panels``). ``None`` checks every panel.

    Raises:
        ApiError: With the validation error; a broken option rule adds the
            ``errors`` list to the response body
    """
    try:
        # Pydantic model validation does importlib.metadata I/O, which must
        # not block the event loop.
        await hass.async_add_executor_job(validate_panels, data, previous)
    except PanelValidationError as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400, {"errors": exc.errors}) from exc
    except Exception as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400) from exc


async def _validate_device_config(hass: Any, config: dict, what: str = "Device config") -> None:
    """Validate device settings off the event loop."""
    try:
        await hass.async_add_executor_job(validate_device_config, config)
    except Exception as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400) from exc


def _known_device_config(config: dict) -> dict:
    """Return only supported settings, including the nested update settings."""
    migrate_device_config_keys(config)
    known = {key: config[key] for key in DEVICE_CONFIG_FIELDS if key in config}
    if isinstance(config.get("update"), dict):
        known["update"] = config["update"]
    return known


def _keep_skipped_firmware_version(config: dict, stored: dict) -> None:
    """Carry the stored skipped firmware version into ``config``, whatever it says.

    Only *Skip this version* (``UpdateControlView``) writes the skip; a settings
    save from an editor that read the settings before the skip must not undo it.
    """
    skipped = (stored.get("update") or {}).get("skipped_firmware_version")
    update = config.get("update")
    if skipped:
        config["update"] = {
            **(update if isinstance(update, dict) else {}),
            "skipped_firmware_version": skipped,
        }
    elif isinstance(update, dict):
        update.pop("skipped_firmware_version", None)


def _store_device(data: dict, device: str) -> dict:
    """Return one stored device or raise a not-found API error."""
    devices = data.get("devices", {})
    if device not in devices:
        raise ApiError(f'Device "{device}" not found', 404)
    return devices[device]


async def push_panels(hass: Any, entry_id: str, data: dict, device_name: str | None = None) -> dict:
    """Apply saved panel data to the running apps; returns the JSON response body.

    Reloads the entry when the set of enabled devices changed (notify entities
    are created per running device at setup) or no apps are running; otherwise
    rebuilds each device's runtime config the way setup does and applies it on
    the app's worker. When ``device_name`` is set, only that app is rebuilt;
    virtual hosts and viewers still receive the updated store. Live previews
    follow the reloaded apps.
    """
    from .. import _build_config_dict
    from ..web.preview.live_panel import async_reload_viewers
    from ..web.websocket import async_reload_hosts

    await async_reload_hosts(hass, entry_id, data)
    apps = get_apps(hass, entry_id)
    if not isinstance(apps, dict):
        # Not set up yet, or an app object instead of the devices dict (the
        # pre-multi-device store format): nothing to push to.
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
    # Same rule as setup, so a store-only device (settings without a config
    # entry record) doesn't force a reload on every save.
    if set(enabled_device_names(entry.data, data)) != set(apps):
        hass.config_entries.async_schedule_reload(entry_id)
        return {"status": "ok", "reloaded": True}

    for app_name, app in apps.items():
        if device_name is not None and app_name != device_name:
            continue
        if not app.device_config:
            continue
        try:
            cfg = _build_config_dict(entry.data, data, device_name=app_name)
            await app.async_run_on_worker(app.reload_config, cfg)
        except Exception:
            _LOGGER.exception(
                "Failed to push panel update to device '%s' for entry %s",
                app_name,
                entry_id,
            )
    await async_reload_viewers(hass, entry_id)

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


def _device_yaml_data(dev_data: dict, store_data: dict) -> dict:
    """Include the active custom definition so a device YAML is self-contained."""
    result = _strip_empty_configs(dev_data)
    config = result.get("config", {})
    themes = store_data.get("themes", {})
    result["theme_definitions"] = [
        {"id": theme_id, **themes[theme_id]}
        for theme_id in sorted(
            {
                config.get("theme_id", "dark"),
                *(
                    panel.get("theme_id")
                    for panel in result["panels"]
                    if isinstance(panel, dict) and panel.get("theme_id")
                ),
            }
        )
        if theme_id in themes
    ]
    if not result["theme_definitions"]:
        result.pop("theme_definitions")
    theme_id = config.get("theme_id", "dark")
    if theme_id in themes:
        result["theme_definition"] = {"id": theme_id, **themes[theme_id]}
    return result


class PanelConfigView(HomeAssistantView):
    """Read the complete panel store for one config entry."""

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
        result.setdefault("themes", {})
        normalize_device_order(result)
        from ..haui.mapping.panel import get_system_panel_entries

        result["system_panels"] = await hass.async_add_executor_job(get_system_panel_entries, lang)

        # Enrich each device with friendly_name from HA device registry.
        # Always refresh — the stored value (if any) may be stale since users
        # can change a device's name via HA Settings → Devices & Services.
        for dev_key, dev_data in result.get("devices", {}).items():
            friendly_name = lookup_device_registry_name(hass, dev_key)
            dev_data["friendly_name"] = friendly_name

        return self.json(result)


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
        from ..hub.esphome_helpers import discover_esphome_devices

        discovered = await discover_esphome_devices(hass)
        return self.json({"devices": discovered})

    @require_admin
    @api_errors
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
            raise ApiError("Body must be {'devices': [...]}", 400)

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            raise ApiError("Config entry not found", 404)

        from ..haui.device_config import find_store_device
        from ..hub.esphome_helpers import hub_device_entry

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
        # in the panel store. A device whose settings are still stored (a
        # store-only device) keeps them.
        store = panel_store(hass, entry_id)
        panels_data = await store.async_load() or empty_store()
        store_devices = panels_data.setdefault("devices", {})
        for name, enabled in enabled_by_name.items():
            store_dev = find_store_device(store_devices, name)
            if store_dev is None:
                store_dev = store_devices[name] = empty_device()
            store_dev.setdefault("config", {})["enabled"] = enabled
        normalize_device_order(panels_data)
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
    @api_errors
    async def delete(self, request, entry_id: str):
        """Remove a device from the hub together with its settings and panels.

        Query param ``name`` identifies the device.
        """
        hass = request.app["hass"]
        name = (request.query.get("name") or "").strip()
        if not name:
            raise ApiError("Device name is required", 400)

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            raise ApiError("Config entry not found", 404)

        existing_in_ce = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        if name not in existing_in_ce:
            raise ApiError(f'Device "{name}" not found', 404)

        await async_remove_device(hass, entry, name)

        return self.json({"status": "ok"})


class DeviceSettingsView(HomeAssistantView):
    """Read or replace one device's stored settings."""

    url = "/api/nspanel_haui/devices/{entry_id}/{device}"
    name = "api:nspanel_haui:device_settings"
    requires_auth = True

    @require_admin
    @api_errors
    async def get(self, request, entry_id: str, device: str):
        """Return one device's stored settings."""
        hass = request.app["hass"]
        data = await panel_store(hass, entry_id).async_load() or empty_store()
        config = copy.deepcopy(_store_device(data, device).get("config") or {})
        migrate_device_config_keys(config)
        return self.json({"device": device, "config": config})

    @require_admin
    @api_errors
    async def put(self, request, entry_id: str, device: str):
        """Replace one device's settings without changing its panels or other devices."""
        hass = request.app["hass"]
        body = await json_object(request)
        config = body.get("config")
        if not isinstance(config, dict):
            raise ApiError("Body must be {'config': {...}}", 400)

        known = _known_device_config(config)
        await _validate_device_config(hass, known)
        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
        store_dev = _store_device(data, device)
        _keep_skipped_firmware_version(known, store_dev.get("config") or {})

        from ..haui.mapping.color import BUILTIN_THEMES

        theme_id = known.get("theme_id", "dark")
        if theme_id not in {**data.get("themes", {}), **BUILTIN_THEMES}:
            raise ApiError(f"Unknown color theme {theme_id!r}", 400)

        store_dev["config"] = known
        await store.async_save(data)
        return self.json(
            {
                "status": "ok",
                "device": device,
                "config": known,
                **await push_panels(hass, entry_id, data, device_name=device),
            }
        )


class DevicePanelsView(HomeAssistantView):
    """Replace one device's panels; the store GET returns every device's panels."""

    url = "/api/nspanel_haui/panels/{entry_id}/{device}"
    name = "api:nspanel_haui:device_panels"
    requires_auth = True

    @require_admin
    @api_errors
    async def put(self, request, entry_id: str, device: str):
        """Replace one device's panels without changing settings or other devices."""
        hass = request.app["hass"]
        body = await json_object(request)
        panels = body.get("panels")
        if not isinstance(panels, list):
            raise ApiError("Body must be {'panels': [...]}", 400)

        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
        store_dev = _store_device(data, device)
        await _validate_panels(
            hass, {"devices": {device: {"panels": panels}}}, f"Panels of {device}", previous=data
        )
        candidate = {
            **data,
            "devices": {
                **data.get("devices", {}),
                device: {**store_dev, "panels": panels},
            },
        }
        ensure_known_theme_ids(candidate, data.get("themes", {}))
        store_dev["panels"] = panels
        store_dev["last_panel_update"] = now_iso()
        await store.async_save(data)
        return self.json(
            {
                "status": "ok",
                "device": device,
                **await push_panels(hass, entry_id, data, device_name=device),
            }
        )


class DeviceOrderView(HomeAssistantView):
    """Store editor device order; runtime device ordering comes from the config entry."""

    url = "/api/nspanel_haui/device_order/{entry_id}"
    name = "api:nspanel_haui:device_order"
    requires_auth = True

    @require_admin
    @api_errors
    async def put(self, request, entry_id: str):
        """Replace and normalize the editor's device order."""
        hass = request.app["hass"]
        body = await json_object(request)
        device_order = body.get("device_order")
        if not isinstance(device_order, list) or any(
            not isinstance(name, str) for name in device_order
        ):
            raise ApiError("Body must be {'device_order': [names]}", 400)

        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
        data["device_order"] = list(device_order)
        normalize_device_order(data)
        await store.async_save(data)
        return self.json({"status": "ok", "device_order": data["device_order"]})


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

        device_name = query_device(request)

        if device_name:
            if device_name not in devices:
                return error(self, f'Device "{device_name}" not found', 404)
            export = _device_yaml_data(devices[device_name], data)
        else:
            export = {name: _device_yaml_data(dev_data, data) for name, dev_data in devices.items()}

        import yaml

        yaml_str = yaml.dump(export, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return web.Response(text=yaml_str, content_type="application/x-yaml")

    @require_admin
    @api_errors
    async def post(self, request, entry_id: str):
        """Import device configuration from YAML.

        Query param ``device`` specifies which device to update (required).
        The YAML body should contain the device's ``config`` and ``panels``.

        When devices already exist they are **replaced**; when absent they are
        added.  Other devices in the store are left untouched.
        """
        hass = request.app["hass"]
        device_name = query_device(request)
        if not device_name:
            raise ApiError("Query param 'device' is required", 400)

        import yaml

        body = await request.text()
        try:
            parsed: dict = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            raise ApiError(f"Invalid YAML: {exc}", 400) from exc

        if not isinstance(parsed, dict):
            raise ApiError("YAML root must be a mapping", 400)

        # The YAML must expose the device's ``config`` and/or ``panels``
        # directly; wrapped-under-device-name imports are no longer accepted.
        if "config" not in parsed and "panels" not in parsed:
            raise ApiError(
                "YAML must contain a 'config' and/or 'panels' mapping for the device", 400
            )

        config = parsed.get("config", {})
        if not isinstance(config, dict):
            raise ApiError("'config' must be a mapping", 400)

        panels = parsed.get("panels", [])
        if not isinstance(panels, list):
            raise ApiError("'panels' must be a list", 400)

        # Discard unknown settings while retaining the supported nested update block.
        known_config = _known_device_config(config)
        theme_definition = parsed.get("theme_definition")
        theme_definitions = parsed.get("theme_definitions", [])
        if theme_definitions is None:
            theme_definitions = []
        if not isinstance(theme_definitions, list):
            raise ApiError("'theme_definitions' must be a list", 400)
        if theme_definition is not None:
            if not isinstance(theme_definition, dict):
                raise ApiError("'theme_definition' must include a theme ID", 400)
            theme_definitions = [theme_definition, *theme_definitions]
        raw_theme_definitions: dict[str, dict] = {}
        legacy_theme_id = None
        for definition in theme_definitions:
            if not isinstance(definition, dict) or not isinstance(definition.get("id"), str):
                raise ApiError("Theme definitions must include a theme ID", 400)
            theme_id = definition["id"]
            theme_payload = {key: value for key, value in definition.items() if key != "id"}
            existing_definition = raw_theme_definitions.get(theme_id)
            if existing_definition is not None and existing_definition != theme_payload:
                raise ApiError(f"Conflicting definitions for color theme {theme_id!r}", 400)
            raw_theme_definitions[theme_id] = theme_payload
            if definition is theme_definition:
                legacy_theme_id = theme_id

        imported_themes = {}
        if raw_theme_definitions:
            from ..haui.mapping.color import validate_themes

            try:
                imported_themes = await hass.async_add_executor_job(
                    validate_themes, raw_theme_definitions
                )
            except Exception as exc:
                raise ApiError(str(exc), 400) from exc
        if legacy_theme_id and "theme_id" not in known_config:
            known_config["theme_id"] = legacy_theme_id
        await _validate_panels(
            hass,
            {"devices": {device_name: {"config": known_config, "panels": panels}}},
            "YAML import",
        )

        store = panel_store(hass, entry_id)
        store_data = await store.async_load() or empty_store()
        store_themes = store_data.setdefault("themes", {})

        for theme_id, imported_theme in imported_themes.items():
            existing = store_themes.get(theme_id)
            if existing is not None and existing != imported_theme:
                raise ApiError("Imported color theme ID conflicts with an existing theme", 409)
        candidate_themes = {**store_themes, **imported_themes}
        imported_device = {
            "config": known_config,
            "panels": panels,
            "last_panel_update": now_iso(),
        }
        candidate_store = {
            **store_data,
            "devices": {
                **store_data.get("devices", {}),
                device_name: imported_device,
            },
        }
        ensure_known_theme_ids(candidate_store, candidate_themes)
        store_themes.update(imported_themes)
        store_data.setdefault("devices", {})[device_name] = imported_device
        await store.async_save(store_data)

        return self.json({**await push_panels(hass, entry_id, store_data), "device": device_name})

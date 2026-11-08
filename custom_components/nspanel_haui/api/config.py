"""Panel and device configuration: the panel store, devices, YAML import/export."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..esphome_helpers import lookup_device_registry_name
from ..haui.config_models import validate_panels
from ..storage import (
    async_remove_device,
    empty_device,
    empty_store,
    enabled_device_names,
    panel_store,
)
from .common import ApiError, api_errors, error, get_apps, now_iso, query_device

_LOGGER = logging.getLogger(__name__)


async def _validate_panels(hass: Any, data: dict, what: str) -> None:
    """Validate panel data in the executor.

    Raises:
        ApiError: With the validation error
    """
    try:
        # Pydantic model validation does importlib.metadata I/O, which must
        # not block the event loop.
        await hass.async_add_executor_job(validate_panels, data)
    except Exception as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400) from exc


async def push_panels(hass: Any, entry_id: str, data: dict) -> dict:
    """Apply saved panel data to the running apps; returns the JSON response body.

    Reloads the entry when the set of enabled devices changed (notify entities
    are created per running device at setup) or no apps are running; otherwise
    rebuilds each device's runtime config the way setup does and applies it on
    the app's worker. The editor's virtual apps (live preview, panel cards)
    get the saved config too.
    """
    from .. import _build_config_dict
    from ..websocket_api import async_reload_hosts

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

    profile_migration_saved = False
    for device_name, app in apps.items():
        if not app.device_config:
            continue
        try:
            cfg = _build_config_dict(entry.data, data, device_name=device_name)
            await app.async_run_on_worker(app.reload_config, cfg)
            profile_config = await app.async_run_on_worker(app.device.get_config)
            if _store_profile_migration(data, device_name, profile_config):
                profile_migration_saved = True
        except Exception:
            _LOGGER.exception(
                "Failed to push panel update to device '%s' for entry %s",
                device_name,
                entry_id,
            )

    if profile_migration_saved:
        await panel_store(hass, entry_id).async_save(data)

    return {"status": "ok"}


def _store_profile_migration(data: dict, device_name: str, profile_config: dict) -> bool:
    """Copy the device's migrated day/night profile values into the store data.

    Returns:
        bool: Whether a stored value changed and the store must be saved
    """
    if not profile_config.get("day_night_profiles_initialized"):
        return False
    from ..haui.device_config import find_store_device

    store_device = find_store_device(data.get("devices", {}), device_name)
    if store_device is None:
        return False
    stored_config = store_device.setdefault("config", {})
    changed = False
    for key in (
        "day_brightness_full",
        "day_brightness_dimmed",
        "day_duration_dim",
        "day_night_profiles_initialized",
    ):
        value = profile_config[key]
        if stored_config.get(key) != value:
            stored_config[key] = value
            changed = True
    return changed


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
    scheme_id = config.get("color_scheme_id", "dark")
    scheme = store_data.get("color_schemes", {}).get(scheme_id)
    if scheme is not None:
        result["color_scheme_definition"] = {"id": scheme_id, **scheme}
    return result


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
        result.setdefault("color_schemes", {})
        from ..haui.mapping.panel import get_system_panel_entries

        result["system_panels"] = await hass.async_add_executor_job(get_system_panel_entries, lang)

        # Enrich each device with friendly_name from HA device registry.
        # Always refresh — the stored value (if any) may be stale since users
        # can change a device's name via HA Settings → Devices & Services.
        for dev_key, dev_data in result.get("devices", {}).items():
            friendly_name = lookup_device_registry_name(hass, dev_key)
            dev_data["friendly_name"] = friendly_name

        return self.json(result)

    @require_admin
    @api_errors
    async def post(self, request, entry_id: str):
        """Save panel store data for a config entry."""
        hass = request.app["hass"]
        data = await request.json()
        store = panel_store(hass, entry_id)
        existing = await store.async_load() or empty_store()
        data["color_schemes"] = existing.get("color_schemes", {})
        from ..haui.mapping.color import BUILTIN_COLOR_SCHEMES, validate_color_schemes

        try:
            data["color_schemes"] = await hass.async_add_executor_job(
                validate_color_schemes, data["color_schemes"]
            )
        except Exception as exc:
            raise ApiError(str(exc), 400) from exc
        builtin_names = {scheme["name"].casefold() for scheme in BUILTIN_COLOR_SCHEMES.values()}
        if builtin_names.intersection(
            scheme["name"].casefold() for scheme in data["color_schemes"].values()
        ):
            raise ApiError("Custom scheme names must not duplicate built-in schemes", 400)
        active_ids = {
            dev.get("config", {}).get("color_scheme_id", "dark")
            for dev in data.get("devices", {}).values()
            if isinstance(dev, dict)
        }
        removed_in_use = (
            set(existing.get("color_schemes", {})) - set(data["color_schemes"])
        ) & active_ids
        if removed_in_use:
            raise ApiError("Cannot remove a color scheme selected by a device", 409)
        for device_name, device_data in data.get("devices", {}).items():
            scheme_id = device_data.get("config", {}).get("color_scheme_id", "dark")
            if scheme_id not in BUILTIN_COLOR_SCHEMES and scheme_id not in data["color_schemes"]:
                raise ApiError(f"Unknown color scheme {scheme_id!r} for device {device_name}", 400)
        # GET adds these for display; they are not part of the store.
        data.pop("system_panels", None)
        for dev_data in data.get("devices", {}).values():
            dev_data.pop("friendly_name", None)

        await _validate_panels(hass, data, "Panel config")

        # Stamp each device with the save timestamp (server-side, not from frontend)
        saved_at = now_iso()
        for dev_data in data.get("devices", {}).values():
            dev_data["last_panel_update"] = saved_at

        await store.async_save(data)
        return self.json(await push_panels(hass, entry_id, data))


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
        from ..esphome_helpers import discover_esphome_devices

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

        from ..esphome_helpers import hub_device_entry
        from ..haui.device_config import find_store_device

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

        # Validate against known config fields - strip unknown keys
        from ..haui.device_config import DEVICE_CONFIG_FIELDS

        known_config = {k: config.get(k) for k in DEVICE_CONFIG_FIELDS if k in config}
        # The update block is nested and not part of DEVICE_CONFIG_FIELDS, but
        # it is a valid per-device setting (see _build_config_dict).
        if isinstance(config.get("update"), dict):
            known_config["update"] = config["update"]
        scheme_definition = parsed.get("color_scheme_definition")
        scheme_to_import = None
        if scheme_definition is not None:
            if not isinstance(scheme_definition, dict) or not isinstance(
                scheme_definition.get("id"), str
            ):
                raise ApiError("'color_scheme_definition' must include a scheme ID", 400)
            scheme_id = scheme_definition["id"]
            from ..haui.mapping.color import validate_color_schemes

            try:
                scheme_payload = {k: v for k, v in scheme_definition.items() if k != "id"}
                validated_schemes = await hass.async_add_executor_job(
                    validate_color_schemes, {scheme_id: scheme_payload}
                )
            except Exception as exc:
                raise ApiError(str(exc), 400) from exc
            scheme_to_import = validated_schemes[scheme_id]
            known_config["color_scheme_id"] = scheme_id
        await _validate_panels(
            hass,
            {"devices": {device_name: {"config": known_config, "panels": panels}}},
            "YAML import",
        )

        store = panel_store(hass, entry_id)
        store_data = await store.async_load() or empty_store()
        store_schemes = store_data.setdefault("color_schemes", {})
        scheme_id = known_config.get("color_scheme_id", "dark")
        from ..haui.mapping.color import BUILTIN_COLOR_SCHEMES

        if (
            scheme_id not in BUILTIN_COLOR_SCHEMES
            and scheme_id not in store_schemes
            and scheme_to_import is None
        ):
            raise ApiError("Custom color scheme definition is required in device YAML", 400)
        if scheme_to_import is not None:
            existing = store_schemes.get(scheme_id)
            if existing is not None and existing != scheme_to_import:
                raise ApiError("Imported color scheme ID conflicts with an existing scheme", 409)
            store_schemes[scheme_id] = scheme_to_import
        store_data.setdefault("devices", {})[device_name] = {
            "config": known_config,
            "panels": panels,
            "last_panel_update": now_iso(),
        }
        await store.async_save(store_data)

        return self.json({**await push_panels(hass, entry_id, store_data), "device": device_name})

"""REST API for NSPanel HAUI panel configuration.

Exposes panel CRUD endpoints for the frontend HAUI Editor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers.storage import Store

from .haui.config_models import validate_panels

_LOGGER = logging.getLogger(__name__)

PANEL_STORE_VERSION = 1


def _lookup_esphome_friendly_name(hass: Any, node_name: str) -> str:
    """Look up the friendly name (entry.title) for an ESPHome device by node name.

    Returns the friendly name if found, or the node_name as fallback.
    """
    from homeassistant.util import slugify

    slugified = slugify(node_name)
    for entry in hass.config_entries.async_entries("esphome"):
        dev_name = entry.data.get("device_name", "")
        if slugify(dev_name) == slugified:
            return entry.title or node_name
    return node_name


def _read_network_entities(hass: Any, device_name: str) -> dict:
    """Read WiFi/network info from HA sensor entities for a device.

    Returns {ip, ssid, rssi} from entity states only.
    RSSI is float|None; IP and SSID are str, empty if unavailable.

    ESPHome text_sensor entities (wifi_info ip_address, ssid) are
    registered under the sensor domain in HA (Platform.SENSOR), so
    lookup uses `sensor.{slug}_ip` etc.
    """
    from homeassistant.util import slugify

    slug = slugify(device_name)

    ip_state = hass.states.get(f"sensor.{slug}_ip")
    ssid_state = hass.states.get(f"sensor.{slug}_ssid")
    rssi_state = hass.states.get(f"sensor.{slug}_rssi")

    def _val(state: Any) -> str | None:
        if state is not None and state.state not in ("unknown", "unavailable", ""):
            return state.state
        return None

    ip = _val(ip_state) or ""
    ssid = _val(ssid_state) or ""
    rssi_raw = _val(rssi_state)
    rssi = float(rssi_raw) if rssi_raw else None

    return {"ip": ip, "ssid": ssid, "rssi": rssi}


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
        translations = await hass.async_add_executor_job(get_translations, language)

        if flat == "1" or flat is True:
            return self.json(translations.get("text", {}))
        return self.json(translations)


class DeviceStatusView(HomeAssistantView):
    """REST API view returning live device status."""

    url = "/api/nspanel_haui/status/{entry_id}"
    name = "api:nspanel_haui:status"
    requires_auth = True

    async def get(self, request, entry_id: str):
        """Return live device status for a config entry.

        Query param ``device`` (optional) restricts the response to a single
        device.  When omitted an aggregate dict is returned, including both
        enabled and disabled devices (status for disabled devices is read
        directly from HA entities).
        """
        hass = request.app["hass"]
        domain_data = hass.data.get("nspanel_haui", {})
        apps = domain_data.get(entry_id)

        # Support old format (single NSPanelHAUI) for hot-reloads until
        # the next full HA restart picks up the new multi-device code.
        if apps is not None and not isinstance(apps, dict):
            return self.json(apps.get_device_status())

        if not isinstance(apps, dict):
            apps = {}

        device_name = (request.query.get("device") or "").strip()
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
        nw = _read_network_entities(hass, dev_name)

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

    async def get(self, request, entry_id: str):
        """Return the panel store data for a config entry.

        Query param ``language`` (optional, defaults to ``"en"``) controls the
        locale for pre-translating system panel string fields.
        """
        hass = request.app["hass"]
        lang = request.query.get("language", "en")
        store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        data = await store.async_load()
        result = data or {"version": 1, "devices": {}}
        from .haui.mapping.panel import get_system_panel_entries

        result["system_panels"] = await hass.async_add_executor_job(get_system_panel_entries, lang)

        # Enrich each device with friendly_name from ESPHome config entries
        for dev_key, dev_data in result.get("devices", {}).items():
            if "friendly_name" not in dev_data:
                friendly_name = _lookup_esphome_friendly_name(hass, dev_key)
                dev_data["friendly_name"] = friendly_name

        return self.json(result)

    async def post(self, request, entry_id: str):
        """Save panel store data for a config entry."""
        hass = request.app["hass"]
        data = await request.json()

        try:
            # Offload Pydantic model validation to executor thread to avoid
            # blocking the event loop (modelling triggers importlib.metadata I/O).
            await hass.async_add_executor_job(validate_panels, data)
        except Exception as exc:
            _LOGGER.warning("Panel config validation failed: %s", exc)
            return self.json({"status": "error", "message": str(exc)}, status_code=400)

        # Stamp each device with the save timestamp (server-side, not from frontend)
        now_iso = datetime.now(timezone.utc).isoformat()  # noqa: UP017
        for dev_data in data.get("devices", {}).values():
            dev_data["last_panel_update"] = now_iso

        store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        await store.async_save(data)

        # Determine which devices should be running based on incoming data
        domain_data = hass.data.get("nspanel_haui", {})
        apps = domain_data.get(entry_id)

        if apps is None:
            # Entry not yet set up; nothing to push to
            return self.json({"status": "ok"})

        if not isinstance(apps, dict) or not apps:
            # Legacy single-app format or empty apps dict; fall back to reload
            _LOGGER.info(
                "No running apps for entry %s; triggering config entry reload",
                entry_id,
            )
            await hass.config_entries.async_reload(entry_id)
            return self.json({"status": "ok", "reloaded": True})

        # Compute delta between incoming enabled set and running apps
        incoming_enabled: set[str] = {
            dev_name
            for dev_name, dev_data in data.get("devices", {}).items()
            if dev_data.get("config", {}).get("enabled", True)
        }
        running_devices: set[str] = set(apps.keys())

        newly_enabled = incoming_enabled - running_devices
        newly_disabled = running_devices - incoming_enabled
        unchanged = running_devices & incoming_enabled

        # Handle unchanged devices - update panels in-place
        from . import _create_app, _stop_app

        for device_name in unchanged:
            app = apps[device_name]
            if app.device_config:
                try:
                    await hass.async_add_executor_job(app.reload_panels, data)
                except Exception:
                    _LOGGER.exception(
                        "Failed to push panel update to device '%s' for entry %s",
                        device_name,
                        entry_id,
                    )

        # Handle newly-enabled devices - create and start app instances
        for dev_name in newly_enabled:
            entry = hass.config_entries.async_get_entry(entry_id)
            if not entry:
                _LOGGER.warning(
                    "Config entry %s not found; cannot start device '%s'",
                    entry_id,
                    dev_name,
                )
                continue
            try:
                app = await _create_app(
                    hass,
                    entry,
                    entry.data["name"],
                    dict(entry.data),
                    dict(entry.options),
                    data,
                    dev_name,
                )
                apps[dev_name] = app
            except Exception:
                _LOGGER.exception(
                    "Failed to start newly-enabled device '%s' for entry %s",
                    dev_name,
                    entry_id,
                )

        # Handle newly-disabled devices - stop and remove app instances
        for dev_name in newly_disabled:
            app = apps.pop(dev_name, None)
            if app is not None:
                await _stop_app(hass, app)

        return self.json({"status": "ok"})


class DeviceConfigView(HomeAssistantView):
    """REST API view for adding/removing devices per config entry."""

    url = "/api/nspanel_haui/devices/{entry_id}"
    name = "api:nspanel_haui:devices"
    requires_auth = True

    async def post(self, request, entry_id: str):
        """Add a new device to the config entry and panel store."""
        hass = request.app["hass"]
        body = await request.json()
        name = (body.get("name") or "").strip()
        if not name:
            return self.json(
                {"status": "error", "message": "Device name is required"}, status_code=400
            )

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return self.json(
                {"status": "error", "message": "Config entry not found"}, status_code=404
            )

        # Check for duplicate name
        existing_names = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        if name in existing_names:
            return self.json(
                {"status": "error", "message": f'Device "{name}" already exists'}, status_code=409
            )

        import copy

        from .haui.device_config import DEVICE_CONFIG

        # Add to config_entry.data["devices"]
        new_dev = copy.deepcopy(DEVICE_CONFIG)
        new_dev["name"] = name
        new_dev["enabled"] = False
        # New devices are disabled by default; enable via device settings
        if "esphome_device_id" in body:
            new_dev["esphome_device_id"] = body["esphome_device_id"]
        new_data = dict(entry.data)
        new_data.setdefault("devices", []).append(new_dev)
        hass.config_entries.async_update_entry(entry, data=new_data)

        # Add to panel store
        from homeassistant.helpers.storage import Store

        store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        panels_data = await store.async_load() or {"version": 1, "devices": {}}
        if name not in panels_data.get("devices", {}):
            panels_data.setdefault("devices", {})[name] = {
                "config": {},
                "panels": [],
            }
        await store.async_save(panels_data)

        return self.json({"status": "ok"})

    async def delete(self, request, entry_id: str):
        """Remove a device from the config entry, optionally keeping panel config.

        Query param ``name`` identifies the device.  JSON body may carry an
        optional ``keep_config`` boolean - when true the panel store is left
        untouched so that panel definitions survive device removal.
        """
        hass = request.app["hass"]
        name = (request.query.get("name") or "").strip()
        if not name:
            return self.json(
                {"status": "error", "message": "Device name is required"}, status_code=400
            )

        data = await request.json()
        keep_config = data.get("keep_config", False) if data else False

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return self.json(
                {"status": "error", "message": "Config entry not found"}, status_code=404
            )

        # Always remove from config_entry.data["devices"]
        existing_in_ce = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        if name not in existing_in_ce:
            return self.json(
                {"status": "error", "message": f'Device "{name}" not found'},
                status_code=404,
            )

        new_data = dict(entry.data)
        new_data["devices"] = [d for d in new_data.get("devices", []) if d.get("name") != name]
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.debug("Removed device %s from config_entry.data for %s", name, entry_id)

        # Remove from panel store only when keep_config is False
        if not keep_config:
            from homeassistant.helpers.storage import Store

            store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
            panels_data = await store.async_load() or {"version": 1, "devices": {}}
            had_in_store = name in panels_data.get("devices", {})
            if had_in_store:
                panels_data.get("devices", {}).pop(name, None)
                await store.async_save(panels_data)
                _LOGGER.debug("Removed device %s from panel store for %s", name, entry_id)

        return self.json({"status": "ok", "kept_config": keep_config})


class DeviceYamlView(HomeAssistantView):
    """REST API view for YAML import/export of per-device configuration."""

    url = "/api/nspanel_haui/yaml/{entry_id}"
    name = "api:nspanel_haui:yaml"
    requires_auth = True

    async def get(self, request, entry_id: str):
        """Export device configuration as YAML.

        Query param ``device`` (optional) restricts export to a single device.
        When omitted all devices are included.
        """
        hass = request.app["hass"]
        store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        data = await store.async_load() or {"version": 1, "devices": {}}
        devices = data.get("devices", {})

        device_name = (request.query.get("device") or "").strip()

        if device_name:
            if device_name not in devices:
                return self.json(
                    {"status": "error", "message": f'Device "{device_name}" not found'},
                    status_code=404,
                )
            export = _strip_empty_configs(devices[device_name])
        else:
            export = {name: _strip_empty_configs(dev_data) for name, dev_data in devices.items()}

        import yaml

        yaml_str = yaml.dump(export, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return web.Response(text=yaml_str, content_type="application/x-yaml")

    async def post(self, request, entry_id: str):
        """Import device configuration from YAML.

        Query param ``device`` specifies which device to update (required).
        The YAML body should contain the device's ``config`` and ``panels``.

        When devices already exist they are **replaced**; when absent they are
        added.  Other devices in the store are left untouched.
        """
        hass = request.app["hass"]
        device_name = (request.query.get("device") or "").strip()
        if not device_name:
            return self.json(
                {"status": "error", "message": "Query param 'device' is required"},
                status_code=400,
            )

        import yaml

        body = await request.text()
        try:
            parsed: dict = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            return self.json(
                {"status": "error", "message": f"Invalid YAML: {exc}"},
                status_code=400,
            )

        if not isinstance(parsed, dict):
            return self.json(
                {"status": "error", "message": "YAML root must be a mapping"},
                status_code=400,
            )

        # Normalize: accept bare device data or wrapped under the device name
        if "config" in parsed or "panels" in parsed:
            device_data = parsed
        elif device_name in parsed:
            device_data = parsed[device_name]
        else:
            device_data = parsed

        config = device_data.get("config", {})
        if not isinstance(config, dict):
            return self.json(
                {"status": "error", "message": "'config' must be a mapping"},
                status_code=400,
            )

        panels = device_data.get("panels", [])
        if not isinstance(panels, list):
            return self.json(
                {"status": "error", "message": "'panels' must be a list"},
                status_code=400,
            )

        # Validate against known config fields - strip unknown keys
        from .haui.device_config import DEVICE_CONFIG_FIELDS

        known_config = {k: config.get(k) for k in DEVICE_CONFIG_FIELDS if k in config}

        store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        store_data = await store.async_load() or {"version": 1, "devices": {}}
        store_data.setdefault("devices", {})[device_name] = {
            "config": known_config,
            "panels": panels,
        }
        # Stamp with current save time
        now_iso = datetime.now(timezone.utc).isoformat()  # noqa: UP017
        store_data.setdefault("devices", {})[device_name]["last_panel_update"] = now_iso

        await store.async_save(store_data)

        # Push update to the running integration instances
        domain_data = hass.data.get("nspanel_haui", {})
        apps = domain_data.get(entry_id)
        if apps and isinstance(apps, dict):
            if apps:
                for dname, dapp in apps.items():
                    try:
                        if dapp.device_config:
                            await hass.async_add_executor_job(dapp.reload_panels, store_data)
                    except Exception:
                        _LOGGER.exception(
                            "Failed to push YAML import to device '%s' for entry %s",
                            dname,
                            entry_id,
                        )
            else:
                _LOGGER.info(
                    "No running apps for entry %s; triggering config entry reload",
                    entry_id,
                )
                await hass.config_entries.async_reload(entry_id)
                return self.json({"status": "ok", "device": device_name, "reloaded": True})

        return self.json({"status": "ok", "device": device_name})


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
        name (case-insensitive).  When omitted returns all icon names.
        Maximum 200 results to keep responses small.
        """
        if IconSearchView._icons is None:
            from .haui.mapping.icon_names import ICON_NAMES

            IconSearchView._icons = ICON_NAMES

        query = (request.query.get("q") or "").strip().lower()
        if query:
            results = [name for name in IconSearchView._icons if query in name]
        else:
            results = IconSearchView._icons

        return self.json(results[:200])


class DeviceUpdateDisplayView(HomeAssistantView):
    """REST API endpoint to trigger display refresh on one or all devices."""

    url = "/api/nspanel_haui/update_display/{entry_id}"
    name = "api:nspanel_haui:update_display"
    requires_auth = True

    async def post(self, request, entry_id: str):
        """Refresh the display for the specified device (or all devices).

        JSON body may carry an optional ``device`` field (device name, or ``*``
        for all devices).  When omitted defaults to ``*``.
        """
        hass = request.app["hass"]
        body = await request.json() or {}
        device_name = (body.get("device") or "*").strip()

        domain_data = hass.data.get("nspanel_haui", {})
        apps = domain_data.get(entry_id)

        if not isinstance(apps, dict):
            return self.json(
                {"status": "error", "message": "No running devices"},
                status_code=400,
            )

        if device_name and device_name != "*":
            app = apps.get(device_name)
            if app is None:
                return self.json(
                    {"status": "error", "message": f'Device "{device_name}" not found'},
                    status_code=404,
                )
            await hass.async_add_executor_job(app.update_display)
            return self.json({"status": "ok", "devices_updated": [device_name]})

        # Update all devices
        updated: list[str] = []
        for dname, dapp in apps.items():
            try:
                await hass.async_add_executor_job(dapp.update_display)
                updated.append(dname)
            except Exception:
                _LOGGER.exception("Failed to update display for device '%s'", dname)

        return self.json({"status": "ok", "devices_updated": updated})

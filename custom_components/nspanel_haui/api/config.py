"""Panel and device configuration: the panel store, devices, YAML import/export."""

from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from typing import Any

import yaml
from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..haui.config_models import PanelValidationError, validate_device_config, validate_panels
from ..haui.device_config import DEVICE_CONFIG_FIELDS
from ..haui.mapping.color import BUILTIN_THEMES, validate_themes
from ..hub.esphome_helpers import lookup_device_registry_name
from ..hub.storage import (
    async_remove_device,
    empty_device,
    empty_store,
    migrate_device_config_keys,
    normalize_device_order,
    panel_store,
)
from .common import (
    ApiError,
    api_errors,
    ensure_known_theme_ids,
    error,
    json_object,
    now_iso,
    query_device,
)
from .panel_edits import edit_panels

_LOGGER = logging.getLogger(__name__)


async def _validate(hass: Any, what: str, validator: Callable[..., Any], *args: Any) -> None:
    """Run a config validator off the event loop and answer a failure with a 400.

    Args:
        hass: Home Assistant
        what: Names the data in the log
        validator: ``validate_panels`` or ``validate_device_config``
        args: The validator's arguments

    Raises:
        ApiError: With the validator's message; a refused panel adds its
            ``errors`` list to the response body
    """
    try:
        # Pydantic validation does importlib.metadata I/O, which must not
        # block the event loop.
        await hass.async_add_executor_job(validator, *args)
    except PanelValidationError as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400, {"errors": exc.errors}) from exc
    except Exception as exc:
        _LOGGER.warning("%s validation failed: %s", what, exc)
        raise ApiError(str(exc), 400) from exc


def _known_device_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return only supported settings, including the nested update settings."""
    migrate_device_config_keys(config)
    known = {key: config[key] for key in DEVICE_CONFIG_FIELDS if key in config}
    if isinstance(config.get("update"), dict):
        known["update"] = config["update"]
    return known


def _keep_skipped_firmware_version(config: dict[str, Any], stored: dict[str, Any]) -> None:
    """Carry the stored skipped firmware version into ``config``.

    Only *Skip this version* (``UpdateControlView``) writes the skip, so a
    settings save cannot undo it.
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


def _store_device(data: dict[str, Any], device: str) -> dict[str, Any]:
    """Return one stored device or raise a not-found API error."""
    devices = data.get("devices", {})
    if device not in devices:
        raise ApiError(f'Device "{device}" not found', 404)
    return devices[device]


def _strip_empty_configs(dev_data: dict[str, Any]) -> dict[str, Any]:
    """Return a device's settings without the ones it never set, plus its panels."""
    config = dict(dev_data.get("config", {}))
    cleaned = {k: v for k, v in config.items() if v is not None}
    result: dict[str, Any] = {}
    if cleaned:
        result["config"] = cleaned
    result["panels"] = list(dev_data.get("panels", []))
    return result


def _panel_keys(panels: list[Any]) -> set[str]:
    """Return the keys a stored panel list names."""
    return {str(panel.get("key", "")) for panel in panels if isinstance(panel, dict)}


def _keep_panel_refs(config: dict[str, Any], keep: Callable[[str], bool]) -> None:
    """Drop every home and idle reference to a panel key ``keep`` refuses.

    ``home_panel``, ``idle_panel`` and ``idle_panel_extra`` name panels of the
    device these settings belong to; a dangling reference warns on every load.
    """
    home = config.get("home_panel")
    if isinstance(home, str) and home and not keep(home):
        config["home_panel"] = ""
    idle = config.get("idle_panel")
    if isinstance(idle, list):
        config["idle_panel"] = [key for key in idle if keep(key)]
    elif isinstance(idle, str) and idle and not keep(idle):
        config["idle_panel"] = ""
    extra = config.get("idle_panel_extra")
    if isinstance(extra, str) and extra:
        config["idle_panel_extra"] = ", ".join(
            key for key in (part.strip() for part in extra.split(",")) if keep(key)
        )


def _device_yaml_data(dev_data: dict[str, Any], store_data: dict[str, Any]) -> dict[str, Any]:
    """Return a device's config and panels, with the custom themes they use."""
    result = _strip_empty_configs(dev_data)
    config = result.get("config", {})
    themes = store_data.get("themes", {})
    active_id = config.get("theme_id", "dark")
    used = {
        active_id,
        *(
            panel.get("theme_id")
            for panel in result["panels"]
            if isinstance(panel, dict) and panel.get("theme_id")
        ),
    }
    definitions = [
        {"id": theme_id, **themes[theme_id]} for theme_id in sorted(used) if theme_id in themes
    ]
    if definitions:
        result["theme_definitions"] = definitions
    if active_id in themes:
        result["theme_definition"] = {"id": active_id, **themes[active_id]}
    return result


class PanelConfigView(HomeAssistantView):
    """Read the complete panel store of one config entry."""

    url = "/api/nspanel_haui/panels/{entry_id}"
    name = "api:nspanel_haui:panels"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the panel store data for a config entry.

        Query param ``language`` (optional, defaults to ``"en"``) selects the
        locale of the translated system panel fields.
        """
        from ..haui.mapping.panel import get_system_panel_entries

        hass = request.app["hass"]
        lang = request.query.get("language", "en")
        store = panel_store(hass, entry_id)
        data = await store.async_load()
        result = data or empty_store()
        result.setdefault("themes", {})
        normalize_device_order(result)
        result["system_panels"] = await hass.async_add_executor_job(get_system_panel_entries, lang)

        # Read the name from the device registry: it changes there, not in the store.
        for dev_key, dev_data in result.get("devices", {}).items():
            dev_data["friendly_name"] = lookup_device_registry_name(hass, dev_key)

        return self.json(result)


class DeviceConfigView(HomeAssistantView):
    """Add, list and remove the devices of one config entry."""

    url = "/api/nspanel_haui/devices/{entry_id}"
    name = "api:nspanel_haui:devices"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the discovered ESPHome HAUI devices available for adding."""
        from ..hub.esphome_helpers import discover_esphome_devices

        hass = request.app["hass"]
        discovered = await discover_esphome_devices(hass)
        return self.json({"devices": discovered})

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Add the devices a batch body ``{devices: [{name, enabled, ...}, ...]}`` names.

        A newly enabled device starts once the entry's update listener reloads
        it.
        """
        hass = request.app["hass"]
        body = await json_object(request)

        devices_to_add = body.get("devices")
        if not isinstance(devices_to_add, list):
            raise ApiError("Body must be {'devices': [...]}", 400)

        from ..haui.device_config import find_store_device
        from ..hub.esphome_helpers import hub_device_entry

        async with edit_panels(hass, entry_id) as edit:
            entry = edit.entry
            existing_names = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
            new_devices: list[dict[str, Any]] = []
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

            # Settings, ``enabled`` included, live in the store; a store-only
            # device keeps the ones it still has.
            panels_data = await edit.load()
            store_devices = panels_data.setdefault("devices", {})
            for name, enabled in enabled_by_name.items():
                store_dev = find_store_device(store_devices, name)
                if store_dev is None:
                    store_dev = store_devices[name] = empty_device()
                store_dev.setdefault("config", {})["enabled"] = enabled
            normalize_device_order(panels_data)
            new_data = {
                **entry.data,
                "devices": [*entry.data.get("devices", []), *new_devices],
                "removed_devices": [
                    n for n in entry.data.get("removed_devices", []) if n not in names_added
                ],
            }
            await edit.save(panels_data, apply=False, entry_data=new_data)

        return self.json({"status": "ok", "devices_added": names_added})

    @require_admin
    @api_errors
    async def delete(self, request: web.Request, entry_id: str) -> web.Response:
        """Remove the device the ``name`` query param names, with its store entry."""
        hass = request.app["hass"]
        name = (request.query.get("name") or "").strip()
        if not name:
            raise ApiError("Device name is required", 400)

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            raise ApiError("Config entry not found", 404)

        if not await async_remove_device(hass, entry, name):
            raise ApiError(f'Device "{name}" not found', 404)

        return self.json({"status": "ok"})


class DeviceSettingsView(HomeAssistantView):
    """Read or replace the stored settings of one device."""

    url = "/api/nspanel_haui/devices/{entry_id}/{device}"
    name = "api:nspanel_haui:device_settings"
    requires_auth = True

    @require_admin
    @api_errors
    async def get(self, request: web.Request, entry_id: str, device: str) -> web.Response:
        """Return one device's stored settings."""
        hass = request.app["hass"]
        data = await panel_store(hass, entry_id).async_load() or empty_store()
        config = copy.deepcopy(_store_device(data, device).get("config") or {})
        migrate_device_config_keys(config)
        return self.json({"device": device, "config": config})

    @require_admin
    @api_errors
    async def put(self, request: web.Request, entry_id: str, device: str) -> web.Response:
        """Replace one device's settings; its panels and the other devices stay."""
        hass = request.app["hass"]
        body = await json_object(request)
        config = body.get("config")
        if not isinstance(config, dict):
            raise ApiError("Body must be {'config': {...}}", 400)

        known = _known_device_config(config)
        await _validate(hass, "Device config", validate_device_config, known)
        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            store_dev = _store_device(data, device)
            _keep_skipped_firmware_version(known, store_dev.get("config") or {})

            theme_id = known.get("theme_id", "dark")
            if theme_id not in {**data.get("themes", {}), **BUILTIN_THEMES}:
                raise ApiError(f"Unknown color theme {theme_id!r}", 400)

            store_dev["config"] = known
            pushed = await edit.save(data, devices=(device,))
        return self.json(
            {
                "status": "ok",
                "device": device,
                "config": known,
                **pushed,
            }
        )


class DevicePanelsView(HomeAssistantView):
    """Replace the panels of one device; the store GET returns every device's."""

    url = "/api/nspanel_haui/panels/{entry_id}/{device}"
    name = "api:nspanel_haui:device_panels"
    requires_auth = True

    @require_admin
    @api_errors
    async def put(self, request: web.Request, entry_id: str, device: str) -> web.Response:
        """Replace one device's panels; its settings and the other devices stay."""
        hass = request.app["hass"]
        body = await json_object(request)
        panels = body.get("panels")
        if not isinstance(panels, list):
            raise ApiError("Body must be {'panels': [...]}", 400)

        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            store_dev = _store_device(data, device)
            await _validate(
                hass,
                f"Panels of {device}",
                validate_panels,
                {"devices": {device: {"panels": panels}}},
                data,
            )
            candidate = {
                **data,
                "devices": {
                    **data.get("devices", {}),
                    device: {**store_dev, "panels": panels},
                },
            }
            ensure_known_theme_ids(candidate, data.get("themes", {}))
            # A removed panel leaves no home or idle reference behind, so the
            # returned config is what the editor shows.
            removed = _panel_keys(store_dev.get("panels") or []) - _panel_keys(panels)
            _keep_panel_refs(store_dev.setdefault("config", {}), lambda key: key not in removed)
            store_dev["panels"] = panels
            store_dev["last_panel_update"] = now_iso()
            pushed = await edit.save(data, devices=(device,))
        return self.json(
            {
                "status": "ok",
                "device": device,
                "config": store_dev.get("config") or {},
                **pushed,
            }
        )


def _free_panel_key(panels: list[Any], key: str, panel_type: str) -> str:
    """Return ``key`` when no panel in ``panels`` uses it, else a free ``{type}_{n}``.

    Keys are compared without case, as the editor does.
    """
    used = {str(panel.get("key", "")).lower() for panel in panels if isinstance(panel, dict)}
    if key.lower() not in used:
        return key
    index = 0
    while f"{panel_type}_{index}".lower() in used:
        index += 1
    return f"{panel_type}_{index}"


class DevicePanelMoveView(HomeAssistantView):
    """Move one of a device's panels to another device of the same hub."""

    url = "/api/nspanel_haui/panels/{entry_id}/{device}/move"
    name = "api:nspanel_haui:device_panel_move"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str, device: str) -> web.Response:
        """Move the panel ``key`` to the device ``to``, in one save of both devices.

        The panel keeps its key unless the target already uses it; it then gets
        a free ``{type}_{n}`` key, which the response names. A popup a device
        extends stays with that device. The source device's home and idle
        settings drop the moved key, but its gestures keep the user's entries.
        """
        from ..haui.mapping.panel import POPUP_PANEL_MAPPING

        hass = request.app["hass"]
        body = await json_object(request)
        key = body.get("key")
        target = body.get("to")
        if not isinstance(key, str) or not key or not isinstance(target, str) or not target:
            raise ApiError("Body must be {'key': str, 'to': str}", 400)
        if target == device:
            raise ApiError("The panel is already on this device", 400)

        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            source_dev = _store_device(data, device)
            target_dev = _store_device(data, target)
            source_panels = list(source_dev.get("panels") or [])
            panel = next(
                (
                    entry
                    for entry in source_panels
                    if isinstance(entry, dict) and entry.get("key") == key
                ),
                None,
            )
            if panel is None:
                raise ApiError(f'Panel "{key}" not found on "{device}"', 404)
            if key in POPUP_PANEL_MAPPING:
                raise ApiError("A popup a device extends cannot be moved", 400)

            target_panels = list(target_dev.get("panels") or [])
            new_key = _free_panel_key(target_panels, key, str(panel.get("type") or "panel"))
            source_panels.remove(panel)
            target_panels.append({**panel, "key": new_key})

            await _validate(
                hass,
                f"Moving {key} from {device} to {target}",
                validate_panels,
                {"devices": {device: {"panels": source_panels}, target: {"panels": target_panels}}},
                data,
            )
            candidate = {
                **data,
                "devices": {
                    **data.get("devices", {}),
                    device: {**source_dev, "panels": source_panels},
                    target: {**target_dev, "panels": target_panels},
                },
            }
            ensure_known_theme_ids(candidate, data.get("themes", {}))
            updated = now_iso()
            # The source device loses the panel, so its home and idle settings
            # cannot keep naming it.
            _keep_panel_refs(source_dev.setdefault("config", {}), lambda ref: ref != key)
            source_dev["panels"] = source_panels
            source_dev["last_panel_update"] = updated
            target_dev["panels"] = target_panels
            target_dev["last_panel_update"] = updated
            pushed = await edit.save(data, devices=(device, target))
        return self.json(
            {
                **pushed,
                "status": "ok",
                "key": new_key,
                "panels": {device: source_panels, target: target_panels},
                "config": source_dev.get("config") or {},
            }
        )


class DeviceOrderView(HomeAssistantView):
    """Store the editor's device order; the entry itself orders the runtime devices."""

    url = "/api/nspanel_haui/device_order/{entry_id}"
    name = "api:nspanel_haui:device_order"
    requires_auth = True

    @require_admin
    @api_errors
    async def put(self, request: web.Request, entry_id: str) -> web.Response:
        """Replace and normalize the order the editor lists the devices in."""
        hass = request.app["hass"]
        body = await json_object(request)
        device_order = body.get("device_order")
        if not isinstance(device_order, list) or any(
            not isinstance(name, str) for name in device_order
        ):
            raise ApiError("Body must be {'device_order': [names]}", 400)

        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            data["device_order"] = list(device_order)
            normalize_device_order(data)
            await edit.save(data, apply=False)
        return self.json({"status": "ok", "device_order": data["device_order"]})


class DeviceYamlView(HomeAssistantView):
    """Export and import the configuration of one device as YAML."""

    url = "/api/nspanel_haui/yaml/{entry_id}"
    name = "api:nspanel_haui:yaml"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Export one device's configuration, or every device's without ``device``."""
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

        yaml_str = yaml.dump(export, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return web.Response(text=yaml_str, content_type="application/x-yaml")

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Import the YAML body as the configuration of the ``device`` query param.

        The body names ``config`` and ``panels`` at its top level, plus the
        custom themes the configuration uses. Other devices are left untouched.
        """
        hass = request.app["hass"]
        device_name = query_device(request)
        if not device_name:
            raise ApiError("Query param 'device' is required", 400)

        body = await request.text()
        try:
            parsed: dict[str, Any] = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            raise ApiError(f"Invalid YAML: {exc}", 400) from exc

        if not isinstance(parsed, dict):
            raise ApiError("YAML root must be a mapping", 400)

        # The device's settings and panels sit at the top level of the file.
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

        known_config = _known_device_config(config)
        theme_definition = parsed.get("theme_definition")
        theme_definitions = parsed.get("theme_definitions") or []
        if not isinstance(theme_definitions, list):
            raise ApiError("'theme_definitions' must be a list", 400)
        if theme_definition is not None:
            if not isinstance(theme_definition, dict):
                raise ApiError("'theme_definition' must include a theme ID", 400)
            theme_definitions = [theme_definition, *theme_definitions]
        raw_theme_definitions: dict[str, dict[str, Any]] = {}
        active_theme_id = None
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
                active_theme_id = theme_id

        imported_themes = {}
        if raw_theme_definitions:
            try:
                imported_themes = await hass.async_add_executor_job(
                    validate_themes, raw_theme_definitions
                )
            except ValueError as exc:
                raise ApiError(str(exc), 400) from exc
        if active_theme_id and "theme_id" not in known_config:
            known_config["theme_id"] = active_theme_id
        await _validate(
            hass,
            "YAML import",
            validate_panels,
            {"devices": {device_name: {"config": known_config, "panels": panels}}},
        )

        async with edit_panels(hass, entry_id) as edit:
            store_data = await edit.load()
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
            pushed = await edit.save(store_data)

        return self.json({**pushed, "device": device_name})


# The sections a copy can take from one device: its panels, its stored settings
# and its update settings.
COPY_SECTIONS: frozenset[str] = frozenset({"panels", "settings", "update"})


def _copied_config(
    source: dict[str, Any],
    target: dict[str, Any],
    sections: set[str],
    panels: list[Any],
) -> dict[str, Any]:
    """Return the target device's settings after copying the picked sections.

    Copying the settings replaces every device setting the store holds; whether
    the device runs belongs to the target, so ``enabled`` stays. The ``update``
    block is a section of its own, and the target always keeps its own skipped
    firmware version: only *Skip this version* writes that.
    """
    config = copy.deepcopy(target)
    if "settings" in sections:
        for key in DEVICE_CONFIG_FIELDS:
            if key != "enabled":
                config.pop(key, None)
        config.update(
            {
                key: copy.deepcopy(value)
                for key, value in source.items()
                if key in DEVICE_CONFIG_FIELDS and key != "enabled"
            }
        )
    if "update" in sections:
        config["update"] = copy.deepcopy(source.get("update") or {})
    known = _known_device_config(config)
    _keep_skipped_firmware_version(known, target)
    if "settings" in sections:
        _keep_panel_refs(known, _panel_keys(panels).__contains__)
    return known


class DeviceCopyView(HomeAssistantView):
    """Copy the picked sections of one device onto other devices of the hub."""

    url = "/api/nspanel_haui/copy/{entry_id}"
    name = "api:nspanel_haui:device_copy"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Write the picked sections of the device ``from`` onto each device in ``to``.

        Body: ``{"from": str, "to": [str], "sections": [str]}``, a section being
        one of ``panels``, ``settings`` and ``update``. Every target is written
        in one save, so a copy that breaks a rule changes nothing.
        """
        hass = request.app["hass"]
        body = await json_object(request)
        source = body.get("from")
        targets = body.get("to")
        sections = body.get("sections")
        if not isinstance(source, str) or not source:
            raise ApiError("Body must be {'from': str, 'to': [str], 'sections': [str]}", 400)
        if (
            not isinstance(targets, list)
            or not targets
            or any(not isinstance(name, str) or not name for name in targets)
        ):
            raise ApiError("'to' must be a non-empty list of device names", 400)
        # The same device twice in one request is one copy.
        targets = list(dict.fromkeys(targets))
        if source in targets:
            raise ApiError("A device cannot be copied onto itself", 400)
        if not isinstance(sections, list) or not sections:
            raise ApiError(f"'sections' must name one of {sorted(COPY_SECTIONS)}", 400)
        unknown = sorted(set(sections) - COPY_SECTIONS)
        if unknown:
            raise ApiError(f"Unknown copy section {unknown[0]!r}", 400)
        chosen = set(sections)

        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            source_dev = _store_device(data, source)
            source_panels = copy.deepcopy(list(source_dev.get("panels") or []))
            source_config = copy.deepcopy(source_dev.get("config") or {})

            candidates: dict[str, dict[str, Any]] = {}
            for name in targets:
                target_dev = _store_device(data, name)
                panels = (
                    copy.deepcopy(source_panels)
                    if "panels" in chosen
                    else list(target_dev.get("panels") or [])
                )
                candidates[name] = {
                    "config": _copied_config(
                        source_config, target_dev.get("config") or {}, chosen, panels
                    ),
                    "panels": panels,
                }

            what = f"Copy of {source} onto {', '.join(targets)}"
            await _validate(
                hass,
                what,
                validate_panels,
                {
                    "devices": {
                        name: {"config": dev["config"], "panels": dev["panels"]}
                        for name, dev in candidates.items()
                    }
                },
                data,
            )

            candidate = {
                **data,
                "devices": {
                    **data.get("devices", {}),
                    **{
                        name: {**_store_device(data, name), **dev}
                        for name, dev in candidates.items()
                    },
                },
            }
            ensure_known_theme_ids(candidate, data.get("themes", {}))

            updated = now_iso()
            for name, dev in candidates.items():
                stored = _store_device(data, name)
                stored["config"] = dev["config"]
                if "panels" in chosen:
                    stored["panels"] = dev["panels"]
                    stored["last_panel_update"] = updated
            pushed = await edit.save(data, devices=targets)

        return self.json({**pushed, "status": "ok", "devices": list(targets)})

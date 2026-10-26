"""NSPanel HAUI custom integration for Home Assistant."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

PLATFORMS: list[str] = ["notify", "sensor"]

# Config helpers - moved to haui/device_config.py for single source of truth
from .haui.device_config import (  # noqa: E402
    apply_panel_store,
    populate_devices_from_store,
    validate_config,
)


def _build_config_dict(
    data: dict[str, Any],
    panels: dict[str, Any] | None = None,
    *,
    device_name: str = "",
) -> dict[str, Any]:
    """Build the combined config dict from three independent layers.

    - ``data``: hub name + device identity (from config_entry.data)
    - ``panels``: device settings and panel definitions per device (from
      PanelStorage)
    - ``device_name``: which device in ``data["devices"]`` this config is for.
      When provided, only that device is included and panel store data is
      scoped to it.
    """
    from .haui.device_config import DEVICE_CONFIG, DEVICE_CONFIG_FIELDS
    from .haui.mapping.const import DEFAULT_CONFIG

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["device"]["name"] = device_name or data.get("name", "")

    devices = data.get("devices", [])
    if devices:
        cfg["devices"] = copy.deepcopy(devices)

    # When device_name is given, filter cfg["devices"] to only that device
    # so _apply_panel_store and downstream code see a single-device config.
    if device_name:
        cfg_devices = cfg.get("devices", [])
        filtered = [d for d in cfg_devices if d.get("name") == device_name]
        if not filtered:
            # Device not found in the data list — create a minimal entry
            # so the config is still valid for the runtime app.
            filtered = [{"name": device_name}]
        cfg["devices"] = filtered

    store_devices = panels.get("devices", {}) if panels else {}
    if store_devices:
        apply_panel_store(cfg, store_devices, DEVICE_CONFIG_FIELDS)

    populate_devices_from_store(cfg, store_devices, DEVICE_CONFIG_FIELDS)

    # Collect panels from the (now single) runtime device.
    cfg_devices = cfg.get("devices", [])
    if cfg_devices:
        all_panels = list(cfg_devices[0].get("panels", []))
        if all_panels:
            cfg["panels"] = all_panels

    # Ensure every device entry has all DEVICE_CONFIG keys
    for dev in cfg.get("devices", []):
        for key, val in DEVICE_CONFIG.items():
            if key not in dev:
                dev[key] = copy.deepcopy(val)

    # Filter out disabled devices - runs after store merge and defaults fill
    # so store overrides of "enabled" are respected.
    cfg["devices"] = [d for d in cfg.get("devices", []) if d.get("enabled", True)]
    if not cfg.get("devices"):
        _LOGGER.warning(
            "No enabled devices found in config; HAUI will skip all runtime device management"
        )
    validate_config(cfg)
    return cfg


async def _link_esphome_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    ha_device_id: str,
    dev_name: str,
) -> None:
    """Link the ESPHome device to the nspanel_haui integration.

    Adds an ``nspanel_haui`` identifier to the existing ESPHome device entry and
    attaches our config entry so the device shows up in the nspanel_haui hub
    page. The device selector (integration: nspanel_haui) in services.yaml
    matches the extra identifier, and clicking the device in the hub page goes to
    the ESPHome device (its primary config entry).

    Safe to call when the device is already linked (idempotent).
    """
    from homeassistant.helpers import device_registry as dr

    dev_reg = dr.async_get(hass)
    esphome_dev = dev_reg.async_get(ha_device_id)
    if not esphome_dev:
        return

    nspanel_identifier = ("nspanel_haui", dev_name)
    has_identifier = nspanel_identifier in esphome_dev.identifiers
    has_config_entry = esphome_dev.config_entry_id == entry.entry_id

    if has_identifier and has_config_entry:
        return  # already linked

    kwargs: dict[str, Any] = {}
    if not has_identifier:
        kwargs["merge_identifiers"] = {nspanel_identifier}
    if not has_config_entry:
        kwargs["add_config_entry_id"] = entry.entry_id
    dev_reg.async_update_device(ha_device_id, **kwargs)


async def _create_app(
    hass: HomeAssistant,
    entry: ConfigEntry,
    name: str,
    data: dict[str, Any],
    panels: dict[str, Any] | None,
    dev_name: str,
) -> NSPanelHAUI:
    """Create and initialize a single NSPanelHAUI app instance for a device.

    Builds the device config from the config layers (data,
    panels), resolves the ESPHome HA device_id, adds an ``nspanel_haui``
    identifier to the ESPHome device entry so the device selector
    (integration: nspanel_haui) can find it, initializes the app on the
    executor thread, and returns the ready-to-use instance.

    The caller is responsible for storing the returned app in the running
    apps dict (hass.data[DOMAIN][entry.entry_id][dev_name]).
    """
    from .esphome_helpers import resolve_ha_device_id
    from .nspanel_haui import NSPanelHAUI

    cfg = _build_config_dict(data, panels, device_name=dev_name)
    ha_device_id = resolve_ha_device_id(hass, dev_name)
    app = NSPanelHAUI(
        hass,
        name,
        cfg,
        runtime_device_name=dev_name,
        ha_device_id=ha_device_id,
    )
    app._last_panel_update = (
        panels.get("devices", {}).get(dev_name, {}).get("last_panel_update") if panels else None
    )
    await app.async_run_on_worker(app.initialize)

    # Link the ESPHome device to our integration so it shows in the hub page
    # and the device selector (integration: nspanel_haui) can find it.
    if ha_device_id:
        await _link_esphome_device(hass, entry, ha_device_id, dev_name)

    _LOGGER.info("NSPanel HAUI instance for device '%s' started", dev_name)
    return app


async def _stop_app(app: NSPanelHAUI) -> bool:
    """Stop a single NSPanelHAUI app instance.

    Returns ``True`` on success, ``False`` on error.
    """
    try:
        await app.async_run_on_worker(app.stop)
        return True
    except Exception:
        _LOGGER.exception(
            "Error stopping NSPanel HAUI instance for device '%s'",
            app._runtime_device_name,
        )
        return False


def _device_issue_id(device_name: str) -> str:
    """Return the issue id used for a device startup failure."""
    from homeassistant.util import slugify

    from .repairs import DEVICE_START_FAILED

    return f"{DEVICE_START_FAILED}_{slugify(device_name)}"


def _create_device_start_failed_issue(
    hass: HomeAssistant,
    device_name: str,
    error: BaseException,
) -> None:
    """Surface a failed device startup in the Repairs UI."""
    from homeassistant.helpers import issue_registry as ir

    ir.async_create_issue(
        hass,
        DOMAIN,
        _device_issue_id(device_name),
        is_fixable=True,
        is_persistent=False,
        learn_more_url="https://happydasch.github.io/nspanel_haui/troubleshooting/",
        severity=ir.IssueSeverity.ERROR,
        translation_key="device_start_failed",
        translation_placeholders={
            "device": device_name,
            "error": str(error) or "Unknown error",
        },
    )


def _delete_device_start_failed_issue(hass: HomeAssistant, device_name: str) -> None:
    """Remove the startup-failure issue once a device starts successfully."""
    from homeassistant.helpers import issue_registry as ir

    ir.async_delete_issue(hass, DOMAIN, _device_issue_id(device_name))


def _create_hub_idle_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Warn in the Repairs UI when the hub has no enabled devices."""
    from homeassistant.helpers import issue_registry as ir

    ir.async_create_issue(
        hass,
        DOMAIN,
        "hub_idle",
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="hub_idle",
        translation_placeholders={"hub": entry.title},
    )


def _delete_hub_idle_issue(hass: HomeAssistant) -> None:
    """Remove the idle-hub warning once at least one device is enabled."""
    from homeassistant.helpers import issue_registry as ir

    ir.async_delete_issue(hass, DOMAIN, "hub_idle")


async def _trigger_haui_discovery(hass: HomeAssistant) -> bool:
    """Surface HAUI as a discovery suggestion on the HA dashboard.

    Bails out immediately when a hub entry already exists — we do not
    auto-modify existing hubs from the registry listener; device add/
    remove happens via the HAUI Editor.

    Returns ``True`` when a discovery flow was scheduled.
    """
    if hass.config_entries.async_entries(DOMAIN):
        return False

    from .esphome_helpers import discover_esphome_devices

    discovered = await discover_esphome_devices(hass)
    if not discovered:
        return False

    from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
    from homeassistant.helpers import discovery_flow

    discovery_flow.async_create_flow(
        hass,
        DOMAIN,
        {"source": SOURCE_INTEGRATION_DISCOVERY},
        {"count": len(discovered)},
    )
    return True


# ── Auto-discovery ───────────────────────────────────────────────
_DISCOVERY_INITIALIZED = False


async def _register_discovery(hass: HomeAssistant) -> None:
    """Register the persistent device registry listener once per HA session.

    Listens for new ESPHome HAUI devices appearing in the device registry
    and auto-adds them to the hub.  The listener stays alive for the
    entire HA session so that devices added later (e.g. via ESPHome
    integration after the hub was created) are picked up automatically.

    Must be called from ``async_setup`` (integration-level), not
    ``async_setup_entry``, so it runs once at startup regardless of
    whether a hub entry exists yet.
    """
    global _DISCOVERY_INITIALIZED
    if _DISCOVERY_INITIALIZED:
        return
    _DISCOVERY_INITIALIZED = True

    from homeassistant.core import callback as ha_callback
    from homeassistant.helpers import device_registry as dr

    from .esphome_helpers import is_haui_device, resolve_ha_device_id

    def _reload_if_device_resolved(hub_entry: ConfigEntry) -> None:
        # An app started before its ESPHome device was registered has no device
        # id: no events reach it, its device isn't linked and the notify platform
        # skipped it. Reloading re-creates the app, which resolves and links it.
        apps = hass.data.get(DOMAIN, {}).get(hub_entry.entry_id) or {}
        if any(
            app._ha_device_id is None and resolve_ha_device_id(hass, dev_name)
            for dev_name, app in apps.items()
        ):
            hass.config_entries.async_schedule_reload(hub_entry.entry_id)

    @ha_callback
    def _on_device_registry_change(event: Any) -> None:
        """Persistent listener: add new HAUI devices and pick up late-registered ones."""
        data = event.data if isinstance(event.data, dict) else {}
        if data.get("action") not in ("create", "update"):
            return
        device_id = data.get("device_id", "")
        if not device_id:
            return
        dev_entry = dr.async_get(hass).async_get(device_id)
        if not dev_entry:
            return
        # A device belongs to a single config entry; config_entry_id replaces
        # the deprecated config_entries set.
        cid = dev_entry.config_entry_id
        if not cid:
            return
        entry = hass.config_entries.async_get_entry(cid)
        if entry and entry.domain == "esphome" and is_haui_device(hass, entry):
            for hub_entry in hass.config_entries.async_entries(DOMAIN):
                hass.async_create_task(_auto_add_unconfigured_devices(hass, hub_entry))
                _reload_if_device_resolved(hub_entry)

    hass.bus.async_listen(
        dr.EVENT_DEVICE_REGISTRY_UPDATED,
        _on_device_registry_change,
    )

    # Bootstrap: if no hub exists yet, trigger the initial discovery flow
    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(_trigger_haui_discovery(hass))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NSPanel HAUI from a config entry.

    Loads panels from the HA Store, then creates one NSPanelHAUI app
    per enabled device in entry.data["devices"].  Events are routed to
    the correct app via HA device_id filtering.
    """

    # Devices whose ESPHome entry registers later are picked up by the
    # session-wide registry listener (_register_discovery).
    from .storage import PanelStorage

    hass.data.setdefault(DOMAIN, {})
    name: str = entry.data["name"]

    panels: dict[str, Any] | None
    try:
        panel_storage = PanelStorage(hass, entry.entry_id, entry)
        panels = await panel_storage.load()
    except Exception:
        _LOGGER.warning(
            "NSPanel HAUI '%s': could not load panel store, using defaults",
            name,
            exc_info=True,
        )
        panels = {"version": 1, "devices": {}}

    data = dict(entry.data)

    # ── create apps ────────────────────────────────────────────────────
    # One app per enabled device; ``enabled`` lives in the device's store config.
    from .storage import enabled_device_names

    apps: dict = {}

    for device_name in enabled_device_names(data, panels):
        try:
            apps[device_name] = await _create_app(hass, entry, name, data, panels, device_name)
        except Exception as exc:
            _LOGGER.exception(
                "NSPanel HAUI '%s': failed to start device '%s'",
                name,
                device_name,
            )
            _create_device_start_failed_issue(hass, device_name, exc)
        else:
            _delete_device_start_failed_issue(hass, device_name)

    hass.data[DOMAIN][entry.entry_id] = apps
    # Forwarded even for an idle hub so unload always has platforms to unload.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    if not apps:
        # Devices added later trigger a reload which re-runs this setup.
        _create_hub_idle_issue(hass, entry)
        _LOGGER.warning("NSPanel HAUI '%s': no enabled devices configured; hub is idle", name)
        return True

    _delete_hub_idle_issue(hass)

    # ── auto-add newly discovered ESPHome HAUI devices ─────────────
    # Schedule a deferred scan for ESPHome entries with HAUI firmware
    # that aren't already configured.  Useful in Docker bridge mode
    # where mDNS auto-discovery doesn't fire — users add ESPHome
    # entries manually via the ESPHome integration, and this picks
    # them up without requiring a manual "Scan" button press.
    hass.async_create_task(_auto_add_unconfigured_devices(hass, entry))

    return True


async def _auto_add_unconfigured_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Auto-add unconfigured HAUI ESPHome devices to the hub.

    Scans for ESPHome config entries with HAUI firmware that aren't
    already listed in the hub entry's device list.  New devices are added
    to the entry (identity only); the entry's update listener reloads the
    hub, and setup gives them an empty store entry, so they start enabled.

    Safe to call multiple times (checks ``configured_names``).
    """
    from .esphome_helpers import discover_esphome_devices, hub_device_entry

    try:
        discovered = await discover_esphome_devices(hass)
        configured_names = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        # Devices the user removed stay removed until they add them again.
        removed_names = set(entry.data.get("removed_devices", []))
        unconfigured = [
            d
            for d in discovered
            if d["name"] not in configured_names and d["name"] not in removed_names
        ]

        if not unconfigured:
            return

        new_devices = list(entry.data.get("devices", []))
        for dev in unconfigured:
            new_devices.append(hub_device_entry(dev))
            _LOGGER.info(
                "Auto-added HAUI device '%s' to hub '%s'",
                dev["name"],
                entry.title,
            )

        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "devices": new_devices},
        )
        _LOGGER.info(
            "Auto-added %d device(s) to hub '%s'; reloading",
            len(unconfigured),
            entry.title,
        )
    except Exception:
        _LOGGER.warning(
            "Auto-discovery scan for hub '%s' failed",
            entry.title,
            exc_info=True,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop and unload a NSPanel HAUI config entry."""
    # Unload entity platforms (notify entities) before removing app data
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    apps: dict | None = hass.data[DOMAIN].pop(entry.entry_id, None)

    if apps is None:
        return True

    errors = False
    for _device_name, app in apps.items():
        if not await _stop_app(app):
            errors = True
        # Remove our config_entry_id from the ESPHome device so it no
        # longer shows in the nspanel_haui hub page.
        if app._ha_device_id:
            try:
                from homeassistant.helpers import device_registry as dr

                dev_reg = dr.async_get(hass)
                dev_reg.async_update_device(
                    app._ha_device_id,
                    remove_config_entry_id=entry.entry_id,
                )
            except Exception:
                _LOGGER.debug(
                    "Could not remove config entry from device '%s'",
                    _device_name,
                    exc_info=True,
                )
    return not errors


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the hub's panel store when the hub is removed."""
    from .storage import panel_store

    await panel_store(hass, entry.entry_id).async_remove()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when its data or options change.

    Goes through HA's reload so the entry's ``async_on_unload`` callbacks run
    (removing this listener before setup adds it again) and concurrent
    reloads are serialised by the entry's setup lock.
    """
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the NSPanel HAUI integration.

    Registers the panel config REST API view and frontend static path.
    """
    from .api import (
        ColorDefaultsView,
        DeviceConfigView,
        DeviceStatusView,
        DeviceUpdateDisplayView,
        DeviceUpdateTftView,
        DeviceYamlView,
        FirmwareDownloadView,
        IconSearchView,
        PanelConfigView,
        PanelTypesView,
        TranslationsView,
    )
    from .editor_panel import async_register_frontend
    from .services import async_register_services

    hass.http.register_view(TranslationsView())
    hass.http.register_view(PanelConfigView())
    hass.http.register_view(PanelTypesView())
    hass.http.register_view(ColorDefaultsView())
    hass.http.register_view(DeviceConfigView())
    hass.http.register_view(DeviceStatusView())
    hass.http.register_view(DeviceUpdateDisplayView())
    hass.http.register_view(DeviceUpdateTftView())
    hass.http.register_view(FirmwareDownloadView())
    hass.http.register_view(DeviceYamlView())
    hass.http.register_view(IconSearchView())
    await async_register_frontend(hass)
    async_register_services(hass)

    _LOGGER.info(
        "NSPanel HAUI integration loaded (hubs=%d)",
        len(hass.config_entries.async_entries(DOMAIN)),
    )

    await _register_discovery(hass)
    return True

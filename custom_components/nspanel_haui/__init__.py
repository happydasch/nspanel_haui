"""NSPanel HAUI custom integration for Home Assistant."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nspanel_haui"


# Config helpers - moved to haui/device_config.py for single source of truth
from .haui.device_config import (  # noqa: E402
    _apply_panel_store,
    _populate_devices_from_store,
    _validate_config,
)


def _build_config_dict(
    data: dict[str, Any],
    options: dict[str, Any],
    panels: dict[str, Any] | None = None,
    *,
    device_name: str = "",
) -> dict[str, Any]:
    """Build the combined config dict from three independent layers.

    - ``data``: connection + device identity (from config_entry.data)
    - ``options``: runtime toggles (from config_entry.options)
    - ``panels``: panel definitions per device (from PanelStorage)
    - ``device_name``: which device in ``data["devices"]`` this config is for.
      When provided, only that device is included and panel store data is
      scoped to it.
    """
    from .haui.device_config import DEVICE_CONFIG, DEVICE_CONFIG_FIELDS
    from .haui.mapping.const import DEFAULT_CONFIG

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["device"]["name"] = data.get("name", "")

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
        _apply_panel_store(cfg, store_devices, DEVICE_CONFIG_FIELDS)

    _populate_devices_from_store(cfg, store_devices, DEVICE_CONFIG_FIELDS)

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
    _validate_config(cfg)
    return cfg


async def _create_app(
    hass: HomeAssistant,
    entry: ConfigEntry,
    name: str,
    data: dict[str, Any],
    options: dict[str, Any],
    panels: dict[str, Any] | None,
    dev_name: str,
) -> NSPanelHAUI:
    """Create and initialize a single NSPanelHAUI app instance for a device.

    Builds the device config from the three config layers (data, options,
    panels), resolves the HA device_id, initializes the app on the executor
    thread, and returns the ready-to-use instance.

    The caller is responsible for storing the returned app in the running
    apps dict (hass.data[DOMAIN][entry.entry_id][dev_name]).
    """
    from .esphome_helpers import resolve_ha_device_id
    from .nspanel_haui import NSPanelHAUI

    cfg = _build_config_dict(data, options, panels, device_name=dev_name)
    ha_device_id = resolve_ha_device_id(hass, dev_name)
    app = NSPanelHAUI(
        hass, name, cfg,
        runtime_device_name=dev_name,
        ha_device_id=ha_device_id,
    )
    app._last_panel_update = (
        panels.get("devices", {}).get(dev_name, {}).get("last_panel_update")
        if panels else None
    )
    await hass.async_add_executor_job(app.initialize)
    _LOGGER.info("NSPanel HAUI instance for device '%s' started", dev_name)
    return app


async def _stop_app(
    hass: HomeAssistant,
    app: NSPanelHAUI,
) -> bool:
    """Stop a single NSPanelHAUI app instance.

    Returns ``True`` on success, ``False`` on error.
    """
    try:
        await hass.async_add_executor_job(app.stop)
        return True
    except Exception:
        _LOGGER.exception(
            "Error stopping NSPanel HAUI instance for device '%s'",
            app._runtime_device_name,
        )
        return False


async def _auto_add_esphome_devices(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Auto-discover ESPHome devices and add missing ones to the config entry.

    Compares discovered ESPHome devices against the existing device list.
    When new devices are found they are added to ``config_entry.data`` and
    the panel store, then ``async_update_entry`` triggers a full reload.

    Returns ``True`` when devices were added (triggering a reload);
    ``False`` otherwise.
    """
    from .esphome_helpers import discover_esphome_devices
    from .haui.device_config import DEVICE_CONFIG

    existing_names: set[str] = {
        d["name"] for d in entry.data.get("devices", []) if d.get("name")
    }
    discovered = await discover_esphome_devices(hass)

    new_devices: list[dict[str, Any]] = []
    for d in discovered:
        if d["name"] not in existing_names:
            dev = copy.deepcopy(DEVICE_CONFIG)
            dev["name"] = d["name"]
            dev["enabled"] = False  # New devices are disabled by default
            if d.get("esphome_device_id"):
                dev["esphome_device_id"] = d["esphome_device_id"]
            new_devices.append(dev)
            _LOGGER.info("Auto-discovered new NSPanel device: %s", d["name"])

    if not new_devices:
        return False

    # Update config_entry.data
    new_data = dict(entry.data)
    new_data.setdefault("devices", []).extend(new_devices)

    # Update panel store so new devices survive reloads
    from homeassistant.helpers.storage import Store

    store_panels: Store = Store(hass, 1, f"nspanel_haui.{entry.entry_id}_panels")
    panels_data = await store_panels.async_load() or {"version": 1, "devices": {}}
    for dev in new_devices:
        name = dev["name"]
        if name not in panels_data.get("devices", {}):
            panels_data.setdefault("devices", {})[name] = {
                "config": {},
                "panels": [],
            }
    await store_panels.async_save(panels_data)

    # Trigger full reload - async_update_entry fires the update listener
    hass.config_entries.async_update_entry(entry, data=new_data)
    _LOGGER.info(
        "Auto-added %d device(s): %s",
        len(new_devices),
        ", ".join(d["name"] for d in new_devices),
    )
    return True


async def _auto_discover_task(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Background task: run initial auto-discovery after entry setup."""
    try:
        added = await _auto_add_esphome_devices(hass, entry)
        if not added:
            _LOGGER.debug("Auto-discovery initial scan: no new devices found")
    except Exception:
        _LOGGER.exception("Auto-discovery scan failed for %s", entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NSPanel HAUI from a config entry.

    Loads panels from the HA Store, then creates one NSPanelHAUI app
    per enabled device in entry.data["devices"].  Events are routed to
    the correct app via HA device_id filtering.
    """
    from homeassistant.core import callback as ha_callback

    from .esphome_helpers import resolve_ha_device_id
    from .storage import PanelStorage

    hass.data.setdefault(DOMAIN, {})
    name: str = entry.data["name"]

    options = dict(entry.options)

    panels: dict[str, Any] | None
    try:
        panel_storage = PanelStorage(hass, entry.entry_id, entry)
        panels = await panel_storage.load()
    except Exception:
        _LOGGER.warning(
            "NSPanel HAUI '%s': could not load panel store, using defaults",
            name, exc_info=True,
        )
        panels = {"version": 1, "devices": {}}

    data = dict(entry.data)

    # ── create apps ────────────────────────────────────────────────────
    # One app per enabled device.  Use _build_config_dict without a
    # device_name filter first to resolve the enabled flag from all
    # config layers (entry.data, panel store, defaults).
    apps: dict = {}
    any_missing_device_id = False

    full_cfg = _build_config_dict(data, options, panels)

    for dev in full_cfg.get("devices", []):
        device_name = dev.get("name", "")
        if not device_name:
            _LOGGER.warning("Device entry missing 'name'; skipping")
            continue
        try:
            app = await _create_app(hass, entry, name, data, options, panels, device_name)
            if app._ha_device_id is None:
                any_missing_device_id = True
            apps[device_name] = app
        except Exception:
            _LOGGER.exception(
                "NSPanel HAUI '%s': failed to start device '%s'",
                name, device_name,
            )

    if not apps:
        _LOGGER.warning("NSPanel HAUI '%s': no enabled devices configured; entry is idle", name)
        # Store an empty dict so the entry is registered as active rather
        # than failing.  Devices added later trigger a reload which will
        # re-run async_setup_entry and populate real apps.
        hass.data[DOMAIN][entry.entry_id] = {}
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        return True

    hass.data[DOMAIN][entry.entry_id] = apps
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # ── device-id resolution race ──────────────────────────────────────
    # If any device could not resolve its HA device_id, listen for new
    # ESPHome config entries and patch the proxy when one appears.
    if any_missing_device_id:

        @ha_callback
        async def _resolve_device_id(event: Any) -> None:
            entry_id: str = event.data.get("entry_id", "")
            if not entry_id:
                return
            new_entry = hass.config_entries.async_get_entry(entry_id)
            if not new_entry or new_entry.domain != "esphome":
                return
            for dname, dapp in apps.items():
                if dapp._ha_device_id is None:
                    resolved = resolve_ha_device_id(hass, dname)
                    if resolved:
                        dapp._ha_device_id = resolved
                        proxy = dapp._plugin_proxies.get("ESPHome")
                        if proxy is not None:
                            proxy._device_id = resolved
                        _LOGGER.info(
                            "Resolved HA device_id for '%s': %s", dname, resolved
                        )
            # Once all are resolved, cancel the listener
            if all(a._ha_device_id is not None for a in apps.values()):
                _cancel_listener()

        _cancel_listener = hass.bus.async_listen(
            "config_entry_added", _resolve_device_id
        )

        # Store cancel handle so unload can clean it up
        _device_id_listeners: dict = hass.data[DOMAIN].setdefault(
            "_device_id_listeners", {}
        )
        _device_id_listeners[entry.entry_id] = _cancel_listener

    # Run initial auto-discovery scan in background - catches ESPHome
    # devices that were set up before our config entry was loaded.
    # Cancel any previous auto-discover task for this entry first to
    # prevent duplicate concurrent scans during rapid reload cycles.
    _auto_tasks: dict[str, Any] = hass.data[DOMAIN].setdefault("_auto_discover_tasks", {})
    prev_task = _auto_tasks.get(entry.entry_id)
    if prev_task and not prev_task.done():
        prev_task.cancel()
    task = hass.loop.create_task(_auto_discover_task(hass, entry))
    _auto_tasks[entry.entry_id] = task

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop and unload a NSPanel HAUI config entry."""
    apps: dict | None = hass.data[DOMAIN].pop(entry.entry_id, None)

    # Cancel device-id resolution listener if present
    _device_id_listeners: dict = hass.data[DOMAIN].get("_device_id_listeners", {})
    cancel = _device_id_listeners.pop(entry.entry_id, None)
    if cancel is not None:
        cancel()

    if apps is None:
        return True

    errors = False
    for _device_name, app in apps.items():
        if not await _stop_app(hass, app):
            errors = True
    return not errors


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to new version."""
    from .config_flow import NSPanelHAUIConfigFlow

    return await NSPanelHAUIConfigFlow.async_migrate_entry(hass, config_entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the NSPanel HAUI integration.

    Registers the panel config REST API view and frontend static path.
    """
    from .api import (
        DeviceConfigView,
        DeviceDiscoveryView,
        DeviceStatusView,
        DeviceYamlView,
        IconSearchView,
        PanelConfigView,
        PanelTypesView,
    )
    from .frontend import async_register_frontend

    hass.http.register_view(PanelConfigView())
    hass.http.register_view(PanelTypesView())
    hass.http.register_view(DeviceDiscoveryView())
    hass.http.register_view(DeviceConfigView())
    hass.http.register_view(DeviceStatusView())
    hass.http.register_view(DeviceYamlView())
    hass.http.register_view(IconSearchView())
    await async_register_frontend(hass)

    # ── auto-discovery ──────────────────────────────────────────────
    # Listen for new ESPHome config entries and auto-add them as
    # NSPanel devices.  Works both at startup (entries loaded after
    # integration setup) and at runtime (newly provisioned NSPanels).
    async def _on_config_entry_added(event: Any) -> None:
        entry_id: str = event.data.get("entry_id", "")
        if not entry_id:
            return
        new_entry = hass.config_entries.async_get_entry(entry_id)
        if not new_entry or new_entry.domain != "esphome":
            return
        for our_entry in hass.config_entries.async_entries(DOMAIN):
            try:
                await _auto_add_esphome_devices(hass, our_entry)
            except Exception:
                _LOGGER.exception("Auto-discovery event handler failed")

    hass.bus.async_listen("config_entry_added", _on_config_entry_added)

    return True

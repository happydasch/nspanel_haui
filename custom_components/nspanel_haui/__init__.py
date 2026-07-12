"""NSPanel HAUI custom integration for Home Assistant."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import config_validation as cv

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nspanel_haui"
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

# Config helpers - moved to haui/device_config.py for single source of truth
from .haui.device_config import (  # noqa: E402
    apply_panel_store,
    populate_devices_from_store,
    validate_config,
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
        hass,
        name,
        cfg,
        runtime_device_name=dev_name,
        ha_device_id=ha_device_id,
    )
    app._last_panel_update = (
        panels.get("devices", {}).get(dev_name, {}).get("last_panel_update") if panels else None
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
    """Register discovery resources once per HA session.

    No-op when a hub entry already exists — no scans, no listeners, no
    flood. Discovery is *only* about getting the first hub created;
    once it exists the user manages devices via the HAUI Editor.

    When no hub exists: schedule a one-shot ``_trigger_haui_discovery``
    and install a single device-registry listener that fires the same
    trigger when an ESPHome HAUI device shows up. The listener
    self-unsubscribes the moment a hub entry exists.
    """
    global _DISCOVERY_INITIALIZED
    if _DISCOVERY_INITIALIZED:
        return
    _DISCOVERY_INITIALIZED = True

    if hass.config_entries.async_entries(DOMAIN):
        return

    from homeassistant.core import callback as ha_callback
    from homeassistant.helpers import device_registry as dr

    from .esphome_helpers import is_haui_device

    cancel: list[Any] = []

    @ha_callback
    def _on_device_registry_change(event: Any) -> None:
        # Self-unsubscribe once a hub exists.
        if hass.config_entries.async_entries(DOMAIN):
            if cancel:
                cancel.pop()()
            return
        data = event.data if isinstance(event.data, dict) else {}
        if data.get("action") not in ("create", "update"):
            return
        device_id = data.get("device_id", "")
        if not device_id:
            return
        dev_entry = dr.async_get(hass).async_get(device_id)
        if not dev_entry:
            return
        for cid in dev_entry.config_entries:
            entry = hass.config_entries.async_get_entry(cid)
            if entry and entry.domain == "esphome" and is_haui_device(hass, entry):
                hass.async_create_task(_trigger_haui_discovery(hass))
                break

    cancel.append(
        hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            _on_device_registry_change,
        )
    )

    # One-shot bootstrap covers the case where HAUI devices already
    # exist in the registry before our integration was loaded.
    hass.async_create_task(_trigger_haui_discovery(hass))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NSPanel HAUI from a config entry.

    Loads panels from the HA Store, then creates one NSPanelHAUI app
    per enabled device in entry.data["devices"].  Events are routed to
    the correct app via HA device_id filtering.
    """

    # ── ensure discovery listener is registered (runs even on restart) ──
    await _register_discovery(hass)
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
            name,
            exc_info=True,
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
                name,
                device_name,
            )

    if not apps:
        _LOGGER.warning("NSPanel HAUI '%s': no enabled devices configured; hub is idle", name)
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
    # ESPHome devices in the registry and patch the proxy when one appears.
    if any_missing_device_id:
        from homeassistant.helpers import device_registry as dr

        @ha_callback
        async def _resolve_device_id(event: Any) -> None:
            if event.data.get("action") != "create":
                return
            device_id: str = event.data.get("device_id", "")
            if not device_id:
                return
            dev_reg = dr.async_get(hass)
            device_entry = dev_reg.async_get(device_id)
            if not device_entry:
                return
            # Find any ESPHome config entry on this new device
            esphome_id: str | None = None
            for config_entry_id in device_entry.config_entries:
                entry = hass.config_entries.async_get_entry(config_entry_id)
                if entry and entry.domain == "esphome":
                    esphome_id = entry.entry_id
                    break
            if not esphome_id:
                return
            for dname, dapp in apps.items():
                if dapp._ha_device_id is None:
                    resolved = resolve_ha_device_id(hass, dname)
                    if resolved:
                        dapp._ha_device_id = resolved
                        proxy = dapp._plugin_proxies.get("ESPHome")
                        if proxy is not None:
                            proxy._device_id = resolved
                        _LOGGER.info("Resolved HA device_id for '%s': %s", dname, resolved)
            # Once all are resolved, cancel the listener
            if all(a._ha_device_id is not None for a in apps.values()):
                _cancel_listener()

        _cancel_listener = hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            _resolve_device_id,
        )

        # Store cancel handle so unload can clean it up
        _device_id_listeners: dict = hass.data[DOMAIN].setdefault("_device_id_listeners", {})
        _device_id_listeners[entry.entry_id] = _cancel_listener

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
    already listed in the hub entry's device list.  When new devices
    are found, adds them and reloads the hub so they appear as app
    instances.

    Safe to call multiple times (checks ``configured_names``).
    """
    from .esphome_helpers import discover_esphome_devices
    from .haui.device_config import DEVICE_CONFIG

    try:
        discovered = await discover_esphome_devices(hass)
        configured_names = {d["name"] for d in entry.data.get("devices", []) if "name" in d}
        unconfigured = [d for d in discovered if d["name"] not in configured_names]
        if not unconfigured:
            return

        import copy

        new_devices = list(entry.data.get("devices", []))
        for dev in unconfigured:
            new_dev = copy.deepcopy(DEVICE_CONFIG)
            new_dev["name"] = dev["name"]
            new_dev["enabled"] = True
            if dev.get("esphome_device_id"):
                new_dev["esphome_device_id"] = dev["esphome_device_id"]
            new_devices.append(new_dev)
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
        await async_reload_entry(hass, entry)
    except Exception:
        _LOGGER.warning(
            "Auto-discovery scan for hub '%s' failed",
            entry.title,
            exc_info=True,
        )


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
        ColorDefaultsView,
        DeviceConfigView,
        DeviceStatusView,
        DeviceUpdateDisplayView,
        DeviceYamlView,
        IconSearchView,
        PanelConfigView,
        PanelTypesView,
        TranslationsView,
    )
    from .frontend import async_register_frontend
    from .services import async_register_services

    hass.http.register_view(TranslationsView())
    hass.http.register_view(PanelConfigView())
    hass.http.register_view(PanelTypesView())
    hass.http.register_view(ColorDefaultsView())
    hass.http.register_view(DeviceConfigView())
    hass.http.register_view(DeviceStatusView())
    hass.http.register_view(DeviceUpdateDisplayView())
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

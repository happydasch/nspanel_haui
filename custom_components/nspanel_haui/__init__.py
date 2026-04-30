"""NSPanel HAUI custom integration for Home Assistant."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nspanel_haui"


def _options_to_config_dict(name: str, options: dict[str, Any]) -> dict[str, Any]:
    """Build the config dict NSPanelHAUI expects from structured entry options.

    Priority is controlled by options["config_mode"]:
    - "yaml": use config_yaml (safe_load), ignoring structured options
    - "ui" (default): use structured options (devices, panels, topic_prefix)
    """
    import yaml

    from .haui.mapping.const import DEFAULT_CONFIG

    config_mode = options.get("config_mode", "ui")

    if config_mode == "yaml" and options.get("config_yaml"):
        return yaml.safe_load(options["config_yaml"]) or {}

    # UI mode (or fallback if YAML mode but config_yaml is missing)
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["device"]["name"] = name

    if "mqtt_topic_prefix" in options:
        cfg["mqtt"]["topic_prefix"] = options["mqtt_topic_prefix"]

    # Multi-device support: copy per-device configs from options
    if options.get("devices"):
        cfg["devices"] = copy.deepcopy(options["devices"])
        # Flatten per-device panels for runtime backward compat
        all_panels = []
        for dev in cfg["devices"]:
            all_panels.extend(dev.get("panels", []))
        cfg["panels"] = all_panels
    elif "panels" in options:
        # Backward compat: old top-level panels
        cfg["panels"] = list(options["panels"])

    return cfg


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NSPanel HAUI from a config entry."""
    import yaml

    from .nspanel_haui import NSPanelHAUI

    hass.data.setdefault(DOMAIN, {})
    name: str = entry.data["name"]

    try:
        cfg = _options_to_config_dict(name, dict(entry.options))
    except yaml.YAMLError:
        _LOGGER.error("NSPanel HAUI '%s': failed to parse config YAML", name)
        return False

    try:
        app = NSPanelHAUI(hass, name, cfg)
        await hass.async_add_executor_job(app.initialize)
    except Exception:
        _LOGGER.exception("NSPanel HAUI '%s': failed to start", name)
        return False

    hass.data[DOMAIN][entry.entry_id] = app
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _LOGGER.info("NSPanel HAUI instance '%s' started", name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop and unload a NSPanel HAUI config entry."""
    from .nspanel_haui import NSPanelHAUI

    app: NSPanelHAUI | None = hass.data[DOMAIN].pop(entry.entry_id, None)
    if app is not None:
        try:
            await hass.async_add_executor_job(app.stop)
        except Exception:
            _LOGGER.exception(
                "NSPanel HAUI '%s': error stopping instance", entry.data["name"]
            )
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to new version."""
    from .config_flow import NSPanelHAUIConfigFlow

    return await NSPanelHAUIConfigFlow.async_migrate_entry(hass, config_entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

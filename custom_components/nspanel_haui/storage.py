"""HA Store wrapper for panel configuration.

Per-device settings (including ``enabled``) and panels are stored in HA's
storage system. config_entry.data holds only the hub name, each device's
identity (name and ESPHome device id) and ``removed_devices``. The frontend
HAUI Editor reads/writes the store via the REST API in api.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .haui.device_config import find_store_device

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


_LOGGER = logging.getLogger(__name__)

PANEL_STORE_VERSION = 1

# Device-config keys renamed by the stable-release vocabulary change.  The
# runtime reads only the new names, so a device setting that still lives under
# a legacy key silently fell back to its default (most notably an unset
# ``idle_panel`` disabled the idle page and hid the idle button).  The store
# loader renames these in place; a value already stored under the new key wins.
DEVICE_CONFIG_KEY_RENAMES: dict[str, str] = {
    "sleep_panel": "idle_panel",
    "sleep_panel_extra": "idle_panel_extra",
    "show_sleep_button": "show_idle_button",
    "use_auto_sleeping": "use_auto_display_off",
    "timeout_sleep": "timeout_display_off",
}


def migrate_device_config_keys(device_config: dict) -> bool:
    """Rename legacy device-config keys in place.

    Args:
        device_config: The ``config`` dict of one device in the panel store.

    Returns:
        True when any key was moved.  The legacy key is removed either way so
        the migration is idempotent and a later explicit ``idle_panel`` /
        ``use_auto_display_off`` / ... under the new name is never overwritten.
    """
    modified = False
    for old_key, new_key in DEVICE_CONFIG_KEY_RENAMES.items():
        if old_key not in device_config:
            continue
        old_value = device_config.pop(old_key)
        if new_key not in device_config:
            device_config[new_key] = old_value
        modified = True
    return modified


def panel_store(hass: Any, entry_id: str) -> Store:
    """Return the HA Store holding the panel config of one config entry."""
    return Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")


def empty_store() -> dict:
    """Return a fresh panel store payload for an entry with no saved panels."""
    return {"version": 1, "devices": {}}


def empty_device() -> dict:
    """Return a fresh store entry for a device: default settings, no panels."""
    return {"config": {}, "panels": []}


async def async_remove_device(
    hass: Any, entry: ConfigEntry, name: str, *, keep_config: bool
) -> None:
    """Remove a device from the hub.

    The entry's update listener reloads the hub, which stops the device's app.

    Args:
        hass: Home Assistant instance.
        entry: The hub's config entry.
        name: Name of the device to remove.
        keep_config: Leave the device's settings and panels in the store.
    """
    if not keep_config:
        store = panel_store(hass, entry.entry_id)
        panels_data = await store.async_load() or empty_store()
        if name in panels_data.get("devices", {}):
            panels_data["devices"].pop(name)
            await store.async_save(panels_data)
            _LOGGER.debug("Removed device %s from panel store for %s", name, entry.entry_id)

    new_data = dict(entry.data)
    new_data["devices"] = [d for d in new_data.get("devices", []) if d.get("name") != name]
    # Keeps auto-add from adding the device straight back while ESPHome still has it.
    new_data["removed_devices"] = [*entry.data.get("removed_devices", []), name]
    hass.config_entries.async_update_entry(entry, data=new_data)
    _LOGGER.debug("Removed device %s from config_entry.data for %s", name, entry.entry_id)


def enabled_device_names(entry_data: dict, store_data: dict) -> list[str]:
    """Return the devices of the hub that should run, in config-entry order.

    A device runs when the config entry lists it and its store settings don't
    disable it. Store-only devices (removed with "keep config") never run.

    Args:
        entry_data: Config-entry data (device identities).
        store_data: Panel store payload (device settings).

    Returns:
        list[str]: Names of the enabled devices.
    """
    store_devices = store_data.get("devices", {})
    names = []
    for dev in entry_data.get("devices", []):
        name = dev.get("name", "")
        if not name:
            _LOGGER.warning("Config entry device without a name; skipping")
            continue
        store_dev = find_store_device(store_devices, name) or {}
        if store_dev.get("config", {}).get("enabled", True):
            names.append(name)
    return names


class PanelStorage:
    """HA Store wrapper for per-entry panel configuration."""

    def __init__(self, hass: Any, entry_id: str, config_entry: ConfigEntry | None = None) -> None:
        self._store: Store = panel_store(hass, entry_id)
        self._config_entry: ConfigEntry | None = config_entry

    async def load(self) -> dict:
        """Load panel data from store, returning default if empty.

        Adds an empty store entry for every device in config_entry.data that
        the store doesn't have yet (e.g. added by the config flow or
        auto-discovery).
        """
        data = await self._store.async_load()
        result: dict = data or empty_store()

        if self._config_entry is not None:
            modified = False
            store_devices = result.setdefault("devices", {})
            for ce_dev in self._config_entry.data.get("devices", []):
                dev_name = ce_dev.get("name")
                if dev_name and find_store_device(store_devices, dev_name) is None:
                    store_devices[dev_name] = empty_device()
                    modified = True

            if modified:
                await self._store.async_save(result)

        # Migrate legacy device-config keys in place (also without a config
        # entry: the store holds the same shape either way).  One-time, then
        # idempotent — see DEVICE_CONFIG_KEY_RENAMES.
        modified = False
        for dev_data in result.get("devices", {}).values():
            if not isinstance(dev_data, dict):
                continue
            config = dev_data.get("config")
            if isinstance(config, dict) and migrate_device_config_keys(config):
                modified = True

        if modified:
            await self._store.async_save(result)

        return result

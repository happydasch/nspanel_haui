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

from ..haui.device_config import DEVICE_CONFIG, find_store_device
from ..haui.mapping.const import GESTURES, UPDATE_POLICY_FIELDS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


_LOGGER = logging.getLogger(__name__)

PANEL_STORE_VERSION = 1
# Device-config keys renamed in the idle/display settings release.
DEVICE_CONFIG_KEY_RENAMES: dict[str, str] = {
    "sleep_panel": "idle_panel",
    "sleep_panel_extra": "idle_panel_extra",
    "show_sleep_button": "show_idle_button",
    "use_auto_sleeping": "use_auto_display_off",
    "timeout_sleep": "timeout_display_off",
}


def migrate_device_config_keys(device_config: dict) -> bool:
    """Rename legacy device-config keys in place and convert the old gesture settings.

    A device that stored its own automatic update policy before the hub-wide
    policy existed keeps it: it is marked ``update.policy_override``.
    """
    modified = migrate_update_policy_override(device_config)
    for old_key, new_key in DEVICE_CONFIG_KEY_RENAMES.items():
        if old_key not in device_config:
            continue
        old_value = device_config.pop(old_key)
        if new_key not in device_config:
            device_config[new_key] = old_value
        modified = True
    return migrate_gesture_settings(device_config) or modified


def migrate_update_policy_override(device_config: dict) -> bool:
    """Mark a device that stored its own update policy as overriding the hub's.

    Runs once: a device whose ``update`` block already says ``policy_override``
    (either way) is left alone.
    """
    update = device_config.get("update")
    if not isinstance(update, dict) or "policy_override" in update:
        return False
    if not any(field in update for field in UPDATE_POLICY_FIELDS):
        return False
    update["policy_override"] = True
    return True


def migrate_gesture_settings(device_config: dict) -> bool:
    """Merge ``swipe_actions`` and ``gesture_sequences`` into ``gestures`` in place.

    0.4.7 stored ``gesture_sequences`` and had fixed single swipes (the
    ``gestures`` defaults); 0.5 development builds added ``swipe_actions``.
    Each swipe with an action becomes a one-swipe gesture ahead of the
    sequences; a swipe without one gets no gesture, so it still does nothing.
    An existing ``gestures`` value wins and the old keys are only dropped.
    """
    if "swipe_actions" not in device_config and "gesture_sequences" not in device_config:
        return False
    swipe_actions = device_config.pop("swipe_actions", None)
    sequences = device_config.pop("gesture_sequences", None) or []
    if "gestures" in device_config:
        return True
    if swipe_actions is None:
        gestures = [dict(gesture) for gesture in DEVICE_CONFIG["gestures"]]
    else:
        gestures = [
            {"swipes": [swipe], "action": swipe_actions[swipe], "timeframe": 3}
            for swipe in GESTURES
            if swipe_actions.get(swipe)
        ]
    gestures += [
        {
            "swipes": list(sequence["sequence"]),
            "action": sequence["open"],
            "timeframe": sequence["timeframe"],
        }
        for sequence in sequences
    ]
    device_config["gestures"] = gestures
    return True


def drop_fixed_sys_overrides(device_name: str, device_data: dict) -> bool:
    """Remove stored edits of system panels that can no longer be edited.

    Earlier versions let every system panel be edited; now only the popups can.
    An edited System, Blank, Settings or About panel is dropped, so the
    built-in one is back.

    Args:
        device_name: Name of the device, for the log.
        device_data: One device of the panel store.

    Returns:
        True when any panel was removed.
    """
    from ..haui.mapping.panel import SYS_PANEL_MAPPING

    panels = device_data.get("panels", [])
    kept = []
    for panel in panels:
        key = panel.get("key")
        if key in SYS_PANEL_MAPPING:
            _LOGGER.warning(
                "Removed the edited system panel %s of %s: only popups can be edited",
                key,
                device_name,
            )
            continue
        kept.append(panel)
    if len(kept) == len(panels):
        return False
    device_data["panels"] = kept
    return True


def panel_store(hass: Any, entry_id: str) -> Store:
    """Return the HA Store holding the panel config of one config entry."""
    return Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")


def empty_store() -> dict:
    """Return a fresh panel store payload for an entry with no saved panels."""
    return {"version": 1, "device_order": [], "devices": {}, "themes": {}, "update_policy": {}}


def normalize_device_order(store_data: dict) -> bool:
    """Keep the stored device order unique and synchronized with the device map.

    Existing valid order is preserved; devices missing from the order are
    appended in the store mapping's insertion order.
    """
    devices = store_data.get("devices", {})
    if not isinstance(devices, dict):
        devices = {}
    current = store_data.get("device_order", [])
    if not isinstance(current, list):
        current = []
    order: list[str] = []
    for name in current:
        if isinstance(name, str) and name in devices and name not in order:
            order.append(name)
    order.extend(name for name in devices if name not in order)
    if store_data.get("device_order") == order:
        return False
    store_data["device_order"] = order
    return True


def empty_device() -> dict:
    """Return a fresh store entry for a device: default settings, no panels."""
    return {"config": {}, "panels": []}


async def async_remove_device(hass: Any, entry: ConfigEntry, name: str) -> None:
    """Remove a device from the hub, together with its settings and panels.

    The entry's update listener reloads the hub, which stops the device's app.

    Args:
        hass: Home Assistant instance.
        entry: The hub's config entry.
        name: Name of the device to remove.
    """
    store = panel_store(hass, entry.entry_id)
    panels_data = await store.async_load() or empty_store()
    devices = panels_data.get("devices", {})
    modified = False
    if name in devices:
        devices.pop(name)
        modified = True
    if normalize_device_order(panels_data):
        modified = True
    if modified:
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
    disable it. Store-only devices (settings without a config-entry record)
    never run.

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
        root_modified = False
        if self._config_entry is not None:
            modified = False
            store_devices = result.setdefault("devices", {})
            for ce_dev in self._config_entry.data.get("devices", []):
                dev_name = ce_dev.get("name")
                if dev_name and find_store_device(store_devices, dev_name) is None:
                    store_devices[dev_name] = empty_device()
                    modified = True

            if modified:
                root_modified = True

        # Migrate legacy device-config keys in place (also without a config
        # entry: the store holds the same shape either way).  One-time, then
        # idempotent — see DEVICE_CONFIG_KEY_RENAMES.
        modified = root_modified
        for dev_name, dev_data in result.get("devices", {}).items():
            if not isinstance(dev_data, dict):
                continue
            config = dev_data.get("config")
            if isinstance(config, dict) and migrate_device_config_keys(config):
                modified = True
            if drop_fixed_sys_overrides(dev_name, dev_data):
                modified = True

        if normalize_device_order(result):
            modified = True

        if modified:
            await self._store.async_save(result)

        return result

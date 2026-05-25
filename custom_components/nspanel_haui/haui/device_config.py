"""Device configuration constants, helpers, and typed accessor.

Leaf module - imports nothing from ``haui/``.  All device-config logic lives
here so that ``haui/mapping/const.py``, ``storage.py``, ``__init__.py``, and
``haui/config_models.py`` can share a single source of truth.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template for a single device entry (one physical NSPanel)
# ---------------------------------------------------------------------------

DEVICE_CONFIG: dict[str, Any] = {
    "name": "",
    "panels": [{"type": "clock"}],
    "esphome_device_id": "",  # ESPHome device ID when matched to an existing ESPHome device
    "enabled": True,  # device can be disabled to hide from runtime without deleting config
    "locale": "en_US",
    # hardware buttons
    "button_left_entity": "",
    "button_right_entity": "",
    # navigation
    "home_panel": "",  # panel key of the home panel (empty = none set)
    "sleep_panel": "",  # panel key of the sleep panel (empty = none set)
    "wakeup_panel": "",  # panel key of the wakeup panel (empty = none set)
    "show_home_button": False,
    "show_sleep_button": False,
    "show_notifications_button": True,
    # logging
    "log_items": False,
    "debug_level": 0,
    # exit sleep / wakeup
    "home_on_wakeup": False,
    "home_on_first_touch": True,
    "home_only_when_on": False,
    "home_on_button_toggle": False,
    # interaction
    "reset_interaction_on_button": True,
    "return_to_home_after_seconds": 0,
    "always_return_to_home": False,
    # hub-side idle timeout (seconds, 0 = disabled).
    # Fallback when the device doesn't publish esphome.timeout events
    # (e.g., use_auto_sleeping is OFF on the device).
    "hub_idle_timeout": 0,
    "use_relay_left": True,
    "use_relay_right": True,
    "sound_on_startup": True,
    # color overrides (dict[str, int] — RGB565 values overriding COLORS defaults)
    "color_overrides": {},
    "sound_on_notification": True,
}

# ---------------------------------------------------------------------------
# Config fields that are editable per-device and stored in the panel store.
# Excludes identity fields (name, esphome_device_id) and panels (stored
# independently under the device entry).
# ---------------------------------------------------------------------------

DEVICE_CONFIG_FIELDS: list[str] = [
    "locale",
    "button_left_entity",
    "button_right_entity",
    "home_panel",
    "sleep_panel",
    "wakeup_panel",
    "show_home_button",
    "show_sleep_button",
    "show_notifications_button",
    "enabled",
    "log_items",
    "debug_level",
    "home_on_wakeup",
    "home_on_first_touch",
    "home_only_when_on",
    "home_on_button_toggle",
    "reset_interaction_on_button",
    "return_to_home_after_seconds",
    "always_return_to_home",
    "hub_idle_timeout",
    "sound_on_startup",
    "use_relay_left",
    "use_relay_right",
    "sound_on_notification",
    "color_overrides",
]

# ---------------------------------------------------------------------------
# Locale options for device configuration
# ---------------------------------------------------------------------------

LOCALE_OPTIONS: list[tuple[str, str]] = [
    ("en_US", "English"),
    ("de_DE", "Deutsch"),
    ("nl_NL", "Nederlands"),
    ("pl_PL", "Polski"),
]

# ---------------------------------------------------------------------------
# Config validation and merge helpers (moved from __init__.py)
# ---------------------------------------------------------------------------


def _validate_config(cfg: dict[str, Any]) -> None:
    """Validate that all keys from DEFAULT_CONFIG and DEVICE_CONFIG are present.

    Raises ValueError with a list of missing keys if any are absent or None.
    """
    from .mapping.const import DEFAULT_CONFIG

    missing: list[str] = []

    def _check_keys(prefix: str, reference: dict, target: dict) -> None:
        for key, ref_val in reference.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in target:
                missing.append(full_key)
                continue
            tgt_val = target[key]
            if tgt_val is None:
                missing.append(f"{full_key} (is None)")
                continue
            if isinstance(ref_val, dict):
                if not isinstance(tgt_val, dict):
                    missing.append(f"{full_key} (expected dict, got {type(tgt_val).__name__})")
                    continue
                _check_keys(full_key, ref_val, tgt_val)

    _check_keys("", DEFAULT_CONFIG, cfg)

    # Validate each device entry has all DEVICE_CONFIG keys
    for i, dev in enumerate(cfg.get("devices", [])):
        for key in DEVICE_CONFIG:
            full_key = f"devices[{i}].{key}"
            if key not in dev:
                missing.append(full_key)
            elif dev[key] is None:
                missing.append(f"{full_key} (is None)")

    if missing:
        raise ValueError(
            "Config validation failed - missing or None keys:\n  " + "\n  ".join(sorted(missing))
        )


def _find_store_device(store_devices: dict, dev_name: str) -> dict | None:
    """Find a device in the store by exact or case-insensitive name match."""
    store_dev = store_devices.get(dev_name)
    if store_dev is not None:
        return store_dev
    dev_name_lower = dev_name.lower()
    for store_key, store_val in store_devices.items():
        if store_key.lower() == dev_name_lower:
            _LOGGER.debug(
                "Matched device '%s' to store key '%s' via case-insensitive lookup",
                dev_name,
                store_key,
            )
            return store_val
    return None


def _merge_store_fields(source: dict, target: dict, fields: list) -> None:
    """Copy fields from *source* into *target* when they exist in *source*."""
    for field in fields:
        if field in source:
            target[field] = source[field]


def _populate_devices_from_store(cfg: dict, store_devices: dict, fields: list) -> None:
    """Build ``cfg['devices']`` list from store data when no devices exist in config."""
    if cfg.get("devices"):
        return
    cfg["devices"] = []
    for dev_name, store_dev in store_devices.items():
        entry = {"name": dev_name, "panels": store_dev.get("panels", [])}
        if "config" in store_dev:
            _merge_store_fields(store_dev["config"], entry, fields)
        cfg["devices"].append(entry)


def _apply_panel_store(cfg: dict, store: dict, fields: list) -> None:
    """Apply per-device panel store data to the config."""
    for dev in cfg.get("devices", []):
        dev_name = dev.get("name", "")
        store_dev = _find_store_device(store, dev_name)
        if store_dev is None:
            continue
        dev["panels"] = store_dev.get("panels", [])
        if "config" in store_dev:
            _merge_store_fields(store_dev["config"], dev, fields)

    # Apply to cfg["device"] (HAUIDevice runtime config) from the runtime
    # device only. Runtime device = first entry in cfg["devices"] (matches
    # NSPanelHAUI.initialize); cfg["device"]["name"] mirrors the runtime
    # device name when one is available, so it may also be used as a lookup key.
    devs = cfg.get("devices", [])
    runtime_name = devs[0].get("name", "") if devs else ""
    if not runtime_name:
        runtime_name = cfg.get("device", {}).get("name", "")
    if runtime_name:
        store_dev = _find_store_device(store, runtime_name)
        if store_dev and "config" in store_dev:
            _merge_store_fields(store_dev["config"], cfg["device"], fields)

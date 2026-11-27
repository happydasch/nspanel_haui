"""Device configuration constants, helpers, and typed accessor.

Leaf module - imports nothing from ``haui/``.  All device-config logic lives
here so that ``haui/mapping/const.py``, ``storage.py``, ``__init__.py``, and
``haui/config_models.py`` can share a single source of truth.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

_LOGGER = logging.getLogger(__name__)

LOCALE_OPTIONS: list[tuple[str, str]] = [
    ("en_US", "English"),
    ("de_DE", "Deutsch"),
    ("nl_NL", "Nederlands"),
    ("pl_PL", "Polski"),
    ("fr_FR", "Français"),
    ("sk_SK", "Slovenčina"),
]

# Log levels per device: the threshold for this device's app logs; DEBUG adds
# state-change and display-command diagnostics.
LOG_LEVEL_OPTIONS: list[str] = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

# Settings that may be None: the hub leaves the value to the device.
OPTIONAL_DEVICE_CONFIG_FIELDS = frozenset({"brightness", "brightness_dim"})

DEVICE_CONFIG: dict[str, Any] = {
    "name": "",
    "panels": [{"type": "clock"}],
    "esphome_device_id": "",  # ESPHome device ID when matched to an existing ESPHome device
    "enabled": True,  # device can be disabled to hide from runtime without deleting config
    "locale": "en_US",
    # time/date formatting (empty = inherit the hub-level default from DEFAULT_CONFIG)
    "time_format": "",
    "date_format": "",
    "date_format_locale": "",
    # hardware buttons
    "button_left_entity": "",
    "button_right_entity": "",
    # navigation
    "home_panel": "",  # panel key of the home panel (empty = none set)
    # Idle page: the automatic page-switch target; independent of display-off.
    "idle_panel": "",  # panel key of the idle page (empty = none set)
    # Comma-separated panel keys cycled on repeated entries (carousel).
    "idle_panel_extra": "",
    "show_home_button": False,
    "show_idle_button": False,
    "show_notifications_button": True,
    # page settle delay (seconds)
    # Wait this long after the page-change ack before rendering, so all widgets
    # are initialised. The ack (0x66) already means the page is active, so this
    # is only a margin: 0.05 s is half the former 0.1 s and still covers a
    # Nextion finishing a page's Preinitialize. Raise it only if the log shows
    # "Invalid variable name" (0x1A) right after a page change.
    "page_settle_delay": 0.05,
    # logging
    "log_level": "INFO",
    # stale-data indicator threshold in seconds (0 = off)
    "stale_data_seconds": 0,
    # Swipe gestures: swipes in order within ``timeframe`` run ``action``
    # (``next_panel``, ``prev_panel`` or a panel key).
    "gestures": [
        {"swipes": ["swipe_left"], "action": "next_panel", "timeframe": 3},
        {"swipes": ["swipe_right"], "action": "prev_panel", "timeframe": 3},
        {"swipes": ["swipe_up"], "action": "sys_about", "timeframe": 3},
        {"swipes": ["swipe_down"], "action": "sys_settings", "timeframe": 3},
    ],
    # interaction
    "reset_interaction_on_button": True,
    # snapshot restore limit: -1 = no limit, 0 = never restore, >0 = max age in seconds
    "snapshot_max_age_seconds": -1,
    # auto-navigate-home timeout in seconds (0 = disabled); keep it below the
    # display-off/dim timeout.
    "auto_navigate_home_timeout": 0,
    "use_relay_left": True,
    "use_relay_right": True,
    "use_auto_dimming": True,
    "use_auto_page": True,
    "use_auto_display_off": True,
    "timeout_dimming": 10,
    "timeout_page": 30,
    "timeout_display_off": 120,
    # Fade time of the dimming transition (firmware "Duration Dimming", 0-5).
    "duration_dimming": 2.0,
    # Full brightness in percent; None leaves the panel's value (required once
    # the schedule has entries).
    "brightness": None,
    # Dimmed brightness in percent; None leaves the panel's value.
    "brightness_dim": None,
    # Schedule windows override sound, brightness, dimming and display-off; the
    # first entry containing now applies. Entry: {"start": "21:00", "end":
    # "sunrise", "end_offset": -30, "sound": False, "brightness": 20,
    # "brightness_dim": 5, "display_off": True, "timeout_dimming": 10,
    # "timeout_display_off": 30}; a None value falls back to the device setting.
    # Offsets are minutes, -720..720.
    "schedule": [],
    "sound_on_startup": False,
    # Active semantic colour definitions (built-ins or saved themes).
    # A theme carries both icon palettes; its page background picks the one used.
    "theme_id": "dark",
    "sound_on_notification": False,
    "persistent_sound_interval": 5,  # seconds between repeats for persistent notifications
    # Display model: EU landscape or US portrait/landscape; selects the TFT asset.
    "display_model": "eu",
}

# TFT asset per display model: only the US portrait mount needs the rotated one.
DISPLAY_MODEL_TFT_FILENAME: dict[str, str] = {
    "eu": "nspanel_haui.tft",
    "us": "nspanel_haui_portrait.tft",
}


def tft_filename_for_model(display_model: str | None, default: str = "nspanel_haui.tft") -> str:
    """Return the TFT asset filename the given display model needs.

    Args:
        display_model: The device's ``display_model`` value.  Unknown or empty
            values (e.g. a fresh config before the option ships) fall back to
            the landscape TFT so existing installs keep updating.
        default: Filename to return for unknown models.

    Returns:
        str: TFT filename, e.g. ``nspanel_haui_portrait.tft`` for ``us``.
    """
    return DISPLAY_MODEL_TFT_FILENAME.get(str(display_model or "").lower(), default)


def is_portrait_model(display_model: str | None) -> bool:
    """Return whether ``display_model`` runs the rotated portrait TFT layout."""
    return tft_filename_for_model(display_model) == DISPLAY_MODEL_TFT_FILENAME["us"]


# Fields synced from the store, minus meta-fields handled elsewhere.
DEVICE_CONFIG_FIELDS: list[str] = [
    k for k in DEVICE_CONFIG if k not in ("name", "panels", "esphome_device_id")
]

# Hub-scoped display defaults: the config entry's ``options`` keys that every
# panel inherits when its own value is empty, and that are editable outside the
# editor's per-device settings.  They overlay the root of the config dict.
HUB_OPTION_KEYS: tuple[str, ...] = ("time_format", "date_format", "date_format_locale")


def hub_options(options: Mapping[str, Any] | None) -> dict[str, str]:
    """Return the hub option keys that hold a non-empty string.

    An absent or blank option means "keep the built-in default from
    ``DEFAULT_CONFIG``", so a stored options dict can never leave a root key
    empty or invalid.

    Args:
        options: The config entry's ``options`` mapping, or ``None``.

    Returns:
        dict[str, str]: Known option keys with a non-blank string value.
    """
    resolved: dict[str, str] = {}
    for key in HUB_OPTION_KEYS:
        value = (options or {}).get(key)
        if isinstance(value, str) and value.strip():
            resolved[key] = value
    return resolved


def apply_hub_options(cfg: dict[str, Any], options: Mapping[str, Any] | None) -> None:
    """Overlay the hub's display defaults onto the root of *cfg*.

    *cfg* is modified in place; keys the options leave unset keep their
    ``DEFAULT_CONFIG`` value.
    """
    cfg.update(hub_options(options))


def resolve_snapshot_max_age(cfg: dict[str, Any]) -> int:
    """Resolve the snapshot restore limit from *cfg*.

    -1 = no limit (always restore), 0 = never restore, >0 = max age in
    seconds after which the idle-page exit falls back to the home panel.
    """
    value = cfg.get("snapshot_max_age_seconds", -1)
    return -1 if value is None else value


def validate_config(cfg: dict[str, Any]) -> None:
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
                if not (prefix == "device" and key in OPTIONAL_DEVICE_CONFIG_FIELDS):
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
            elif dev[key] is None and key not in OPTIONAL_DEVICE_CONFIG_FIELDS:
                missing.append(f"{full_key} (is None)")

    if missing:
        raise ValueError(
            "Config validation failed - missing or None keys:\n  " + "\n  ".join(sorted(missing))
        )


def find_store_device(store_devices: dict, dev_name: str) -> dict | None:
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


def merge_store_fields(source: dict, target: dict, fields: list) -> None:
    """Copy fields from *source* into *target* when they exist in *source*."""
    for field in fields:
        if field in source:
            target[field] = source[field]


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base* and return *base*.

    Nested dictionaries are merged key-wise so defaults survive when the
    override only sets a subset. Non-dict values in *override* replace the
    corresponding value in *base*. *base* is modified in place.
    """
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def populate_devices_from_store(cfg: dict, store_devices: dict, fields: list) -> None:
    """Build ``cfg['devices']`` list from store data when no devices exist in config."""
    if cfg.get("devices"):
        return
    cfg["devices"] = []
    for dev_name, store_dev in store_devices.items():
        entry = {"name": dev_name, "panels": store_dev.get("panels", [])}
        if "config" in store_dev:
            merge_store_fields(store_dev["config"], entry, fields)
        cfg["devices"].append(entry)


def apply_panel_store(cfg: dict, store: dict, fields: list) -> None:
    """Apply per-device panel store data to the config."""
    for dev in cfg.get("devices", []):
        dev_name = dev.get("name", "")
        store_dev = find_store_device(store, dev_name)
        if store_dev is None:
            continue
        dev["panels"] = store_dev.get("panels", [])
        if "config" in store_dev:
            merge_store_fields(store_dev["config"], dev, fields)

    # Apply the runtime device's settings; it is the first entry in cfg["devices"].
    devs = cfg.get("devices", [])
    runtime_name = devs[0].get("name", "") if devs else ""
    if not runtime_name:
        runtime_name = cfg.get("device", {}).get("name", "")
    if runtime_name:
        store_dev = find_store_device(store, runtime_name)
        if store_dev and "config" in store_dev:
            merge_store_fields(store_dev["config"], cfg["device"], fields)

"""HA Store wrapper for panel configuration.

Per-device settings (including ``enabled``) and panels are stored in HA's
storage system. config_entry.data holds only the hub name, each device's
identity (name and ESPHome device id) and ``removed_devices``. The frontend
HAUI Editor reads and writes it through the REST API.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Coroutine, Mapping
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from ..haui.device_config import DEVICE_CONFIG, find_store_device
from ..haui.mapping.color import BUILTIN_THEMES, active_tile_color
from ..haui.mapping.const import GESTURES
from ..haui.utils.color import parse_color_value

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

# Settings that no longer exist: the theme variant went away with the themes'
# own icon palettes, which the theme's page background selects.
REMOVED_DEVICE_CONFIG_KEYS = ("theme_variant",)


def migrate_device_config_keys(device_config: dict[str, Any]) -> bool:
    """Rename legacy device-config keys in place and convert the old gesture settings."""
    modified = False
    for old_key, new_key in DEVICE_CONFIG_KEY_RENAMES.items():
        if old_key not in device_config:
            continue
        old_value = device_config.pop(old_key)
        if new_key not in device_config:
            device_config[new_key] = old_value
        modified = True
    for removed_key in REMOVED_DEVICE_CONFIG_KEYS:
        if removed_key in device_config:
            del device_config[removed_key]
            modified = True
    return migrate_gesture_settings(device_config) or modified


# The automatic-install settings the hub-wide update policy of the 0.5.0
# development builds held for every device.
_HUB_POLICY_FIELDS = (
    "firmware_auto_update",
    "auto_install",
    "install_delay",
    "max_attempts",
    "retry_interval",
)


def migrate_hub_update_policy(store_data: dict[str, Any]) -> bool:
    """Give every device the update settings it ran with under the hub-wide policy.

    The 0.5.0 development builds kept one automatic update policy for the hub
    (store key ``update_policy``), which a device followed unless its
    ``update.policy_override`` was on. Update settings belong to each device
    again: a device that followed the hub takes the hub's values, a device that
    overrode it (or stored its own before the policy existed) keeps its own.
    """
    modified = "update_policy" in store_data
    hub_policy = store_data.pop("update_policy", None) or {}
    for dev_data in store_data.get("devices", {}).values():
        config = dev_data.get("config") if isinstance(dev_data, dict) else None
        if not isinstance(config, dict):
            continue
        stored = config.get("update")
        update = dict(stored) if isinstance(stored, dict) else {}
        own = update.pop("policy_override", None)
        if own is None:
            own = any(field in update for field in _HUB_POLICY_FIELDS)
        if not own:
            for field in _HUB_POLICY_FIELDS:
                update.pop(field, None)
            update.update(hub_policy)
        if update != (stored or {}):
            config["update"] = update
            modified = True
    return modified


def migrate_gesture_settings(device_config: dict[str, Any]) -> bool:
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


# The firmware's initial "Brightness Dimmed" (esphome/nspanel_haui/number.yaml).
FIRMWARE_BRIGHTNESS_DIM = 20


def migrate_schedule_brightness_dim(device_name: str, device_config: dict[str, Any]) -> bool:
    """Give a schedule that dims a dimmed brightness to restore when its entries end.

    0.5.0 let an entry set ``brightness_dim`` while the device left it to the
    panel, so the entry's value stayed after the entry ended. A device setting
    is required now; such a device takes the firmware's default.

    Args:
        device_name: Name of the device, for the log.
        device_config: The device's stored settings.

    Returns:
        True when the setting was added.
    """
    if device_config.get("brightness_dim") is not None:
        return False
    schedule = device_config.get("schedule") or []
    if not any(entry.get("brightness_dim") is not None for entry in schedule):
        return False
    device_config["brightness_dim"] = FIRMWARE_BRIGHTNESS_DIM
    _LOGGER.warning(
        "Set the dimmed brightness of %s to %s %%: its schedule dims the display and "
        "needs a dimmed brightness to restore when an entry ends",
        device_name,
        FIRMWARE_BRIGHTNESS_DIM,
    )
    return True


def drop_fixed_sys_overrides(device_name: str, device_data: dict[str, Any]) -> bool:
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


# The muted text tone of each built-in palette: the quick start's word clock
# preset stored one as the colour of the unlit letters.
MUTED_TEXT_TONES = frozenset(theme["colors"]["text_inactive"] for theme in BUILTIN_THEMES.values())


def drop_preset_clock_off_color(device_name: str, device_data: dict[str, Any]) -> bool:
    """Drop the off-letter colour the quick start's word clock preset stored.

    The preset wrote the device theme's muted text tone there. An unlit letter
    belongs in the tone of the page behind it, which is what an empty field
    gives the page; on a light page the muted text tone sits nearly as dark as
    the lit letters, so the two could hardly be told apart.

    Args:
        device_name: Name of the device, for the log.
        device_data: One device of the panel store.

    Returns:
        True when a panel was changed.
    """
    modified = False
    for panel in device_data.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("type") != "clocktwo":
            continue
        stored = panel.get("off_color")
        if not stored or parse_color_value(stored) not in MUTED_TEXT_TONES:
            continue
        del panel["off_color"]
        modified = True
        _LOGGER.warning(
            "Cleared the off-letter color of %s on %s: unlit letters take the color "
            "of the page behind them",
            panel.get("key") or panel.get("title") or "the word clock",
            device_name,
        )
    return modified


# The colours the quick start's grid presets wrote into every tile: the built-in
# palettes' on-tile background and their entity-on colour.
PRESET_TILE_COLORS = frozenset(
    active_tile_color(theme["colors"]["background"], theme["colors"]["entity_on"])
    for theme in BUILTIN_THEMES.values()
)
PRESET_POWER_COLORS = frozenset(theme["colors"]["entity_on"] for theme in BUILTIN_THEMES.values())
# A preset mixed its colour in RGB888 and the hub mixes in RGB565, so a stored
# value can sit one step of a channel off the palette entry it names.
TILE_COLOR_CHANNEL_STEP = 1


def _same_color(stored: int, entry: int) -> bool:
    """Whether two RGB565 colours are the same up to one step of each channel."""
    return all(
        abs(((stored >> shift) & mask) - ((entry >> shift) & mask)) <= TILE_COLOR_CHANNEL_STEP
        for shift, mask in ((11, 0x1F), (5, 0x3F), (0, 0x1F))
    )


def _is_preset_color(value: Any, palette: frozenset[int]) -> bool:
    """Whether a stored tile colour names one of the quick start's theme colours."""
    if isinstance(value, bool) or not isinstance(value, str | int):
        return False
    if isinstance(value, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", value.strip()) is None:
        return False
    stored = parse_color_value(value)
    return any(_same_color(stored, entry) for entry in palette)


def drop_preset_grid_tile_colors(device_name: str, device_data: dict[str, Any]) -> bool:
    """Drop the theme colours the quick start's grid presets stored as literals.

    A preset wrote the device theme's on-tile background and power-button colour
    into every tile, which pinned those tiles to the theme the setup was created
    in: after a theme change an on tile kept a dark tint on a light page. The hub
    resolves both from the theme on every render now (``haui/page/grid.py``), so
    a stored value that is one of the built-in palettes is dropped and a colour
    the user picked stays.

    Args:
        device_name: Name of the device, for the log.
        device_data: One device of the panel store.

    Returns:
        True when a panel was changed.
    """
    modified = False
    for panel in device_data.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("type") != "grid":
            continue
        dropped = False
        for entry in panel.get("items") or []:
            if not isinstance(entry, dict):
                continue
            if _is_preset_color(entry.get("power_color"), PRESET_POWER_COLORS):
                del entry["power_color"]
                dropped = True
            back_color = entry.get("back_color")
            if isinstance(back_color, dict):
                for state in ("on", "playing"):
                    if _is_preset_color(back_color.get(state), PRESET_TILE_COLORS):
                        del back_color[state]
                        dropped = True
                if not back_color:
                    del entry["back_color"]
            elif _is_preset_color(back_color, PRESET_TILE_COLORS):
                del entry["back_color"]
                dropped = True
        if dropped:
            modified = True
            _LOGGER.warning(
                "Cleared the theme colors of the grid tiles of %s on %s: an on tile "
                "follows the selected theme",
                panel.get("key") or panel.get("title") or "a grid panel",
                device_name,
            )
    return modified


def panel_store(hass: Any, entry_id: str) -> Store[dict[str, Any]]:
    """Return the HA Store holding the panel config of one config entry."""
    return Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")


async def finish_panel_write[T](operation: Coroutine[Any, Any, T]) -> T:
    """Keep the caller's entry lock until a started write finishes."""
    task = asyncio.create_task(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # A cancelled await cannot stop the executor's file write. Let it
        # finish before allowing a later edit to load or overwrite its data.
        while not task.done():
            try:
                await asyncio.wait((task,))
            except asyncio.CancelledError:
                continue
        if not task.cancelled() and (error := task.exception()) is not None:
            _LOGGER.error("Panel store operation failed after cancellation", exc_info=error)
        raise


def empty_store() -> dict[str, Any]:
    """Return a fresh panel store payload for an entry with no saved panels."""
    return {"version": 1, "device_order": [], "devices": {}, "themes": {}}


def normalize_device_order(store_data: dict[str, Any]) -> bool:
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


def empty_device() -> dict[str, Any]:
    """Return a fresh store entry for a device: default settings, no panels."""
    return {"config": {}, "panels": []}


async def async_remove_device(hass: Any, entry: ConfigEntry, name: str) -> bool:
    """Remove the device and schedule the hub reload via its entry listener."""
    async with entry.setup_lock:
        if hass.config_entries.async_get_entry(entry.entry_id) is not entry:
            return False
        if not any(device.get("name") == name for device in entry.data.get("devices", [])):
            return False
        store = panel_store(hass, entry.entry_id)
        panels_data = await store.async_load() or empty_store()
        devices = panels_data.get("devices", {})
        modified = False
        if name in devices:
            devices.pop(name)
            modified = True
        if normalize_device_order(panels_data):
            modified = True

        async def commit_removal() -> None:
            if modified:
                await store.async_save(panels_data)
                _LOGGER.debug("Removed device %s from panel store for %s", name, entry.entry_id)

            new_data = dict(entry.data)
            new_data["devices"] = [d for d in new_data.get("devices", []) if d.get("name") != name]
            # Keeps auto-add from adding the device straight back while ESPHome still has it.
            new_data["removed_devices"] = [*entry.data.get("removed_devices", []), name]
            hass.config_entries.async_update_entry(entry, data=new_data)
            _LOGGER.debug("Removed device %s from config_entry.data for %s", name, entry.entry_id)

        await finish_panel_write(commit_removal())
    return True


def enabled_device_names(entry_data: Mapping[str, Any], store_data: Mapping[str, Any]) -> list[str]:
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
        self._store: Store[dict[str, Any]] = panel_store(hass, entry_id)
        self._config_entry: ConfigEntry | None = config_entry

    async def load(self) -> dict[str, Any]:
        """Load panel data from store, returning default if empty.

        Adds an empty store entry for every device in config_entry.data that
        the store doesn't have yet (e.g. added by the config flow or
        auto-discovery).
        """
        data = await self._store.async_load()
        result: dict[str, Any] = data or empty_store()
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
        modified = migrate_hub_update_policy(result) or root_modified
        for dev_name, dev_data in result.get("devices", {}).items():
            if not isinstance(dev_data, dict):
                continue
            config = dev_data.get("config")
            if isinstance(config, dict):
                if migrate_device_config_keys(config):
                    modified = True
                if migrate_schedule_brightness_dim(dev_name, config):
                    modified = True
            if drop_fixed_sys_overrides(dev_name, dev_data):
                modified = True
            if drop_preset_clock_off_color(dev_name, dev_data):
                modified = True
            if drop_preset_grid_tile_colors(dev_name, dev_data):
                modified = True

        if normalize_device_order(result):
            modified = True

        if modified:
            await finish_panel_write(self._store.async_save(result))

        return result

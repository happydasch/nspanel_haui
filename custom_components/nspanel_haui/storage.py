"""HA Store wrapper for panel configuration.

Panels are stored independently in HA's storage system, separate from
config_entry.data (connection + device identity) and config_entry.options
(runtime toggles). The frontend HAUI Editor reads/writes panels via the
REST API in api.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .haui.device_config import DEVICE_CONFIG_FIELDS  # noqa: F401  # re-export for bw-compat

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


PANEL_STORE_VERSION = 1


class PanelStorage:
    """HA Store wrapper for per-entry panel configuration."""

    def __init__(self, hass: Any, entry_id: str, config_entry: ConfigEntry | None = None) -> None:
        self._store: Store = Store(hass, PANEL_STORE_VERSION, f"nspanel_haui.{entry_id}_panels")
        self._config_entry: ConfigEntry | None = config_entry

    async def load(self) -> dict:
        """Load panel data from store, returning default if empty.

        On first load for a config entry, auto-populates per-device
        ``config`` objects from config_entry.data and adds any devices
        that exist in config_entry but not yet in the store.
        """
        data = await self._store.async_load()
        result: dict = data or {"version": 1, "devices": {}}

        if self._config_entry is not None:
            modified = False
            ce_devices: list[dict] = self._config_entry.data.get("devices", [])
            ce_devices_by_name: dict[str, dict] = {d["name"]: d for d in ce_devices if "name" in d}

            # Auto-populate config for existing store devices that lack it
            for dev_name, dev_data in result.get("devices", {}).items():
                if "config" not in dev_data:
                    ce_dev = ce_devices_by_name.get(dev_name)
                    if ce_dev:
                        dev_data["config"] = {
                            field: ce_dev.get(field) for field in DEVICE_CONFIG_FIELDS
                        }
                        modified = True

            # Add devices from config_entry that aren't in the store yet
            for dev_name, ce_dev in ce_devices_by_name.items():
                if dev_name not in result.get("devices", {}):
                    result.setdefault("devices", {})[dev_name] = {
                        "config": {field: ce_dev.get(field) for field in DEVICE_CONFIG_FIELDS},
                        "panels": [],
                    }
                    modified = True

            # Migration: old "mode" field -> new "show_in_navigation" field
            for dev_data in result.get("devices", {}).values():
                for panel in dev_data.get("panels", []):
                    if isinstance(panel, dict) and "mode" in panel:
                        mode_val = panel.get("mode")
                        if mode_val in ("subpanel", "popup"):
                            panel["show_in_navigation"] = False
                        # "panel" (default) - remove mode; show_in_navigation defaults to True
                        del panel["mode"]
                        modified = True

            if modified:
                await self._store.async_save(result)

        return result

    async def save(self, data: dict) -> None:
        """Save panel data to store."""
        await self._store.async_save(data)

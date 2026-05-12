"""Config flow for NSPanel HAUI.

Per-device and panel configuration lives in the custom frontend panel
editor (talks to ``/api/nspanel_haui/panels``).
"""

from __future__ import annotations

import copy
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectOptionDict

from .esphome_helpers import discover_esphome_devices as _discover_esphome_devices
from .haui.device_config import DEVICE_CONFIG

DOMAIN = "nspanel_haui"


class NSPanelHAUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the hub entry - auto-discovers ESPHome devices and creates entry."""
        # Prevent multiple config entries - only one hub supported
        if self._async_current_entries():
            # TODO user readable string
            return self.async_abort(reason="single_instance_allowed")

        name = "NSPanel HAUI Hub"

        # Discover NSPanel devices via ESPHome config entries
        devices: list[dict[str, Any]] = []
        discovered = await _discover_esphome_devices(self.hass)
        for d in discovered:
            dev = copy.deepcopy(DEVICE_CONFIG)
            dev["name"] = d["name"]
            dev["enabled"] = False  # New devices are disabled by default
            if d.get("esphome_device_id"):
                dev["esphome_device_id"] = d["esphome_device_id"]
            devices.append(dev)

        await self.async_set_unique_id(name)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=name,
            data={
                "name": name,
                "devices": devices,
            },
        )

    async def async_step_select_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Second step: pick discovered devices."""
        discovered: list[dict] = getattr(self, "_discovered_devices", [])
        entry_name: str = getattr(self, "_entry_name", "nspanel_haui")

        if user_input is not None:
            selected: list[str] = user_input.get("selected_devices", [])

            discovered_map: dict[str, dict] = {d["name"]: d for d in discovered}
            devices_list: list[dict] = []
            for device_name in selected:
                dev = copy.deepcopy(DEVICE_CONFIG)
                dev["name"] = device_name
                dev["enabled"] = False  # New devices are disabled by default
                match = discovered_map.get(device_name)
                if match:
                    dev["esphome_device_id"] = match.get("esphome_device_id", "")
                devices_list.append(dev)

            return self.async_create_entry(
                title=entry_name,
                data={
                    "name": entry_name,
                    "devices": devices_list,
                },
            )

        if not discovered:
            return self.async_show_form(
                step_id="select_devices",
                data_schema=vol.Schema({}),
                description_placeholders={"count": "0", "esphome_info": ""},
            )

        esphome_count = sum(1 for d in discovered if d.get("esphome_device_id"))
        esphome_info = f"ESPHome matched: {esphome_count} device(s)" if esphome_count > 0 else ""

        preselected = [d["name"] for d in discovered if d.get("esphome_device_id")]
        if not preselected:
            preselected = [d["name"] for d in discovered]

        device_options = [
            SelectOptionDict(
                value=d["name"],
                label=d["name"],
            )
            for d in discovered
        ]
        return self.async_show_form(
            step_id="select_devices",
            data_schema=vol.Schema({
                vol.Required("selected_devices", default=preselected): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.LIST,
                        multiple=True,
                    )
                ),
            }),
            description_placeholders={
                "count": str(len(discovered)),
                "esphome_info": esphome_info,
            },
        )

    @staticmethod
    async def async_migrate_entry(hass, config_entry):
        """No migration needed - current version."""
        return True

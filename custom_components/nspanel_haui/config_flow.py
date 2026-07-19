"""Config flow for NSPanel HAUI.

Per-device and panel configuration lives in the custom frontend panel
editor (talks to ``/api/nspanel_haui/panels``).
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant import config_entries

from .esphome_helpers import discover_esphome_devices as _discover_esphome_devices
from .haui.device_config import DEVICE_CONFIG

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nspanel_haui"


def _make_device_entry(d: dict[str, Any]) -> dict[str, Any]:
    """Build a hub device entry from a discovery result."""
    dev = copy.deepcopy(DEVICE_CONFIG)
    dev["name"] = d["name"]
    dev["enabled"] = True
    if d.get("esphome_device_id"):
        dev["esphome_device_id"] = d["esphome_device_id"]
    return dev


class NSPanelHAUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    HUB_NAME = "NSPanel HAUI Hub"

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the hub entry - auto-discovers ESPHome devices and creates entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        discovered = await _discover_esphome_devices(self.hass)
        devices = [_make_device_entry(d) for d in discovered]

        _LOGGER.info("Creating hub entry with %d device(s)", len(devices))

        await self.async_set_unique_id(self.HUB_NAME)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=self.HUB_NAME,
            data={"name": self.HUB_NAME, "devices": devices},
        )

    async def _async_show_discovery_card(
        self,
    ) -> config_entries.ConfigFlowResult:
        """Validate HAUI devices exist, then show the discovery card."""
        await self.async_set_unique_id(self.HUB_NAME)
        self._abort_if_unique_id_configured()

        discovered = await _discover_esphome_devices(self.hass)
        if not discovered:
            return self.async_abort(reason="no_devices_found")

        self._discovered_devices = discovered
        self.context["title_placeholders"] = {
            "name": self.HUB_NAME,
            "count": str(len(discovered)),
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Discovery confirmation card shown on the HA dashboard."""
        discovered = getattr(self, "_discovered_devices", None) or []
        if user_input is not None:
            devices = [_make_device_entry(d) for d in discovered]
            _LOGGER.info(
                "Creating hub entry with %d HAUI device(s)",
                len(devices),
            )
            return self.async_create_entry(
                title=self.HUB_NAME,
                data={"name": self.HUB_NAME, "devices": devices},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "count": str(len(discovered)),
                "names": ", ".join(d["name"] for d in discovered) or "—",
            },
        )

    async def async_step_integration_discovery(
        self,
        discovery_info: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Surface a discovery card on the dashboard."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return await self._async_show_discovery_card()

    async def async_step_zeroconf(
        self,
        discovery_info: Any,
    ) -> config_entries.ConfigFlowResult:
        """Handle zeroconf discovery (manifest filters by project_name)."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return await self._async_show_discovery_card()

    async def async_step_dhcp(
        self,
        discovery_info: Any,
    ) -> config_entries.ConfigFlowResult:
        """Handle DHCP discovery for registered HAUI devices."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return await self._async_show_discovery_card()

    @staticmethod
    async def async_migrate_entry(hass, config_entry):
        """No migration needed - current version."""
        return True

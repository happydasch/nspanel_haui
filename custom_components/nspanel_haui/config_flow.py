"""Config flow for NSPanel HAUI.

Hub-scoped settings - the hub name and the display defaults every panel
inherits - are changed after setup through this integration's options flow:
:class:`NSPanelHAUIHubOptionsFlow`.  Per-device settings and panels are saved
through dedicated routes in the custom frontend panel editor:
``/api/nspanel_haui/devices``, ``/api/nspanel_haui/panels``,
``/api/nspanel_haui/device_order`` and ``/api/nspanel_haui/themes``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import DOMAIN
from .haui.device_config import HUB_OPTION_KEYS, hub_options
from .haui.mapping.const import DEFAULT_CONFIG
from .haui.utils.locale_data import normalize_pattern_name
from .hub.esphome_helpers import discover_esphome_devices as _discover_esphome_devices
from .hub.esphome_helpers import hub_device_entry

_LOGGER = logging.getLogger(__name__)

# Locale date layouts a panel can inherit; the same values the editor offers,
# where the selected layout follows the device language.  Each one is a selector
# option value, so it has to be a valid translation key (see
# ``haui/utils/locale_data.py``).
DATE_FORMAT_LOCALE_OPTIONS: tuple[str, ...] = (
    "full",
    "long",
    "medium",
    "short",
    "weekday_short",
    "weekday_full",
)

# A longer strftime pattern is a paste accident, not a format.
MAX_FORMAT_LENGTH = 64

# Option keys whose value is a strftime pattern.
FORMAT_OPTION_KEYS: tuple[str, ...] = ("time_format", "date_format")


def _hub_settings_schema(values: Mapping[str, Any]) -> vol.Schema:
    """Build the hub settings form with *values* shown as the defaults.

    Args:
        values: The values to prefill, normally what a panel inherits today.

    Returns:
        vol.Schema: The options form.
    """
    schema: dict[Any, Any] = {
        vol.Required("name", default=values.get("name", "")): TextSelector(),
    }
    for key in FORMAT_OPTION_KEYS:
        schema[vol.Required(key, default=values.get(key, ""))] = TextSelector()
    # A layout stored before the rename is offered under its current name.
    stored_layout = normalize_pattern_name(values.get("date_format_locale", ""))
    schema[vol.Required("date_format_locale", default=stored_layout)] = SelectSelector(
        SelectSelectorConfig(
            options=list(DATE_FORMAT_LOCALE_OPTIONS),
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="date_format_locale",
        )
    )
    return vol.Schema(schema)


class NSPanelHAUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    HUB_NAME = "NSPanel HAUI Hub"

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NSPanelHAUIHubOptionsFlow:
        """Return the flow that edits the hub-scoped settings."""
        return NSPanelHAUIHubOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the hub entry - auto-discovers ESPHome devices and creates entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        discovered = await _discover_esphome_devices(self.hass)
        devices = [hub_device_entry(d) for d in discovered]

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
            devices = [hub_device_entry(d) for d in discovered]
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


class NSPanelHAUIHubOptionsFlow(config_entries.OptionsFlow):
    """Edit the settings that belong to the hub rather than to a device.

    The hub name is the config entry's title, the one value Home Assistant
    shows for this integration; the display formats are the defaults every
    panel inherits while its own value is empty.  Saving reloads the entry, so
    every panel restarts with the new defaults.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Rename the hub and set the display defaults every panel inherits."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input.get("name", "")).strip()
            options = hub_options(user_input)
            if not name:
                errors["base"] = "empty_name"
            else:
                for key in FORMAT_OPTION_KEYS:
                    value = options.get(key, "")
                    if value and ("%" not in value or len(value) > MAX_FORMAT_LENGTH):
                        errors["base"] = "invalid_format"
                        break

            if not errors:
                # One write: ``async_create_entry`` stores the same options, so
                # the entry's update listener reloads the hub exactly once.
                self.hass.config_entries.async_update_entry(
                    self.config_entry, title=name, options=options
                )
                _LOGGER.info("NSPanel HAUI hub settings saved (name=%r)", name)
                return self.async_create_entry(data=options)

        # Prefill what a panel inherits today: the built-in default, overlaid by
        # whatever the hub already stores.
        shown: dict[str, Any] = {key: DEFAULT_CONFIG[key] for key in HUB_OPTION_KEYS}
        shown.update(hub_options(self.config_entry.options))
        shown["name"] = self.config_entry.title
        if user_input is not None:
            # Show what was submitted, so a rejected value stays visible.
            shown.update(user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_hub_settings_schema(shown),
            errors=errors,
        )

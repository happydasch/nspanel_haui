"""Repairs platform for NSPanel HAUI.

Provides fix flows for issues created by the integration (see ``__init__.py``
and ``strings.json`` -> ``issues``).  The flow manager deletes the issue
automatically once its fix flow finishes.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

# Issue id prefix shared with __init__.py; device issues are
# ``device_start_failed_<slugified device name>``.
DEVICE_START_FAILED = "device_start_failed"


class DeviceStartFailedFixFlow(RepairsFlow):
    """Retry starting a device by reloading the hub config entry."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Start the fix flow."""
        return await self.async_step_reload()

    async def async_step_reload(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Confirm and reload the hub so the device is set up again."""
        if user_input is not None:
            entries = self.hass.config_entries.async_entries(DOMAIN)
            if entries:
                self.hass.config_entries.async_schedule_reload(entries[0].entry_id)
            return self.async_create_entry(title="", data={})

        issue_data = self.data or {}
        placeholders: dict[str, str] = {"device": str(issue_data.get("device", ""))}
        # Resolve the placeholders the issue was created with (device, error),
        # matching the default ConfirmRepairFlow behaviour.
        issue_registry = ir.async_get(self.hass)
        if issue := issue_registry.async_get_issue(self.handler, self.issue_id):
            placeholders.update(issue.translation_placeholders or {})
        return self.async_show_form(
            step_id="reload",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None = None,
    *args: Any,
    **kwargs: Any,
) -> RepairsFlow | None:
    """Create a fix flow for a fixable issue, or ``None`` to use the default."""
    if issue_id.startswith(DEVICE_START_FAILED):
        return DeviceStartFailedFixFlow()
    return None

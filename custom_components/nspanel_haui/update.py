"""Update platform for NSPanel HAUI.

Exposes each panel's display TFT as a "HAUI Display" update entity, next to
the firmware's own "HAUI Firmware" entity on the same device.  The installed
version is the TFT the display reports, the latest version the TFT the
firmware needs (its ``yaml_version``).  Installing runs the hub's TFT update:
the device downloads the matching GitHub release TFT and flashes the display.

State arrives as ``nspanel_haui.display_update_changed`` events that the
update controller fires on every version or update-state change, so no
polling or worker round-trip is needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN
from .haui.controller.update import (
    DISPLAY_UPDATE_EVENT,
    UPDATE_STATE_CHECKING,
    UPDATE_STATE_ERROR,
    UPDATE_STATE_INSTALLING,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .nspanel_haui import NSPanelHAUI


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one display update entity per linked device in this hub entry."""
    apps: dict[str, NSPanelHAUI] = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NSPanelDisplayUpdate] = []
    for dev_name, app in apps.items():
        if app._ha_device_id is None:
            # Same rule as the notify and sensor platforms: an entity would
            # create a bare device holding the identifier that the ESPHome
            # link adds later, making that link fail.
            continue
        entities.append(NSPanelDisplayUpdate(app, dev_name, config_entry))

    async_add_entities(entities)


class NSPanelDisplayUpdate(UpdateEntity):
    """Display TFT of one NSPanel device as a Home Assistant update entity."""

    _attr_has_entity_name = True
    _attr_name = "HAUI Display"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.SPECIFIC_VERSION
    )
    _attr_title = "NSPanel HAUI display"
    _attr_available = False

    def __init__(
        self,
        app: NSPanelHAUI,
        dev_name: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the display update entity.

        Args:
            app: The NSPanelHAUI app instance for the target device.
            dev_name: Display name of the device.
            config_entry: The HA config entry for this hub.
        """
        self._app = app
        self._dev_name = dev_name
        self._update_state: str | None = None
        self._attr_unique_id = f"{config_entry.entry_id}_{dev_name}_display_update"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_name)})
        self._listeners: list[Any] = []

    @property
    def in_progress(self) -> bool:
        """Whether the hub is installing a TFT.

        Read from the hub's update state: the upload runs for minutes after
        ``async_install`` returns, and Home Assistant resets
        ``_attr_in_progress`` when it does.
        """
        return self._update_state in (UPDATE_STATE_CHECKING, UPDATE_STATE_INSTALLING)

    async def async_added_to_hass(self) -> None:
        """Subscribe to the hub's display update events."""
        self._listeners.append(
            self.hass.bus.async_listen(DISPLAY_UPDATE_EVENT, self._async_display_update)
        )
        # The device may have connected before the entity was added.
        self._app.dispatch(self._app.publish_display_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the event bus listener."""
        for remove in self._listeners:
            remove()
        self._listeners.clear()

    async def _async_display_update(self, event: Event) -> None:
        """Update versions and progress from a hub display update event."""
        data = event.data or {}
        if data.get("device") != self._dev_name:
            return
        self._update_state = data.get("state")
        self._attr_installed_version = data.get("installed_version")
        self._attr_latest_version = data.get("latest_version")
        # The upload blocks the device and ends in a reboot, so the entity
        # stays available while an install keeps the device offline.
        self._attr_available = (
            bool(data.get("connected")) or self._update_state == UPDATE_STATE_INSTALLING
        )
        self.async_write_ha_state()

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install the TFT the firmware needs, or the GitHub release ``version``.

        Raises:
            HomeAssistantError: When the install could not start (device
                offline, no matching GitHub release, upload command not sent).
        """
        result = await self._app.async_run_on_worker(self._app.install_tft, version)
        if result.get("state") == UPDATE_STATE_ERROR:
            raise HomeAssistantError(result.get("last_error") or "TFT update failed")

"""Update platform for NSPanel HAUI.

Exposes two update entities per panel:

- "HAUI Firmware" — the ESPHome firmware.  The installed version is the
  firmware's ``yaml_version``, the latest version the one the firmware
  manifest at the device's ``firmware_manifest_url`` names (by default the
  latest GitHub release's).  Installing flashes the manifest's image with the
  firmware's ``install_firmware_url`` action.
- "HAUI Display" — the display TFT.  The installed version is the TFT the
  display reports, the latest version the TFT the firmware needs (its
  ``yaml_version``).  Installing runs the hub's TFT update: the device
  downloads the matching GitHub release TFT and flashes the display.

State arrives as events that the update controller fires on every version or
update-state change, so no polling or worker round-trip is needed.
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
    FIRMWARE_UPDATE_EVENT,
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
    """Set up the firmware and display update entities of each linked device."""
    apps: dict[str, NSPanelHAUI] = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[_NSPanelUpdate] = []
    for dev_name, app in apps.items():
        if app._ha_device_id is None:
            # Same rule as the notify and sensor platforms: an entity would
            # create a bare device holding the identifier that the ESPHome
            # link adds later, making that link fail.
            continue
        firmware = NSPanelFirmwareUpdate(app, dev_name, config_entry)
        _reclaim_firmware_entity_id(hass, firmware._attr_unique_id)
        entities.append(firmware)
        entities.append(NSPanelDisplayUpdate(app, dev_name, config_entry))

    async_add_entities(entities)


def _reclaim_firmware_entity_id(hass: HomeAssistant, unique_id: str | None) -> None:
    """Rename the HAUI Firmware entity to the id the firmware's own entity had.

    Firmware 0.4.2 and 0.4.3 declare an ESPHome update entity named "HAUI
    Firmware" that holds ``update.<device>_haui_firmware``, so Home Assistant
    registers this entity as ``..._2``.  ESPHome deletes its entity once the
    panel reboots into firmware without it; the next setup then renames this
    one, so automations keep the familiar entity id.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("update", DOMAIN, unique_id)
    if entity_id is None or not entity_id.endswith("_2"):
        return
    wanted = entity_id.removesuffix("_2")
    if registry.async_is_registered(wanted) or hass.states.get(wanted) is not None:
        return
    registry.async_update_entity(entity_id, new_entity_id=wanted)


class _NSPanelUpdate(UpdateEntity):
    """Update entity of one NSPanel device, fed by the update controller's events."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.SPECIFIC_VERSION
    )
    _attr_available = False
    # Event the update controller fires for this entity, and the unique id suffix.
    _event: str
    _key: str

    def __init__(
        self,
        app: NSPanelHAUI,
        dev_name: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the update entity.

        Args:
            app: The NSPanelHAUI app instance for the target device.
            dev_name: Display name of the device.
            config_entry: The HA config entry for this hub.
        """
        self._app = app
        self._dev_name = dev_name
        self._attr_unique_id = f"{config_entry.entry_id}_{dev_name}_{self._key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_name)})
        self._listeners: list[Any] = []

    async def async_added_to_hass(self) -> None:
        """Subscribe to the hub's update events."""
        self._listeners.append(self.hass.bus.async_listen(self._event, self._async_update_event))
        # The device may have connected before the entity was added.
        self._request_state()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the event bus listener."""
        for remove in self._listeners:
            remove()
        self._listeners.clear()

    async def _async_update_event(self, event: Event) -> None:
        """Update versions and progress from a hub update event."""
        data = event.data or {}
        if data.get("device") != self._dev_name:
            return
        self._attr_installed_version = data.get("installed_version")
        self._attr_latest_version = data.get("latest_version")
        installing = self._apply(data)
        # An install blocks the device and ends in a reboot, so the entity
        # stays available while an install keeps the device offline.
        self._attr_available = bool(data.get("connected")) or installing
        self.async_write_ha_state()

    def _request_state(self) -> None:
        """Ask the hub to fire this entity's event with the current state."""
        raise NotImplementedError

    def _apply(self, data: dict[str, Any]) -> bool:
        """Take the install state from an event; return whether an install runs."""
        raise NotImplementedError


class NSPanelFirmwareUpdate(_NSPanelUpdate):
    """ESPHome firmware of one NSPanel device as a Home Assistant update entity."""

    _attr_name = "HAUI Firmware"
    _attr_title = "NSPanel HAUI firmware"
    _event = FIRMWARE_UPDATE_EVENT
    _key = "firmware_update"
    _installing = False

    @property
    def in_progress(self) -> bool:
        """Whether the device is installing a firmware.

        Read from the hub's install state: the device flashes the image and
        reboots after ``async_install`` returns, and Home Assistant resets
        ``_attr_in_progress`` when it does.
        """
        return self._installing

    def _request_state(self) -> None:
        self._app.dispatch(self._app.publish_firmware_update)

    def _apply(self, data: dict[str, Any]) -> bool:
        self._installing = bool(data.get("installing"))
        return self._installing

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install the offered firmware, or the manifest or GitHub release ``version``.

        Raises:
            HomeAssistantError: When the install could not start (device
                offline, manifest or release unreadable, install action
                missing).
        """
        result = await self._app.async_run_on_worker(self._app.install_firmware, version, None)
        if result.get("firmware_install_error"):
            raise HomeAssistantError(result["firmware_install_error"])


class NSPanelDisplayUpdate(_NSPanelUpdate):
    """Display TFT of one NSPanel device as a Home Assistant update entity."""

    _attr_name = "HAUI Display"
    _attr_title = "NSPanel HAUI display"
    _event = DISPLAY_UPDATE_EVENT
    _key = "display_update"
    _update_state: str | None = None

    @property
    def in_progress(self) -> bool:
        """Whether the hub is installing a TFT.

        Read from the hub's update state: the upload runs for minutes after
        ``async_install`` returns, and Home Assistant resets
        ``_attr_in_progress`` when it does.
        """
        return self._update_state in (UPDATE_STATE_CHECKING, UPDATE_STATE_INSTALLING)

    def _request_state(self) -> None:
        self._app.dispatch(self._app.publish_display_update)

    def _apply(self, data: dict[str, Any]) -> bool:
        self._update_state = data.get("state")
        return self._update_state == UPDATE_STATE_INSTALLING

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install the TFT the firmware needs, or the GitHub release ``version``.

        Raises:
            HomeAssistantError: When the install could not start (device
                offline, no matching GitHub release, upload command not sent).
        """
        result = await self._app.async_run_on_worker(self._app.install_tft, version)
        if result.get("state") == UPDATE_STATE_ERROR:
            raise HomeAssistantError(result.get("last_error") or "TFT update failed")

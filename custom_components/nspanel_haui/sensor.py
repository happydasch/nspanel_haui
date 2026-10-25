"""Sensor platform for NSPanel HAUI.

Exposes the current display page of each device as a string sensor for
automation triggers.  The sensor is updated from the hub's
``nspanel_haui.page_changed`` events on the HA event bus — the hub fires them
whenever a panel is opened or closed, so no per-app polling or worker
round-trip is needed.  A ``nspanel_haui.connection_changed`` event marks the
sensor unavailable while the panel device is offline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .nspanel_haui import NSPanelHAUI

PAGE_CHANGED_EVENT = "nspanel_haui.page_changed"
CONNECTION_CHANGED_EVENT = "nspanel_haui.connection_changed"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one current-page sensor per linked device in this hub entry."""
    apps: dict[str, NSPanelHAUI] = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NSPanelPageSensor] = []
    for dev_name, app in apps.items():
        if app._ha_device_id is None:
            # Same rule as the notify platform: a sensor would create a bare
            # device holding the identifier that the ESPHome link adds later,
            # making that link fail.  The entry reloads once the device links.
            continue
        entities.append(NSPanelPageSensor(app, dev_name, config_entry))

    async_add_entities(entities)


class NSPanelPageSensor(SensorEntity):
    """Current display page of one NSPanel device, as a string sensor.

    The native value is the Nextion page name (e.g. ``grid``, ``weather``,
    ``popup_light``); attributes carry the panel key, type and title so
    automations can react to the specific panel shown.
    """

    _attr_has_entity_name = True
    _attr_name = "Current page"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:view-dashboard-outline"
    _attr_available = False
    _attr_native_value: str | None = None

    def __init__(
        self,
        app: NSPanelHAUI,
        dev_name: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the current-page sensor.

        Args:
            app: The NSPanelHAUI app instance for the target device.
            dev_name: Display name of the device.
            config_entry: The HA config entry for this hub.
        """
        self._app = app
        self._dev_name = dev_name
        self._attr_unique_id = f"{config_entry.entry_id}_{dev_name}_current_page"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_name)})
        self._listeners: list[Any] = []

    async def async_added_to_hass(self) -> None:
        """Subscribe to the hub's page/connection events on the HA bus."""
        bus = self.hass.bus
        self._listeners.append(bus.async_listen(PAGE_CHANGED_EVENT, self._async_page_changed))
        self._listeners.append(
            bus.async_listen(CONNECTION_CHANGED_EVENT, self._async_connection_changed)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the event bus listeners."""
        for remove in self._listeners:
            remove()
        self._listeners.clear()

    async def _async_page_changed(self, event: Event) -> None:
        """Update the sensor when the hub opens or closes a panel."""
        data = event.data or {}
        if data.get("device") != self._dev_name:
            return
        self._attr_native_value = data.get("page") or data.get("panel")
        self._attr_extra_state_attributes = {
            "panel": data.get("panel") or "",
            "type": data.get("type") or "",
            "title": data.get("title") or "",
        }
        self._attr_available = True
        self.async_write_ha_state()

    async def _async_connection_changed(self, event: Event) -> None:
        """Mark the sensor unavailable while the panel device is offline."""
        data = event.data or {}
        if data.get("device") != self._dev_name:
            return
        self._attr_available = bool(data.get("connected"))
        if not self._attr_available:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
        self.async_write_ha_state()

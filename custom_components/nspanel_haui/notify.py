"""Notify platform for NSPanel HAUI.

Exposes one NotifyEntity per device, plus a persistent variant, so
automations and scripts can use the standard ``notify.send_message``
service to send notifications to the panel display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .nspanel_haui import NSPanelHAUI


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up notify entities for every device in this hub entry."""
    apps: dict[str, NSPanelHAUI] = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NSPanelNotifyEntity] = []
    for dev_name, app in apps.items():
        if app is None:
            continue
        entities.append(NSPanelNotifyEntity(app, dev_name, config_entry, persistent=False))
        entities.append(NSPanelNotifyEntity(app, dev_name, config_entry, persistent=True))

    async_add_entities(entities)


class NSPanelNotifyEntity(NotifyEntity):
    """Notify entity for a single NSPanel HAUI device.

    Sends notifications to the panel display through the
    device's notification controller.
    """

    _attr_has_entity_name = True
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(
        self,
        app: NSPanelHAUI,
        dev_name: str,
        config_entry: ConfigEntry,
        persistent: bool = False,
    ) -> None:
        """Initialize the notify entity.

        Args:
            app: The NSPanelHAUI app instance for the target device.
            dev_name: Display name of the device.
            config_entry: The HA config entry for this hub.
            persistent: When True, notification sound loops until dismissed.
        """
        self._app = app
        self._persistent = persistent

        suffix = "_persistent" if persistent else ""
        self._attr_unique_id = f"{config_entry.entry_id}_{dev_name}_notify{suffix}"

        if persistent:
            self._attr_name = "Persistent notification"
        else:
            self._attr_name = None  # inherit device name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev_name)},
        )

    def send_message(self, message: str, title: str | None = None) -> None:
        """Send a message to the panel display.

        Called on the executor thread by the base ``NotifyEntity``
        machinery.
        """
        notif_ctrl = self._app.controller.get("notification")
        if notif_ctrl is None:
            return

        notif_ctrl.send_notification(
            title=title or "Home Assistant",
            message=message,
            persistent=self._persistent,
        )

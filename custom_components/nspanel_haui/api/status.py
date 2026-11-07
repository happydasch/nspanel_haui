"""Live device state: status, notification queue and display refresh."""

from __future__ import annotations

from typing import Any

from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..esphome_helpers import read_network_entities, resolve_temperature_entity_id
from .common import (
    ALL_DEVICES,
    api_errors,
    body_device,
    device_app,
    error,
    for_each_app,
    get_apps,
    json_object,
    query_device,
    running_apps,
)


class DeviceStatusView(HomeAssistantView):
    """REST API view returning live device status."""

    url = "/api/nspanel_haui/status/{entry_id}"
    name = "api:nspanel_haui:status"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return live device status for a config entry.

        Query param ``device`` (optional) restricts the response to a single
        device.  When omitted an aggregate dict is returned, including both
        enabled and disabled devices (status for disabled devices is read
        directly from HA entities).
        """
        hass = request.app["hass"]
        apps = get_apps(hass, entry_id) or {}

        device_name = query_device(request)
        if device_name:
            app = apps.get(device_name)
            if app is not None:
                return self.json(await self._build_running_status(hass, app, device_name))
            # Device may be disabled or pending — read from HA entities
            status = self._build_entity_status(hass, entry_id, device_name)
            if status is not None:
                return self.json(status)
            return self.json(
                {"error": f"device {device_name!r} not found"},
                status_code=404,
            )

        # Enabled devices use their NSPanelHAUI instance, disabled devices get
        # a minimal status from HA entities.
        entry = hass.config_entries.async_get_entry(entry_id)
        all_devices = entry.data.get("devices", []) if entry else []
        result: dict[str, dict] = {}

        for dev in all_devices:
            dev_name = dev.get("name", "")
            if not dev_name:
                continue
            app = apps.get(dev_name)
            if app is not None:
                result[dev_name] = await self._build_running_status(hass, app, dev_name)
            else:
                status = self._build_entity_status(hass, entry_id, dev_name)
                if status is not None:
                    result[dev_name] = status

        return self.json({"devices": result})

    @staticmethod
    async def _build_running_status(hass: Any, app: Any, device_name: str) -> dict:
        """Combine HA-loop entity readings with an app-worker status snapshot."""
        # HA's registries and entity states are event-loop-owned; obtain only
        # the app's mutable runtime snapshot on its worker.
        network_info = read_network_entities(hass, device_name)
        status = await app.async_run_on_worker(app.get_device_status)
        status["device_info"].update(network_info)
        status["device_info"]["temperature_entity_id"] = resolve_temperature_entity_id(
            hass, device_name
        )
        return status

    @staticmethod
    def _build_entity_status(hass: Any, entry_id: str, dev_name: str) -> dict | None:
        """Build a minimal status from HA entities for a configured device without an app.

        Registry and state access is Home Assistant event-loop work; this must
        not go to the executor.
        """
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or not any(
            device.get("name") == dev_name for device in entry.data.get("devices", [])
        ):
            return None
        nw = read_network_entities(hass, dev_name)
        return {
            "connected": False,
            "connection_state": "disabled",
            "current_page": "",
            "device_info": {
                "name": dev_name,
                "tft_version": "",
                "tft_required_version": "",
                "yaml_version": "",
                "ip": nw["ip"],
                "ssid": nw["ssid"],
                "rssi": nw["rssi"],
                "temperature_entity_id": resolve_temperature_entity_id(hass, dev_name),
                "last_panel_update": None,
                "last_connection": None,
            },
        }


class NotificationsView(HomeAssistantView):
    """REST API for reading and dismissing queued device notifications."""

    url = "/api/nspanel_haui/notifications/{entry_id}"
    name = "api:nspanel_haui:notifications"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return queued notifications for one device or the whole hub entry."""
        apps = get_apps(request.app["hass"], entry_id) or {}
        device_name = query_device(request)
        if device_name:
            app = apps.get(device_name)
            if app is None:
                return self.json([], status_code=200)
            return self.json(await self._read_app_notifications(app))

        notifications = []
        for app in apps.values():
            notifications.extend(await self._read_app_notifications(app))
        return self.json(notifications)

    @require_admin
    async def delete(self, request, entry_id: str):
        """Dismiss one queued notification by device name and queue identifier."""
        device_name = query_device(request)
        notification_id = (request.query.get("id") or "").strip()
        if not device_name or not notification_id:
            return error(self, "device and id are required", 400)

        apps = get_apps(request.app["hass"], entry_id) or {}
        app = apps.get(device_name)
        if app is None:
            return error(self, "device not found", 404)

        def remove_notification() -> bool:
            controller = app.controller.get("notification")
            if controller is None:
                return False
            for notification in controller.get_notifications():
                if notification.notif_id == notification_id:
                    return controller.remove_notification(notification)
            return False

        removed = await app.async_run_on_worker(remove_notification)
        if not removed:
            return error(self, "notification not found", 404)
        return self.json({"status": "ok"})

    @staticmethod
    async def _read_app_notifications(app) -> list[dict[str, Any]]:
        """Read a device's queue on its worker thread and serialize public fields."""

        def read_notifications() -> list[dict[str, Any]]:
            controller = app.controller.get("notification")
            if controller is None:
                return []
            return [
                {
                    "id": notification.notif_id,
                    "device": app.device.get_name(),
                    "title": str(notification.title),
                    "message": str(notification.message),
                    "icon": notification.icon,
                    "notif_type": notification.notif_type,
                    "persistent": notification.persistent,
                }
                for notification in controller.get_notifications()
            ]

        return await app.async_run_on_worker(read_notifications)


class DeviceRefreshDisplayView(HomeAssistantView):
    """REST API endpoint to trigger display refresh on one or all devices."""

    url = "/api/nspanel_haui/refresh_display/{entry_id}"
    name = "api:nspanel_haui:refresh_display"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request, entry_id: str):
        """Refresh the display for the specified device (or all devices).

        JSON body may carry an optional ``device`` field (device name, or ``*``
        for all devices).  When omitted defaults to ``*``.
        """
        device_name = body_device(await json_object(request))
        apps = running_apps(request.app["hass"], entry_id)

        if device_name != ALL_DEVICES:
            app = device_app(apps, device_name)
            await app.async_run_on_worker(app.refresh_display)
            return self.json({"status": "ok", "devices_updated": [device_name]})

        async def refresh(_name: str, app: Any) -> None:
            await app.async_run_on_worker(app.refresh_display)

        updated, _failed = await for_each_app(apps, "refresh the display", refresh)
        return self.json({"status": "ok", "devices_updated": updated})

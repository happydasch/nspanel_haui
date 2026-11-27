"""Live device state: status, notification queue and display refresh."""

from __future__ import annotations

from typing import Any

from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..hub.esphome_helpers import (
    read_network_entities,
    resolve_brightness_entity_ids,
    resolve_temperature_entity_id,
)
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
    """Return the live status of the devices of one entry."""

    url = "/api/nspanel_haui/status/{entry_id}"
    name = "api:nspanel_haui:status"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return one device's status, or every device's by name.

        Query param ``device`` restricts the response to a single device.
        Without it every device of the entry is included: a running device is
        asked for its status, a disabled or not yet started one is read from
        its Home Assistant entities.
        """
        hass = request.app["hass"]
        apps = get_apps(hass, entry_id) or {}
        device_name = query_device(request)

        if device_name:
            app = apps.get(device_name)
            if app is not None:
                return self.json(await self._build_running_status(hass, app, device_name))
            if device_name not in self._device_names(hass, entry_id):
                return self.json(
                    {"error": f"device {device_name!r} not found"},
                    status_code=404,
                )
            return self.json(self._build_entity_status(hass, device_name))

        devices: dict[str, dict[str, Any]] = {}
        for name in self._device_names(hass, entry_id):
            app = apps.get(name)
            devices[name] = (
                await self._build_running_status(hass, app, name)
                if app is not None
                else self._build_entity_status(hass, name)
            )

        from ..hub.rollout import rollout_snapshot

        return self.json({"devices": devices, "rollout": rollout_snapshot(hass, entry_id)})

    @staticmethod
    def _device_names(hass: Any, entry_id: str) -> list[str]:
        """Return the names of the devices the entry lists."""
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return []
        return [dev["name"] for dev in entry.data.get("devices", []) if dev.get("name")]

    @staticmethod
    async def _build_running_status(hass: Any, app: Any, device_name: str) -> dict[str, Any]:
        """Combine HA-loop entity readings with an app-worker status snapshot."""
        # HA's registries and entity states are event-loop-owned; take only the
        # app's mutable runtime snapshot on its worker.
        network_info = read_network_entities(hass, device_name)
        status = await app.async_run_on_worker(app.get_device_status)
        status["device_info"].update(network_info)
        status["device_info"]["temperature_entity_id"] = resolve_temperature_entity_id(
            hass, device_name
        )
        status["device_info"].update(resolve_brightness_entity_ids(hass, device_name))
        return status

    @staticmethod
    def _build_entity_status(hass: Any, device_name: str) -> dict[str, Any]:
        """Build a minimal status from HA entities for a device without an app.

        Registry and state access is Home Assistant event-loop work; this must
        not go to the executor.
        """
        network = read_network_entities(hass, device_name)
        return {
            "connected": False,
            "connection_state": "disabled",
            "current_page": "",
            "current_panel": "",
            "device_info": {
                "name": device_name,
                "tft_version": "",
                "tft_required_version": "",
                "display_baud": None,
                "yaml_version": "",
                "ip": network["ip"],
                "ssid": network["ssid"],
                "rssi": network["rssi"],
                "temperature_entity_id": resolve_temperature_entity_id(hass, device_name),
                **resolve_brightness_entity_ids(hass, device_name),
                "last_panel_update": None,
                "last_connection": None,
            },
        }


class NotificationsView(HomeAssistantView):
    """Read and dismiss the queued notifications of the devices."""

    url = "/api/nspanel_haui/notifications/{entry_id}"
    name = "api:nspanel_haui:notifications"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the queued notifications of one device, or of every device."""
        apps = get_apps(request.app["hass"], entry_id) or {}
        device_name = query_device(request)
        if device_name:
            app = apps.get(device_name)
            if app is None:
                return self.json([])
            return self.json(await self._read_app_notifications(app))

        notifications = []
        for app in apps.values():
            notifications.extend(await self._read_app_notifications(app))
        return self.json(notifications)

    @require_admin
    async def delete(self, request: web.Request, entry_id: str) -> web.Response:
        """Dismiss one queued notification, named by ``device`` and ``id``."""
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
    async def _read_app_notifications(app: Any) -> list[dict[str, Any]]:
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
                    "icon_color": notification.icon_color,
                    "sound": notification.sound,
                    "persistent": notification.persistent,
                    "force_show": notification.force_show,
                    "text_size": notification.text_size,
                    "timeout": notification.timeout,
                }
                for notification in controller.get_notifications()
            ]

        return await app.async_run_on_worker(read_notifications)


class DeviceRefreshDisplayView(HomeAssistantView):
    """Refresh the display of one or of every device."""

    url = "/api/nspanel_haui/refresh_display/{entry_id}"
    name = "api:nspanel_haui:refresh_display"
    requires_auth = True

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Refresh the display of the device the body names, ``*`` for every device.

        The body's ``device`` field is optional and defaults to ``*``.
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

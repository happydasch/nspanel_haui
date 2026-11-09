"""WebSocket commands for the editor's virtual panel (sandbox preview and cards).

Every device has at most one virtual app (``virtual_panel.VirtualPanelHost``),
started on first use and stopped after ``IDLE_STOP_SECONDS`` without a viewer
or a card render. Sandbox previews and panel cards share it. The live preview
has commands of its own (``preview/live_panel.py``).

- ``nspanel_haui/virtual_panel/subscribe`` attaches a sandbox preview to the
  device's app and streams its display output to the editor until the
  subscription is closed. The first message is ``{"type": "started", ...}``;
  the others are the messages of ``virtual_panel.VirtualESPHomeProxy`` and the
  hardware buttons' lights. From then on the app mirrors the device's
  notification queue.
- ``nspanel_haui/virtual_panel/event`` injects a touch, swipe or hardware
  button.
- ``nspanel_haui/virtual_panel/home`` leaves the idle page and opens the home
  panel, for a preview switching back from Live.
- ``nspanel_haui/virtual_panel/idle`` acts as if the inactivity timeout opened
  the idle page.
- ``nspanel_haui/virtual_panel/reset_sandbox`` drops simulated entity states.
- ``nspanel_haui/virtual_panel/render`` renders one panel as its editor card
  shows it, without touching what a live preview shows.

Admin only, like the editor itself.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

HOSTS_KEY = f"{DOMAIN}_virtual_hosts"
# A device's virtual app keeps a worker thread and state listeners; stop it
# once nothing has used it for this long.
IDLE_STOP_SECONDS = 600


class _Hosts:
    """The virtual apps of every hub: one per device, started on first use."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass
        self._tasks: dict[tuple[str, str], asyncio.Task] = {}
        self._idle: dict[tuple[str, str], asyncio.TimerHandle] = {}
        # live preview viewer id -> (host key, host, owning connection)
        self.viewers: dict[str, tuple[tuple[str, str], Any, Any]] = {}

    async def async_get(self, entry: Any, device: str) -> Any:
        key = (entry.entry_id, device)
        task = self._tasks.get(key)
        if task is None:
            task = self._hass.loop.create_task(_create_host(self._hass, entry, device))
            self._tasks[key] = task
        try:
            host = await asyncio.shield(task)
        except Exception:
            if self._tasks.get(key) is task:
                self._tasks.pop(key)
            raise
        self.touch(key)
        return host

    def touch(self, key: tuple[str, str]) -> None:
        """Restart the idle countdown of a host."""
        handle = self._idle.pop(key, None)
        if handle is not None:
            handle.cancel()
        self._idle[key] = self._hass.loop.call_later(IDLE_STOP_SECONDS, self._idle_check, key)

    def _idle_check(self, key: tuple[str, str]) -> None:
        self._idle.pop(key, None)
        task = self._tasks.get(key)
        if task is None or not task.done() or task.exception() is not None:
            return
        if task.result().viewer_count:
            self.touch(key)
            return
        # Forgotten before the stop runs: a use in between starts a new host
        # instead of attaching to this one.
        self._hass.async_create_task(self._forget(key).async_stop())

    def running(self, entry_id: str) -> list[tuple[str, Any]]:
        """(device, host) of every started host of a hub."""
        return [
            (device, task.result())
            for (owner, device), task in self._tasks.items()
            if owner == entry_id and task.done() and task.exception() is None
        ]

    def _forget(self, key: tuple[str, str]) -> Any | None:
        """Drop a host at once, so the next use starts a new one; returns it if started."""
        handle = self._idle.pop(key, None)
        if handle is not None:
            handle.cancel()
        task = self._tasks.pop(key, None)
        self.viewers = {vid: v for vid, v in self.viewers.items() if v[0] != key}
        if task is None or not task.done() or task.exception() is not None:
            return None
        return task.result()

    async def async_stop(self, key: tuple[str, str]) -> None:
        host = self._forget(key)
        if host is not None:
            await host.async_stop()


def _hosts(hass: Any) -> _Hosts:
    hosts = hass.data.get(HOSTS_KEY)
    if hosts is None:
        hosts = hass.data[HOSTS_KEY] = _Hosts(hass)
    return hosts


async def _create_host(hass: Any, entry: Any, device: str) -> Any:
    from .. import _build_config_dict
    from ..hub.esphome_helpers import resolve_ha_device_id
    from ..hub.storage import empty_store, panel_store
    from .preview.virtual_panel import VirtualPanelHost

    store = await panel_store(hass, entry.entry_id).async_load() or empty_store()
    cfg = _build_config_dict(entry.data, store, device_name=device)
    ha_device_id = resolve_ha_device_id(hass, device)
    running = (hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}).get(device)
    device_info = (
        await running.async_run_on_worker(lambda: dict(running.device.device_info))
        if running is not None
        else {}
    )
    host = VirtualPanelHost(
        hass,
        device,
        cfg,
        ha_device_id=ha_device_id,
        device_info=device_info,
    )
    await host.async_start()
    return host


async def async_reload_hosts(hass: Any, entry_id: str, data: dict) -> None:
    """Apply a saved store to the hub's virtual apps, as a save does on the devices."""
    from .. import _build_config_dict

    hosts = hass.data.get(HOSTS_KEY)
    entry = hass.config_entries.async_get_entry(entry_id)
    if hosts is None or entry is None:
        return
    devices = {d.get("name") for d in entry.data.get("devices", [])}
    for device, host in hosts.running(entry_id):
        if device not in devices:
            await hosts.async_stop((entry_id, device))
            continue
        await host.async_reload(_build_config_dict(entry.data, data, device_name=device))


async def async_stop_hosts(hass: Any, entry_id: str) -> None:
    """Stop the hub's virtual apps (entry unload)."""
    hosts = hass.data.get(HOSTS_KEY)
    if hosts is None:
        return
    for device, _host in hosts.running(entry_id):
        await hosts.async_stop((entry_id, device))


def _device_entry(hass: Any, connection: Any, msg: dict[str, Any]) -> Any | None:
    """The hub entry when ``msg`` names one of its devices, else an error is sent."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    devices = [d.get("name") for d in entry.data.get("devices", [])] if entry else []
    if msg["device"] not in devices:
        connection.send_error(msg["id"], "not_found", "Unknown hub or device")
        return None
    return entry


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/subscribe",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    from ..haui.device_config import is_portrait_model

    entry = _device_entry(hass, connection, msg)
    if entry is None:
        return
    msg_id = msg["id"]
    hosts = _hosts(hass)
    key = (entry.entry_id, msg["device"])
    viewer_id = uuid.uuid4().hex

    def _send(message: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg_id, message))

    def sink(message: dict[str, Any]) -> None:
        hass.loop.call_soon_threadsafe(_send, message)

    closed = False

    def _unsubscribe() -> None:
        nonlocal closed
        closed = True
        viewer = hosts.viewers.pop(viewer_id, None)
        if viewer is not None:
            viewer[1].detach(viewer_id)
            hosts.touch(key)

    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    try:
        host = await hosts.async_get(entry, msg["device"])
    except Exception:
        _LOGGER.exception("Virtual panel for '%s' failed to start", msg["device"])
        _send({"type": "error", "message": "start_failed"})
        return
    running = (hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}).get(msg["device"])
    if running is not None:
        await host.async_follow_device(running)
        await host.async_follow_notifications(running)
    # Closed while the app started: attaching now would keep a viewer nobody sees.
    if closed:
        return
    _send(
        {
            "type": "started",
            "session_id": viewer_id,
            "portrait": is_portrait_model(host.app.device.get("display_model")),
        }
    )
    hosts.viewers[viewer_id] = (key, host, connection)
    host.attach(viewer_id, sink)


def _get_host(hass: Any, connection: Any, msg: dict[str, Any]) -> Any | None:
    viewer = _hosts(hass).viewers.get(msg["session_id"])
    if viewer is None or viewer[2] is not connection:
        connection.send_error(msg["id"], "not_found", "Unknown live preview session")
        return None
    return viewer[1]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/event",
        vol.Required("session_id"): str,
        vol.Required("name"): str,
        vol.Optional("value", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_event(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    host = _get_host(hass, connection, msg)
    if host is None:
        return
    try:
        host.send_event(msg["name"], msg["value"])
    except ValueError as exc:
        connection.send_error(msg["id"], "invalid_event", str(exc))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/home",
        vol.Required("session_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_home(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    host = _get_host(hass, connection, msg)
    if host is None:
        return
    host.show_home()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/idle",
        vol.Required("session_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_idle(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    host = _get_host(hass, connection, msg)
    if host is None:
        return
    host.show_idle()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/reset_sandbox",
        vol.Required("session_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_reset_sandbox(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    host = _get_host(hass, connection, msg)
    if host is None:
        return
    host.reset_sandbox()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/render",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
        # A panel config as the editor holds it (unsaved edits included), or
        # the key of the device's configured panel (system panels).
        vol.Exclusive("panel", "target"): dict,
        vol.Exclusive("key", "target"): str,
        vol.Optional("kwargs"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_render(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    entry = _device_entry(hass, connection, msg)
    if entry is None:
        return
    if ("panel" in msg) == ("key" in msg):
        connection.send_error(msg["id"], "invalid_format", "Pass either a panel or a key")
        return
    host = await _hosts(hass).async_get(entry, msg["device"])
    running = (hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}).get(msg["device"])
    if running is not None:
        await host.async_follow_device(running)
    try:
        panel = msg["panel"] if "panel" in msg else await host.async_configured_panel(msg["key"])
        result = await host.async_render(panel, msg.get("kwargs"))
    except ValueError as exc:
        connection.send_error(msg["id"], "invalid_panel", str(exc))
        return
    connection.send_result(msg["id"], result)


def async_register_websocket_commands(hass: Any) -> None:
    """Register the virtual panel's WebSocket commands."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_event)
    websocket_api.async_register_command(hass, ws_home)
    websocket_api.async_register_command(hass, ws_idle)
    websocket_api.async_register_command(hass, ws_reset_sandbox)
    websocket_api.async_register_command(hass, ws_render)

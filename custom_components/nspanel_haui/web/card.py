"""WebSocket commands of the dashboard card (``frontend/card/``).

The card shows one device's screen on a Home Assistant dashboard to every
signed-in user, so these commands are not admin-only. They only read:

- ``nspanel_haui/card/devices`` lists the devices a card can show: those
  with a running hub app, in the hub's device order, with their orientation.
- ``nspanel_haui/card/home/subscribe`` streams the device's home panel
  (``preview/home_stream.py``), run on its virtual app with real states.
- ``nspanel_haui/card/live/subscribe`` streams what the real panel shows, as
  the editor's live preview gets it (``preview/live_panel.LivePanel``). The
  viewer is not one of the live preview's sessions, so no input command finds
  it: those stay admin-only, like the editor and every other command.

A subscription the hub ends (the hub entry unloads, the device is removed)
gets ``{"type": "ended"}`` as its last message; the card subscribes again.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN
from .preview.live_panel import LivePanel
from .websocket import _device_entry, _hosts

_LOGGER = logging.getLogger(__name__)

LIVE_VIEWERS_KEY = f"{DOMAIN}_card_live_viewers"


def _running_app(hass: Any, entry_id: str, device: str) -> Any | None:
    return (hass.data.get(DOMAIN, {}).get(entry_id) or {}).get(device)


def _live_viewers(hass: Any) -> dict[str, tuple[str, Callable[[], None]]]:
    """Viewer id -> (hub entry id, end); a card's live viewers, apart from the editor's."""
    return hass.data.setdefault(LIVE_VIEWERS_KEY, {})


@websocket_api.websocket_command({vol.Required("type"): "nspanel_haui/card/devices"})
@websocket_api.async_response
async def ws_devices(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    devices = []
    for entry_id, apps in hass.data.get(DOMAIN, {}).items():
        for name, app in apps.items():
            portrait = await app.async_run_on_worker(lambda app=app: app.device.is_portrait)
            devices.append({"entry_id": entry_id, "name": name, "portrait": portrait})
    connection.send_result(msg["id"], devices)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/card/home/subscribe",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
    }
)
@websocket_api.async_response
async def ws_home_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    entry = _device_entry(hass, connection, msg)
    if entry is None:
        return
    running = _running_app(hass, entry.entry_id, msg["device"])
    if running is None:
        connection.send_error(msg["id"], "not_found", "The device's hub app is not running")
        return
    msg_id = msg["id"]
    hosts = _hosts(hass)
    key = (entry.entry_id, msg["device"])
    viewer_id = uuid.uuid4().hex
    host: Any | None = None
    closed = False

    def sink(message: dict[str, Any]) -> None:
        hass.loop.call_soon_threadsafe(
            connection.send_message, websocket_api.event_message(msg_id, message)
        )

    def _unsubscribe() -> None:
        nonlocal closed
        closed = True
        if host is not None:
            host.home.detach(viewer_id)
            hosts.touch(key)

    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    try:
        started = await hosts.async_get(entry, msg["device"])
        await started.async_follow_device(running)
        # The header's notification indicator follows the panel's queue.
        await started.async_follow_notifications(running)
    except Exception:
        _LOGGER.exception("Home panel card of '%s' failed to start", msg["device"])
        sink({"type": "error", "message": "start_failed"})
        return
    # Closed while the app started: attaching now would keep a viewer nobody sees.
    if closed:
        return
    host = started
    host.home.attach(viewer_id, sink)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/card/live/subscribe",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
    }
)
@websocket_api.async_response
async def ws_live_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    running = _running_app(hass, msg["entry_id"], msg["device"])
    if running is None:
        connection.send_error(msg["id"], "not_found", "The device's hub app is not running")
        return
    msg_id = msg["id"]
    viewer_id = uuid.uuid4().hex
    viewers = _live_viewers(hass)

    def sink(message: dict[str, Any]) -> None:
        hass.loop.call_soon_threadsafe(
            connection.send_message, websocket_api.event_message(msg_id, message)
        )

    viewer = LivePanel(hass, running, sink)

    def _end() -> None:
        if viewers.pop(viewer_id, None) is not None:
            viewer.stop()
            sink({"type": "ended"})

    def _unsubscribe() -> None:
        if viewers.pop(viewer_id, None) is not None:
            viewer.stop()

    # Registered before it starts: an unsubscribe during the start stops it.
    viewers[viewer_id] = (msg["entry_id"], _end)
    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    try:
        await viewer.async_start(viewer_id)
    except Exception:
        _LOGGER.exception("Live card of '%s' failed to start", msg["device"])
        sink({"type": "error", "message": "start_failed"})


async def async_end_live_viewers(hass: Any, entry_id: str) -> None:
    """End the entry's live card viewers before its apps stop; the cards subscribe again."""
    for owner, end in list(_live_viewers(hass).values()):
        if owner == entry_id:
            end()


def async_register_commands(hass: Any) -> None:
    """Register the dashboard card's WebSocket commands."""
    websocket_api.async_register_command(hass, ws_devices)
    websocket_api.async_register_command(hass, ws_home_subscribe)
    websocket_api.async_register_command(hass, ws_live_subscribe)

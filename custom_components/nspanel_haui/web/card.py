"""WebSocket commands of the dashboard card (``frontend/card/``).

The card shows a hub's panels on a Home Assistant dashboard to every signed-in
user, so these commands are not admin-only. They only read:

- ``nspanel_haui/card/devices`` lists the hub's devices a card can name, in
  the hub's device order, with their Home Assistant ``device_id`` and whether
  they run. A disabled device stays in the list: its card keeps drawing the
  hub's render of its panels, and says its setting instead of a state.
- ``nspanel_haui/card/home/subscribe`` streams the device's home panel
  (``preview/home_stream.py``), run on its virtual app with real states, the
  panel's own state and its hardware button lights. A disabled device has no
  running app, so its stream reports no state - the render comes from its
  stored settings, which is all a card needs for the screen.
- ``nspanel_haui/card/live/subscribe`` streams what the real panel shows, as
  the editor's live preview gets it (``preview/live_panel.LivePanel``). It
  needs the running app: a disabled device has no live screen. The viewer is
  not one of the live preview's sessions, so no input command finds it: those
  stay admin-only, like the editor and every other command.

A subscription names its device either by ``device_id`` (the Home Assistant
device of the panel, which the card editor stores and a rename does not
change) or by the hub ``entry_id`` and the hub device's ``device`` name.

A subscription the hub ends (the hub entry unloads, the device is removed)
gets ``{"type": "ended"}`` as its last message; the card subscribes again.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

import probatio as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN
from ..haui.device_config import find_store_device
from ..hub.esphome_helpers import resolve_ha_device_id
from .preview.live_panel import LivePanel
from .websocket import _device_entry, _hosts

_LOGGER = logging.getLogger(__name__)

LIVE_VIEWERS_KEY = f"{DOMAIN}_card_live_viewers"


def _running_app(hass: Any, entry_id: str, device: str) -> Any | None:
    return (hass.data.get(DOMAIN, {}).get(entry_id) or {}).get(device)


async def _device_enabled(hass: Any, entry: Any, name: str) -> bool:
    """Whether the hub runs ``name``: its store setting, which defaults to on."""
    from ..hub import storage

    store = await storage.panel_store(hass, entry.entry_id).async_load() or {}
    record = find_store_device(store.get("devices", {}), name) or {}
    return bool((record.get("config") or {}).get("enabled", True))


async def _running_or_error(
    hass: Any, connection: Any, msg: dict[str, Any], entry: Any, device: str
) -> Any | None:
    """The device's running app, or the error saying why a live card cannot mirror it.

    A live card shows what the panel itself shows, so it needs the device's
    app. A disabled device is told apart from one whose app is still starting:
    the card says which, and subscribes again either way.
    """
    running = _running_app(hass, entry.entry_id, device)
    if running is not None:
        return running
    if not await _device_enabled(hass, entry, device):
        connection.send_error(msg["id"], "disabled", "The device is disabled in NSPanel HAUI")
    else:
        connection.send_error(msg["id"], "not_found", "The device's hub app is not running")
    return None


async def _home_target(
    hass: Any, connection: Any, msg: dict[str, Any]
) -> tuple[Any, str, Any | None] | None:
    """The hub entry, the device name and its running app, if the card can draw it.

    A disabled device has no running app, but the hub still renders its panels
    from its stored settings, so its card keeps its screen; only the panel's
    own state is missing. An enabled device whose app is still starting is
    told apart, and the card subscribes again.
    """
    target = _card_device(hass, connection, msg)
    if target is None:
        return None
    entry, device = target
    running = _running_app(hass, entry.entry_id, device)
    if running is None and await _device_enabled(hass, entry, device):
        connection.send_error(msg["id"], "not_found", "The device's hub app is not running")
        return None
    return entry, device, running


def _live_viewers(hass: Any) -> dict[str, tuple[str, Callable[[], None]]]:
    """Viewer id -> (hub entry id, end); a card's live viewers, apart from the editor's."""
    return hass.data.setdefault(LIVE_VIEWERS_KEY, {})


def _card_device(hass: Any, connection: Any, msg: dict[str, Any]) -> tuple[Any, str] | None:
    """The hub entry and device name ``msg`` names, else an error is sent.

    ``device_id`` wins: it is the Home Assistant device of the panel, so a
    device renamed in the editor keeps every dashboard working.
    """
    device_id = msg.get("device_id")
    if device_id:
        for entry_id in hass.data.get(DOMAIN, {}):
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None:
                continue
            for record in entry.data.get("devices", []):
                name = record.get("name")
                if name and resolve_ha_device_id(hass, name) == device_id:
                    return entry, name
        connection.send_error(msg["id"], "not_found", "Unknown device")
        return None
    if not msg.get("entry_id") or not msg.get("device"):
        connection.send_error(msg["id"], "invalid_format", "Pass device_id, or entry_id and device")
        return None
    entry = _device_entry(hass, connection, msg)
    if entry is None:
        return None
    return entry, msg["device"]


def _target_fields() -> dict[Any, Any]:
    """The schema fields naming a card's device (see ``_card_device``)."""
    return {
        vol.Optional("device_id"): str,
        vol.Optional("entry_id"): str,
        vol.Optional("device"): str,
    }


@websocket_api.websocket_command({vol.Required("type"): "nspanel_haui/card/devices"})
@websocket_api.async_response
async def ws_devices(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    devices = []
    for entry_id in hass.data.get(DOMAIN, {}):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            continue
        for record in entry.data.get("devices", []):
            name = record.get("name")
            if not name:
                continue
            devices.append(
                {
                    "entry_id": entry_id,
                    "name": name,
                    "device_id": resolve_ha_device_id(hass, name),
                    "enabled": await _device_enabled(hass, entry, name),
                }
            )
    connection.send_result(msg["id"], devices)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/card/home/subscribe",
        **_target_fields(),
    }
)
@websocket_api.async_response
async def ws_home_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    target = await _home_target(hass, connection, msg)
    if target is None:
        return
    entry, device, running = target
    msg_id = msg["id"]
    hosts = _hosts(hass)
    key = (entry.entry_id, device)
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
        started = await hosts.async_get(entry, device)
        if running is not None:
            await started.async_follow_device(running)
            # The panel's state, its queue and the frame's button lights.
            await started.async_follow_panel(running)
    except Exception:
        _LOGGER.exception("Home panel card of '%s' failed to start", device)
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
        **_target_fields(),
    }
)
@websocket_api.async_response
async def ws_live_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    target = _card_device(hass, connection, msg)
    if target is None:
        return
    entry, device = target
    running = await _running_or_error(hass, connection, msg, entry, device)
    if running is None:
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
    viewers[viewer_id] = (entry.entry_id, _end)
    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    try:
        await viewer.async_start(viewer_id)
    except Exception:
        _LOGGER.exception("Live card of '%s' failed to start", device)
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

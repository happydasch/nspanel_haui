"""WebSocket commands for the editor's virtual panel (live preview).

- ``nspanel_haui/virtual_panel/subscribe`` starts a virtual panel for one
  device and streams its display output to the editor until the subscription
  is closed. The first message is ``{"type": "started", ...}``; the others are
  the messages of ``virtual_panel.VirtualESPHomeProxy`` and the sandbox.
- ``nspanel_haui/virtual_panel/event`` injects a touch, swipe, hardware button
  or idle timeout.
- ``nspanel_haui/virtual_panel/configure`` switches between sandbox and live
  mode.

Admin only, like the editor itself: live mode controls real entities.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SESSIONS_KEY = f"{DOMAIN}_virtual_sessions"
# Each session is a full app with its own worker thread and listeners.
MAX_SESSIONS = 4


def _sessions(hass: Any) -> dict[str, Any]:
    return hass.data.setdefault(SESSIONS_KEY, {})


async def _protected_entities(hass: Any, ha_device_id: str | None) -> frozenset[str]:
    """Entity ids of the real device's settings; a preview never changes them.

    The relay switches are left out: in live mode the preview's hardware
    buttons switch the real relays, as the panel's buttons do.
    """
    if ha_device_id is None:
        return frozenset()
    from homeassistant.helpers import entity_registry as er

    from .virtual_panel import RELAY_ENTITY_NAMES

    registry = er.async_get(hass)
    entries = er.async_entries_for_device(registry, ha_device_id, include_disabled_entities=True)
    relays = set(RELAY_ENTITY_NAMES.values())
    return frozenset(
        entry.entity_id
        for entry in entries
        if getattr(entry, "original_name", None) not in relays
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/subscribe",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
        vol.Optional("live", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    from . import _build_config_dict
    from .esphome_helpers import resolve_ha_device_id
    from .haui.device_config import is_portrait_model
    from .storage import empty_store, panel_store
    from .virtual_panel import VirtualPanelSession

    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    device = msg["device"]
    if entry is None or device not in [d.get("name") for d in entry.data.get("devices", [])]:
        connection.send_error(msg["id"], "not_found", "Unknown hub or device")
        return
    sessions = _sessions(hass)
    if len(sessions) >= MAX_SESSIONS:
        connection.send_error(msg["id"], "too_many_sessions", "Close another live preview first")
        return

    store = await panel_store(hass, entry.entry_id).async_load() or empty_store()
    cfg = _build_config_dict(entry.data, store, device_name=device)
    ha_device_id = resolve_ha_device_id(hass, device)
    running = (hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}).get(device)
    device_info = dict(running.device.device_info) if running is not None else {}

    msg_id = msg["id"]

    def _send(message: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg_id, message))

    def sink(message: dict[str, Any]) -> None:
        hass.loop.call_soon_threadsafe(_send, message)

    session = VirtualPanelSession(
        hass,
        device,
        cfg,
        sink,
        ha_device_id=ha_device_id,
        device_info=device_info,
        protected_entities=await _protected_entities(hass, ha_device_id),
        live=msg["live"],
    )
    sessions[session.id] = session

    def _unsubscribe() -> None:
        if sessions.pop(session.id, None) is not None:
            hass.async_create_task(session.async_stop())

    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    _send(
        {
            "type": "started",
            "session_id": session.id,
            "portrait": is_portrait_model(cfg["device"].get("display_model")),
            "live": msg["live"],
        }
    )
    try:
        await session.async_start()
    except Exception:
        _LOGGER.exception("Virtual panel for '%s' failed to start", device)
        _unsubscribe()
        _send({"type": "error", "message": "start_failed"})


def _get_session(hass: Any, connection: Any, msg: dict[str, Any]) -> Any | None:
    session = _sessions(hass).get(msg["session_id"])
    if session is None:
        connection.send_error(msg["id"], "not_found", "Unknown live preview session")
    return session


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
    session = _get_session(hass, connection, msg)
    if session is None:
        return
    try:
        session.send_event(msg["name"], msg["value"])
    except ValueError as exc:
        connection.send_error(msg["id"], "invalid_event", str(exc))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/virtual_panel/configure",
        vol.Required("session_id"): str,
        vol.Required("live"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_configure(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    session = _get_session(hass, connection, msg)
    if session is None:
        return
    session.set_live(msg["live"])
    connection.send_result(msg["id"])


def async_register_websocket_commands(hass: Any) -> None:
    """Register the virtual panel's WebSocket commands."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_event)
    websocket_api.async_register_command(hass, ws_configure)

"""Live preview: the editor's view of a running panel, driven by the device's own app.

A live viewer mirrors the hub app of a device (``NSPanelHAUI``): it streams
the display commands that app sends to the panel and hands the editor's
touches, swipes, hardware buttons and idle requests to that app once they
are checked. Nothing is simulated and no second page runs: the app makes its
normal Home Assistant service calls, so a live viewer acts on real entities.
The sandbox preview (``virtual_panel.py``) shares nothing with it.

- ``nspanel_haui/live_panel/subscribe`` attaches a viewer to the device's
  app and streams its display output and status until the subscription is
  closed. The first message is ``{"type": "started", ...}``. Attaching
  replays what the current page was sent since it loaded (its
  ``load_commands``, then the ESPHome controller's ``page_commands``), so the
  viewer gets every widget without the panel drawing anything again.
- ``nspanel_haui/live_panel/event`` passes a touch, swipe or hardware button.
- ``nspanel_haui/live_panel/action`` opens the idle page or resets the
  inactivity timer.

A save (``api.config.push_panels``) reaches the viewers through
``async_reload_viewers``: the button settings decide which entity each
button light shows.

Admin only, like the editor itself: a live viewer controls real entities.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ...const import DOMAIN
from ...haui.abstract.haui_event import HAUIEvent
from ...haui.mapping.const import GESTURES, ESPEvent
from .button_lights import (
    RELAY_ENTITY_NAMES,
    ButtonLight,
    button_entity_ids,
    light_state,
    lights_message,
)

_LOGGER = logging.getLogger(__name__)

VIEWERS_KEY = f"{DOMAIN}_live_viewers"

# Sink for messages to the browser; must be safe to call from any thread.
Sink = Callable[[dict[str, Any]], None]

# What a person can do to a real panel.
_EVENTS = frozenset(
    {
        ESPEvent.COMPONENT,
        ESPEvent.TOUCH_START,
        ESPEvent.TOUCH_END,
        ESPEvent.GESTURE,
        ESPEvent.BUTTON_LEFT,
        ESPEvent.BUTTON_RIGHT,
    }
)
_COMPONENT_EVENT = re.compile(r"(\d+),(\d+),([01])\Z")
_TOUCH_END_EVENT = re.compile(r"(\d+),(\d+),(\d+),(\d+)\Z")
_ACTIONS = ("idle", "reset_interaction_timer")


class LivePanel:
    """One live viewer of a device's app."""

    def __init__(self, hass: Any, source: Any, sink: Sink) -> None:
        self._hass = hass
        self._source = source
        self._sink = sink
        self._unsubscribes: list[Callable[[], None]] = []
        self._untrack_lights: Callable[[], None] | None = None
        self._light_entities: dict[ButtonLight, str] = {}
        self._lights: dict[ButtonLight, str] = {}
        self._stopped = False

    async def async_start(self, session_id: str) -> None:
        """Seed the viewer with the panel's screen and follow it from then on."""
        unsubscribes, light_entities = await self._source.async_run_on_worker(
            self._attach, session_id
        )
        self._unsubscribes.extend(unsubscribes)
        if self._stopped:
            self.stop()
            return
        self._track_lights(light_entities)

    def stop(self) -> None:
        """Stop following the app; runs on the event loop."""
        self._stopped = True
        for unsubscribe in self._unsubscribes:
            unsubscribe()
        self._unsubscribes.clear()
        if self._untrack_lights is not None:
            self._untrack_lights()
            self._untrack_lights = None

    async def async_reload_lights(self) -> None:
        """Follow a save: the button settings decide what each light shows."""
        entity_ids = await self._source.async_run_on_worker(button_entity_ids, self._source.device)
        if not self._stopped:
            self._track_lights(entity_ids)

    async def async_event(self, name: str, value: str) -> None:
        """Check a browser interaction and apply it on the app's worker.

        Raises:
            ValueError: If the panel is disconnected or a person could not cause it.
        """
        await self._source.async_run_on_worker(_dispatch_event, self._source, name, value)

    async def async_slider(self, page_id: int, component_id: int, value: int) -> None:
        """Apply a browser slider value to the current page's registered control."""
        await self._source.async_run_on_worker(
            _dispatch_slider, self._source, page_id, component_id, value
        )

    async def async_action(self, action: str) -> None:
        """Open the idle page or reset the inactivity timer on the panel.

        Raises:
            ValueError: If the panel is disconnected or the action is unknown.
        """
        await self._source.async_run_on_worker(_dispatch_action, self._source, action)

    # app worker

    def _attach(
        self, session_id: str
    ) -> tuple[list[Callable[[], None]], dict[ButtonLight, str | None]]:
        """Subscribe and seed in one go, so no display output slips in between.

        Seeding replays the page; a page the app has prepared but not drawn
        yet (waiting for the display's page event) gets its commands through
        the subscription.
        """
        source = self._source
        self._sink(
            {"type": "started", "session_id": session_id, "portrait": source.device.is_portrait}
        )
        unsubscribes = [
            source.subscribe_preview_state(self._on_state),
            source.subscribe_preview_output(self._on_output),
        ]
        self._on_state(source.get_preview_state())
        page = source.controller["navigation"].page
        if page is not None:
            # The page as the panel shows it: what it read while loading, then
            # what it was sent since. Nothing goes to the panel.
            self._sink({"type": "commands", "commands": page.load_commands})
            self._sink({"type": "page", "page": page.page_id})
            commands = source.controller["esphome"].page_commands()
            if commands:
                self._sink({"type": "commands", "commands": commands})
        return unsubscribes, button_entity_ids(source.device)

    def _on_state(self, state: dict[str, Any]) -> None:
        self._sink(
            {
                "type": "physical",
                "idle": state["idle"],
                "display_state": state["display_state"],
                "connected": state["connected"],
            }
        )
        if state.get("event") == ESPEvent.PAGE and state.get("page") is not None:
            self._sink({"type": "page", "page": int(state["page"])})

    def _on_output(self, command: str, value: Any) -> None:
        if command == "send_command":
            self._sink({"type": "commands", "commands": [value]})
        elif command == "send_commands":
            self._sink({"type": "commands", "commands": list(value)})
        elif command == "goto_page":
            self._sink({"type": "page", "page": int(value)})

    # event loop

    def _track_lights(self, entity_ids: dict[ButtonLight, str | None]) -> None:
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_state_change_event

        if self._untrack_lights is not None:
            self._untrack_lights()
            self._untrack_lights = None
        self._light_entities = {key: eid for key, eid in entity_ids.items() if eid}
        self._lights = {key: self._light(eid) for key, eid in self._light_entities.items()}
        self._sink(lights_message(self._lights))
        if not self._light_entities:
            return

        @callback
        def _changed(event: Any) -> None:
            entity_id = event.data["entity_id"]
            for key, eid in self._light_entities.items():
                if eid == entity_id:
                    self._lights[key] = self._light(eid)
            self._sink(lights_message(self._lights))

        self._untrack_lights = async_track_state_change_event(
            self._hass, sorted(set(self._light_entities.values())), _changed
        )

    def _light(self, entity_id: str) -> str:
        state = self._hass.states.get(entity_id)
        if state is None:
            return light_state(None, None, entity_id)
        return light_state(state.state, dict(state.attributes), entity_id)


def _require_connected(source: Any) -> None:
    connection = source.controller.get("connection")
    if connection is None or not connection.is_connected:
        raise ValueError("The physical device is disconnected")


def _dispatch_event(source: Any, name: str, value: str) -> None:
    """Check one browser interaction and apply it; runs on the app's worker."""
    _require_connected(source)
    if name not in _EVENTS:
        raise ValueError(f"Event not allowed in live mode: {name}")

    device = source.device
    if name == ESPEvent.COMPONENT:
        match = _COMPONENT_EVENT.fullmatch(value)
        page = source.controller["navigation"].page
        if not match or page is None:
            raise ValueError("Invalid component event")
        page_id, component_id, _button_state = map(int, match.groups())
        if page_id != page.page_id or not any(
            component.id == component_id for component in page.COMPONENTS.values()
        ):
            raise ValueError("Component is not on the physical panel's current page")
    elif name == ESPEvent.TOUCH_START:
        if value not in ("", "1"):
            raise ValueError("Invalid touch-start event")
        if value == "":
            device.reset_interaction_timer()
    elif name == ESPEvent.TOUCH_END:
        match = _TOUCH_END_EVENT.fullmatch(value)
        if not match:
            raise ValueError("Invalid touch-end event")
        x1, y1, x2, y2 = map(int, match.groups())
        width, height = (320, 480) if device.is_portrait else (480, 320)
        if any(x < 1 or y < 1 or x >= width or y >= height for x, y in ((x1, y1), (x2, y2))):
            raise ValueError("Touch coordinates are outside the physical display")
    elif name == ESPEvent.GESTURE:
        if value not in GESTURES:
            raise ValueError("Invalid gesture")
    else:
        if value not in ("0", "1"):
            raise ValueError("Invalid hardware-button event")
        if value == "1":
            device.reset_interaction_timer()
            side = "left" if name == ESPEvent.BUTTON_LEFT else "right"
            # The firmware switches the relay itself when the real button is
            # pressed in relay mode; a button pressed in the editor has to.
            if device.get(f"use_relay_{side}", True):
                relay = device.find_esphome_entity_id("switch", RELAY_ENTITY_NAMES[side])
                if relay:
                    source.call_service("switch.toggle", target={"entity_id": relay})

    source.callback_event(HAUIEvent(name, value))


def _dispatch_slider(source: Any, page_id: int, component_id: int, value: int) -> None:
    """Validate and apply one live-preview slider value on the app worker."""
    _require_connected(source)
    page = source.controller["navigation"].page
    if page is None or page.page_id != page_id:
        raise ValueError("Slider is not on the physical panel's current page")
    page.dispatch_slider_value(component_id, value)


def _dispatch_action(source: Any, action: str) -> None:
    """Apply a live action; runs on the app's worker."""
    _require_connected(source)
    if action == "reset_interaction_timer":
        source.device.reset_interaction_timer()
    elif action == "idle":
        source.controller["navigation"].open_idle_panel(True)
    else:
        raise ValueError(f"Live action not allowed: {action}")


# WebSocket commands


def _viewers(hass: Any) -> dict[str, tuple[LivePanel, Any, str, int]]:
    """Session id -> (viewer, owning connection, hub entry id, subscription id)."""
    return hass.data.setdefault(VIEWERS_KEY, {})


async def async_stop_viewers(hass: Any, entry_id: str) -> None:
    """Stop and unregister the entry's live viewers before its apps stop."""
    viewers = _viewers(hass)
    for session_id, (viewer, connection, owner, msg_id) in list(viewers.items()):
        if owner != entry_id:
            continue
        viewers.pop(session_id, None)
        connection.subscriptions.pop(msg_id, None)
        viewer.stop()


async def async_reload_viewers(hass: Any, entry_id: str) -> None:
    """Apply a save to the hub's live viewers, once the devices' apps took it."""
    for viewer, _connection, owner, _msg_id in list(_viewers(hass).values()):
        if owner != entry_id:
            continue
        try:
            await viewer.async_reload_lights()
        except Exception:
            # A viewer of an app that stopped (entry reload) until its dialog closes.
            _LOGGER.exception("Live preview could not follow the save")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/live_panel/subscribe",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_subscribe(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    running = (hass.data.get(DOMAIN, {}).get(msg["entry_id"]) or {}).get(msg["device"])
    if running is None:
        connection.send_error(msg["id"], "not_found", "The device's hub app is not running")
        return
    msg_id = msg["id"]
    session_id = uuid.uuid4().hex
    viewers = _viewers(hass)

    def sink(message: dict[str, Any]) -> None:
        hass.loop.call_soon_threadsafe(
            connection.send_message, websocket_api.event_message(msg_id, message)
        )

    viewer = LivePanel(hass, running, sink)
    # Registered before it starts: an unsubscribe during the start stops it.
    viewers[session_id] = (viewer, connection, msg["entry_id"], msg_id)

    def _unsubscribe() -> None:
        if viewers.pop(session_id, None) is not None:
            viewer.stop()

    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    try:
        await viewer.async_start(session_id)
    except Exception:
        _LOGGER.exception("Live preview of '%s' failed to start", msg["device"])
        sink({"type": "error", "message": "start_failed"})


def _viewer(hass: Any, connection: Any, msg: dict[str, Any]) -> LivePanel | None:
    entry = _viewers(hass).get(msg["session_id"])
    if entry is None or entry[1] is not connection:
        connection.send_error(msg["id"], "not_found", "Unknown live preview session")
        return None
    return entry[0]


async def _answer(connection: Any, msg: dict[str, Any], call: Awaitable[None], what: str) -> None:
    """Send the result of a live interaction; a failure names its cause in the log."""
    try:
        await call
    except ValueError as exc:
        connection.send_error(msg["id"], f"invalid_{what}", str(exc))
        return
    except Exception:
        _LOGGER.exception("Live %s failed: %s", what, msg)
        connection.send_error(
            msg["id"],
            f"live_{what}_failed",
            f"The live {what} failed; check the Home Assistant log for details.",
        )
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/live_panel/event",
        vol.Required("session_id"): str,
        vol.Required("name"): vol.All(str, vol.Length(max=64)),
        vol.Optional("value", default=""): vol.All(str, vol.Length(max=64)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_event(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    viewer = _viewer(hass, connection, msg)
    if viewer is not None:
        await _answer(connection, msg, viewer.async_event(msg["name"], msg["value"]), "event")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/live_panel/slider",
        vol.Required("session_id"): str,
        vol.Required("page_id"): int,
        vol.Required("component_id"): int,
        vol.Required("value"): vol.All(int, vol.Range(min=0, max=100)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_slider(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    viewer = _viewer(hass, connection, msg)
    if viewer is not None:
        await _answer(
            connection,
            msg,
            viewer.async_slider(msg["page_id"], msg["component_id"], msg["value"]),
            "slider",
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nspanel_haui/live_panel/action",
        vol.Required("session_id"): str,
        vol.Required("action"): vol.In(_ACTIONS),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_action(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    viewer = _viewer(hass, connection, msg)
    if viewer is not None:
        await _answer(connection, msg, viewer.async_action(msg["action"]), "action")


def async_register_commands(hass: Any) -> None:
    """Register the live preview's WebSocket commands."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_event)
    websocket_api.async_register_command(hass, ws_slider)
    websocket_api.async_register_command(hass, ws_action)

"""HA adapter layer.

Bridges Home Assistant's async API to the synchronous interface used by haui/ core components.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

from .haui.mapping.const import ESPAction, NotificationAction

_LOGGER = logging.getLogger(__name__)


class ItemProxy:
    """Wraps a HA state entry to provide a simple synchronous entity interface."""

    def __init__(
        self,
        hass: Any,
        loop: asyncio.AbstractEventLoop,
        entity_id: str,
        proxy: Any = None,
    ) -> None:
        self._hass = hass
        self._loop = loop
        self.entity_id = entity_id
        self._proxy = proxy
        self._handles: dict[str, Callable] = {}

    @property
    def state(self) -> Any:
        s = self._hass.states.get(self.entity_id)
        return s.state if s else None

    @property
    def attributes(self) -> dict[str, Any]:
        s = self._hass.states.get(self.entity_id)
        return dict(s.attributes) if s else {}

    def get_state(self) -> Any:
        return self.state

    def call_service(self, service: str, **kwargs: Any) -> None:
        domain = self.entity_id.split(".")[0]

        async def _call() -> None:
            await self._hass.services.async_call(
                domain,
                service,
                service_data=kwargs or {},
                target={"entity_id": self.entity_id},
                blocking=False,
            )

        asyncio.run_coroutine_threadsafe(_call(), self._loop)

    def turn_on(self, **kwargs: Any) -> None:
        self.call_service("turn_on", **kwargs)

    def turn_off(self, **kwargs: Any) -> None:
        self.call_service("turn_off", **kwargs)

    def set_state(self, state: Any = None, **kwargs: Any) -> None:
        if state is None:
            return
        domain = self.entity_id.split(".")[0]
        if domain == "number":
            self.call_service("set_value", value=state)
        else:
            self._loop.call_soon_threadsafe(self._hass.states.async_set, self.entity_id, str(state))

    def listen_state(self, cb: Callable, attribute: str | None = None, **kwargs: Any) -> str:
        if self._proxy is not None:
            return self._proxy.listen_state(cb, self.entity_id, attribute=attribute, **kwargs)
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        @ha_callback
        def _ha_cb(event: Any) -> None:
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if attribute and attribute not in ("state", None):
                old = old_state.attributes.get(attribute) if old_state else None
                new = new_state.attributes.get(attribute) if new_state else None
            else:
                old = old_state.state if old_state else None
                new = new_state.state if new_state else None
            self._hass.async_create_task(
                self._hass.async_add_executor_job(
                    cb, self.entity_id, attribute or "state", old, new, {}
                )
            )

        async def _register() -> None:
            from homeassistant.helpers.event import async_track_state_change_event  # noqa: PLC0415

            remove = async_track_state_change_event(self._hass, self.entity_id, _ha_cb)
            self._handles[handle_id] = remove

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id


class ESPHomeProxy:
    """Bridge to ESPHome native API for device communication.

    All ESPHome device actions are exposed as HA services:
      esphome.<device_name>_<action_name>

    Device events come through the HA event bus with esphome.* event types.
    """

    def __init__(
        self,
        hass: Any,
        loop: asyncio.AbstractEventLoop,
        device_name: str = "",
        device_id: str | None = None,
    ) -> None:
        self._hass = hass
        self._loop = loop
        self._device_name = device_name
        self._device_id: str | None = device_id
        self._event_listeners: list[Callable] = []

    def listen_event(
        self,
        cb: Callable,
        event_type: str,
        topic: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Listen for ESPHome device events on the HA event bus.

        All device events use the static event type ``esphome.nspanel_event``.
        The dynamic event name (e.g. ``esphome.touch_end``) is carried in
        ``data.name``.  The ``topic`` parameter is repurposed as a device name
        filter.
        """

        def _event_cb(event: Any) -> None:
            data = event.data or {}

            # Filter by HA device_id so each app only receives events for its device
            if self._device_id and data.get("device_id") != self._device_id:
                return

            # Pass to sync callback on executor thread
            wrapped_data = {
                "name": data.get("name", ""),
                "value": data.get("value", ""),
            }
            self._hass.async_add_executor_job(cb, event.event_type, wrapped_data, {})

        async def _subscribe() -> None:
            from homeassistant.core import callback as ha_callback  # noqa: PLC0415

            remove = self._hass.bus.async_listen(event_type, ha_callback(_event_cb))
            self._event_listeners.append(remove)

        asyncio.run_coroutine_threadsafe(_subscribe(), self._loop).result(timeout=10)

    def cancel_listen_events(self) -> None:
        """Cancel all event bus listeners registered via listen_event."""
        for remove in self._event_listeners:
            self._loop.call_soon_threadsafe(remove)
        self._event_listeners.clear()

    # Actions that take no parameters
    _PARAMETERLESS_ACTIONS: set[str] = {
        "hub_heartbeat",
        "hub_connection_initialized",
        "hub_connection_closed",
        "req_device_info",
        "req_device_state",
        "upload_tft",
        "haui_discover",
    }

    # Actions where value should be treated as a dict passed directly
    _NOTIFICATION_ACTIONS = set(member.value for member in NotificationAction)

    def _build_service_data(self, name: str, value: Any) -> dict[str, Any]:
        """Build ESPHome service data from action name and value."""
        if isinstance(value, dict):
            return dict(value)

        if name in self._PARAMETERLESS_ACTIONS:
            return {}

        service_data: dict[str, Any] = {}

        if name == ESPAction.SEND_COMMAND:
            service_data["cmd"] = value
        elif name == ESPAction.SEND_COMMANDS:
            service_data["commands"] = self._normalize_commands(value)
        elif name == ESPAction.GOTO_PAGE:
            service_data["page"] = value
        elif name == ESPAction.SET_BRIGHTNESS:
            service_data["intensity"] = int(value) if value else 0
        elif name in ("req_val", "req_txt"):
            service_data["name"] = value
        elif name == ESPAction.UPLOAD_TFT_URL:
            service_data["url"] = value
        elif name == ESPAction.PLAY_RTTTL:
            service_data["song_str"] = value
        elif name == ESPAction.PLAY_SOUND:
            service_data["name"] = value
        elif name == ESPAction.RESET_LAST_INTERACTION:
            service_data["offset"] = int(value) if value else 0
        elif name in self._NOTIFICATION_ACTIONS:
            if isinstance(value, str):
                service_data["title"] = value
            else:
                service_data.update(value)
        else:
            service_data["value"] = value

        return service_data

    @staticmethod
    def _normalize_commands(value: Any) -> list:
        """Normalize commands payload into a list of command strings."""
        if isinstance(value, str):
            try:
                cmds = json.loads(value)
            except json.JSONDecodeError:
                return [value]
        else:
            cmds = value
        if isinstance(cmds, dict):
            cmds = cmds.get("commands", [])
        if not isinstance(cmds, list):
            return [cmds]
        return cmds

    def publish(self, topic: str, payload: Any) -> None:
        """Publish to ESPHome device via native API service call.

        In the native API model:
        - 'topic' becomes the ESPHome service suffix (action name)
        - 'payload' is JSON decoded to get 'name' and 'value'
        - We call esphome.<device>_<name> with the value as parameter
        """

        async def _call_service() -> None:
            try:
                try:
                    data = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    data = {"name": topic, "value": payload}

                name = data.get("name", topic)
                value = data.get("value", "")
                service_data = self._build_service_data(name, value)
                devices = self._get_target_devices()

                for device_name in devices:
                    service_name = f"{device_name}_{name}"

                    # INFO level so service calls are visible in normal logs
                    _LOGGER.info(
                        "→ ESPHome: esphome.%s %s",
                        service_name,
                        service_data if service_data else "(no args)",
                    )

                    try:
                        await self._hass.services.async_call(
                            "esphome", service_name, service_data, blocking=False
                        )
                    except Exception as e:
                        msg = str(e)
                        if "not ready" in msg or "ConnectionState" in msg:
                            _LOGGER.debug(
                                "ESPHome service %s deferred (device %s not ready): %s",
                                service_name,
                                device_name,
                                msg,
                            )
                        else:
                            _LOGGER.warning(
                                "Failed to call ESPHome service %s for device %s: %s",
                                service_name,
                                device_name,
                                msg,
                            )
            except Exception as exc:
                _LOGGER.error("publish(%s) coroutine failed: %s", topic, exc)

        # Non-blocking: schedule the service call without waiting.
        # All ESPHome actions are fire-and-forget; blocking here would
        # tie up executor threads and cause heartbeat timeouts on the device.
        try:
            asyncio.run_coroutine_threadsafe(_call_service(), self._loop)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("publish() failed: %s", exc)

    def _get_target_devices(self) -> list[str]:
        """Get list of target device service prefixes for ESPHome calls.

        ESPHome services are named ``<node_name>_<action>`` where *node_name*
        is the ESPHome YAML node name (lowercase, with hyphens and spaces
        replaced by underscores), not the HA display title.  We try to read
        the stored node name from the config entry data, and fall back to
        sanitizing the display title.
        """

        def _sanitize(name: str) -> str:
            return name.lower().replace(" ", "_").replace("-", "_")

        devices: list[str] = []
        for entry in self._hass.config_entries.async_entries("esphome"):
            # Prefer the real ESPHome node name from the config entry
            device_name = entry.data.get("device_name", "")
            if device_name:
                devices.append(_sanitize(device_name))
            elif hasattr(entry, "title") and entry.title:
                devices.append(_sanitize(entry.title))
        # Filter to only the configured device name if one was supplied
        if self._device_name:
            normalized = _sanitize(self._device_name)
            devices = [d for d in devices if d == normalized]
        # If no matching entries found, log an error and return empty list.
        # Previously we fell back to ALL ESPHome entries, but that would
        # cross-route commands across devices in a multi-device setup.
        if not devices:
            if self._device_name:
                _LOGGER.error(
                    "No ESPHome device matched configured '%s'; no targets available",
                    self._device_name,
                )
        return devices


class HAAdapter:
    """Adapter that bridges HA's async API to the synchronous interface expected by haui/ core.

    NSPanelHAUI inherits from this to provide the full API surface to all haui sub-components
    via self.app. All HA calls are bridged from synchronous executor threads back to the
    asyncio event loop via asyncio.run_coroutine_threadsafe.
    """

    def __init__(self, hass: Any, name: str) -> None:
        self.hass = hass
        self.name = name
        self._loop: asyncio.AbstractEventLoop = hass.loop
        self._state_handles: dict[str, Callable] = {}
        self._timer_handles: dict[str, Callable] = {}
        self._timer_meta: dict[str, dict] = {}  # handle_id -> {callback_name, type, interval}
        self._status_logs: list[str] = []  # last 100 lines for status view
        self._plugin_proxies: dict[str, Any] = {}  # plugin_name -> proxy instance

    # logging

    def log(self, msg: str, **kwargs: Any) -> None:
        level_name = kwargs.get("level", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        exc_info = kwargs.get("exc_info")
        _LOGGER.log(level, msg, exc_info=exc_info)
        # Capture last 100 log lines for the status view
        import time as _time
        ts = _time.strftime("%H:%M:%S")
        self._status_logs.append(f"[{ts}] {level_name[:4]} {msg}")
        if len(self._status_logs) > 100:
            self._status_logs = self._status_logs[-100:]


    def get_status_logs(self) -> list[str]:
        """Return a copy of the captured status log lines."""
        return list(self._status_logs)
    def stop(self) -> None:
        """Centralized cleanup: cancel all remaining listeners and timers.

        Called during config entry reload/unload as a belt-and-suspenders
        measure after individual controllers have had their stop_part()
        called.  Logs a warning for any handles still present, which
        indicates a controller is missing cleanup in its stop_part.
        """
        # Cancel any remaining state listeners
        if self._state_handles:
            self.log(
                f"Cleaning up {len(self._state_handles)} orphaned state listener(s)",
                level="DEBUG",
            )
            for remove in list(self._state_handles.values()):
                self._loop.call_soon_threadsafe(remove)
            self._state_handles.clear()

        # Cancel any remaining timers
        if self._timer_handles:
            self.log(
                f"Cleaning up {len(self._timer_handles)} orphaned timer(s)",
                level="DEBUG",
            )
            for remove in list(self._timer_handles.values()):
                self._loop.call_soon_threadsafe(remove)
            self._timer_handles.clear()
            self._timer_meta.clear()

        # Cancel ESPHome event bus listeners on any cached proxies
        for _plugin_name, proxy in list(self._plugin_proxies.items()):
            if hasattr(proxy, "cancel_listen_events"):
                proxy.cancel_listen_events()
        self._plugin_proxies.clear()

    # entities

    def item_exists(self, entity_id: str) -> bool:
        return self.hass.states.get(entity_id) is not None

    def get_item(self, entity_id: str) -> ItemProxy:
        return ItemProxy(self.hass, self._loop, entity_id, proxy=self)

    # services

    def call_service(self, service: str, **kwargs: Any) -> Any:
        if not isinstance(service, str) or "." not in service.replace("/", "."):
            raise ValueError(f"Invalid service: {service!r}")
        domain, svc = service.replace("/", ".").split(".", 1)
        target = kwargs.pop("target", None)
        if "service_data" in kwargs:
            service_data = kwargs.pop("service_data")
        else:
            service_data = kwargs

        async def _call() -> Any:
            try:
                response = await self.hass.services.async_call(
                    domain,
                    svc,
                    service_data=service_data or {},
                    target=target,
                    blocking=True,
                    return_response=True,
                )
                if response:
                    return {"result": {"response": response}}
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("call_service %s/%s error: %s", domain, svc, exc)
            return None

        try:
            return asyncio.run_coroutine_threadsafe(_call(), self._loop).result(timeout=30)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("call_service %s/%s timed out or failed: %s", domain, svc, exc)
            return None

    # templates

    def render_template(self, template_str: str) -> str:
        from homeassistant.helpers.template import Template  # noqa: PLC0415

        tmpl = Template(template_str, self.hass)

        async def _render() -> str:
            try:
                return str(tmpl.async_render())
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("render_template error: %s", exc)
                return template_str

        try:
            return asyncio.run_coroutine_threadsafe(_render(), self._loop).result(timeout=10)
        except Exception:  # noqa: BLE001
            return template_str

    # state listeners

    def listen_state(
        self,
        cb: Callable,
        entity_id: str,
        attribute: str | None = None,
        **kwargs: Any,
    ) -> str:
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        @ha_callback
        def _ha_cb(event: Any) -> None:
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if attribute and attribute not in ("state", None):
                old = old_state.attributes.get(attribute) if old_state else None
                new = new_state.attributes.get(attribute) if new_state else None
            else:
                old = old_state.state if old_state else None
                new = new_state.state if new_state else None
            self.hass.async_add_executor_job(cb, entity_id, attribute or "state", old, new, {})

        async def _register() -> None:
            from homeassistant.helpers.event import async_track_state_change_event  # noqa: PLC0415

            remove = async_track_state_change_event(self.hass, entity_id, _ha_cb)
            self._state_handles[handle_id] = remove

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id

    def cancel_listen_state(self, handle: str) -> None:
        remove = self._state_handles.pop(handle, None)
        if remove:
            self._loop.call_soon_threadsafe(remove)

    # timers

    def run_every(
        self,
        cb: Callable,
        start: Any,
        interval: int | float,
        **kwargs: Any,
    ) -> str:
        import re
        from datetime import timedelta  # noqa: PLC0415

        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        self._timer_meta[handle_id] = {
            "callback_name": getattr(cb, "__name__", str(cb)),
            "type": "interval",
            "interval": interval,
        }

        @ha_callback
        def _ha_cb(now: Any) -> None:
            async def _task() -> None:
                await self.hass.async_add_executor_job(cb, {})

            self.hass.async_create_task(_task())

        # Parse "now+N" pattern - if matched, fire the first callback after
        # N seconds via async_call_later, then switch to recurring
        # async_track_time_interval.  All other start values (None,
        # timedelta, datetime, utcnow) use the existing
        # async_track_time_interval path for backward compatibility.
        _now_plus: int | None = None
        if isinstance(start, str):
            m = re.match(r"^now\+(\d+)$", start)
            if m:
                _now_plus = int(m.group(1))

        async def _register() -> None:
            from homeassistant.helpers.event import (  # noqa: PLC0415
                async_call_later,
                async_track_time_interval,
            )

            if _now_plus is not None:

                @ha_callback
                def _first_cb(now: Any) -> None:
                    _ha_cb(now)
                    remove = async_track_time_interval(
                        self.hass, _ha_cb, timedelta(seconds=interval)
                    )
                    self._timer_handles[handle_id] = remove

                remove = async_call_later(self.hass, _now_plus, _first_cb)
            else:
                remove = async_track_time_interval(self.hass, _ha_cb, timedelta(seconds=interval))

            self._timer_handles[handle_id] = remove

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id

    def run_in(self, cb: Callable, delay: int | float, **kwargs: Any) -> str:
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        self._timer_meta[handle_id] = {
            "callback_name": getattr(cb, "__name__", str(cb)),
            "type": "one_shot",
            "interval": delay,
        }

        @ha_callback
        def _ha_cb(now: Any) -> None:
            self._timer_handles.pop(handle_id, None)

            async def _task() -> None:
                await self.hass.async_add_executor_job(cb, {})

            self.hass.async_create_task(_task())

        async def _register() -> None:
            from homeassistant.helpers.event import async_call_later  # noqa: PLC0415

            remove = async_call_later(self.hass, delay, _ha_cb)
            self._timer_handles[handle_id] = remove

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id

    def cancel_timer(self, handle: str) -> None:
        remove = self._timer_handles.pop(handle, None)
        self._timer_meta.pop(handle, None)
        if remove:
            self._loop.call_soon_threadsafe(remove)

    def run_minutely(self, cb: Callable, start: Any = None, **kwargs: Any) -> str:
        return self.run_every(cb, start, 60, **kwargs)

    def run_hourly(self, cb: Callable, start: Any = None, **kwargs: Any) -> str:
        return self.run_every(cb, start, 3600, **kwargs)
    def run_daily(self, cb: Callable, start: Any = None, **kwargs: Any) -> str:
        return self.run_every(cb, start, 86400, **kwargs)

    # ESPHome

    def get_plugin_api(
        self, plugin_name: str, device_name: str = "", device_id: str | None = None
    ) -> Any:
        if plugin_name == "ESPHome":
            proxy = ESPHomeProxy(
                self.hass, self._loop, device_name=device_name, device_id=device_id
            )
            self._plugin_proxies[plugin_name] = proxy
            return proxy
        raise ValueError(f"Unsupported plugin: {plugin_name}")

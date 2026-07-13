"""HA adapter layer.

Bridges Home Assistant's async API to the synchronous interface used by haui/ core components.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

from .haui.mapping.const import ESPAction, NotificationAction

_LOGGER = logging.getLogger(__name__)


# HA target keys required for entity service calls.
_TARGET_KEYS = frozenset({"entity_id", "device_id", "area_id", "floor_id", "label_id"})


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
            try:
                await self._hass.services.async_call(
                    domain,
                    service,
                    service_data=kwargs or {},
                    target={"entity_id": self.entity_id},
                    blocking=True,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "ItemProxy.call_service %s.%s for %s failed: %s",
                    domain,
                    service,
                    self.entity_id,
                    exc,
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
    """Bridge to ESPHome native API for direct device communication.

    Sends commands to the ESPHome device via the native API client
    (``entry_data.client.execute_service()``) instead of routing through
    ``hass.services.async_call("esphome", ...)``, eliminating the HA service
    bus indirection.

    Device events are still received via the HA event bus (the ESPHome
    firmware publishes them through ``homeassistant.event``).
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

    def _get_runtime_entry_data(self) -> Any | None:
        """Find the ESPHome config entry for this device and return its RuntimeEntryData.

        Returns ``None`` when the ESPHome config entry has not been found or
        ``entry.runtime_data`` has not been populated yet.
        """
        from .esphome_helpers import normalize_device_name

        if not self._device_name:
            return None
        normalized = normalize_device_name(self._device_name)
        for entry in self._hass.config_entries.async_entries("esphome"):
            dev_name = entry.data.get("device_name", "")
            if dev_name and normalize_device_name(dev_name) == normalized:
                try:
                    return entry.runtime_data
                except AttributeError:
                    return None
        return None

    @staticmethod
    def _find_service(services: dict[int, Any], name: str) -> Any | None:
        """Find a UserService by name in the ESPHome services dict (keyed by int key).

        Returns the service object, or ``None`` if not found (device has not
        yet shared its service definitions).
        """
        for service in services.values():
            if hasattr(service, "name") and service.name == name:
                return service
        return None

    def _build_service_data(self, name: str, value: Any) -> dict[str, Any]:
        """Build ESPHome service data from action name and value.

        The output format matches the variable names declared in the
        ``api.yaml`` action definition.
        """
        if isinstance(value, dict):
            # Dict values are passed directly as top-level service data.
            # This allows callers like hub_connection_response({"version": "..."})
            # to work without adding every ServerResponse to the explicit branches.
            return dict(value)

        if name in self._PARAMETERLESS_ACTIONS:
            return {}

        service_data: dict[str, Any] = {}

        if name == ESPAction.SEND_COMMAND:
            service_data["cmd"] = value
        elif name == ESPAction.SEND_COMMANDS:
            service_data["commands"] = value if isinstance(value, list) else [value]
        elif name == ESPAction.GOTO_PAGE:
            service_data["page"] = value
        elif name == ESPAction.SET_BRIGHTNESS:
            service_data["intensity"] = int(value) if value else 0
        elif name in ("req_val", "req_txt"):
            if isinstance(value, dict):
                service_data["name"] = value.get("name", "")
                service_data["source_type"] = value.get("source_type", "component")
            else:
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

    def publish(self, name: str, value: str | dict | list = "") -> None:
        """Execute a service on the ESPHome device via its native API client.

        Looks up the device's ``RuntimeEntryData`` (populated by the ESPHome
        integration), finds the matching ``UserService`` by name, and calls
        ``APIClient.execute_service()`` directly — bypassing the HA service
        bus entirely.

        Args:
            name: Service/action name (e.g. ``"send_command"``, ``"set_brightness"``).
            value: Parameter value matching the action's declared variable
                type.  ``str`` for single-value actions, ``list`` for
                ``send_commands``, ``dict`` for ``hub_connection_response``.
        """

        async def _call_service() -> None:
            try:
                service_data = self._build_service_data(name, value)

                entry_data = self._get_runtime_entry_data()
                if entry_data is None:
                    _LOGGER.warning(
                        "ESPHome publish('%s'): no ESPHome entry found for device '%s'"
                        " — command will be lost",
                        name,
                        self._device_name,
                    )
                    return

                if not entry_data.available or entry_data.client is None:
                    _LOGGER.warning(
                        "ESPHome publish('%s'): device '%s' not available — command deferred",
                        name,
                        self._device_name,
                    )
                    return

                service = self._find_service(entry_data.services, name)
                if service is None:
                    _LOGGER.warning(
                        "ESPHome publish('%s'): service not found on device '%s'"
                        " — device may not have shared its definitions yet",
                        name,
                        self._device_name,
                    )
                    return

                _LOGGER.info(
                    "→ ESPHome native: %s %s",
                    name,
                    service_data if service_data else "(no args)",
                )

                await entry_data.client.execute_service(service, service_data)

            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "ESPHome publish('%s') failed: %s",
                    name,
                    exc,
                )

        # Block until the service call completes so that multiple chunks
        # from a single send_cmds batch are delivered to the ESP32
        # sequentially, not concurrently.  Fire-and-forget scheduling caused
        # all chunks to pile up in the Nextion's command queue at once,
        # overflowing max_queue_size and losing commands.
        future = asyncio.run_coroutine_threadsafe(_call_service(), self._loop)
        try:
            future.result(timeout=10)
        except TimeoutError:
            _LOGGER.warning("ESPHome publish('%s') timed out after 10s", name)
        except Exception as exc:  # noqa: BLE001
            # Exception already logged inside _call_service; swallow the
            # propagated copy so the executor thread is not disrupted.
            _LOGGER.debug("publish('%s') future raised: %s", name, exc)


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

    def get_entity_state(self, entity_id: str) -> str | None:
        """Read the current state of a HA entity by entity_id.

        Returns the state string (e.g. "-67") or None if the entity doesn't exist.
        Thread-safe — ``hass.states.get`` is safe to call from executor threads.
        """
        s = self.hass.states.get(entity_id)
        return s.state if s else None

    def get_item(self, entity_id: str) -> ItemProxy:
        return ItemProxy(self.hass, self._loop, entity_id, proxy=self)

    # services

    def call_service(self, service: str, return_response: bool = False, **kwargs: Any) -> Any:
        if not isinstance(service, str) or "." not in service.replace("/", "."):
            raise ValueError(f"Invalid service: {service!r}")
        domain, svc = service.replace("/", ".").split(".", 1)
        target = kwargs.pop("target", None)
        if "service_data" in kwargs:
            service_data = kwargs.pop("service_data")
        else:
            service_data = kwargs

        # If target wasn't provided but service_data contains HA targeting keys,
        # promote them so HA's async_call validation passes.
        if target is None and isinstance(service_data, dict):
            target_keys = _TARGET_KEYS & set(service_data)
            if target_keys:
                target = {k: service_data.pop(k) for k in target_keys}

        # If service_data contains a nested "target" dict (e.g.
        # {"target": {"entity_id": "..."}}), promote it to the top-level
        # target parameter.
        if target is None and isinstance(service_data, dict):
            nested_target = service_data.get("target")
            if isinstance(nested_target, dict) and _TARGET_KEYS & set(nested_target):
                target = nested_target
                del service_data["target"]

        # If there's still no target or entity targeting keys in service_data,
        # the call can't succeed on entity-registered services — HA validates
        # that one must be present.
        has_targeting = isinstance(service_data, dict) and bool(_TARGET_KEYS & set(service_data))
        if (not target) and not has_targeting:
            _LOGGER.warning(
                "call_service %s/%s skipped: no target entity specified; "
                "provide entity_id, device_id, area_id, floor_id, or label_id",
                domain,
                svc,
            )
            return None

        async def _call() -> Any:
            try:
                response = await self.hass.services.async_call(
                    domain,
                    svc,
                    service_data=service_data or {},
                    target=target,
                    blocking=True,
                    return_response=return_response,
                )
                if return_response and response:
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

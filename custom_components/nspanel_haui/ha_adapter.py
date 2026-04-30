"""HA adapter layer — bridges Home Assistant's async API to the synchronous interface used by haui/ core components."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


class EntityProxy:
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
            self._loop.call_soon_threadsafe(
                self._hass.states.async_set, self.entity_id, str(state)
            )

    def listen_state(
        self, cb: Callable, attribute: str | None = None, **kwargs: Any
    ) -> str:
        if self._proxy is not None:
            return self._proxy.listen_state(cb, self.entity_id, attribute=attribute, **kwargs)
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        @ha_callback
        def _ha_cb(event: Any) -> None:
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            old = old_state.state if old_state else None
            new = new_state.state if new_state else None
            self._hass.async_create_task(
                self._hass.async_add_executor_job(
                    cb, self.entity_id, attribute or "state", old, new, {}
                )
            )

        async def _register() -> None:
            from homeassistant.helpers.event import async_track_state_change_event  # noqa: PLC0415

            async_track_state_change_event(self._hass, self.entity_id, _ha_cb)

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id


class MQTTProxy:
    """Translates haui MQTT calls to the HA MQTT component."""

    def __init__(self, hass: Any, loop: asyncio.AbstractEventLoop) -> None:
        self._hass = hass
        self._loop = loop

    def mqtt_subscribe(self, topic: str) -> None:
        pass

    def listen_event(
        self,
        cb: Callable,
        event_type: str,
        topic: str | None = None,
        **kwargs: Any,
    ) -> None:
        if event_type != "MQTT_MESSAGE" or not topic:
            return

        def _msg_cb(message: Any) -> None:
            data = {"topic": message.topic, "payload": message.payload}
            self._hass.async_add_executor_job(cb, "MQTT_MESSAGE", data, {})

        async def _subscribe() -> None:
            from homeassistant.components import mqtt  # noqa: PLC0415
            from homeassistant.core import callback as ha_callback  # noqa: PLC0415

            await mqtt.async_subscribe(self._hass, topic, ha_callback(_msg_cb))

        asyncio.run_coroutine_threadsafe(_subscribe(), self._loop).result(timeout=10)

    def mqtt_publish(self, topic: str, payload: Any, retain: bool = False) -> None:
        async def _publish() -> None:
            from homeassistant.components import mqtt  # noqa: PLC0415

            await mqtt.async_publish(self._hass, topic, payload, retain=retain)

        asyncio.run_coroutine_threadsafe(_publish(), self._loop)


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

    # logging

    def log(self, msg: str, **kwargs: Any) -> None:
        level_name = kwargs.get("level", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        _LOGGER.log(level, msg)

    # entities

    def entity_exists(self, entity_id: str) -> bool:
        return self.hass.states.get(entity_id) is not None

    def get_entity(self, entity_id: str) -> EntityProxy:
        return EntityProxy(self.hass, self._loop, entity_id, proxy=self)

    # services

    def call_service(self, service: str, **kwargs: Any) -> Any:
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
                _LOGGER.debug("call_service %s/%s error: %s", domain, svc, exc)
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
            self.hass.async_add_executor_job(
                cb, entity_id, attribute or "state", old, new, {}
            )

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
        from datetime import timedelta  # noqa: PLC0415
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

        @ha_callback
        def _ha_cb(now: Any) -> None:
            async def _task() -> None:
                await self.hass.async_add_executor_job(cb, {})
            self.hass.async_create_task(_task())

        async def _register() -> None:
            from homeassistant.helpers.event import async_track_time_interval  # noqa: PLC0415

            remove = async_track_time_interval(self.hass, _ha_cb, timedelta(seconds=interval))
            self._timer_handles[handle_id] = remove

        asyncio.run_coroutine_threadsafe(_register(), self._loop).result(timeout=10)
        return handle_id

    def run_in(self, cb: Callable, delay: int | float, **kwargs: Any) -> str:
        from homeassistant.core import callback as ha_callback  # noqa: PLC0415

        handle_id = str(uuid.uuid4())

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
        if remove:
            self._loop.call_soon_threadsafe(remove)

    def run_minutely(self, cb: Callable, start: Any = None, **kwargs: Any) -> str:
        return self.run_every(cb, start, 60, **kwargs)

    def run_hourly(self, cb: Callable, start: Any = None, **kwargs: Any) -> str:
        return self.run_every(cb, start, 3600, **kwargs)

    # MQTT

    def get_plugin_api(self, plugin_name: str) -> Any:
        if plugin_name == "MQTT":
            return MQTTProxy(self.hass, self._loop)
        raise ValueError(f"Unsupported plugin: {plugin_name}")

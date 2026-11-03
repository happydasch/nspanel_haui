"""Virtual panel: the editor's interactive live preview, driven by the real hub code.

A virtual panel is a second ``NSPanelHAUI`` app for one device, built from
the same stored config. Instead of the ESPHome native API it talks to a
browser:

- ``VirtualESPHomeProxy`` plays the firmware's side. Display commands
  (``send_command(s)``, ``goto_page``, brightness, sounds) go to a sink that
  forwards them to the editor; touches, swipes and hardware buttons come back
  from the editor as the same ``esphome.*`` events the firmware publishes.
- ``VirtualNSPanelHAUI`` reads entity states through a ``Sandbox``. In sandbox
  mode every service call changes only simulated state; in live mode calls
  reach Home Assistant, except calls to the real device's own entities
  (relays, auto-dimming, brightness numbers), which always stay simulated.
- The app never fires HA bus events, never persists to the panel store and
  never checks for or installs firmware/TFT updates.

``VirtualPanelSession`` owns one virtual app for the lifetime of an open
preview (see ``websocket_api.py``).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

from .ha_adapter import ItemProxy
from .haui.controller.update import HAUIUpdateController
from .haui.mapping.const import ESP_NS_EVENT, ESPEvent, ESPResponse, ServerRequest
from .haui.version import get_version
from .nspanel_haui import NSPanelHAUI
from .sandbox import Sandbox

_LOGGER = logging.getLogger(__name__)

# Sink for messages to the browser; must be safe to call from any thread.
Sink = Callable[[dict[str, Any]], None]

# Device events the browser may inject: what a person can do to a real panel.
BROWSER_EVENTS: frozenset[str] = frozenset(
    {
        ESPEvent.COMPONENT,
        ESPEvent.TOUCH_START,
        ESPEvent.TOUCH_END,
        ESPEvent.GESTURE,
        ESPEvent.BUTTON_LEFT,
        ESPEvent.BUTTON_RIGHT,
        ESPEvent.TIMEOUT,
        # The browser holds the widget values the hub reads (sliders).
        ESPResponse.READ_RESPONSE,
    }
)

# Same value as the firmware's ``$heartbeat_interval`` substitution.
HEARTBEAT_INTERVAL = 5

# Firmware actions forwarded to the browser as ``{"type": "action", ...}``.
_FORWARDED_ACTIONS = frozenset(
    {"set_brightness", "play_sound", "play_rtttl", "display_off", "display_on"}
)
# Firmware actions a virtual device refuses: they would flash real hardware.
_REFUSED_ACTIONS = frozenset({"upload_tft_url", "install_firmware_url"})


class InertUpdateController(HAUIUpdateController):
    """Update controller of a virtual panel: never checks, never installs."""

    def start_part(self) -> None:
        pass

    def stop_part(self) -> None:
        pass

    def on_connection_changed(self, connected: bool) -> None:
        pass

    def check_for_update(self, force_refresh: bool = False) -> dict[str, Any]:
        return {}

    def manual_check_for_update(self) -> dict[str, Any]:
        return {}

    def install_tft(self, version: str | None = None) -> dict[str, Any]:
        return {"state": "error", "version": version, "last_error": "virtual panel"}

    def install_tft_url(self, url: str) -> dict[str, Any]:
        return {"state": "error", "version": None, "last_error": "virtual panel"}

    def install_firmware(self, version: str | None = None, url: str | None = None) -> dict:
        return {"firmware_installing": False, "firmware_install_error": "virtual panel"}


class VirtualESPHomeProxy:
    """Stands in for ``ESPHomeProxy`` and for the firmware behind it."""

    def __init__(self, app: VirtualNSPanelHAUI, sink: Sink, device_info: dict[str, Any]) -> None:
        self._app = app
        self._sink = sink
        self._device_info = device_info
        self._listeners: list[Callable] = []
        self._heartbeat_handle: str | None = None
        self._page: int = 0

    # ESPHomeProxy interface

    def listen_event(self, cb: Callable, event_type: str, topic: str | None = None, **kw: Any):
        self._listeners.append(cb)

    def cancel_listen_events(self) -> None:
        self._listeners.clear()
        if self._heartbeat_handle is not None:
            self._app.cancel_timer(self._heartbeat_handle)
            self._heartbeat_handle = None

    def publish(self, name: str, value: Any = "") -> bool:
        """Handle a firmware action the hub sends; runs on the app's worker."""
        if name == "send_command":
            self._sink({"type": "commands", "commands": [value]})
        elif name == "send_commands":
            self._sink({"type": "commands", "commands": list(value)})
        elif name == "goto_page":
            self._page = int(value)
            self._sink({"type": "page", "page": self._page})
            # The display reports every page change back (Preinitialize ``sendme``).
            self.emit(ESPEvent.PAGE, str(self._page))
        elif name == "hub_connection_response":
            self.emit(
                ServerRequest.RES_CONNECTION,
                json.dumps({"heartbeat_interval": str(HEARTBEAT_INTERVAL)}),
            )
        elif name == "req_device_state":
            self.emit(ESPResponse.RES_DEVICE_STATE, json.dumps(self._device_state()))
        elif name == "hub_connection_initialized":
            self._start_heartbeat()
        elif name in ("req_val", "req_txt"):
            # Answered by the browser with an esphome.read_response event.
            self._sink({"type": "request", "kind": name[4:], "name": value})
        elif name in _FORWARDED_ACTIONS:
            self._sink({"type": "action", "name": name, "value": value})
        elif name in _REFUSED_ACTIONS:
            _LOGGER.warning("Virtual panel refused '%s'", name)
            return False
        else:
            # hub_heartbeat, reset_last_interaction, ...: nothing on a virtual
            # device answers or needs them.
            _LOGGER.debug("Virtual panel ignored '%s'", name)
        return True

    # firmware side

    def connect(self) -> None:
        """Start the connection handshake, as a booting device does."""
        self.emit(ServerRequest.REQ_CONNECTION, json.dumps(self._device_info))

    def emit(self, name: str, value: str = "") -> None:
        """Publish a device event to the hub; safe to call from any thread."""
        data = {"name": str(name), "value": value}
        for cb in list(self._listeners):
            self._app.hass.loop.call_soon_threadsafe(self._app.dispatch, cb, ESP_NS_EVENT, data, {})

    def _start_heartbeat(self) -> None:
        if self._heartbeat_handle is None:
            self._heartbeat_handle = self._app.run_every(
                lambda _kwargs: self.emit(ServerRequest.HEARTBEAT),
                f"now+{HEARTBEAT_INTERVAL}",
                HEARTBEAT_INTERVAL,
            )

    def _device_state(self) -> dict[str, Any]:
        return {
            "page": self._page,
            "brightness": 100,
            "button_left": 0,
            "button_right": 0,
            "relay_left": 0,
            "relay_right": 0,
            "use_relay_left": 0,
            "use_relay_right": 0,
            "display_state": "on",
            "yaml_version": self._device_info.get("yaml_version", ""),
            # Empty means "unknown" to the hub, never "outdated".
            "tft_version": self._device_info.get("tft_version", ""),
            "firmware_variant": self._device_info.get("firmware_variant", ""),
            "ssid": "",
            "rssi": 0,
        }


class SandboxItemProxy(ItemProxy):
    """``ItemProxy`` that reads through the sandbox and routes calls via the virtual app."""

    def __init__(self, app: VirtualNSPanelHAUI, entity_id: str) -> None:
        super().__init__(app.hass, app.hass.loop, entity_id, proxy=app)
        self._app = app

    @property
    def state(self) -> Any:
        sim = self._app.sandbox.get(self.entity_id)
        return sim.state if sim else None

    @property
    def last_updated(self) -> Any:
        sim = self._app.sandbox.get(self.entity_id)
        return sim.last_updated if sim else None

    @property
    def attributes(self) -> dict[str, Any]:
        sim = self._app.sandbox.get(self.entity_id)
        return dict(sim.attributes) if sim else {}

    def call_service(self, service: str, **kwargs: Any) -> None:
        domain = self.entity_id.split(".", 1)[0]
        self._app.call_service(
            f"{domain}.{service}", target={"entity_id": self.entity_id}, service_data=kwargs
        )


class VirtualNSPanelHAUI(NSPanelHAUI):
    """``NSPanelHAUI`` for the editor's virtual panel (see module docstring)."""

    def __init__(
        self,
        hass: Any,
        name: str,
        config_args: dict,
        *,
        runtime_device_name: str,
        ha_device_id: str | None,
        sink: Sink,
        device_info: dict[str, Any],
        protected_entities: frozenset[str] = frozenset(),
        live: bool = False,
    ) -> None:
        super().__init__(
            hass,
            name,
            config_args,
            runtime_device_name=runtime_device_name,
            ha_device_id=ha_device_id,
        )
        self.live = live
        self.sandbox = Sandbox(self._read_real_state)
        self._sink = sink
        self._protected = protected_entities
        self._sandbox_listeners: dict[str, tuple[str, str | None, Callable]] = {}
        self.virtual_esphome = VirtualESPHomeProxy(self, sink, device_info)

    def _read_real_state(self, entity_id: str) -> tuple[str, dict[str, Any]] | None:
        state = self.hass.states.get(entity_id)
        return (state.state, dict(state.attributes)) if state else None

    def _create_update_controller(self, config: dict[str, Any]) -> HAUIUpdateController:
        return InertUpdateController(self, config)

    # HAAdapter overrides

    def get_plugin_api(
        self, plugin_name: str, device_name: str = "", device_id: str | None = None
    ) -> Any:
        if plugin_name != "ESPHome":
            raise ValueError(f"Unsupported plugin: {plugin_name}")
        return self.virtual_esphome

    def fire_event(self, event_type: str, data: dict | None = None) -> None:
        # Automations listen for the real device's events; a preview must not trigger them.
        _LOGGER.debug("Virtual panel suppressed event %s", event_type)

    def item_exists(self, entity_id: str) -> bool:
        return self.sandbox.get(entity_id) is not None

    def get_item(self, entity_id: str) -> SandboxItemProxy:
        return SandboxItemProxy(self, entity_id)

    def listen_state(
        self, cb: Callable, entity_id: str, attribute: str | None = None, **kwargs: Any
    ) -> str:
        handle = super().listen_state(cb, entity_id, attribute=attribute, **kwargs)
        self._sandbox_listeners[handle] = (entity_id, attribute, cb)
        return handle

    def cancel_listen_state(self, handle: str) -> None:
        self._sandbox_listeners.pop(handle, None)
        super().cancel_listen_state(handle)

    def call_service(
        self,
        service: str,
        return_response: bool = False,
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> Any:
        if return_response:
            # Queries such as weather/get_forecasts change nothing.
            return super().call_service(service, return_response, raise_on_error, **kwargs)
        domain, svc, service_data, target = self._split_service_call(service, dict(kwargs))
        entity_ids = _target_entity_ids(target)
        if self.live and not any(eid in self._protected for eid in entity_ids):
            return super().call_service(service, return_response, raise_on_error, **kwargs)
        self.simulate_service(domain, svc, entity_ids, service_data or {})
        return True if raise_on_error else None

    # sandbox

    def simulate_service(
        self, domain: str, service: str, entity_ids: list[str], data: dict[str, Any]
    ) -> None:
        simulated, changes = self.sandbox.apply(domain, service, entity_ids, data)
        if not simulated:
            self.log(f"Sandbox: {domain}.{service} is not simulated", level="DEBUG")
            return
        for entity_id, old, new in changes:
            self._notify_sandbox_change(entity_id, old, new)
        if changes:
            self._sink({"type": "sandbox", "entities": self.sandbox.simulated_ids()})

    def reset_sandbox(self) -> None:
        """Drop the simulated states, so every entity shows its real state again."""
        for entity_id in self.sandbox.reset():
            # The listener sees the real state as the new value.
            self._notify_sandbox_change(entity_id, None, self.sandbox.get(entity_id))
        self._sink({"type": "sandbox", "entities": []})

    def _notify_sandbox_change(self, entity_id: str, old: Any, new: Any) -> None:
        for handle, (listen_id, attribute, cb) in list(self._sandbox_listeners.items()):
            if listen_id != entity_id:
                continue
            attr = attribute or "state"
            if attr in ("state", "all"):
                old_val = old.state if old else None
                new_val = new.state if new else None
            else:
                old_val = old.attributes.get(attr) if old else None
                new_val = new.attributes.get(attr) if new else None
                if old_val == new_val:
                    continue
            # Queued like a real state change, so it runs after the current callback.
            self.hass.loop.call_soon_threadsafe(
                self.dispatch, self._fire_state, handle, cb, entity_id, attr, old_val, new_val
            )


def _target_entity_ids(target: dict[str, Any] | None) -> list[str]:
    if not target:
        return []
    ids = target.get("entity_id", [])
    return [ids] if isinstance(ids, str) else list(ids)


class VirtualPanelSession:
    """One open live preview: a virtual app for one device and its browser sink."""

    def __init__(
        self,
        hass: Any,
        device_name: str,
        config_args: dict,
        sink: Sink,
        *,
        ha_device_id: str | None = None,
        device_info: dict[str, Any] | None = None,
        protected_entities: frozenset[str] = frozenset(),
        live: bool = False,
    ) -> None:
        self.id = uuid.uuid4().hex
        info = {
            "name": device_name,
            "friendly_name": device_name,
            "ip": "",
            "ssid": "",
            "rssi": 0,
            "uptime": 0,
            "yaml_version": get_version(),
            "tft_version": "",
            "firmware_variant": "",
        }
        info.update({k: v for k, v in (device_info or {}).items() if k in info and v})
        self.app = VirtualNSPanelHAUI(
            hass,
            f"virtual_{self.id[:8]}",
            config_args,
            runtime_device_name=device_name,
            ha_device_id=ha_device_id,
            sink=sink,
            device_info=info,
            protected_entities=protected_entities,
            live=live,
        )

    async def async_start(self) -> None:
        await self.app.async_run_on_worker(self.app.initialize)
        self.app.virtual_esphome.connect()

    async def async_stop(self) -> None:
        await self.app.async_run_on_worker(self.app.stop)

    def send_event(self, name: str, value: str) -> None:
        """Inject a device event from the browser.

        Raises:
            ValueError: If ``name`` is not an event a person can cause on a panel.
        """
        if name not in BROWSER_EVENTS:
            raise ValueError(f"Event not allowed from the preview: {name}")
        self.app.virtual_esphome.emit(name, value)

    def set_live(self, live: bool) -> None:
        self.app.live = live

    def reset_sandbox(self) -> None:
        self.app.dispatch(self.app.reset_sandbox)

"""Virtual panel: the editor's sandbox preview, driven by the real hub code.

A virtual panel is a second ``NSPanelHAUI`` app for one device, built from
the same stored config. Instead of the ESPHome native API it talks to a
browser:

- ``VirtualESPHomeProxy`` plays the firmware's side. Display commands
  (``send_command(s)``, ``goto_page``, brightness, sounds) go to a sink that
  forwards them to the editor; touches, swipes and hardware buttons come back
  from the editor as the same ``esphome.*`` events the firmware publishes.
- ``VirtualNSPanelHAUI`` reads entity states through a ``Sandbox``: input
  changes only simulated states, never a real entity.
- The app never fires HA bus events, never persists to the panel store and
  never checks for or installs firmware/TFT updates.

``VirtualPanelHost`` owns the one virtual app of a device (see
``web/websocket.py``). Every open sandbox preview of the device is a viewer of
that app, and the editor's panel cards are rendered on it too: each card runs
its panel's page in isolation (``_PanelRender``), so a card never moves what a
viewer sees. The live preview, which shows and drives the real panel, is
``live_panel.py``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from ...haui.abstract.haui_panel import HAUIPanel
from ...haui.controller.update import HAUIUpdateController
from ...haui.device import HAUIDevice
from ...haui.mapping.const import (
    ESP_NS_EVENT,
    ESPCommand,
    ESPEvent,
    ESPResponse,
    ServerRequest,
)
from ...haui.mapping.panel import PANEL_MAPPING, POPUP_PANEL_MAPPING
from ...haui.utils.page import get_page_class_for_panel, get_page_id_for_panel
from ...haui.utils.text import get_translation
from ...haui.version import get_version
from ...hub.adapter import ItemProxy
from ...hub.app import NSPanelHAUI
from .button_lights import (
    RELAY_ENTITY_NAMES,
    ButtonLight,
    button_entity_ids,
    light_state,
    lights_message,
)
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


class VirtualDevice(HAUIDevice):
    """Device of a virtual panel: leaves the firmware's auto switches alone.

    The switches belong to the real device, whose hub app keeps them in line
    with settings and the page on its screen. A hardware button switches its
    relay in the sandbox, as the firmware does on the real panel.
    """

    def process_event(self, event: Any) -> None:
        """Mirror ESPHome's press-edge relay action before the hub handles the event."""
        if event.value == "1" and event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT):
            side = "left" if event.name == ESPEvent.BUTTON_LEFT else "right"
            self._toggle_firmware_relay(side)
        super().process_event(event)

    def _toggle_firmware_relay(self, side: str) -> None:
        if not self.get(f"use_relay_{side}", True):
            return
        relay_name = RELAY_ENTITY_NAMES[side]
        entity_id = self.find_esphome_entity_id("switch", relay_name)
        if entity_id is None:
            self.log(f"Virtual panel: no {relay_name} switch on the device")
            return
        self.app.call_service("switch.toggle", target={"entity_id": entity_id})


class InertUpdateController(HAUIUpdateController):
    """Update controller of a virtual panel: never checks, never installs.

    Every entry point that would fetch from GitHub or flash the device
    answers at once instead; a saved config (``reload_options``) only takes
    the new settings.
    """

    def start_part(self) -> None:
        pass

    def stop_part(self) -> None:
        pass

    def reload_options(self, config: dict[str, Any]) -> None:
        self.config = config

    def on_connection_changed(self, connected: bool) -> None:
        pass

    def start_async_check(
        self,
        force_refresh: bool = False,
        *,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        **_kwargs: Any,
    ) -> None:
        if on_complete is not None:
            on_complete(self._check_result("virtual panel"))

    def start_async_tft_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        on_complete(self.install_tft(version))

    def start_async_firmware_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        on_complete({"firmware_installing": False, "firmware_install_error": "virtual panel"})

    def start_async_list_tft_releases(self, on_complete: Callable[[dict[str, Any]], None]) -> None:
        on_complete({"releases": [], "required": None, "error": "virtual panel"})

    def start_async_list_firmware_releases(
        self, on_complete: Callable[[dict[str, Any]], None]
    ) -> None:
        on_complete({"releases": [], "error": "virtual panel"})

    def install_tft(self, version: str | None = None) -> dict[str, Any]:
        return {"state": "error", "version": version, "last_error": "virtual panel"}

    def install_tft_url(self, url: str) -> dict[str, Any]:
        return {"state": "error", "version": None, "last_error": "virtual panel"}


class VirtualESPHomeProxy:
    """Stands in for ``ESPHomeProxy`` and for the firmware behind it."""

    def __init__(self, app: VirtualNSPanelHAUI, sink: Sink, device_info: dict[str, Any]) -> None:
        self._app = app
        self._sink = sink
        self._device_info = device_info
        self._listeners: list[Callable] = []
        self._heartbeat_handle: str | None = None
        self._page: int = 0
        self._idle = False
        self._entities: dict[str, str] = {}

    def set_device_info(self, device_info: dict[str, Any]) -> None:
        """Update the metadata reported by the simulated device."""
        self._device_info = dict(device_info)

    @property
    def idle(self) -> bool:
        """Whether the idle page shows, as last reported to the browser."""
        return self._idle

    @property
    def entities(self) -> dict[str, str]:
        """Widget name -> entity id, as last reported to the browser."""
        return dict(self._entities)

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
        self._report_idle()
        self._report_entities()
        return True

    def publish_detached(self, name: str, value: Any = "") -> None:
        """Fire-and-forget action (the hub→device heartbeat).

        A virtual device has no liveness to keep, so nothing answers it.
        """

    def _report_entities(self) -> None:
        """Tell the browser which widgets show which entity, when that changes."""
        navigation = self._app.controller.get("navigation")
        page = navigation.page if navigation is not None else None
        entities = page.entity_map() if page is not None and page.panel is not None else {}
        if entities != self._entities:
            self._entities = entities
            self._sink({"type": "entities", "map": entities})

    def _report_idle(self) -> None:
        """Tell the browser when the idle page starts or ends.

        Entering and leaving the idle page always draws a page, so checking
        after every display output catches each change.
        """
        navigation = self._app.controller.get("navigation")
        idle = bool(navigation is not None and navigation.idle_panel_active)
        if idle != self._idle:
            self._idle = idle
            self._sink({"type": "idle", "active": idle})

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
    ) -> None:
        super().__init__(
            hass,
            name,
            config_args,
            runtime_device_name=runtime_device_name,
            ha_device_id=ha_device_id,
        )
        self.sandbox = Sandbox(self._read_real_state)
        self._sink = sink
        self._sandbox_listeners: dict[str, tuple[str, str | None, Callable]] = {}
        # Hardware button lights (see button_lights.py), from simulated states.
        self._button_entity_ids: dict[ButtonLight, str] = {}
        self._button_handles: dict[ButtonLight, str] = {}
        self._button_states: dict[ButtonLight, str] = {}
        self.virtual_esphome = VirtualESPHomeProxy(self, sink, device_info)

    def _read_real_state(self, entity_id: str) -> tuple[str, dict[str, Any]] | None:
        state = self.hass.states.get(entity_id)
        return (state.state, dict(state.attributes)) if state else None

    def start_relay_state_tracking(self) -> None:
        """Publish the hardware button lights and follow their simulated states.

        Call again after a config change: it follows the new entities.
        """
        for key, entity_id in button_entity_ids(self.device).items():
            self._track_button_state(key, entity_id)
        self._publish_relay_states()

    def _track_button_state(self, key: ButtonLight, entity_id: str | None) -> None:
        if self._button_entity_ids.get(key) != entity_id:
            handle = self._button_handles.pop(key, None)
            if handle is not None:
                self.cancel_listen_state(handle)
            self._button_entity_ids.pop(key, None)
            if entity_id:
                self._button_entity_ids[key] = entity_id
                self._button_handles[key] = self.listen_state(
                    lambda _entity, _attribute, _old, _new, _kwargs, button=key: (
                        self._on_button_state_changed(button)
                    ),
                    entity_id,
                )
        if entity_id:
            item = self.get_item(entity_id)
            self._button_states[key] = light_state(item.state, item.attributes, entity_id)
        else:
            self._button_states.pop(key, None)

    def _on_button_state_changed(self, key: ButtonLight) -> None:
        entity_id = self._button_entity_ids[key]
        item = self.get_item(entity_id)
        self._button_states[key] = light_state(item.state, item.attributes, entity_id)
        self._publish_relay_states()

    def _publish_relay_states(self) -> None:
        self._sink(lights_message(self._button_states))

    def stop_relay_state_tracking(self) -> None:
        """Release the state listeners when the virtual app stops."""
        for handle in self._button_handles.values():
            self.cancel_listen_state(handle)
        self._button_handles.clear()
        self._button_entity_ids.clear()

    def _create_device(self, config: dict[str, Any]) -> HAUIDevice:
        return VirtualDevice(self, config)

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
        self.simulate_service(domain, svc, _target_entity_ids(target), service_data or {})
        return True if raise_on_error else None

    # sandbox

    def simulate_service(
        self, domain: str, service: str, entity_ids: list[str], data: dict[str, Any]
    ) -> None:
        simulated, changes = self.sandbox.apply(domain, service, entity_ids, data)
        if not simulated:
            self.log(f"Sandbox: {domain}.{service} is not simulated", level="DEBUG")
            return
        if changes:
            self._report_sandbox_state()
        for entity_id, old, new in changes:
            self._notify_sandbox_change(entity_id, old, new)

    def reset_sandbox(self) -> None:
        """Drop the simulated states, so every entity shows its real state again."""
        for entity_id in self.sandbox.reset():
            # The listener sees the real state as the new value.
            self._notify_sandbox_change(entity_id, None, self.sandbox.get(entity_id))
        self._report_sandbox_state()

    def _report_sandbox_state(self) -> None:
        self._sink({"type": "sandbox", "changed": self.sandbox.has_changes})

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


def _translated(value: Any, locale: str) -> Any:
    """A preview kwarg in the device's language: display text and lists of it."""
    if isinstance(value, str):
        return get_translation(value, locale)
    if isinstance(value, list):
        return [get_translation(v, locale) if isinstance(v, str) else v for v in value]
    return value


def _sample_rank(state: Any) -> int:
    """How well an entity shows what its popup can do: on, then off, then no state."""
    if state.state in ("unavailable", "unknown"):
        return 2
    return 1 if state.state == "off" else 0


def preview_kwargs(hass: Any, panel_config: dict[str, Any]) -> dict[str, Any]:
    """The sample context a popup's card opens it with; call from the event loop.

    See ``PageDescriptor.preview_kwargs``. An entity popup (``popup_<page>``)
    opens for an entity of its ``item`` option's domain, as a tap on such an
    entity would: the first one that is on, else the first one that is off.
    """
    panel_type = str(panel_config.get("type", ""))
    mapping = PANEL_MAPPING.get(panel_type)
    if mapping is None:
        return {}
    descriptor = mapping[1].DESCRIPTOR
    kwargs = {
        key: value
        for key, value in (descriptor.preview_kwargs or {}).items()
        if key not in panel_config
    }
    # Known by its system key: an edited entity popup is saved with the user
    # type (popup_light → light).
    entity_popup = panel_config.get("key") in POPUP_PANEL_MAPPING
    if entity_popup and "item" not in panel_config and "item_id" not in panel_config:
        domain = next((o.domain for o in descriptor.options if o.key == "item"), None)
        entity_ids = sorted(hass.states.async_entity_ids(domain)) if domain else []
        if entity_ids:
            entity_id = min(entity_ids, key=lambda e: _sample_rank(hass.states.get(e)))
            kwargs.update(item=entity_id, item_id=entity_id)
    return kwargs


class _RecordingESPHome:
    """The ESPHome controller as a card render sees it: display output is recorded.

    Page switches, sounds and value requests belong to the live display and are
    dropped.
    """

    def __init__(self) -> None:
        self.commands: list[str] = []

    def send_cmd(self, cmd: str, value: Any = "", force: bool = False) -> None:
        name = cmd if cmd.startswith("esphome.") else f"esphome.{cmd}"
        if name == ESPCommand.SEND_COMMAND:
            self.commands.append(value)
        elif name == ESPCommand.SEND_COMMANDS:
            self.commands.extend(value)

    def reset_prev_cmd(self) -> None:
        pass

    def publish_detached(self, cmd: str, value: Any = "") -> None:
        """Fire-and-forget actions (the heartbeat) have no live device here."""


class _RenderNavigation:
    """Navigation as a card render sees it: no action moves the live display."""

    page = None
    panel = None
    idle_panel_active = False

    def open_panel(self, *args: Any, **kwargs: Any) -> None:
        pass

    close_panel = open_home_panel = reload_panel = refresh_panel = go_back = open_panel
    open_prev_panel = open_next_panel = open_idle_panel = exit_idle_to_prev_or_home = open_panel


class _RenderBlinker:
    """The shared notification blinker; a refresh redraws the render's own page."""

    def __init__(self, notification: _RenderNotification) -> None:
        self._notification = notification

    @property
    def new_notifications(self) -> bool:
        return bool(self._notification.real.blinker.new_notifications)

    def refresh(self) -> None:
        if self._notification.refresh_fn is not None:
            self._notification.refresh_fn()


class _RenderNotification:
    """Notification state of the shared app; the indicator draws on the render page.

    Registering the blinker callback here keeps the live page's callback.
    """

    def __init__(self, real: Any) -> None:
        self.real = real
        self.refresh_fn: Callable[[], None] | None = None
        self.blinker = _RenderBlinker(self)

    def has_notifications(self) -> bool:
        return bool(self.real.has_notifications())

    def set_blinker_callback(self, refresh_fn: Callable[[], None]) -> None:
        self.refresh_fn = refresh_fn

    def clear_blinker_callback(self) -> None:
        self.refresh_fn = None

    def open_notifications(self) -> None:
        pass


class _RenderApp:
    """The shared virtual app as one card render sees it.

    Reads (config, entity states, translations, timers) go to the app. Display
    output is recorded, navigation does nothing and only service calls that
    return data, such as weather forecasts, are made: a card changes nothing.
    """

    def __init__(self, app: VirtualNSPanelHAUI, esphome: _RecordingESPHome) -> None:
        self._app = app
        self.controller = {
            **app.controller,
            "esphome": esphome,
            "navigation": _RenderNavigation(),
            "notification": _RenderNotification(app.controller["notification"]),
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._app, name)

    def get_item(self, entity_id: str) -> SandboxItemProxy:
        # Item service calls come back through this view, so they are filtered too.
        return SandboxItemProxy(self, entity_id)  # type: ignore[arg-type]

    def call_service(
        self,
        service: str,
        return_response: bool = False,
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not return_response:
            _LOGGER.debug("Card render skipped service call %s", service)
            return None
        return self._app.call_service(service, return_response, raise_on_error, **kwargs)


class _PanelRender:
    """One panel rendered on a page of its own; create, start and stop on the app's worker.

    The page runs its full lifecycle as navigation would drive it. Commands sent
    while the page load is prepared come ``before`` the page switch, as on the
    device (the theme colours and a picture background must be set before the
    page loads); the rest follow it.
    """

    def __init__(
        self, app: VirtualNSPanelHAUI, panel_config: dict[str, Any], kwargs: dict[str, Any]
    ) -> None:
        panel_type = panel_config.get("type", "")
        page_id = get_page_id_for_panel(panel_type)
        page_class = get_page_class_for_panel(panel_type)
        if page_id is None or page_class is None:
            raise ValueError(f"Unknown panel type: {panel_type!r}")
        self.page_id = page_id
        self._esphome = _RecordingESPHome()
        view = _RenderApp(app, self._esphome)
        locale = app.device.get_locale()
        kwargs = {key: _translated(value, locale) for key, value in kwargs.items()}
        if isinstance(kwargs.get("unlock_panel"), dict):
            # Navigation passes the panel to unlock as a locked panel object.
            unlock_panel = HAUIPanel(view, kwargs["unlock_panel"])  # type: ignore[arg-type]
            unlock_panel.set_state("locked", True)
            kwargs["unlock_panel"] = unlock_panel
        self._panel = HAUIPanel(view, panel_config)  # type: ignore[arg-type]
        self._panel.apply_kwargs(kwargs)
        self._page = page_class(view, {"page_id": page_id})  # type: ignore[arg-type]
        self.before: list[str] = []

    @property
    def commands(self) -> list[str]:
        return self._esphome.commands

    def start(self) -> None:
        self._page.prepare_page_load(self._panel)
        self.before = list(self._esphome.commands)
        self._esphome.commands.clear()
        self._page.start()
        self._page.set_panel(self._panel)

    def stop(self) -> None:
        # set_panel(None) stops the panel: its listeners, timers and debounces.
        self._page.set_panel(None)
        self._page.stop()


class VirtualPanelHost:
    """The editor's virtual panel for one device: one app for every preview.

    Sandbox previews are viewers of the virtual app's display output, and its
    simulated states are shared by all of them. Panel cards render single
    panels in isolation on the same app.
    """

    def __init__(
        self,
        hass: Any,
        device_name: str,
        config_args: dict,
        *,
        ha_device_id: str | None = None,
        device_info: dict[str, Any] | None = None,
    ) -> None:
        self._viewers: dict[str, Sink] = {}
        # Physical notification id -> its copy in the virtual queue.
        self._preview_notification_ids: dict[str, str] = {}
        self._notification_source: Any | None = None
        self._unfollow_notifications: Callable[[], None] | None = None
        self._viewers_lock = threading.Lock()
        self._connected = False
        info = {
            "name": device_name,
            "friendly_name": device_name,
            "ip": "",
            "ssid": "",
            "rssi": 0,
            "uptime": 0,
            "yaml_version": get_version() if device_info is None else "",
            "tft_version": "",
            "firmware_variant": "",
        }
        info.update({k: v for k, v in (device_info or {}).items() if k in info})
        self._device_info = dict(info)
        self._follow: asyncio.Future[None] | None = None
        self.app = VirtualNSPanelHAUI(
            hass,
            f"virtual_{device_name}",
            config_args,
            runtime_device_name=device_name,
            ha_device_id=ha_device_id,
            sink=self._broadcast,
            device_info=info,
        )

    async def async_start(self) -> None:
        """Initialize the app. Its display boots when the first viewer attaches."""
        await self.app.async_run_on_worker(self.app.initialize)
        await self.async_set_device_info(self._device_info)

    async def async_set_device_info(self, device_info: dict[str, Any]) -> None:
        """Apply physical-device metadata to the simulated app on its worker.

        Only the metadata keys are taken (versions, network, name): the rest of
        the physical device's info (``display_state``, ``page``, ...) describes
        its display, and a dark panel would pause the preview's cycle cards.
        """
        self._device_info.update({k: v for k, v in device_info.items() if k in self._device_info})
        info = dict(self._device_info)

        def _set_device_info() -> None:
            self.app.device.set_device_info(dict(info))
            self.app.virtual_esphome.set_device_info(info)

        await self.app.async_run_on_worker(_set_device_info)

    async def async_follow_device(self, running: Any) -> None:
        """Take the physical device's metadata (versions, network) for previews and cards."""
        if self._follow is None or self._follow.done():
            self._follow = asyncio.ensure_future(self._async_follow_device(running))
        await asyncio.shield(self._follow)

    async def _async_follow_device(self, running: Any) -> None:
        device_info = await running.async_run_on_worker(lambda: dict(running.device.device_info))
        await self.async_set_device_info(device_info)

    async def async_follow_notifications(self, running: Any) -> None:
        """Mirror the physical device's notification queue, read-only, from now on.

        Every change of that queue is applied to the virtual app's queue; a
        notification dismissed in the preview stays queued on the panel.
        """
        if self._notification_source is running:
            return
        self._stop_following_notifications()
        self._notification_source = running
        controller = running.controller["notification"]

        def _changed(state: dict[str, Any]) -> None:
            # On the physical app's worker, so its queue is read there.
            if state["event"] == "notifications":
                self.app.hass.loop.call_soon_threadsafe(
                    self.app.dispatch, self._sync_notifications, controller.get_notifications()
                )

        self._unfollow_notifications = running.subscribe_preview_state(_changed)
        snapshot = await running.async_run_on_worker(controller.get_notifications)
        await self.app.async_run_on_worker(self._sync_notifications, snapshot)

    def _stop_following_notifications(self) -> None:
        if self._unfollow_notifications is not None:
            self._unfollow_notifications()
            self._unfollow_notifications = None
        self._notification_source = None

    async def async_stop(self) -> None:
        self._stop_following_notifications()
        await self.app.async_run_on_worker(self.app.stop_relay_state_tracking)
        await self.app.async_run_on_worker(self.app.stop)

    async def async_reload(self, config_args: dict) -> None:
        """Apply a saved config, as a save does on the device's own app."""
        await self.app.async_run_on_worker(self.app.reload_config, config_args)
        # Relay mode and the button entities are device settings.
        if self.viewer_count:
            await self.app.async_run_on_worker(self.app.start_relay_state_tracking)

    # viewers (sandbox previews)

    @property
    def viewer_count(self) -> int:
        with self._viewers_lock:
            return len(self._viewers)

    def attach(self, viewer_id: str, sink: Sink) -> None:
        """Attach a viewer; the first one boots the virtual display."""
        with self._viewers_lock:
            self._viewers[viewer_id] = sink
        self.app.dispatch(self.app.start_relay_state_tracking)
        self.app.dispatch(
            lambda: sink({"type": "sandbox", "changed": self.app.sandbox.has_changes})
        )
        if self._connected:
            self.app.dispatch(self._redraw_for, sink)
        else:
            self._connected = True
            self.app.virtual_esphome.connect()

    def detach(self, viewer_id: str) -> bool:
        """Remove a viewer; returns whether it was attached."""
        with self._viewers_lock:
            return self._viewers.pop(viewer_id, None) is not None

    def _broadcast(self, message: dict[str, Any]) -> None:
        with self._viewers_lock:
            sinks = list(self._viewers.values())
        for sink in sinks:
            sink(message)

    def _redraw_for(self, sink: Sink) -> None:
        proxy = self.app.virtual_esphome
        sink({"type": "idle", "active": proxy.idle})
        sink({"type": "entities", "map": proxy.entities})
        navigation = self.app.controller["navigation"]
        if navigation.panel is not None:
            navigation.reload_panel()

    # panel cards

    async def async_configured_panel(self, key: str) -> dict[str, Any]:
        """The device's panel with this key as the hub opens it.

        System panels come with their defaults, or the saved override of them.

        Raises:
            ValueError: If the device has no panel with this key.
        """

        def _config() -> dict[str, Any]:
            panel = self.app.device_config.get_panel(key)
            if panel is None:
                raise ValueError(f"Unknown panel key: {key!r}")
            return panel.get_default_config()

        return await self.app.async_run_on_worker(_config)

    async def async_render(
        self,
        panel_config: dict[str, Any],
        kwargs: dict[str, Any] | None = None,
        *,
        settle: float = 0.3,
        timeout: float = 3.0,
    ) -> dict[str, Any]:
        """Render one panel as its card shows it, without touching the live display.

        Delayed output (debounced item updates) is collected until the page
        has been quiet for ``settle`` seconds, at most ``timeout`` seconds.

        Returns:
            ``{"page": id, "before": [...], "commands": [...]}``: the commands
            sent before the page switch and those that draw the page.
        """
        kwargs = {**preview_kwargs(self.app.hass, panel_config), **(kwargs or {})}
        render = await self.app.async_run_on_worker(_PanelRender, self.app, panel_config, kwargs)
        loop = asyncio.get_running_loop()
        try:
            await self.app.async_run_on_worker(render.start)
            deadline = loop.time() + timeout
            count, quiet_since = len(render.commands), loop.time()
            while loop.time() < deadline:
                await asyncio.sleep(0.05)
                if len(render.commands) != count:
                    count, quiet_since = len(render.commands), loop.time()
                elif loop.time() - quiet_since >= settle:
                    break
        finally:
            await self.app.async_run_on_worker(render.stop)
        return {"page": render.page_id, "before": render.before, "commands": list(render.commands)}

    def _sync_notifications(self, notifications: list[Any]) -> None:
        """Reconcile the physical queue's snapshot on the virtual app's worker."""
        controller = self.app.controller["notification"]
        snapshot = {notification.notif_id: notification for notification in notifications}
        queued = {
            notification.notif_id: notification for notification in controller.get_notifications()
        }

        for source_id, local_id in list(self._preview_notification_ids.items()):
            if source_id in snapshot:
                continue
            notification = queued.get(local_id)
            navigation = self.app.controller.get("navigation")
            current_panel = navigation.get_current_panel() if navigation is not None else None
            # Any panel may be shown; only a notification popup has an id.
            was_open = current_panel is not None and current_panel.get("notif_id", None) == local_id
            if notification is not None:
                controller.remove_notification(notification)
            del self._preview_notification_ids[source_id]
            if was_open:
                navigation.close_panel()

        for source_id, notification in snapshot.items():
            if source_id in self._preview_notification_ids:
                continue
            local = controller.add_notification(
                title=notification.title,
                message=notification.message,
                icon=notification.icon,
                persistent=notification.persistent,
                notif_type=notification.notif_type,
                force_show=notification.force_show,
                text_size=notification.text_size,
                timeout=notification.timeout,
            )
            self._preview_notification_ids[source_id] = local.notif_id

    def send_event(self, name: str, value: str) -> None:
        """Inject a device event from the browser.

        Raises:
            ValueError: If ``name`` is not an event a person can cause on a panel.
        """
        if name not in BROWSER_EVENTS:
            raise ValueError(f"Event not allowed from the preview: {name}")
        self.app.virtual_esphome.emit(name, value)

    def show_idle(self) -> None:
        """Act as if the inactivity timeout opened the virtual idle page."""
        navigation = self.app.controller.get("navigation")
        if navigation is not None:
            self.app.dispatch(navigation.open_idle_panel, True)

    def show_home(self) -> None:
        """Start the sandbox over on its home panel, as a preview back from Live.

        Live drives the device's own app, so the virtual app got no touches
        meanwhile: its simulated states are dropped, its idle page is left and
        its inactivity clock starts again, or the idle page would be due at once.
        """
        navigation = self.app.controller.get("navigation")
        if navigation is None:
            return

        def _start_over() -> None:
            self.app.reset_sandbox()
            # A home panel outside the navigation would only suspend the idle session.
            navigation.mark_awake()
            navigation.reset_activity()
            navigation.open_home_panel()

        self.app.dispatch(_start_over)

    def reset_sandbox(self) -> None:
        """Clear the device's simulated states."""
        self.app.dispatch(self.app.reset_sandbox)

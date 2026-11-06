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
  reach Home Assistant, except calls to the real device's settings entities
  (auto-dimming, brightness numbers, ...), which always stay simulated. The
  relays are switched for real in live mode: the hardware buttons do that on
  the panel.
- The app never fires HA bus events, never persists to the panel store and
  never checks for or installs firmware/TFT updates.

``VirtualPanelHost`` owns the one virtual app of a device (see
``websocket_api.py``). Every open live preview of the device is a viewer of
that app, and the editor's panel cards are rendered on it too: each card runs
its panel's page in isolation (``_PanelRender``), so a card never moves what a
viewer sees.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from .ha_adapter import ItemProxy
from .haui.abstract.haui_panel import HAUIPanel
from .haui.controller.update import HAUIUpdateController
from .haui.mapping.const import ESP_NS_EVENT, ESPCommand, ESPEvent, ESPResponse, ServerRequest
from .haui.mapping.panel import PANEL_MAPPING, POPUP_PANEL_MAPPING
from .haui.utils.page import get_page_class_for_panel, get_page_id_for_panel
from .haui.utils.text import get_translation
from .haui.version import get_version
from .nspanel_haui import NSPanelHAUI
from .sandbox import Sandbox

_LOGGER = logging.getLogger(__name__)

# Protocol 2 adds optional entity-map and idle-state messages. Older open editor
# modules do not understand these message types, so don't send them to those clients.
_METADATA_PROTOCOL_VERSION = 2

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

# The firmware's relay switches (esphome/nspanel_haui/switch.yaml). The
# hardware buttons switch them in relay mode, so unlike the device's settings
# entities they are switched for real in live mode.
RELAY_ENTITY_NAMES: dict[str, str] = {"left": "Relay Left", "right": "Relay Right"}

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
        self._idle = False
        self._entities: dict[str, str] = {}

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
        domain, svc, service_data, target = self._split_service_call(service, dict(kwargs))
        entity_ids = _target_entity_ids(target)
        protected_target = any(eid in self._protected for eid in entity_ids)
        if self.live and target is not None and any(key != "entity_id" for key in target):
            self.log(
                f"Live preview refused {domain}.{svc}: target selectors cannot be checked safely",
                level="WARNING",
            )
            return None
        if return_response:
            # Queries such as weather/get_forecasts change nothing. Do not let a
            # response-bearing call bypass protection for device settings.
            if self.live and protected_target:
                self.log(
                    f"Live preview refused response call {domain}.{svc} to a protected entity",
                    level="WARNING",
                )
                return None
            return super().call_service(service, return_response, raise_on_error, **kwargs)
        if self.live and not protected_target:
            return super().call_service(service, return_response, raise_on_error, **kwargs)
        self.simulate_service(domain, svc, entity_ids, service_data or {})
        return True if raise_on_error else None

    def press_hardware_button(self, side: str) -> None:
        """Do what the firmware does on a hardware button press: toggle its relay in relay mode.

        On the device the firmware switches the relay itself (sensor.yaml,
        ``on_press``), so the hub never sees it; the virtual device does it
        through the relay's switch entity, simulated or real by mode.
        """
        if not self.device.get(f"use_relay_{side}", True):
            return
        entity_id = self.device.find_esphome_entity_id("switch", RELAY_ENTITY_NAMES[side])
        if entity_id is None:
            self.log(f"Virtual panel: no {RELAY_ENTITY_NAMES[side]} switch on the device")
            return
        self.call_service("switch/toggle", target={"entity_id": entity_id})

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


def _send_compatible(sink: Sink, protocol_version: int, message: dict[str, Any]) -> None:
    """Send to one viewer, without the metadata messages its protocol predates."""
    if protocol_version < _METADATA_PROTOCOL_VERSION and message.get("type") in {
        "entities",
        "idle",
    }:
        return
    sink(message)


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

    Live previews attach as viewers: each sees the app's display output and can
    touch it. Panel cards render single panels in isolation on the same app.
    The sandbox/live mode belongs to the app, so it is shared by all viewers.
    """

    def __init__(
        self,
        hass: Any,
        device_name: str,
        config_args: dict,
        *,
        ha_device_id: str | None = None,
        device_info: dict[str, Any] | None = None,
        protected_entities: frozenset[str] = frozenset(),
        live: bool = False,
    ) -> None:
        self._viewers: dict[str, tuple[Sink, int]] = {}
        self._viewers_lock = threading.Lock()
        self._connected = False
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
            f"virtual_{device_name}",
            config_args,
            runtime_device_name=device_name,
            ha_device_id=ha_device_id,
            sink=self._broadcast,
            device_info=info,
            protected_entities=protected_entities,
            live=live,
        )

    async def async_start(self) -> None:
        """Initialize the app. Its display boots when the first viewer attaches."""
        await self.app.async_run_on_worker(self.app.initialize)

    async def async_stop(self) -> None:
        await self.app.async_run_on_worker(self.app.stop)

    async def async_reload(self, config_args: dict) -> None:
        """Apply a saved config, as a save does on the device's own app."""
        await self.app.async_run_on_worker(self.app.reload_config, config_args)

    # viewers (live previews)

    @property
    def viewer_count(self) -> int:
        with self._viewers_lock:
            return len(self._viewers)

    def attach(
        self, viewer_id: str, sink: Sink, *, protocol_version: int = _METADATA_PROTOCOL_VERSION
    ) -> None:
        """Add a live-preview viewer; call from the event loop.

        The first viewer boots the display. A later one starts blank, so the
        current panel is drawn again (for every viewer) and the viewer learns
        the idle, entity and sandbox state it missed.
        """
        with self._viewers_lock:
            self._viewers[viewer_id] = (sink, protocol_version)
        if self._connected:
            self.app.dispatch(self._redraw_for, sink, protocol_version)
        else:
            self._connected = True
            self.app.virtual_esphome.connect()

    def detach(self, viewer_id: str) -> bool:
        """Remove a viewer; returns whether it was attached."""
        with self._viewers_lock:
            return self._viewers.pop(viewer_id, None) is not None

    def has_viewer(self, viewer_id: str) -> bool:
        with self._viewers_lock:
            return viewer_id in self._viewers

    def _broadcast(self, message: dict[str, Any]) -> None:
        with self._viewers_lock:
            viewers = list(self._viewers.values())
        for sink, protocol_version in viewers:
            _send_compatible(sink, protocol_version, message)

    def _redraw_for(self, sink: Sink, protocol_version: int) -> None:
        proxy = self.app.virtual_esphome
        _send_compatible(sink, protocol_version, {"type": "idle", "active": proxy.idle})
        _send_compatible(sink, protocol_version, {"type": "entities", "map": proxy.entities})
        sink({"type": "sandbox", "entities": self.app.sandbox.simulated_ids()})
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

    def send_event(self, name: str, value: str) -> None:
        """Inject a device event from the browser.

        Raises:
            ValueError: If ``name`` is not an event a person can cause on a panel.
        """
        if name not in BROWSER_EVENTS:
            raise ValueError(f"Event not allowed from the preview: {name}")
        self.app.virtual_esphome.emit(name, value)
        if name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT) and value == "1":
            side = "left" if name == ESPEvent.BUTTON_LEFT else "right"
            self.app.dispatch(self.app.press_hardware_button, side)

    def reset_sandbox(self) -> None:
        """Clear simulated states without changing preview mode."""
        self.app.dispatch(self.app.reset_sandbox)

    def set_live(self, live: bool) -> None:
        """Switch between sandbox and live mode.

        Going live drops the simulated states: they would otherwise keep
        overriding the real states the live calls change.
        """
        self.app.live = live
        if live:
            self.app.dispatch(self.app.reset_sandbox)

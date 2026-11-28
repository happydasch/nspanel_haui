"""A fake app for page tests.

A page runs its full ``set_panel`` lifecycle against ``PageApp``, which records
the display commands, state listeners and service calls, so a test asserts on
what reaches the display and Home Assistant.
"""

from __future__ import annotations

from typing import Any

from custom_components.nspanel_haui.haui.mapping.color import Theme


class Entity:
    """An entity with a state and attributes; ``calls`` lists its service calls."""

    def __init__(self, state: str, attributes: dict[str, Any]) -> None:
        self.state = state
        self.attributes = attributes
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_state(self) -> str:
        return self.state

    def listen_state(self, callback: Any) -> str:
        """Register a state callback, as ``ItemProxy`` does; the page keeps the handle."""
        return f"listen:{self.state}"

    def call_service(self, service: str, **kwargs: Any) -> None:
        self.calls.append((service, kwargs))


class Blinker:
    """The notification indicator: ``refresh()`` runs the page callback it was given."""

    def __init__(self) -> None:
        self.callback: Any = None

    def refresh(self) -> None:
        if self.callback is not None:
            self.callback()


class Controller:
    """Stands in for the ESPHome and notification controllers; ``cmds`` lists the commands."""

    def __init__(self) -> None:
        self.cmds: list[str] = []
        self.blinker = Blinker()

    def send_cmd(self, command: str, value: str | list[str], force: bool = False) -> None:
        self.cmds.extend(value if isinstance(value, list) else [value])

    def has_notifications(self) -> bool:
        return False

    def set_blinker_callback(self, refresh_fn: Any) -> None:
        self.blinker.callback = refresh_fn

    def clear_blinker_callback(self) -> None:
        self.blinker.callback = None


class Device:
    """A landscape device; ``settings`` holds the device config it reports."""

    is_portrait = False

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self._settings = settings or {}
        self.device_info: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def get_locale(self) -> str:
        return "en_US"


class DeviceConfig:
    """Two navigation panels, so a page gets its previous/next header buttons."""

    def get_panels(self, nav_only: bool) -> list[str]:
        return ["home", "panel"]


class PageApp:
    """The app a page talks to: entities by id, a theme and recording controllers."""

    def __init__(
        self,
        entities: dict[str, Entity],
        *,
        controller: Controller | None = None,
        temperature_unit: str = "°C",
        device_settings: dict[str, Any] | None = None,
        portrait: bool = False,
    ) -> None:
        self.entities = entities
        self.theme = Theme()
        self.temperature_unit = temperature_unit
        self.listeners: list[tuple[str, str | None]] = []
        self.ticks: dict[str, list[Any]] = {}
        controller = controller or Controller()
        self.controller: dict[str, Any] = {"esphome": controller, "notification": controller}
        self.device = Device(device_settings)
        self.device.is_portrait = portrait
        self.device_config = DeviceConfig()
        # what the hub's camera stream was asked to do, in order
        self.camera_streams: list[dict[str, Any]] = []
        self.camera_stream_stops = 0

    @property
    def cmds(self) -> list[str]:
        return self.controller["esphome"].cmds

    def log(self, msg: str, **kwargs: Any) -> None:
        pass

    def render_template(self, template: str) -> str:
        """The hub renders a template; the fake returns the value it was given."""
        return template

    def item_exists(self, entity_id: str) -> bool:
        return entity_id in self.entities

    def get_item(self, entity_id: str) -> Entity:
        return self.entities[entity_id]

    def listen_state(self, cb: Any, entity_id: str, attribute: str | None = None, **kwargs: Any):
        self.listeners.append((entity_id, attribute))
        return f"{entity_id}:{attribute}"

    def cancel_listen_state(self, handle: str) -> None:
        pass

    def get_temperature_unit(self) -> str:
        return self.temperature_unit

    def subscribe_tick(self, period: str, cb: Any) -> None:
        self.ticks.setdefault(period, []).append(cb)

    def unsubscribe_tick(self, period: str, cb: Any) -> None:
        if cb in self.ticks.get(period, []):
            self.ticks[period].remove(cb)

    def run_in(self, cb: Any, delay: float, **kwargs: Any) -> str:
        return "timer"

    def run_every(self, cb: Any, start: Any, interval: float, **kwargs: Any) -> str:
        return "interval"

    def cancel_timer(self, handle: str) -> None:
        pass

    def start_camera_page_stream(self, **kwargs: Any) -> None:
        """Record what the camera page hands to the hub's stream."""
        self.camera_streams.append(kwargs)

    def stop_camera_page_stream(self) -> None:
        """Record that the page gave its picture area back."""
        self.camera_stream_stops += 1

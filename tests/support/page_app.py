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

    def call_service(self, service: str, **kwargs: Any) -> None:
        self.calls.append((service, kwargs))


class Controller:
    """Stands in for the ESPHome and notification controllers; ``cmds`` lists the commands."""

    def __init__(self) -> None:
        self.cmds: list[str] = []

    def send_cmd(self, command: str, value: str | list[str], force: bool = False) -> None:
        self.cmds.extend(value if isinstance(value, list) else [value])

    def has_notifications(self) -> bool:
        return False


class Device:
    """A landscape device without settings of its own."""

    is_portrait = False

    def get(self, key: str, default: Any = None) -> Any:
        return default

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
    ) -> None:
        self.entities = entities
        self.theme = Theme()
        self.temperature_unit = temperature_unit
        self.listeners: list[tuple[str, str | None]] = []
        controller = controller or Controller()
        self.controller: dict[str, Any] = {"esphome": controller, "notification": controller}
        self.device = Device()
        self.device_config = DeviceConfig()

    @property
    def cmds(self) -> list[str]:
        return self.controller["esphome"].cmds

    def log(self, msg: str, **kwargs: Any) -> None:
        pass

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

    def run_in(self, cb: Any, delay: float, **kwargs: Any) -> str:
        return "timer"

    def run_every(self, cb: Any, start: Any, interval: float, **kwargs: Any) -> str:
        return "interval"

    def cancel_timer(self, handle: str) -> None:
        pass

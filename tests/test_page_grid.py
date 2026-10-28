"""Grid page: state-keyed tile colours must be resolved and refreshed."""

from __future__ import annotations

from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.page.grid import GridPage
from nspanel_haui.haui.utils.color import parse_color_value


class _Entity:
    def __init__(self, state: str, attributes: dict) -> None:
        self.state = state
        self.attributes = attributes

    def get_state(self) -> str:
        return self.state

    def call_service(self, service: str, **kwargs) -> None:
        pass


class _Controller:
    def __init__(self) -> None:
        self.cmds: list[str] = []

    def send_cmd(self, command: str, value: str | list[str]) -> None:
        self.cmds.extend(value if isinstance(value, list) else [value])

    def has_notifications(self) -> bool:
        return False


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_locale(self) -> str:
        return "en_US"


class _DeviceConfig:
    def get_panels(self, nav_only: bool):
        return ["home", "grid"]


class _App:
    def __init__(self, entities: dict) -> None:
        self.entities = entities
        controller = _Controller()
        self.controller = {"esphome": controller, "notification": controller}
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.listeners: list[str] = []

    @property
    def cmds(self) -> list[str]:
        return self.controller["esphome"].cmds

    def log(self, msg: str, **kwargs) -> None:
        pass

    def item_exists(self, entity_id: str) -> bool:
        return entity_id in self.entities

    def get_item(self, entity_id: str):
        return self.entities[entity_id]

    def listen_state(self, cb, entity_id: str, attribute=None, **kwargs) -> str:
        handle = f"{entity_id}:{attribute}"
        self.listeners.append(handle)
        return handle

    def cancel_listen_state(self, handle: str) -> None:
        pass

    def run_in(self, cb, delay, **kwargs):
        return "timer"

    def run_every(self, cb, start, interval, **kwargs):
        return "interval"

    def cancel_timer(self, handle) -> None:
        pass


def _last_color(app: _App, component: str) -> int | None:
    prefix = f"{component}.bco="
    for cmd in reversed(app.cmds):
        if cmd.startswith(prefix):
            return int(cmd[len(prefix) :])
    return None


def test_state_keyed_background_is_resolved_and_refreshed() -> None:
    light = _Entity("off", {"friendly_name": "Lamp"})
    app = _App({"light.lamp": light})
    panel = HAUIPanel(
        app,
        {
            "type": "grid",
            "items": [
                {
                    "item": "light.lamp",
                    "back_color": {"on": "#ff0000", "off": "#00ff00"},
                }
            ],
        },
    )
    page = GridPage(app, {"page_id": 9})
    page.set_panel(panel)

    # Off -> green (not the black an unresolved dict would render).
    assert _last_color(app, "g1Btn") == parse_color_value("#00ff00")

    light.state = "on"
    page.callback_item_state("light.lamp", "state", None, None, {})
    page._flush_item_updates()

    assert _last_color(app, "g1Btn") == parse_color_value("#ff0000")

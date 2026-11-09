"""A sample Home Assistant world for rendering every panel card on the hub.

Shared by ``gen_preview_gallery.py`` (the card gallery and its PNGs) and
``tests/test_card_renders.py`` (which replays the same renders in the browser's
simulator). The hub runs for real: ``render_every_card`` boots a
``VirtualPanelHost`` on a stubbed Home Assistant holding the states below and
renders a panel of every type, and every system panel, the way the editor's
cards do.

The ``nspanel_haui`` package and the Home Assistant import stubs must be
importable first (``scripts/_ha_stubs.py`` outside pytest).
"""

from __future__ import annotations

import asyncio
import datetime
import re
import sys
import types
from collections.abc import Callable
from typing import Any

# Representative entity states the previews are built from. Each entry is
# (state, attributes); the physical entity ids double as widgets' entities.
ENTITIES: dict[str, tuple[str, dict[str, Any]]] = {
    "light.lamp": (
        "on",
        {
            "friendly_name": "Lamp",
            "brightness": 153,
            "supported_color_modes": ["color_temp", "hs"],
            "color_mode": "color_temp",
            "color_temp_kelvin": 3000,
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6500,
            "supported_features": 0,
        },
    ),
    "switch.fan": ("on", {"friendly_name": "Fan", "device_class": "switch"}),
    "switch.radio": ("off", {"friendly_name": "Radio", "device_class": "switch"}),
    "scene.movie": ("unknown", {"friendly_name": "Movie"}),
    "cover.blind": (
        "open",
        {
            "friendly_name": "Blind",
            "device_class": "blind",
            "current_position": 60,
            "supported_features": 15,
        },
    ),
    "climate.living": (
        "heat",
        {
            "friendly_name": "Living Room",
            "current_temperature": 21.5,
            "temperature": 21.0,
            "hvac_modes": ["off", "heat", "cool", "auto"],
            "fan_modes": ["auto", "low", "high"],
            "swing_modes": ["on", "off"],
            "preset_modes": ["none", "eco", "comfort"],
            "min_temp": 7,
            "max_temp": 35,
            "target_temp_step": 0.5,
            "supported_features": 441,
        },
    ),
    "media_player.tv": (
        "playing",
        {
            "friendly_name": "Living Room TV",
            "media_title": "Morning Coffee",
            "media_artist": "Lo-Fi Beats",
            "volume_level": 0.4,
            "is_volume_muted": False,
            "source": "HDMI 1",
            "source_list": ["HDMI 1", "HDMI 2", "Spotify"],
            "supported_features": 21509,
        },
    ),
    "vacuum.robot": (
        "cleaning",
        {
            "friendly_name": "Robot Vacuum",
            "battery_level": 82,
            "fan_speed": "medium",
            "fan_speed_list": ["low", "medium", "high"],
            "supported_features": 12308,
        },
    ),
    "timer.laundry": (
        "active",
        {
            "friendly_name": "Laundry",
            "duration": "0:30:00",
            "remaining": "0:12:00",
        },
    ),
    "weather.home": (
        "partlycloudy",
        {
            "friendly_name": "Home",
            "temperature": 18.0,
            "temperature_unit": "°C",
            "humidity": 55,
            "pressure": 1013,
            "pressure_unit": "hPa",
            "wind_speed": 12,
            "wind_bearing": 180,
        },
    ),
    "sensor.outside": (
        "18.5",
        {
            "friendly_name": "Outside",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        },
    ),
    "input_select.mode": (
        "Home",
        {
            "friendly_name": "House Mode",
            "options": [
                "Home",
                "Away",
                "Night",
                "Movie",
                "Guest",
                "Holiday",
                "Custom",
                "Other",
                "Test",
                "Extra 10",
                "Extra 11",
                "Extra 12",
            ],
        },
    ),
    "alarm_control_panel.home": (
        "disarmed",
        {
            "friendly_name": "Alarm",
            "code_format": "number",
            "changed_by": None,
        },
    ),
}

# The firmware's own entities, by (domain, ESPHome original_name). The hub
# resolves them through the entity registry (settings, qr and device pages).
FIRMWARE_ENTITIES: list[tuple[str, str, str]] = [
    ("sensor", "Temperature", "sensor.kitchen_temperature"),
    ("sensor", "Brightness", "sensor.kitchen_brightness"),
    ("sensor", "Uptime", "sensor.kitchen_uptime"),
    ("sensor", "RSSI", "sensor.kitchen_rssi"),
    ("number", "Display Model", "number.kitchen_display_model"),
    ("number", "Brightness Full", "number.kitchen_brightness_full"),
    ("number", "Brightness Dimmed", "number.kitchen_brightness_dimmed"),
    ("number", "Duration Dimming", "number.kitchen_duration_dimming"),
    ("number", "Timeout Dimming", "number.kitchen_timeout_dimming"),
    ("number", "Timeout Display-Off", "number.kitchen_timeout_display_off"),
    ("number", "Temperature Correction", "number.kitchen_temperature_correction"),
    ("switch", "Screen Power", "switch.kitchen_screen_power"),
    ("switch", "Use Button Interaction", "switch.kitchen_use_button_interaction"),
    ("switch", "Use Auto-Dimming", "switch.kitchen_use_auto_dimming"),
    ("switch", "Use Auto Display-Off", "switch.kitchen_use_auto_display_off"),
    ("switch", "Relay Left", "switch.kitchen_relay_left"),
    ("switch", "Relay Right", "switch.kitchen_relay_right"),
    ("switch", "Use Relay Left", "switch.kitchen_use_relay_left"),
    ("switch", "Use Relay Right", "switch.kitchen_use_relay_right"),
]

FIRMWARE_STATES: dict[str, tuple[str, dict[str, Any]]] = {
    "sensor.kitchen_temperature": (
        "21.5",
        {
            "friendly_name": "Temperature",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        },
    ),
    "sensor.kitchen_brightness": ("60", {"friendly_name": "Brightness"}),
    "sensor.kitchen_uptime": ("3600", {"friendly_name": "Uptime"}),
    "sensor.kitchen_rssi": ("-58", {"friendly_name": "RSSI"}),
    "number.kitchen_brightness_full": (
        "60",
        {"friendly_name": "Brightness Full", "min": 0, "max": 100, "step": 1},
    ),
    "number.kitchen_brightness_dimmed": (
        "30",
        {"friendly_name": "Brightness Dimmed", "min": 0, "max": 100, "step": 1},
    ),
    "switch.kitchen_use_auto_dimming": ("off", {"friendly_name": "Use Auto-Dimming"}),
    "switch.kitchen_use_auto_display_off": ("off", {"friendly_name": "Use Auto Display-Off"}),
    "switch.kitchen_screen_power": ("on", {"friendly_name": "Screen Power"}),
}

ITEM_GRID = [
    {"item": "light.lamp", "name": "Lamp", "icon": "mdi:lightbulb", "show_power_button": True},
    {"item": "switch.fan", "name": "Fan", "icon": "mdi:fan", "show_power_button": True},
    {"item": "cover.blind", "name": "Blind", "icon": "mdi:blinds-horizontal"},
    {"item": "climate.living", "name": "Living", "icon": "mdi:thermostat"},
    {"item": "media_player.tv", "name": "TV", "icon": "mdi:television"},
    {"item": "scene.movie", "name": "Movie", "icon": "mdi:movie-open"},
]

PANELS: list[dict[str, Any]] = [
    {"type": "grid", "key": "grid_0", "title": "Rooms", "items": ITEM_GRID},
    {"type": "row", "key": "row_0", "title": "Devices", "items": ITEM_GRID[:5]},
    {"type": "light", "key": "light_0", "title": "Lamp", "item": {"item": "light.lamp"}},
    {"type": "climate", "key": "climate_0", "title": "Climate", "item": {"item": "climate.living"}},
    {"type": "media", "key": "media_0", "title": "Media", "item": {"item": "media_player.tv"}},
    {"type": "cover", "key": "cover_0", "title": "Blind", "item": {"item": "cover.blind"}},
    {"type": "vacuum", "key": "vacuum_0", "title": "Vacuum", "item": {"item": "vacuum.robot"}},
    {"type": "timer", "key": "timer_0", "title": "Timer", "item": {"item": "timer.laundry"}},
    {"type": "weather", "key": "weather_0", "title": "Weather", "item": {"item": "weather.home"}},
    {
        "type": "clock",
        "key": "clock_0",
        "title": "Clock",
        "items": [
            {"item": "sensor.outside", "name": "Outside", "icon": "mdi:thermometer"},
            {
                "item": "sensor.kitchen_temperature",
                "name": "Inside",
                "icon": "mdi:home-thermometer",
            },
        ],
    },
    {"type": "clocktwo", "key": "clocktwo_0", "title": "Word Clock"},
    {"type": "qr", "key": "qr_0", "title": "QR", "qr_text": "https://example.com"},
    {
        "type": "alarm",
        "key": "alarm_0",
        "title": "Alarm",
        "item": {"item": "alarm_control_panel.home"},
    },
]


class _State:
    def __init__(self, state: str, attributes: dict[str, Any]) -> None:
        self.state = state
        self.attributes = dict(attributes)
        self.last_updated = datetime.datetime.now(datetime.UTC)


class _Services:
    async def async_call(self, *args: Any, **kwargs: Any) -> None:
        return None


class SampleHass:
    """Home Assistant as the hub sees it: the sample states, nothing else."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        states = {eid: _State(*value) for eid, value in {**ENTITIES, **FIRMWARE_STATES}.items()}
        self.loop = loop
        self.states = types.SimpleNamespace(
            get=states.get,
            async_entity_ids=lambda domain: [e for e in states if e.startswith(f"{domain}.")],
        )
        self.services = _Services()
        self.bus = types.SimpleNamespace(
            async_listen=lambda *a, **k: lambda: None,
            async_fire=lambda *a, **k: None,
        )
        self.config = types.SimpleNamespace(
            units=types.SimpleNamespace(temperature_unit="°C"), time_zone="UTC"
        )
        self.data: dict[str, Any] = {}

    def async_add_executor_job(self, fn: Callable, *args: Any) -> Any:
        return self.loop.run_in_executor(None, fn, *args)


def _slugify(text: str, separator: str = "_") -> str:
    slug = re.sub(r"[^a-z0-9]+", separator, (text or "").lower()).strip(separator)
    return slug or "unknown"


def install_runtime_stubs(
    loop: asyncio.AbstractEventLoop,
    setitem: Callable[[Any, str, Any], None] = lambda target, key, value: target.__setitem__(
        key, value
    ),
    setattr_: Callable[[Any, str, Any], None] = setattr,
) -> None:
    """Stub the Home Assistant helpers the hub imports at call time.

    ``setitem``/``setattr_`` default to plain assignment; tests pass
    ``monkeypatch``'s so the stubs are undone afterwards.
    """
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = lambda hass, entity_id, cb: lambda: None  # type: ignore[attr-defined]
    event.async_call_later = lambda hass, delay, cb: loop.call_later(delay, cb, None).cancel  # type: ignore[attr-defined]
    event.async_track_time_interval = lambda hass, cb, interval: lambda: None  # type: ignore[attr-defined]
    # The firmware's own entities, which the settings, QR and About pages resolve.
    entries = {
        eid: types.SimpleNamespace(
            domain=domain,
            platform="esphome",
            original_name=name,
            disabled_by=None,
            device_id=None,
        )
        for domain, name, eid in FIRMWARE_ENTITIES
    }
    registry = types.ModuleType("homeassistant.helpers.entity_registry")
    registry.async_get = lambda hass: types.SimpleNamespace(entities=entries)  # type: ignore[attr-defined]
    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.now = lambda: datetime.datetime.now(datetime.UTC)  # type: ignore[attr-defined]
    core = types.ModuleType("homeassistant.core")
    core.callback = lambda fn: fn  # type: ignore[attr-defined]
    for name, module in (
        ("homeassistant.helpers.event", event),
        ("homeassistant.helpers.entity_registry", registry),
        ("homeassistant.util.dt", dt_util),
        ("homeassistant.core", core),
    ):
        setitem(sys.modules, name, module)
    setattr_(sys.modules["homeassistant.helpers"], "event", event)
    setattr_(sys.modules["homeassistant.helpers"], "entity_registry", registry)
    util = sys.modules["homeassistant.util"]
    setattr_(util, "dt", dt_util)
    if not hasattr(util, "slugify"):
        setattr_(util, "slugify", _slugify)


def render_every_card(
    loop: asyncio.AbstractEventLoop,
    display_model: str,
    device_settings: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Render every panel card for a device of ``display_model`` (``eu``, ``us``).

    User cards render their sample panel (or a bare panel of the type), system
    cards the device's configured panel by key, as the editor sends them.
    ``device_settings`` are stored device settings laid over the sample ones
    (for example ``color_overrides``).

    Returns:
        Card name (type key or system key) -> ``{page, before, commands}``.
    """
    import custom_components.nspanel_haui as nspanel_haui
    from custom_components.nspanel_haui.haui.mapping.panel import (
        get_system_panel_entries,
        get_user_panel_type_descriptors,
    )
    from custom_components.nspanel_haui.web.preview.virtual_panel import VirtualPanelHost

    store = {
        "devices": {
            "kitchen": {
                "config": {
                    "home_panel": "grid_0",
                    "display_model": display_model,
                    **(device_settings or {}),
                },
                "panels": PANELS,
            }
        }
    }
    config = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]}, store, device_name="kitchen"
    )
    host = VirtualPanelHost(SampleHass(loop), "kitchen", config)
    samples = {panel["type"]: panel for panel in PANELS}

    async def by_key(key: str) -> dict[str, Any]:
        return await host.async_render(await host.async_configured_panel(key))

    async def every_card() -> dict[str, dict[str, Any]]:
        cards = {
            d["type_key"]: host.async_render(
                samples.get(d["type_key"], {"type": d["type_key"], "key": d["type_key"]})
            )
            for d in get_user_panel_type_descriptors()
        }
        for entry in get_system_panel_entries():
            cards[entry["key"]] = by_key(entry["key"])
        return dict(zip(cards, await asyncio.gather(*cards.values()), strict=True))

    def run(coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)

    run(host.async_start())
    try:
        return run(every_card())
    finally:
        run(host.async_stop())

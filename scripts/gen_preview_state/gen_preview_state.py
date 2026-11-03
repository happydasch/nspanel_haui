#!/usr/bin/env python3
"""Snapshot the hub's real display output for every panel page.

The editor's panel cards are drawn by the shared Nextion simulator
(frontend/previews/simulator.js). The HMI hides almost every widget in each
page's Preinitialize code and the hub later reveals them and sets their texts,
values and colours; so a preview that only guessed at visibility looks empty.

This script boots the real hub in the editor's virtual-panel sandbox, opens each
panel page and records exactly what the hub sends to the display, then writes
``custom_components/nspanel_haui/frontend/virtual/preview_state.json``:

    {"<page id>": {"page": <page id>, "commands": ["vis ...", "..."]}}

The simulator replays those commands, so previews show the hub's real colours,
default values and control visibility without starting a live session.

Run it after changing page rendering; ``--check`` (run by the test suite) fails
when the committed snapshot is out of date.

Usage::

    python scripts/gen_preview_state/gen_preview_state.py [--check]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "custom_components"))
sys.path.insert(0, str(ROOT / "scripts"))

import _ha_stubs  # noqa: E402,F401  (installs the Home Assistant stubs)

OUT_FILE = (
    ROOT / "custom_components" / "nspanel_haui" / "frontend" / "virtual" / "preview_state.json"
)

# Fixed instant so time/date widgets render the same on every machine
# (a Monday, so the clock page reads "Mon 24").
FROZEN_NOW = datetime.datetime(2024, 6, 24, 10, 8, 0, tzinfo=datetime.UTC)

DEVICE_INFO = {
    "name": "kitchen",
    "friendly_name": "Kitchen Panel",
    "ip": "192.168.1.50",
    "ssid": "HomeNet",
    "rssi": -58,
    "uptime": 3600,
    "yaml_version": "0.4.5",
    "tft_version": "0.4.5",
    "firmware_variant": "universal",
}

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
    ("sensor", "Last Interaction", "sensor.kitchen_last_interaction"),
    ("number", "Display Model", "number.kitchen_display_model"),
    ("number", "Brightness Full", "number.kitchen_brightness_full"),
    ("number", "Brightness Dimmed", "number.kitchen_brightness_dimmed"),
    ("number", "Duration Dimming", "number.kitchen_duration_dimming"),
    ("number", "Timeout Dimming", "number.kitchen_timeout_dimming"),
    ("number", "Timeout Display-Off", "number.kitchen_timeout_display_off"),
    ("number", "Timeout Page", "number.kitchen_timeout_page"),
    ("number", "Temperature Correction", "number.kitchen_temperature_correction"),
    ("switch", "Screen Power", "switch.kitchen_screen_power"),
    ("switch", "Use Button Interaction", "switch.kitchen_use_button_interaction"),
    ("switch", "Use Auto-Dimming", "switch.kitchen_use_auto_dimming"),
    ("switch", "Use Auto-Page", "switch.kitchen_use_auto_page"),
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
    "sensor.kitchen_last_interaction": ("0", {"friendly_name": "Last Interaction"}),
    "number.kitchen_brightness_full": (
        "60",
        {"friendly_name": "Brightness Full", "min": 0, "max": 100, "step": 1},
    ),
    "number.kitchen_brightness_dimmed": (
        "30",
        {"friendly_name": "Brightness Dimmed", "min": 0, "max": 100, "step": 1},
    ),
    "switch.kitchen_use_auto_dimming": ("off", {"friendly_name": "Use Auto-Dimming"}),
    "switch.kitchen_use_auto_page": ("off", {"friendly_name": "Use Auto-Page"}),
    "switch.kitchen_use_auto_display_off": ("off", {"friendly_name": "Use Auto Display-Off"}),
    "switch.kitchen_screen_power": ("on", {"friendly_name": "Screen Power"}),
}

ITEM_GRID = [
    {"item": "light.lamp", "name": "Lamp", "icon": "mdi:lightbulb"},
    {"item": "switch.fan", "name": "Fan", "icon": "mdi:fan"},
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

# Targets to snapshot: (label, open_panel key, extra kwargs, expected page id).
# The system page (0) is not opened: opening it shows the "waiting for
# connection" failure text, while the HMI's own defaults are what a booting
# device displays. Page 1 (blank) is captured for completeness.
TARGETS: list[tuple[str, str, dict[str, Any], int]] = [
    ("grid", "grid_0", {}, 9),
    ("row", "row_0", {}, 10),
    ("light", "light_0", {}, 13),
    ("climate", "climate_0", {}, 16),
    ("media", "media_0", {}, 14),
    ("cover", "cover_0", {}, 18),
    ("vacuum", "vacuum_0", {}, 15),
    ("timer", "timer_0", {}, 12),
    ("weather", "weather_0", {}, 6),
    ("clock", "clock_0", {}, 7),
    ("clocktwo", "clocktwo_0", {}, 8),
    ("qr", "qr_0", {}, 11),
    ("alarm", "alarm_0", {}, 17),
    ("blank", "sys_blank", {}, 1),
    ("about", "sys_about", {}, 2),
    ("settings", "sys_settings", {}, 3),
    ("notify", "popup_notify", {"item_id": "notify.kitchen"}, 4),
    (
        "select",
        "popup_select",
        {
            "items": ["Home", "Away", "Night", "Movie"],
            "selected": "Home",
        },
        5,
    ),
]


# ---------------------------------------------------------------------------
# Home Assistant stubs
# ---------------------------------------------------------------------------


class _State:
    def __init__(self, state: str, attributes: dict[str, Any]) -> None:
        self.state = state
        self.attributes = dict(attributes)
        self.last_updated = FROZEN_NOW


class _Services:
    async def async_call(self, *args: Any, **kwargs: Any) -> None:
        return None


class _Hass:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        states = {eid: _State(*value) for eid, value in {**ENTITIES, **FIRMWARE_STATES}.items()}
        self.loop = loop
        self._states = states
        self.states = types.SimpleNamespace(get=states.get)
        self.services = _Services()
        self.bus = types.SimpleNamespace(
            async_listen=lambda *a, **k: lambda: None,
            async_fire=lambda *a, **k: None,
        )
        self.config = types.SimpleNamespace(
            units=types.SimpleNamespace(temperature_unit="°C"), time_zone="UTC"
        )
        self.data: dict[str, Any] = {}

    def async_add_executor_job(self, fn, *args):
        return self.loop.run_in_executor(None, fn, *args)


class _EntityEntry:
    def __init__(self, domain: str, original_name: str) -> None:
        self.domain = domain
        self.platform = "esphome"
        self.original_name = original_name
        self.disabled_by = None
        self.device_id = None


class _EntityRegistry:
    def __init__(self, entries: dict[str, _EntityEntry]) -> None:
        self.entities = entries


def _install_runtime_stubs(loop: asyncio.AbstractEventLoop) -> None:
    """Stub the HA helpers the haui core imports at call time."""
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = lambda hass, entity_id, cb: lambda: None
    event.async_call_later = lambda hass, delay, cb: loop.call_later(delay, cb, None).cancel
    event.async_track_time_interval = lambda hass, cb, interval: lambda: None
    sys.modules["homeassistant.helpers.event"] = event

    entries = {eid: _EntityEntry(domain, name) for domain, name, eid in FIRMWARE_ENTITIES}
    registry = types.ModuleType("homeassistant.helpers.entity_registry")
    registry.async_get = lambda hass: _EntityRegistry(entries)
    sys.modules["homeassistant.helpers.entity_registry"] = registry

    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.now = lambda: FROZEN_NOW
    sys.modules["homeassistant.util.dt"] = dt_util
    util = sys.modules.get("homeassistant.util")
    if util is not None:
        util.dt = dt_util

    core = types.ModuleType("homeassistant.core")
    core.callback = lambda fn: fn
    sys.modules["homeassistant.core"] = core

    helpers = sys.modules.get("homeassistant.helpers")
    if helpers is not None:
        helpers.event = event
        helpers.entity_registry = registry

    # The hub slugifies device names with HA's util.slugify.
    import re

    util = sys.modules.get("homeassistant.util")
    if util is not None and not hasattr(util, "slugify"):

        def _slugify(text, separator="_"):
            if not text:
                return ""
            slug = re.sub(r"[^a-z0-9]+", separator, text.lower()).strip(separator)
            return slug or "unknown"

        util.slugify = _slugify


def _freeze_time() -> None:
    """Pin every page's clock so the snapshot is reproducible."""

    class _FixedDateTime(datetime.datetime):
        # Self-reference so both import styles work: `datetime.now()` (class
        # binding) and `datetime.datetime.now()` (module binding).
        datetime = None

        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return FROZEN_NOW.astimezone(tz) if tz else FROZEN_NOW

    _FixedDateTime.datetime = _FixedDateTime

    from nspanel_haui.haui.page import clock, clocktwo, media, timer, weather
    from nspanel_haui.haui.utils import datetime as datetime_util

    for module in (clock, clocktwo, media, timer, weather):
        module.datetime = _FixedDateTime
    datetime_util._get_now = lambda timezone=None: FROZEN_NOW


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------


def _config() -> dict[str, Any]:
    import nspanel_haui

    store = {
        "devices": {
            "kitchen": {
                "config": {
                    "home_panel": "grid_0",
                    "display_model": "eu",
                    "brightness_full": 60,
                    "brightness_dimmed": 30,
                },
                "panels": PANELS,
            }
        }
    }
    return nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]}, store, device_name="kitchen"
    )


def _wait(cond, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return
        time.sleep(0.01)
    raise TimeoutError("preview snapshot condition not met")


def capture(loop: asyncio.AbstractEventLoop) -> dict[str, dict[str, Any]]:
    """Open each page and record the hub's page switch and commands.

    The sink accumulates output per page id (attribution follows the most
    recent page switch), so the boot render and every navigation are captured
    without late renders from a previous page leaking into the next one.
    """
    from nspanel_haui.virtual_panel import VirtualPanelSession

    by_page: dict[int, list[str]] = {}
    current = {"page": None}
    pending: list[str] = []

    # The hub draws a page's widgets and then switches to it, so a burst of
    # commands followed by a page switch belongs to the page being shown.
    def sink(message: dict[str, Any]) -> None:
        nonlocal pending
        if message["type"] == "page":
            page_id = int(message["page"])
            by_page.setdefault(page_id, []).extend(pending)
            pending = []
            current["page"] = page_id
        elif message["type"] == "commands":
            if current["page"] is not None:
                by_page[current["page"]].extend(message["commands"])
            else:
                pending.extend(message["commands"])

    session = VirtualPanelSession(_Hass(loop), "kitchen", _config(), sink)
    session.app.live = False

    def run(coro):
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)

    # Booting the device renders the home panel (grid).
    run(session.async_start())
    _wait(lambda: bool(by_page.get(9)))

    for label, key, kwargs, expected in TARGETS:
        before = len(by_page.get(expected, []))
        try:
            navigation = session.app.controller["navigation"]
            run(
                session.app.async_run_on_worker(
                    lambda k=key, kw=kwargs, nav=navigation: nav.open_panel(k, **kw)
                )
            )
            _wait(lambda pid=expected, n=before: len(by_page.get(pid, [])) > n)
            # Let the page settle so its delayed renders land before the next
            # navigation attributes them elsewhere.
            time.sleep(0.4)
        except Exception as err:  # noqa: BLE001 - a page we cannot render is skipped
            print(f"  ! {label}: {err}", file=sys.stderr)
            continue
        print(f"  {label:10s} -> page {expected:2d}  ({len(by_page[expected])} commands)")

    run(session.async_stop())

    return {
        str(page_id): {"page": page_id, "commands": commands}
        for page_id, commands in sorted(by_page.items())
        # Page 0 only renders transient connection states; the HMI's own
        # defaults ("Waiting for Initialization" + QR) are the useful preview.
        if commands and page_id != 0
    }


def _render(snapshots: dict[str, dict[str, Any]]) -> str:
    ordered = {str(pid): snapshots[str(pid)] for pid in sorted(int(p) for p in snapshots)}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"


def _build() -> str:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        _install_runtime_stubs(loop)
        import nspanel_haui.haui.page  # noqa: F401  (import before freezing time)

        _freeze_time()
        snapshots = capture(loop)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
    return _render(snapshots)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="fail when the snapshot is out of date"
    )
    args = parser.parse_args(argv)

    text = _build()
    if args.check:
        if not OUT_FILE.exists() or OUT_FILE.read_text(encoding="utf-8") != text:
            print(f"{OUT_FILE.relative_to(ROOT)} is out of date", file=sys.stderr)
            print("Run: python scripts/gen_preview_state/gen_preview_state.py", file=sys.stderr)
            return 1
        print(f"✓ {OUT_FILE.relative_to(ROOT)} is up to date")
        return 0
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

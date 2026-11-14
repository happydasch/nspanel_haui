#!/usr/bin/env python3
"""Capture the README's editor screenshots into ``docs/assets/readme/``.

The screenshots show the real editor: the script starts a throwaway Home
Assistant from the development virtual environment (``.venv_ha``,
``docs/develop/development.md``) in a temporary directory, on its own port so
it never touches a development instance on 8123. Home Assistant's ``demo``
integration provides the entities; the hub gets the six devices in ``DEVICES``
(landscape and portrait, dark and light display themes). The devices have no
ESPHome node, so the editor shows them offline, but every preview is the hub's
own render. After onboarding a test user, ``capture_editor.mjs`` captures each
screen in ``SHOTS`` with headless Chrome in Home Assistant's light or dark
theme.

Usage::

    python -m scripts.readme_images.gen_editor_screenshots [--hass PATH] [--chrome PATH]
    python -m scripts.readme_images.gen_editor_screenshots --only editor-settings
"""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.preview_gallery import gen_preview_gallery as gallery

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / "docs" / "assets" / "readme"
INTEGRATION = ROOT / "custom_components" / "nspanel_haui"
WIDTH, HEIGHT = 1600, 1000
START_TIMEOUT = 300
HUB_ENTRY_ID = "01JREADMEDEMOHUB000000000A"

CONFIGURATION_YAML = """\
homeassistant:
  name: Home
  latitude: 52.52
  longitude: 13.40
  elevation: 34
  unit_system: metric
  time_zone: Europe/Berlin
  currency: EUR
  country: DE
  language: en
frontend:
config:
demo:
logger:
  default: warning
"""


def _tile(entity: str, name: str, icon: str, color: str) -> dict[str, str]:
    return {
        "item": entity,
        "name": name,
        "icon": icon,
        "color": "#ffffff",
        "back_color": color,
        "text_color": "#ffffff",
    }


def _entity_panel(panel_type: str, key: str, title: str, entity: str) -> dict[str, Any]:
    return {"type": panel_type, "key": key, "title": title, "item": {"item": entity}, "items": []}


# Device name -> settings and panels in the panel store; every entity is one of the
# demo integration's.
DEVICES: dict[str, dict[str, Any]] = {
    "Living Room": {
        "config": {"home_panel": "grid_0", "idle_panel": "clock_0", "display_model": "eu"},
        "panels": [
            {
                "type": "grid",
                "key": "grid_0",
                "title": "Living Room",
                "items": [
                    _tile("light.living_room_rgbww_lights", "Lights", "mdi:lightbulb", "#e6cf1c"),
                    _tile("cover.living_room_window", "Blinds", "mdi:blinds-horizontal", "#f2801d"),
                    _tile("media_player.living_room", "Music", "mdi:music", "#e58fce"),
                    _tile(
                        "vacuum.demo_vacuum_0_ground_floor", "Vacuum", "mdi:robot-vacuum", "#63c31e"
                    ),
                    _tile("fan.living_room_fan", "Fan", "mdi:fan", "#2f9be0"),
                    _tile("climate.hvac", "Climate", "mdi:snowflake", "#6b63e6"),
                ],
            },
            _entity_panel("light", "light_0", "Lights", "light.living_room_rgbww_lights"),
            _entity_panel("media", "media_0", "Music", "media_player.living_room"),
            _entity_panel("climate", "climate_0", "Climate", "climate.hvac"),
            _entity_panel("cover", "cover_0", "Blinds", "cover.living_room_window"),
            {
                **_entity_panel("weather", "weather_0", "Weather", "weather.demo_weather_south"),
                "background": "summer",
            },
            {
                **_entity_panel("clock", "clock_0", "Clock", "weather.demo_weather_south"),
                "background": "autumn",
                "show_in_navigation": False,
            },
            {
                "type": "qr",
                "key": "qr_0",
                "title": "Guest Wi-Fi",
                "essid": "Guests",
                "password": "welcome-home",
                "items": [],
                "show_in_navigation": False,
            },
            {
                "type": "light",
                "key": "popup_light",
                "title": "Light",
                "show_kelvin": True,
                "items": [],
            },
        ],
    },
    "Kitchen": {
        "config": {
            "home_panel": "row_0",
            "display_model": "eu",
            "theme_id": "light",
            "theme_variant": "light",
        },
        "panels": [
            {
                "type": "row",
                "key": "row_0",
                "title": "Kitchen",
                "items": [
                    {"item": "light.kitchen_lights", "name": "Kitchen lights"},
                    {"item": "cover.kitchen_window", "name": "Window"},
                    {"item": "lock.kitchen_door", "name": "Back door"},
                    {"item": "switch.decorative_lights", "name": "Decoration"},
                    {"item": "media_player.kitchen", "name": "Radio"},
                ],
            },
            {"type": "timer", "key": "timer_0", "title": "Timer", "items": []},
        ],
    },
    "Bedroom": {
        "config": {"home_panel": "clock_0", "display_model": "us"},
        "panels": [
            {
                **_entity_panel("clock", "clock_0", "Clock", "weather.demo_weather_south"),
                "background": "dog_1",
            },
            _entity_panel("light", "light_0", "Bed light", "light.bed_light"),
        ],
    },
    "Office": {
        "config": {"home_panel": "light_0", "display_model": "eu"},
        "panels": [
            _entity_panel("light", "light_0", "Office", "light.office_rgbw_lights"),
            {
                **_entity_panel("weather", "weather_0", "Weather", "weather.demo_weather_north"),
                "background": "winter",
            },
        ],
    },
    "Hallway": {
        "config": {"home_panel": "alarm_0", "display_model": "us"},
        "panels": [
            _entity_panel("alarm", "alarm_0", "Security", "alarm_control_panel.security"),
            {
                "type": "grid",
                "key": "grid_0",
                "title": "Hallway",
                "items": [
                    _tile("lock.front_door", "Front door", "mdi:door-closed-lock", "#2f9be0"),
                    _tile(
                        "light.entrance_color_white_lights", "Entrance", "mdi:lightbulb", "#e6cf1c"
                    ),
                    _tile("cover.garage_door", "Garage", "mdi:garage", "#f2801d"),
                    _tile(
                        "vacuum.demo_vacuum_1_first_floor", "Vacuum", "mdi:robot-vacuum", "#63c31e"
                    ),
                ],
            },
        ],
    },
    "Guest Room": {
        "config": {"home_panel": "media_0", "display_model": "eu"},
        "panels": [
            _entity_panel("media", "media_0", "Music", "media_player.lounge_room"),
            _entity_panel("climate", "climate_0", "Heating", "climate.heatpump"),
        ],
    },
}

# (file name, colour scheme, editor route, label of a button to click first)
SHOTS: list[tuple[str, str, str, str | None]] = [
    ("editor-fleet-light", "light", "#/", None),
    ("editor-fleet-dark", "dark", "#/", None),
    ("editor-device-preview-light", "light", "#/device/Living%20Room", None),
    ("editor-device-preview-dark", "dark", "#/device/Bedroom", None),
    ("editor-panels-light", "light", "#/device/Living%20Room/panels", None),
    ("editor-panels-dark", "dark", "#/device/Living%20Room/panels", None),
    ("editor-edit-panel-light", "light", "#/device/Living%20Room/panel/grid_0", None),
    ("editor-edit-panel-dark", "dark", "#/device/Hallway/panel/grid_0", None),
    ("editor-settings-light", "light", "#/device/Living%20Room/panels", "Settings"),
    ("editor-settings-dark", "dark", "#/device/Living%20Room/panels", "Settings"),
]


def _store_file(key: str, data: dict[str, Any], version: int = 1, minor: int = 1) -> str:
    return json.dumps({"version": version, "minor_version": minor, "key": key, "data": data})


def write_config(config: Path, port: int) -> None:
    """Write a Home Assistant config directory with the hub already set up.

    The HTTP settings go to the store, not YAML: Home Assistant 2026.11 imports a
    YAML ``http:`` block as a pending change, which asks for confirmation and
    reverts to port 8123 when nobody confirms it.
    """
    now = datetime.now(UTC).isoformat()
    store = config / ".storage"
    store.mkdir(parents=True)
    (config / "custom_components").mkdir()
    (config / "custom_components" / "nspanel_haui").symlink_to(INTEGRATION)
    (config / "configuration.yaml").write_text(CONFIGURATION_YAML)
    http = {
        "server_port": port,
        "cors_allowed_origins": ["https://cast.home-assistant.io"],
        "login_attempts_threshold": -1,
        "ip_ban_enabled": True,
        "ssl_profile": "intermediate_v6",
        "use_x_frame_options": True,
        "created_at": now,
        "error": None,
        "error_message": None,
    }
    (store / "http").write_text(
        _store_file(
            "http", {"stable": http, "pending": None, "yaml_migration_done": True}, version=3
        )
    )
    entry = {
        "created_at": now,
        "modified_at": now,
        "data": {"devices": [{"name": name} for name in DEVICES], "name": "NSPanel HAUI Hub"},
        "disabled_by": None,
        "discovery_keys": {},
        "domain": "nspanel_haui",
        "entry_id": HUB_ENTRY_ID,
        "minor_version": 1,
        "options": {},
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "subentries": [],
        "title": "NSPanel HAUI Hub",
        "unique_id": "NSPanel HAUI Hub",
        "version": 1,
    }
    (store / "core.config_entries").write_text(
        _store_file("core.config_entries", {"entries": [entry]}, minor=5)
    )
    panels_key = f"nspanel_haui.{HUB_ENTRY_ID}_panels"
    (store / panels_key).write_text(
        _store_file(
            panels_key,
            {
                "version": 1,
                "device_order": list(DEVICES),
                "themes": {},
                "devices": {
                    name: {
                        "config": {"enabled": True, **device["config"]},
                        "panels": device["panels"],
                    }
                    for name, device in DEVICES.items()
                },
            },
        )
    )


class HomeAssistant:
    """The REST and auth API of the throwaway instance."""

    def __init__(self, port: int) -> None:
        self.base = f"http://127.0.0.1:{port}"
        self.token: str | None = None

    def call(self, path: str, data: dict | None = None, form: bool = False) -> Any:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if data is not None and form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=body, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"null")

    def wait_until(self, ready: Any, what: str, process: subprocess.Popen, log: Path) -> None:
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise SystemExit(f"Home Assistant exited ({process.returncode}):\n{_tail(log)}")
            try:
                if ready():
                    return
            except urllib.error.URLError, ConnectionError:
                pass
            time.sleep(1)
        raise SystemExit(f"Home Assistant: {what} not reached in {START_TIMEOUT} s:\n{_tail(log)}")

    def onboard(self) -> dict[str, Any]:
        """Create the owner with a throwaway password and finish onboarding; return its tokens."""
        client = f"{self.base}/"
        user = self.call(
            "/api/onboarding/users",
            {
                "client_id": client,
                "name": "Demo",
                "username": "demo",
                "password": secrets.token_urlsafe(18),
                "language": "en",
            },
        )
        tokens = self.call(
            "/auth/token",
            {"grant_type": "authorization_code", "code": user["auth_code"], "client_id": client},
            form=True,
        )
        self.token = tokens["access_token"]
        self.call("/api/onboarding/core_config", {})
        self.call("/api/onboarding/analytics", {})
        self.call(
            "/api/onboarding/integration",
            {"client_id": client, "redirect_uri": f"{client}?auth_callback=1"},
        )
        return tokens

    def running(self) -> bool:
        return self.call("/api/config")["state"] == "RUNNING"

    def tidy(self) -> None:
        """Skip the demo's updates and dismiss its notifications: no badges in the sidebar."""
        for state in self.call("/api/states"):
            if state["entity_id"].startswith("update.") and state["state"] == "on":
                self.call("/api/services/update/skip", {"entity_id": state["entity_id"]})
        self.call("/api/services/persistent_notification/dismiss_all", {})


def _tail(log: Path, lines: int = 30) -> str:
    return "\n".join(log.read_text(errors="replace").splitlines()[-lines:])


def capture(chrome: str, hass: HomeAssistant, tokens: dict[str, Any], shots: list[tuple]) -> None:
    """Capture ``shots`` (entries of ``SHOTS``) into ``TARGET`` with ``capture_editor.mjs``."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Needs Node 22+ (capture_editor.mjs drives Chrome over DevTools)")
    jobs = {
        "base": hass.base,
        "tokens": tokens,
        "width": WIDTH,
        "height": HEIGHT,
        "shots": [
            {"hash": route, "scheme": scheme, "path": str(TARGET / f"{name}.png"), "click": click}
            for name, scheme, route, click in shots
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(jobs, handle)
    try:
        subprocess.run([node, str(HERE / "capture_editor.mjs"), chrome, handle.name], check=True)
    finally:
        Path(handle.name).unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the README's editor screenshots.")
    parser.add_argument(
        "--hass",
        default=str(ROOT / ".venv_ha" / "bin" / "hass"),
        help="Home Assistant executable (default: .venv_ha/bin/hass)",
    )
    parser.add_argument("--chrome", help="Chrome or Chromium executable")
    parser.add_argument("--port", type=int, default=8124, help="port of the throwaway instance")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="PREFIX",
        help="capture only the shots whose file name starts with one of these "
        "(e.g. editor-settings)",
    )
    args = parser.parse_args()
    if not Path(args.hass).exists():
        raise SystemExit(f"{args.hass} not found: set up .venv_ha (docs/develop/development.md)")
    shots = [shot for shot in SHOTS if not args.only or shot[0].startswith(tuple(args.only))]
    if not shots:
        raise SystemExit(f"No shot matches {args.only}: {[name for name, *_ in SHOTS]}")
    chrome = gallery.find_chrome(args.chrome)
    hass = HomeAssistant(args.port)

    with tempfile.TemporaryDirectory(prefix="haui-editor-ha-") as tmp:
        config = Path(tmp) / "config"
        write_config(config, args.port)
        log = Path(tmp) / "home-assistant.out"
        with log.open("w") as out:
            process = subprocess.Popen(
                [args.hass, "-c", str(config)], stdout=out, stderr=subprocess.STDOUT
            )
        try:
            hass.wait_until(lambda: hass.call("/api/onboarding") is not None, "HTTP", process, log)
            tokens = hass.onboard()
            hass.wait_until(hass.running, "running state", process, log)
            hass.tidy()
            capture(chrome, hass, tokens, shots)
        finally:
            process.terminate()
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()

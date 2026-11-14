"""Representative entities shared by the editor previews and the card gallery."""

from __future__ import annotations

import datetime
from typing import Any

# Each entry is (state, attributes); these entity IDs are only used inside renders.
SAMPLE_ENTITIES: dict[str, tuple[str, dict[str, Any]]] = {
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
            "media_duration": 210,
            "media_position": 42,
            "volume_level": 0.4,
            "is_volume_muted": False,
            "source": "HDMI 1",
            "source_list": ["HDMI 1", "HDMI 2", "Spotify"],
            "shuffle": False,
            "repeat": "all",
            "group_members": ["media_player.kitchen_speaker"],
            "supported_features": 837813,
        },
    ),
    "media_player.kitchen_speaker": (
        "off",
        {
            "friendly_name": "Kitchen Speaker",
            "volume_level": 0.2,
            "is_volume_muted": False,
            "supported_features": 4,
        },
    ),
    "vacuum.robot": (
        "cleaning",
        {
            "friendly_name": "Robot Vacuum",
            "fan_speed": "medium",
            "fan_speed_list": ["low", "medium", "high"],
            "supported_features": 12860,
        },
    ),
    "sensor.robot_battery": (
        "82",
        {
            "friendly_name": "Robot Battery",
            "unit_of_measurement": "%",
            "device_class": "battery",
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
    "sensor.kitchen_temperature": (
        "21.5",
        {
            "friendly_name": "Temperature",
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


PREVIEW_ENTITIES = {
    f"{domain}.haui_preview_{object_id}": state
    for entity_id, state in SAMPLE_ENTITIES.items()
    for domain, object_id in (entity_id.split(".", 1),)
}


def sample_forecast() -> list[dict[str, Any]]:
    """A representative five-day forecast beginning tomorrow."""
    start = datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    days = [
        ("sunny", 24, 13),
        ("partlycloudy", 22, 12),
        ("rainy", 19, 11),
        ("cloudy", 21, 12),
        ("lightning", 23, 14),
    ]
    return [
        {
            "datetime": (start + datetime.timedelta(days=offset)).isoformat(),
            "condition": condition,
            "temperature": high,
            "templow": low,
        }
        for offset, (condition, high, low) in enumerate(days, start=1)
    ]

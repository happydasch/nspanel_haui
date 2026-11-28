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
    "camera.front_door": ("idle", {"friendly_name": "Front Door"}),
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

#: The sample world's cameras: only these get ``sample_snapshot``'s picture, so a
#: real camera whose snapshot fails keeps the page's placeholder instead of a
#: picture it never took.
SAMPLE_CAMERAS = frozenset(
    entity_id
    for entity_id in (*SAMPLE_ENTITIES, *PREVIEW_ENTITIES)
    if entity_id.startswith("camera.")
)

_SAMPLE_PICTURE: bytes | None = None


def sample_snapshot(entity_id: str) -> bytes | None:
    """A representative snapshot for a sample camera, or None for a real entity.

    A camera page is a picture, so its card has nothing to draw without a frame:
    the editor's previews and the card gallery render the panel like any other
    card and would otherwise show *Waiting for the camera* for ever. This is that
    frame - generated once, the same on every machine, so the committed
    screenshots do not change between runs.

    Args:
        entity_id: The camera the panel names.

    Returns:
        PNG bytes for one of the sample world's cameras, else ``None``.
    """
    global _SAMPLE_PICTURE
    if entity_id not in SAMPLE_CAMERAS:
        return None
    if _SAMPLE_PICTURE is None:
        _SAMPLE_PICTURE = _build_sample_picture()
    return _SAMPLE_PICTURE


def _build_sample_picture() -> bytes:
    """Draw the sample camera's view of a front door: sky, hedge, wall, door.

    Plain shapes and flat colours on purpose: the panel draws a picture as a few
    thousand ``fill`` rectangles, and a scene with recognisable edges is what shows
    a reader of the docs what that looks like at each quality.
    """
    import io

    from PIL import Image, ImageDraw

    width, height = 480, 270
    image = Image.new("RGB", (width, height), (120, 150, 190))
    draw = ImageDraw.Draw(image)
    horizon = 176
    for row in range(horizon):
        shade = row / horizon
        draw.line(
            [(0, row), (width, row)],
            fill=(int(88 + 54 * shade), int(126 + 44 * shade), int(196 - 26 * shade)),
        )
    draw.rectangle([0, horizon, width, height], fill=(54, 92, 62))  # hedge
    draw.ellipse([356, 22, 424, 90], fill=(255, 238, 194))  # sun
    draw.polygon([(70, 104), (198, 40), (326, 104)], fill=(92, 66, 58))  # roof
    draw.rectangle([96, 104, 300, horizon + 8], fill=(186, 176, 164))  # wall
    draw.rectangle([150, 120, 244, horizon + 8], fill=(58, 44, 40))  # door
    draw.ellipse([228, 172, 238, 182], fill=(232, 190, 96))  # handle
    draw.rectangle([262, 122, 292, 158], fill=(214, 224, 236))  # window
    draw.rectangle([0, horizon + 8, width, horizon + 14], fill=(74, 118, 78))  # path
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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

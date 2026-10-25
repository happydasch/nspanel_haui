from __future__ import annotations

import re

from ..mapping.icon_mapping import (
    ALARM_CONTROL_PANEL_MAPPING,
    CLIMATE_MAPPING,
    COVER_MAPPING,
    ICON_MAPPING,
    SENSOR_MAPPING,
    SENSOR_MAPPING_OFF,
    SENSOR_MAPPING_ON,
    WEATHER_MAPPING,
)


def parse_icon(template: str) -> str:
    """Returns the parsed string with icons replaced.

    Args:
        icon_name (str): Icon name

    Returns:
        str: Icon character
    """

    def replace_icon(match: re.Match[str]) -> str:
        icon_name = match.group(2)
        icon = get_icon(icon_name)
        return f"{icon}{match.group(3)}"

    if template != "":
        template = re.sub(r"(mdi|hass):(\S+)($|\s)", replace_icon, template)
    if template and template in ICON_MAPPING:
        template = ICON_MAPPING[template]
    return template


def get_icon(icon_name: str) -> str:
    """Returns the icon chr value from icon name.

    Args:
        icon_name (str): Icon name

    Returns:
        str: Icon character
    """
    if ":" in icon_name:
        icon_name = icon_name.split(":")[1]
    if icon_name in ICON_MAPPING:
        return ICON_MAPPING[icon_name]
    return ICON_MAPPING["alert-circle-outline"]


# Icon for an entity type, whatever its state.
_FIXED_STATE_ICONS: dict[str, str] = {
    "script": "script-text",
    "alarm-arm-fail": "progress-alert",
}
# Entity type -> (state that picks the first icon, first icon, icon for any other state).
_TWO_STATE_ICONS: dict[str, tuple[str, str, str]] = {
    "light": ("on", "lightbulb", "lightbulb-off"),
    "input_boolean": ("on", "check-circle-outline", "close-circle-outline"),
    "lock": ("unlocked", "lock-open", "lock"),
    "sun": ("above_horizon", "weather-sunset-up", "weather-sunset-down"),
}
# Entity type -> state -> icon.
_STATE_ICON_MAPPINGS: dict[str, dict[str, str]] = {
    "weather": WEATHER_MAPPING,
    "alarm_control_panel": ALARM_CONTROL_PANEL_MAPPING,
    "climate": CLIMATE_MAPPING,
}


def get_icon_name_by_state(
    item_type: str, item_state: str, device_class: str | None = None
) -> str | None:
    """Returns the icon for the the given entity state.

    Args:
        item_type (str): Item type
        item_state (str): Item state
        device_class (str): Device class, optional, Defaults to None

    Returns:
        str: Icon name
    """
    if item_type in _FIXED_STATE_ICONS:
        return _FIXED_STATE_ICONS[item_type]
    if item_type in _TWO_STATE_ICONS:
        match_state, matched_icon, other_icon = _TWO_STATE_ICONS[item_type]
        return matched_icon if item_state == match_state else other_icon
    if item_type in _STATE_ICON_MAPPINGS:
        return _STATE_ICON_MAPPINGS[item_type].get(item_state)
    if item_type == "cover":
        if device_class not in COVER_MAPPING:
            return None
        cover_icons = COVER_MAPPING[device_class]
        return cover_icons[1] if item_state == "closed" else cover_icons[0]
    if item_type == "sensor":
        return SENSOR_MAPPING.get(device_class) if device_class else None
    if item_type == "binary_sensor":
        if item_state == "on":
            return SENSOR_MAPPING_ON.get(device_class or "", "checkbox-marked-circle")
        return SENSOR_MAPPING_OFF.get(device_class or "", "radiobox-blank")
    return None


def get_icon_name_by_action(
    item_type: str, action: str, device_class: str | None = None
) -> str | None:
    """Returns the icon for the given action.

    Args:
        item_type (str): Item type
        action (str): Action
        device_class (str, optional): Device class. Defaults to None.

    Returns:
        str: Icon name
    """
    action_icon = None
    if item_type == "cover":
        if action == "open" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][2]
        elif action == "close" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][4]
        elif action == "stop" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][3]
    return action_icon

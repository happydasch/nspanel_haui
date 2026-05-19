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


def get_icon(icon_name: str, return_default: bool = True) -> str:
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
    result_icon = None
    # script entity
    if item_type == "script":
        result_icon = "script-text"
    # alarm arm fail
    elif item_type == "alarm-arm-fail":
        result_icon = "progress-alert"
    # weather entity
    elif item_type == "weather":
        if item_state in WEATHER_MAPPING:
            result_icon = WEATHER_MAPPING[item_state]
    # light entity
    elif item_type == "light":
        if item_state == "on":
            result_icon = "lightbulb"
        else:
            result_icon = "lightbulb-off"
    # boolean input entity
    elif item_type == "input_boolean":
        if item_state == "on":
            result_icon = "check-circle-outline"
        else:
            result_icon = "close-circle-outline"
    # lock entity
    elif item_type == "lock":
        if item_state == "unlocked":
            result_icon = "lock-open"
        else:
            result_icon = "lock"
    # sun entity
    elif item_type == "sun":
        if item_state == "above_horizon":
            result_icon = "weather-sunset-up"
        else:
            result_icon = "weather-sunset-down"
    # alarm control panel entity
    elif item_type == "alarm_control_panel":
        if item_state in ALARM_CONTROL_PANEL_MAPPING:
            result_icon = ALARM_CONTROL_PANEL_MAPPING[item_state]
    # climate entity
    elif item_type == "climate":
        if item_state in CLIMATE_MAPPING:
            result_icon = CLIMATE_MAPPING[item_state]
    # cover entity
    elif item_type == "cover":
        if item_state == "closed":
            if device_class in COVER_MAPPING:
                result_icon = COVER_MAPPING[device_class][1]
        else:
            if device_class in COVER_MAPPING:
                result_icon = COVER_MAPPING[device_class][0]
    # sensor entity
    elif item_type == "sensor":
        if device_class in SENSOR_MAPPING:
            result_icon = SENSOR_MAPPING[device_class]
    # binary sensor entity
    elif item_type == "binary_sensor":
        if item_state == "on":
            result_icon = "checkbox-marked-circle"
            if device_class in SENSOR_MAPPING_ON:
                result_icon = SENSOR_MAPPING_ON[device_class]
        else:
            result_icon = "radiobox-blank"
            if device_class in SENSOR_MAPPING_OFF:
                result_icon = SENSOR_MAPPING_OFF[device_class]

    return result_icon


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

import re

from ..mapping.icon import (
    ICONS_MAPPING,
    COVER_MAPPING,
    ALARM_CONTROL_PANEL_MAPPING,
    WEATHER_MAPPING,
    CLIMATE_MAPPING,
    SENSOR_MAPPING,
    SENSOR_MAPPING_ON,
    SENSOR_MAPPING_OFF,
)


def parse_icon(template):
    """ Returns the parsed string with icons replaced.

    Args:
        icon_name (str): Icon name

    Returns:
        str: Icon character
    """

    def replace_icon(match):
        icon_name = match.group(2)
        icon = get_icon(icon_name)
        return f"{icon}{match.group(3)}"

    if isinstance(template, str) and template != "":
        template = re.sub(r"(mdi|hass):(\S+)($|\s)", replace_icon, template)
    if template and template in ICONS_MAPPING:
        template = ICONS_MAPPING[template]
    return template


def get_icon(icon_name, return_default=True):
    """ Returns the icon chr value from icon name.

    Args:
        icon_name (str): Icon name
        return_default (bool): If true, returns default icon if icon name is not
            found.

    Returns:
        str: Icon character
    """
    if ":" in icon_name:
        icon_name = icon_name.split(":")[1]
    if icon_name in ICONS_MAPPING:
        return ICONS_MAPPING[icon_name]
    elif return_default:
        return ICONS_MAPPING["alert-circle-outline"]
    return None


def get_icon_name_by_state(entity_type, entity_state, device_class=None):
    """ Returns the icon for the the given entity state.

    Args:
        entity_type (str): Entity type
        entity_state (str): Entity state
        device_class (str): Device class, optional, Defaults to None

    Returns:
        str: Icon name
    """
    result_icon = ""
    # script entity
    if entity_type == "script":
        result_icon = "script-text"
    # alarm arm fail
    elif entity_type == "alarm-arm-fail":
        result_icon = "progress-alert"
    # weather entity
    elif entity_type == "weather":
        if entity_state in WEATHER_MAPPING:
            result_icon = WEATHER_MAPPING[entity_state]
    # light entity
    elif entity_type == "light":
        if entity_state == "on":
            result_icon = "lightbulb"
        else:
            result_icon = "lightbulb-off"
    # boolean input entity
    elif entity_type == "input_boolean":
        if entity_state == "on":
            result_icon = "check-circle-outline"
        else:
            result_icon = "close-circle-outline"
    # lock entity
    elif entity_type == "lock":
        if entity_state == "unlocked":
            result_icon = "lock-open"
        else:
            result_icon = "lock"
    # sun entity
    elif entity_type == "sun":
        if entity_state == "above_horizon":
            result_icon = "weather-sunset-up"
        else:
            result_icon = "weather-sunset-down"
    # alarm control panel entity
    elif entity_type == "alarm_control_panel":
        if entity_state in ALARM_CONTROL_PANEL_MAPPING:
            result_icon = ALARM_CONTROL_PANEL_MAPPING[entity_state]
    # climate entity
    elif entity_type == "climate":
        if entity_state in CLIMATE_MAPPING:
            result_icon = CLIMATE_MAPPING[entity_state]
    # cover entity
    elif entity_type == "cover":
        if entity_state == "closed":
            if device_class in COVER_MAPPING:
                result_icon = COVER_MAPPING[device_class][1]
        else:
            if device_class in COVER_MAPPING:
                result_icon = COVER_MAPPING[device_class][0]
    # sensor entity
    elif entity_type == "sensor":
        if device_class in SENSOR_MAPPING:
            result_icon = SENSOR_MAPPING[device_class]
    # binary sensor entity
    elif entity_type == "binary_sensor":
        if entity_state == "on":
            result_icon = "checkbox-marked-circle"
            if device_class in SENSOR_MAPPING_ON:
                result_icon = SENSOR_MAPPING_ON[device_class]
        else:
            result_icon = "radiobox-blank"
            if device_class in SENSOR_MAPPING_OFF:
                result_icon = SENSOR_MAPPING_OFF[device_class]

    return result_icon


def get_icon_name_by_action(entity_type, action, device_class=None):
    """ Returns the icon for the given action.

    Args:
        entity_type (str): Entity type
        action (str): Action
        device_class (str, optional): Device class. Defaults to None.

    Returns:
        str: Icon name
    """
    action_icon = ""
    if entity_type == "cover":
        if action == "open" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][2]
        elif action == "close" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][4]
        elif action == "stop" and device_class in COVER_MAPPING:
            action_icon = COVER_MAPPING[device_class][3]
    return action_icon

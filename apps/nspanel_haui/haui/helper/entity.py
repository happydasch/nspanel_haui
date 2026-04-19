from ..mapping.color import COLORS
from ..mapping.icon import (
    INTERNAL_TYPE_MAPPING,
    MEDIA_CONTENT_TYPE_MAPPING,
    SIMPLE_TYPE_MAPPING,
)
from .color import rgb565_to_rgb, rgb_brightness, rgb_to_rgb565
from .icon import get_icon, get_icon_name_by_state

# --- execute_entity dispatch ---

_TOGGLE_TYPES = frozenset([
    "light", "switch", "cover", "input_boolean", "automation", "fan",
])
_PRESS_TYPES = frozenset(["button", "input_button"])
_TURN_ON_TYPES = frozenset(["scene", "script"])


def execute_entity(haui_entity):
    """Executes the given entity.

    Args:
        haui_entity (HAUIConfigEntity): the entity to execute
    """
    if not haui_entity.has_entity():
        return

    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    entity_state = haui_entity.get_entity_state()

    if entity_type in _TOGGLE_TYPES:
        entity.call_service("toggle")
    elif entity_type in _PRESS_TYPES:
        entity.call_service("press")
    elif entity_type in _TURN_ON_TYPES:
        entity.call_service("turn_on")
    elif entity_type == "lock":
        entity.call_service("unlock" if entity_state == "locked" else "lock")
    elif entity_type == "vacuum":
        entity.call_service("start" if entity_state == "docked" else "return_to_base")
    elif entity_type == "input_select":
        entity.call_service("select_next")


# --- get_entity_color dispatch ---

_ALARM_ARMED_STATES = frozenset([
    "armed_home", "armed_away", "armed_night", "armed_vacation", "pending", "triggered",
])


def _color_weather(entity, entity_state, haui_entity):
    color_name = f"weather_{(entity_state or '').replace('-', '_')}"
    return COLORS.get(color_name, COLORS["weather_default"])


def _color_climate(entity, entity_state, haui_entity):
    return COLORS.get(f"climate_{entity_state}")


def _color_alarm(entity, entity_state, haui_entity):
    if entity_state == "disarmed":
        return COLORS["alarm_disarmed"]
    if entity_state == "arming":
        return COLORS["alarm_arming"]
    if entity_state in _ALARM_ARMED_STATES:
        return COLORS["alarm_armed"]
    return None


def _color_media_player(entity, entity_state, haui_entity):
    if entity_state == "playing":
        return COLORS["entity_on"]
    if entity_state == "unavailable":
        return COLORS["entity_unavailable"]
    return COLORS["entity_off"]


def _color_group(entity, entity_state, haui_entity):
    return COLORS["entity_on"] if entity_state == "on" else COLORS["entity_off"]


def _color_light(entity, entity_state, haui_entity):
    if entity_state != "on":
        return None
    attr = entity.attributes
    if "rgb_color" in attr and attr["rgb_color"]:
        color = attr["rgb_color"]
        if "brightness" in attr:
            color = rgb_brightness(color, attr["brightness"])
        return rgb_to_rgb565(color)
    if "brightness" in attr:
        return rgb_to_rgb565(rgb_brightness(rgb565_to_rgb(COLORS["entity_on"]), attr["brightness"]))
    return None


_COLOR_DISPATCH = {
    "weather": _color_weather,
    "climate": _color_climate,
    "alarm_control_panel": _color_alarm,
    "media_player": _color_media_player,
    "group": _color_group,
    "light": _color_light,
}

_ON_STATES = frozenset(["on", "unlocked", "above_horizon", "home", "active"])


def get_entity_color(haui_entity, default_color):
    """Returns a RGB565 color for the given entity.

    Args:
        haui_entity (HAUIConfigEntity): the entity to get the color for
        default_color (int): Default color to return

    Returns:
        int: RGB565 color
    """
    if not haui_entity.has_entity():
        return default_color

    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    entity_state = haui_entity.get_entity_state()

    # general state-based default
    if entity_state in _ON_STATES:
        result_color = COLORS["entity_on"]
    elif entity_state == "unavailable":
        result_color = COLORS["entity_unavailable"]
    else:
        result_color = COLORS["entity_off"]

    # per-type override
    handler = _COLOR_DISPATCH.get(entity_type)
    if handler:
        color = handler(entity, entity_state, haui_entity)
        if color is not None:
            result_color = color

    return result_color


def get_entity_icon(haui_entity, default_icon):
    """Returns a icon for the given entity.

    Args:
        haui_entity (HAUIConfigEntity): The entity to get the icon for
        default_icon (str): Default icon to return

    Returns:
        str: Icon character
    """

    result_icon = default_icon
    # check internal
    if haui_entity.is_internal():
        internal_type = haui_entity.get_internal_type()
        if internal_type in INTERNAL_TYPE_MAPPING:
            result_icon = INTERNAL_TYPE_MAPPING[internal_type]

    # default alert icon
    if not haui_entity.has_entity():
        return get_icon(result_icon)

    # get entity details
    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    entity_state = haui_entity.get_entity_state()
    device_class = haui_entity.get_entity_attr("device_class")

    # icons only based on entity type
    if entity_type in SIMPLE_TYPE_MAPPING:
        result_icon = SIMPLE_TYPE_MAPPING[entity_type]

    # icon based entity state
    state_icon = get_icon_name_by_state(entity_type, entity_state, device_class)

    # icon based on media_content_type
    overwrite_icon = ""
    if entity_type == "media_player":
        overwrite_icon = "speaker-off"
        if "media_content_type" in entity.attributes:
            if entity.attributes["media_content_type"] in MEDIA_CONTENT_TYPE_MAPPING:
                overwrite_icon = MEDIA_CONTENT_TYPE_MAPPING[
                    entity.attributes["media_content_type"]
                ]
        if "media_channel" in entity.attributes:
            overwrite_icon = "radio"
        if "icon" in entity.attributes:
            overwrite_icon = entity.attributes["icon"]

    if overwrite_icon:
        result_icon = overwrite_icon
    elif state_icon:
        result_icon = state_icon

    return get_icon(result_icon)


# --- get_entity_value dispatch ---

def _value_weather(entity, entity_state, haui_entity):
    temp_unit = haui_entity.get_entity_attr("temperature_unit", "°C")
    temp = haui_entity.get_entity_attr("temperature", "")
    return f"{temp}{temp_unit}" if temp else ""


def _value_button(entity, entity_state, haui_entity):
    return haui_entity.translate("Press")


def _value_scene(entity, entity_state, haui_entity):
    return haui_entity.translate("Activate")


def _value_script(entity, entity_state, haui_entity):
    return haui_entity.translate("Run")


def _value_lock(entity, entity_state, haui_entity):
    return haui_entity.translate("Lock") if entity.state == "unlocked" else haui_entity.translate("Unlock")


_ALARM_VALUE_MAP = {
    "arming": "Arming",
    "disarmed": "Disarmed",
    "disarming": "Disarming",
    "pending": "Pending",
    "triggered": "Triggered",
}


def _value_alarm(entity, entity_state, haui_entity):
    if entity.state.startswith("armed"):
        return haui_entity.translate("Armed")
    label = _ALARM_VALUE_MAP.get(entity.state, entity.state)
    return haui_entity.translate(label)


def _value_vacuum(entity, entity_state, haui_entity):
    return haui_entity.translate("Clean") if entity.state == "docked" else haui_entity.translate("Stop")


_VALUE_DISPATCH = {
    "weather": _value_weather,
    "button": _value_button,
    "input_button": _value_button,
    "scene": _value_scene,
    "script": _value_script,
    "lock": _value_lock,
    "alarm_control_panel": _value_alarm,
    "vacuum": _value_vacuum,
}


def get_entity_value(haui_entity, default_value):
    """Returns a value for the given entity.

    Args:
        haui_entity (HAUIConfigEntity): The entity to get the value for
        default_value (str): Default value to return

    Returns:
        str: Value
    """
    if not haui_entity.has_entity():
        return default_value

    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    entity_state = haui_entity.get_entity_state()

    handler = _VALUE_DISPATCH.get(entity_type)
    if handler:
        return handler(entity, entity_state, haui_entity)
    return haui_entity.translate_entity_state()


def get_entity_name(haui_entity, default_name):
    """Returns the name for the given entity.

    Args:
        haui_entity (HAUIConfigEntity): The entity to get the name for
        default_name (str): Default name to return

    Returns:
        str: A name for the given entity
    """
    name = default_name
    if not haui_entity.has_entity():
        return name

    entity = haui_entity.get_entity()
    name = entity.attributes.get("friendly_name", name)

    return name

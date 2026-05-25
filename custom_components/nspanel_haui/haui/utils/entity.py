from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..mapping.color import COLORS
from ..mapping.icon_mapping import (
    INTERNAL_TYPE_MAPPING,
    MEDIA_CONTENT_TYPE_MAPPING,
    SIMPLE_TYPE_MAPPING,
)
from .color import rgb565_to_rgb, rgb_brightness, rgb_to_rgb565
from .icon import get_icon, get_icon_name_by_state

_ColorGetter = Callable[[str], int]

# Module-level default: direct COLORS dict lookup (no override support).
# HAUIBase subclasses pass self.get_color instead.
_DEFAULT_COLOR_GETTER: _ColorGetter = COLORS.__getitem__

if TYPE_CHECKING:
    from ..abstract.haui_item import HAUIItem

# --- execute_item dispatch ---

_TOGGLE_TYPES = frozenset(
    [
        "light",
        "switch",
        "cover",
        "input_boolean",
        "automation",
        "fan",
    ]
)
_PRESS_TYPES = frozenset(["button", "input_button"])
_TURN_ON_TYPES = frozenset(["scene", "script"])


def execute_item(haui_item: HAUIItem) -> None:
    """Executes the given entity.

    Args:
        haui_item (HAUIItem): the item to execute
    """
    if not haui_item.has_item():
        return

    entity = haui_item.get_item()
    item_type = haui_item.get_item_type()
    item_state = haui_item.get_item_state()

    if item_type in _TOGGLE_TYPES:
        entity.call_service("toggle")
    elif item_type in _PRESS_TYPES:
        entity.call_service("press")
    elif item_type in _TURN_ON_TYPES:
        entity.call_service("turn_on")
    elif item_type == "lock":
        entity.call_service("unlock" if item_state == "locked" else "lock")
    elif item_type == "vacuum":
        entity.call_service("start" if item_state == "docked" else "return_to_base")
    elif item_type == "input_select":
        entity.call_service("select_next")


# --- get_item_color dispatch ---

_ALARM_ARMED_STATES = frozenset(
    [
        "armed_home",
        "armed_away",
        "armed_night",
        "armed_vacation",
        "pending",
        "triggered",
    ]
)


def _color_weather(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int:
    color_name = f"weather_{(item_state or '').replace('-', '_')}"
    return color_getter(color_name) if color_name in COLORS else color_getter("weather_default")


def _color_climate(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int | None:
    key = f"climate_{item_state}"
    return color_getter(key) if key in COLORS else None


def _color_alarm(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int | None:
    if item_state == "disarmed":
        return color_getter("alarm_disarmed")
    if item_state == "arming":
        return color_getter("alarm_arming")
    if item_state in _ALARM_ARMED_STATES:
        return color_getter("alarm_armed")
    return None


def _color_media_player(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int:
    if item_state == "playing":
        return color_getter("entity_on")
    if item_state == "unavailable":
        return color_getter("entity_unavailable")
    return color_getter("entity_off")


def _color_group(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int:
    return color_getter("entity_on") if item_state == "on" else color_getter("entity_off")


def _color_light(
    entity: Any, item_state: str | None, haui_item: HAUIItem,
    color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER,
) -> int | None:
    if item_state != "on":
        return None
    attr = entity.attributes
    if "rgb_color" in attr:
        color = attr["rgb_color"]
        if color is None:
            color = rgb565_to_rgb(color_getter("entity_on"))
        if "brightness" in attr:
            color = rgb_brightness(color, attr["brightness"])
        return rgb_to_rgb565(color)
    if "brightness" in attr:
        return rgb_to_rgb565(
            rgb_brightness(rgb565_to_rgb(color_getter("entity_on")), attr["brightness"])
        )
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


def get_item_color(
    haui_item: HAUIItem, default_color: int, color_getter: _ColorGetter = _DEFAULT_COLOR_GETTER
) -> int:
    """Returns a RGB565 color for the given entity.

    Args:
        haui_item (HAUIItem): the item to get the color for
        default_color (int): Default color to return
        color_getter (Callable): Function to look up color keys, e.g. ``self.get_color``.
            Falls back to ``COLORS.get`` when not provided.

    Returns:
        int: RGB565 color
    """
    if not haui_item.has_item():
        return default_color

    entity = haui_item.get_item()
    item_type = haui_item.get_item_type()
    item_state = haui_item.get_item_state()

    # general state-based default
    if item_state in _ON_STATES:
        result_color = color_getter("entity_on")
    elif item_state == "unavailable":
        result_color = color_getter("entity_unavailable")
    else:
        result_color = color_getter("entity_off")

    # per-type override
    handler = _COLOR_DISPATCH.get(item_type)
    if handler:
        color = handler(entity, item_state, haui_item, color_getter=color_getter)
        if color is not None:
            result_color = color

    return result_color


def get_item_icon(haui_item: HAUIItem, default_icon: str) -> str:
    """Returns a icon for the given entity.

    Args:
        haui_item (HAUIItem): The entity to get the icon for
        default_icon (str): Default icon to return

    Returns:
        str: Icon character
    """

    result_icon = default_icon
    # check internal
    if haui_item.is_internal():
        internal_type = haui_item.get_internal_type()
        if internal_type in INTERNAL_TYPE_MAPPING:
            result_icon = INTERNAL_TYPE_MAPPING[internal_type]

    # default alert icon
    if not haui_item.has_item():
        return get_icon(result_icon)

    # get entity details
    entity = haui_item.get_item()
    item_type = haui_item.get_item_type()
    item_state = haui_item.get_item_state()
    device_class = haui_item.get_item_attr("device_class")

    # icons only based on entity type
    if item_type in SIMPLE_TYPE_MAPPING:
        result_icon = SIMPLE_TYPE_MAPPING[item_type]

    # icon based entity state
    state_icon = get_icon_name_by_state(item_type, item_state or "", device_class)

    # icon based on media_content_type
    overwrite_icon = ""
    if item_type == "media_player":
        overwrite_icon = "speaker-off"
        if (
            "media_content_type" in entity.attributes
            and entity.attributes["media_content_type"] in MEDIA_CONTENT_TYPE_MAPPING
        ):
            overwrite_icon = MEDIA_CONTENT_TYPE_MAPPING[entity.attributes["media_content_type"]]
        if "media_channel" in entity.attributes:
            overwrite_icon = "radio"
        if "icon" in entity.attributes:
            overwrite_icon = entity.attributes["icon"]

    if overwrite_icon:
        result_icon = overwrite_icon
    elif state_icon:
        result_icon = state_icon

    return get_icon(result_icon)


# --- get_item_value dispatch ---


def _value_weather(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    temp_unit = haui_item.get_item_attr("temperature_unit", "°C")
    temp = haui_item.get_item_attr("temperature", "")
    return f"{temp}{temp_unit}" if temp else ""


def _value_button(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    return haui_item.translate("Press")


def _value_scene(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    return haui_item.translate("Activate")


def _value_script(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    return haui_item.translate("Run")


def _value_lock(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    return (
        haui_item.translate("Lock") if entity.state == "unlocked" else haui_item.translate("Unlock")
    )


_ALARM_VALUE_MAP = {
    "arming": "Arming",
    "disarmed": "Disarmed",
    "disarming": "Disarming",
    "pending": "Pending",
    "triggered": "Triggered",
}


def _value_alarm(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    if entity.state.startswith("armed"):
        return haui_item.translate("Armed")
    label = _ALARM_VALUE_MAP.get(entity.state, entity.state)
    return haui_item.translate(label)


def _value_vacuum(entity: Any, item_state: str | None, haui_item: HAUIItem) -> str:
    return haui_item.translate("Clean") if entity.state == "docked" else haui_item.translate("Stop")


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


def get_item_value(haui_item: HAUIItem, default_value: str) -> str:
    """Returns a value for the given entity.

    Args:
        haui_item (HAUIItem): The entity to get the value for
        default_value (str): Default value to return

    Returns:
        str: Value
    """
    if not haui_item.has_item():
        return default_value

    entity = haui_item.get_item()
    item_type = haui_item.get_item_type()
    item_state = haui_item.get_item_state()

    handler = _VALUE_DISPATCH.get(item_type)
    if handler:
        return handler(entity, item_state, haui_item)
    return haui_item.translate_item_state()


def get_item_name(haui_item: HAUIItem, default_name: str) -> str:
    """Returns the name for the given entity.

    Args:
        haui_item (HAUIItem): The entity to get the name for
        default_name (str): Default name to return

    Returns:
        str: A name for the given entity
    """
    name = default_name
    if not haui_item.has_item():
        return name

    entity = haui_item.get_item()
    name = entity.attributes.get("friendly_name", name)

    return name

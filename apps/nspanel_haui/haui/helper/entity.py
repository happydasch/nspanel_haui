import dateutil.parser as dp

from ..mapping.icon import (
    SIMPLE_TYPE_MAPPING, INTERNAL_TYPE_MAPPING,
    MEDIA_CONTENT_TYPE_MAPPING, WEATHER_MAPPING
)

from .datetime import format_datetime
from .color import rgb_to_rgb565, rgb_brightness
from .icon import get_icon, get_icon_name_by_state


def execute_entity(haui_entity):
    """ Executes the given entity.

    Args:
        haui_entity (HAUIConfigEntity): the entity to execute
    """
    if not haui_entity.has_entity():
        return

    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    entity_state = haui_entity.get_entity_state()

    if entity_type in [
        'light', 'switch', 'input_boolean',
        'automation', 'fan'
    ]:
        entity.call_service('toggle')
    elif entity_type in ['button', 'input_button']:
        entity.call_service("press")
    elif entity_type == 'lock':
        if entity_state == 'locked':
            entity.call_service('unlock')
        else:
            entity.call_service('lock')
    elif entity_type == 'vacuum':
        if entity_state == 'docked':
            entity.call_service('start')
        else:
            entity.call_service('return_to_base')
    elif entity_type == 'scene':
        entity.call_service('turn_on')
    elif entity_type == 'script':
        entity.call_service('turn_on')
    elif entity_type == 'input_select':
        entity.call_service('select_next')


def get_entity_color(haui_entity, default_color):
    """ Returns a RGB565 color for the given entity.

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

    # default_color_on #fdd835
    default_color_on = rgb_to_rgb565([253, 216, 53])
    # default_color_off #44739e
    default_color_off = rgb_to_rgb565([68, 115, 158])
    # default_color_unavailable #737373
    default_color_unavailable = rgb_to_rgb565([115, 115, 115])

    # colors based on state
    if entity_state in ['on', 'unlocked', 'above_horizon', 'home', 'active']:
        result_color = default_color_on
    elif entity_state in ['unavailable']:
        result_color = default_color_unavailable
    else:
        result_color = default_color_off

    # weather entity
    if entity_type == 'weather':
        forecast_index = haui_entity.get('forecast_index')
        condition = None
        if 'forecast' in entity.attributes and forecast_index is not None:
            if forecast_index < len(entity.attributes['forecast']):
                condition = entity.attributes['forecast'][forecast_index]['condition']
        else:
            condition = entity_state
        if condition in ['partlycloudy', 'windy']:
            result_color = 38066  # 50% grey
        if condition == 'clear-night':
            result_color = 38060  # yellow grey
        if condition == 'windy-variant':
            result_color: 64495  # red grey
        if condition == 'cloudy':
            result_color = 31728  # grey-blue
        if condition == 'exceptional':
            result_color = 63878  # red
        if condition == 'fog':
            result_color = 38066  # 75% grey
        if condition in ['hail', 'snowy']:
            result_color = 65535  # white
        if condition == 'lightning':
            result_color = 65120  # golden-yellow
        if condition == 'lightning-rainy':
            result_color = 50400  # dark-golden-yellow
        if condition == 'pouring':
            result_color = 12703  # blue
        if condition == 'rainy':
            result_color = 25375  # light-blue
        if condition == 'snowy-rainy':
            result_color = 38079  # light-blue-grey
        if condition == 'sunny':
            result_color = 65504  # bright-yellow
    # alarm control panel entity
    elif entity_type == 'alarm_control_panel':
        if entity_state == 'disarmed':
            result_color = rgb_to_rgb565([13, 160, 53])
        if entity_state == 'arming':
            result_color = rgb_to_rgb565([244, 180, 0])
        if entity_state in [
                'armed_home', 'armed_away', 'armed_night',
                'armed_vacation', 'pending', 'triggered']:
            result_color = rgb_to_rgb565([223, 76, 30])
    # climate entity
    elif entity_type == 'climate':
        if entity_state in ['auto', 'heat_cool']:
            result_color = 1024
        if entity_state == 'heat':
            result_color = 64512
        if entity_state == 'off':
            result_color = 35921
        if entity_state == 'cool':
            result_color = 11487
        if entity_state == 'dry':
            result_color = 60897
        if entity_state == 'fan_only':
            result_color = 35921

    # additional attributes check
    attr = entity.attributes
    if 'rgb_color' in attr:
        color = attr.rgb_color
        if 'brightness' in attr:
            color = rgb_brightness(color, attr.brightness)
        result_color = rgb_to_rgb565(color)
    elif 'brightness' in attr:
        # #fdd835
        color = rgb_brightness([253, 216, 53], attr.brightness)
        result_color = rgb_to_rgb565(color)

    return result_color


def get_entity_icon(haui_entity, default_icon):
    """ Returns a icon for the given entity.

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
    device_class = haui_entity.get_entity_attr('device_class')

    # icons only based on entity type
    if entity_type in SIMPLE_TYPE_MAPPING:
        result_icon = SIMPLE_TYPE_MAPPING[entity_type]

    # icon based entity state
    state_icon = get_icon_name_by_state(entity_type, entity_state, device_class)

    # icon based on media_content_type
    overwrite_icon = ''
    if entity_type == 'media_player':
        overwrite_icon = 'speaker-off'
        if 'media_content_type' in entity.attributes:
            if (entity.attributes['media_content_type']
                    in MEDIA_CONTENT_TYPE_MAPPING):
                overwrite_icon = MEDIA_CONTENT_TYPE_MAPPING[
                    entity.attributes['media_content_type']]
    # weather entity
    elif entity_type == 'weather':
        forecast_index = haui_entity.get('forecast_index')
        condition = None
        if 'forecast' in entity.attributes and forecast_index is not None:
            if forecast_index < len(entity.attributes['forecast']):
                condition = entity.attributes['forecast'][forecast_index]['condition']
        else:
            condition = entity_state
        if condition in WEATHER_MAPPING:
            overwrite_icon = WEATHER_MAPPING[condition]

    if overwrite_icon:
        result_icon = overwrite_icon
    elif state_icon:
        result_icon = state_icon

    return get_icon(result_icon)


def get_entity_value(haui_entity, default_value):
    """ Returns a value for the given entity.

    Args:
        haui_entity (HAUIConfigEntity): The entity to get the value for
        default_value (str): Default value to return

    Returns:
        str: Value
    """
    result_value = default_value
    if not haui_entity.has_entity():
        return result_value

    entity = haui_entity.get_entity()
    entity_type = haui_entity.get_entity_type()
    result_value = haui_entity.get_entity_state()

    # weather entity
    if entity_type == 'weather':
        forecast_index = haui_entity.get('forecast_index')
        temp_unit = haui_entity.get_entity_attr('temperature_unit', '°C')
        if 'forecast' in entity.attributes and forecast_index is not None:
            if forecast_index < len(entity.attributes.forecast):
                result_value = entity.attributes.forecast[forecast_index]['temperature']
        else:
            result_value = haui_entity.get_entity_attr('temperature', '')
        if result_value:
            result_value = f'{result_value}{temp_unit}'
    # button entity
    elif entity_type == 'button':
        result_value = haui_entity.translate('Press')
    # scene entity
    elif entity_type == 'scene':
        result_value = haui_entity.translate('Activate')
    # script entity
    elif entity_type == 'script':
        result_value = haui_entity.translate('Run')
    # lock entity
    elif entity_type == 'lock':
        if entity.state == 'unlocked':
            result_value = haui_entity.translate('Lock')
        else:
            result_value = haui_entity.translate('Unlock')
    # alarm control panel entity
    elif entity_type == 'alarm_control_panel':
        if entity.state.startswith('armed'):
            result_value = haui_entity.translate('Armed')
        elif entity.state == 'arming':
            result_value = haui_entity.translate('Arming')
        elif entity.state == 'disarmed':
            result_value = haui_entity.translate('Disarmed')
        elif entity.state == 'disarming':
            result_value = haui_entity.translate('Disarming')
        elif entity.state == 'pending':
            result_value = haui_entity.translate('Pending')
        elif entity.state == 'triggered':
            result_value = haui_entity.translate('Triggered')
    # climate entity
    elif entity_type == 'climate':
        state_value = haui_entity.translate_state()
        temperature = haui_entity.get_entity_attr('temperature', '')
        temp_unit = haui_entity.get_entity_attr('temperature_unit', '°C')
        value = f'{state_value} {temperature}{temp_unit}'
        currently_tanslation = haui_entity.translate('Currently')
        current_temp = haui_entity.get_entity_attr('current_temperature', '')
        value += f'{currently_tanslation}: {current_temp}{temp_unit}'
    # vacuum entity
    elif entity_type == 'vacuum':
        if entity.state == 'docked':
            result_value = haui_entity.translate('Start cleaning')
        else:
            result_value = haui_entity.translate('Return to dock')
    # default value is using the state
    else:
        # use the translated entity state
        result_value = haui_entity.translate_state()

    return result_value


def get_entity_name(haui_entity, default_name):
    """ Returns the name for the given entity.

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
    entity_type = haui_entity.get_entity_type()
    name = entity.attributes.get('friendly_name', name)

    # weather entity
    if entity_type == 'weather':
        forecast_index = haui_entity.get('forecast_index')
        if 'forecast' in entity.attributes and forecast_index is not None:
            if forecast_index < len(entity.attributes.forecast):
                fdate = dp.parse(entity.attributes.forecast[forecast_index]['datetime'])
                name = format_datetime(fdate, '%a', 'E', haui_entity.get_locale())

    return name

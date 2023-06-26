# ESP Events, ESP will publish on events
# published to recv
ESP_EVENT = {event: event for event in [
    'connected',
    'sleep',
    'wakeup',
    'page',
    'brightness',
    'component',
    'touch_start',
    'touch',
    'touch_end',
    'gesture',
    'button_left',
    'button_right',
    'relay_left',
    'relay_right',
    'timeout',
    'display_state'
]}

# ESP Responses, ESP will publish after requests
# published to recv
ESP_RESPONSE = {response: response for response in [
    'res_device_info',
    'res_device_state',
    'res_int_value',
    'res_txt_value',
    'res_component_int',
    'res_component_txt'
]}

# ESP Requests, ESP will act when receiving this requests
# published to cmd
ESP_REQUEST = {request: request for request in [
    'req_device_info',
    'req_device_state',
    'req_reconnect',
    'req_int_value',
    'req_txt_value',
    'req_component_int',
    'req_component_txt'
]}

# Commands, ESP will act when receiving this commands
# published to cmd
ESP_COMMAND = {command: command for command in [
    'send_command',
    'send_commands',
    'set_component_text',
    'set_component_value',
    'goto_page'
]}

# Server Request, Server will answer this requests
# published to recv
SERVER_REQUEST = {req: req for req in [
    'heartbeat',
    'req_connection',
    'res_connection'
]}

# Server Response, Server will publish after requests
# published to cmd
SERVER_RESPONSE = {resp: resp for resp in [
    'ad_heartbeat',
    'ad_connection_response',
    'ad_connection_initialized',
    'ad_connection_closed'
]}

# all messages on recv
ALL_RECV = {msg: msg for msg in ESP_EVENT}
ALL_RECV.update({msg: msg for msg in ESP_RESPONSE})
ALL_RECV.update({msg: msg for msg in SERVER_REQUEST})

# all messages on cmd
ALL_CMD = {msg: msg for msg in ESP_REQUEST}
ALL_CMD.update({msg: msg for msg in ESP_COMMAND})
ALL_CMD.update({msg: msg for msg in SERVER_RESPONSE})

# internal entity types
INTERNAL_ENTITY_TYPE = ['skip', 'text', 'navigate', 'service']

# entity config
ENTITY_CONFIG = {
    'entity': None,  # entity id
    # by default the values below are returned
    # based on the entity. if defined, the values
    # will be overwritten, see documentation for details
    'state': None,  # entity state override
    'value': None,  # entity value override
    'name': None,  # entity name override
    'icon': None,  # entity icon override
    'color': None,  # entity color override
}

# panel config
PANEL_CONFIG = {
    'type': None,  # panel type
    'key': None,  # internal identifier
    'title': '',  # panel title
    'home_panel': False,  # defines if panel is a home panel
    'sleep_panel': False,  # defines if panel is a sleep panel
    'wakeup_panel': False,  # defines if panel is a wakeup panel
    'nav_panel': True,  # only nav panels will be used for navigation
    'entity': None,  # single entity
    'entities': []  # multiple entities
}

# default config
DEFAULT_CONFIG = {
    # common settings
    'time_format': '%H:%M',
    'date_format': '%A, %d. %B %Y',
    'date_format_babel': 'full',

    # device related settings
    'device': {
        'device_name': 'nspanel_haui',
        'locale': 'en_US',
        # hardware buttons
        'button_left_entity': None,
        'button_right_entity': None,
        'log_commands': False,
    },

    # mqtt related settings
    'mqtt': {
        'topic_prefix': 'nspanel_haui/nspanel_haui',
    },

    # connection related settings
    'connection': {
        'heartbeat_interval': None,  # Default 5 sec, None means use interval provided by device, value in seconds
        'overdue_factor': 2.0,  # Default 2 sec, when to timeout (interval * factor)
    },

    # navigation related settings
    'navigation': {
        'page_timeout': 10.0,  # Default 10 sec, wait for a page to open (sendme result)
    },

    # gesture related settings
    'gesture': {},

    # update related settings
    'update': {
        'update_interval': 86400,  # Defaults to 86400 sec, set to 0 to disable
        'check_on_connect': False,  # Defaults to false, set to true to check for updates on connect
        'on_connect_delay': 60,  # Defaults to 60 sec, delay before checking for updates on connect
    },

    # system panels configuration
    # this panels can be also overriden
    'sys_panels': [
        {
            # blank panel
            'type': 'blank',
            'key': 'sys_blank',
            'nav_panel': False,
        }, {
            # system panel
            'type': 'system',
            'key': 'sys_system',
            'nav_panel': False,
        }, {
            # panel for settings page
            'type': 'system_settings',
            'key': 'sys_settings',
            'nav_panel': False,
        }, {
            # panel for about page
            'type': 'system_about',
            'key': 'sys_about',
            'nav_panel': False,
        }, {
            # popup unlock
            'type': 'popup_unlock',
            'key': 'popup_unlock',
            'nav_panel': False,
        }, {
            # popup notify
            'type': 'popup_notify',
            'key': 'popup_notify',
            'nav_panel': False,
        }, {
            # popup select
            'type': 'popup_select',
            'key': 'popup_select',
            'nav_panel': False,
        }, {
            # popup light
            'type': 'popup_light',
            'key': 'popup_light',
            'nav_panel': False,
        }, {
            # popup thermo
            'type': 'popup_thermo',
            'key': 'popup_thermo',
            'nav_panel': False,
        }, {
            # popup timer
            'type': 'popup_timer',
            'key': 'popup_timer',
            'nav_panel': False,
        }
    ],

    # panels configuration
    'panels': [
        {
            'type': 'clock',
        }
    ]
}

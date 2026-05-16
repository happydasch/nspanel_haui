# ESP Events, ESP will publish on events
# published to recv
from __future__ import annotations

import copy
from enum import StrEnum
from typing import Any

from ..device_config import DEVICE_CONFIG  # noqa: F401  # used at the bottom of this file

ESP_NS_EVENT = "esphome.nspanel_event"


class ESPEvent(StrEnum):
    """Events published by the ESP device on the recv topic."""

    CONNECTED = "esphome.connected"
    SLEEP = "esphome.sleep"
    WAKEUP = "esphome.wakeup"
    PAGE = "esphome.page"
    COMPONENT = "esphome.component"
    TOUCH_START = "esphome.touch_start"
    TOUCH = "esphome.touch"
    TOUCH_END = "esphome.touch_end"
    GESTURE = "esphome.gesture"
    BUTTON_LEFT = "esphome.button_left"
    BUTTON_RIGHT = "esphome.button_right"
    RELAY_LEFT = "esphome.relay_left"
    RELAY_RIGHT = "esphome.relay_right"
    TIMEOUT = "esphome.timeout"
    DISPLAY_STATE = "esphome.display_state"


class ESPAction(StrEnum):
    """ESPHome service actions that HA can call on the device."""

    SEND_COMMAND = "send_command"
    SEND_COMMANDS = "send_commands"
    GOTO_PAGE = "goto_page"
    SET_BRIGHTNESS = "set_brightness"
    UPLOAD_TFT_URL = "upload_tft_url"
    PLAY_RTTTL = "play_rtttl"
    PLAY_SOUND = "play_sound"
    RESET_LAST_INTERACTION = "reset_last_interaction"
    HAUI_DISCOVER = "haui_discover"


class NotificationAction(StrEnum):
    """Notification action variants (published with device_name_ prefix)."""

    SEND_NOTIFICATION = "send_notification"
    SEND_NOTIFICATION_WITH_TIMEOUT = "send_notification_with_timeout"
    SEND_NOTIFICATION_PERSISTENT = "send_notification_persistent"
    SEND_NOTIFICATION_PERSISTENT_WITH_TIMEOUT = "send_notification_persistent_with_timeout"


class ESPResponse(StrEnum):
    """Responses published by the ESP device on the recv topic."""

    RES_DEVICE_INFO = "esphome.res_device_info"
    RES_DEVICE_STATE = "esphome.res_device_state"
    RES_VAL = "esphome.res_val"
    SEND_NOTIFICATION = "esphome.send_notification"


class ESPRequest(StrEnum):
    """Requests that the hub sends to the ESP device on the cmd topic."""

    REQ_DEVICE_INFO = "esphome.req_device_info"
    REQ_DEVICE_STATE = "esphome.req_device_state"
    REQ_VAL = "esphome.req_val"


class ESPCommand(StrEnum):
    """Commands that the hub sends to the ESP device on the cmd topic."""

    SEND_COMMAND = "esphome.send_command"
    SEND_COMMANDS = "esphome.send_commands"
    GOTO_PAGE = "esphome.goto_page"


class NotifEvent(StrEnum):
    """Notification events handled by the hub."""

    NOTIF_ADD = "notif_add"
    NOTIF_REMOVE = "notif_remove"
    NOTIF_CLEAR = "notif_clear"


class ServerRequest(StrEnum):
    """Server requests received from the device on the recv topic."""

    HEARTBEAT = "esphome.heartbeat"
    REQ_CONNECTION = "esphome.req_connection"
    RES_CONNECTION = "esphome.res_connection"


class ServerResponse(StrEnum):
    """Server responses sent to the device on the cmd topic."""

    HUB_HEARTBEAT = "esphome.hub_heartbeat"
    HUB_CONNECTION_RESPONSE = "esphome.hub_connection_response"
    HUB_CONNECTION_INITIALIZED = "esphome.hub_connection_initialized"
    HUB_CONNECTION_CLOSED = "esphome.hub_connection_closed"


class InternalItemType(StrEnum):
    """Internal (non-entity) item types."""

    SKIP = "skip"
    TEXT = "text"
    NAVIGATE = "navigate"
    ACTION = "action"


# all messages on recv
ALL_RECV: frozenset[str] = frozenset(
    member.value for member in (*ESPEvent, *ESPResponse, *ServerRequest)
)

# all messages on cmd
ALL_CMD: frozenset[str] = frozenset(
    member.value for member in (*ESPRequest, *ESPCommand, *ServerResponse)
) | frozenset(f"esphome.{member.value}" for member in ESPAction)

# item config
ITEM_CONFIG: dict[str, Any] = {
    "item": None,  # item id
    "popup_key": None,  # allows to override the default popup
    # by default the values below are returned
    # based on the item. if defined, the values
    # will be overwritten, see documentation for details
    "state": None,  # item state override
    "value": None,  # item value override
    "name": None,  # item name override
    "icon": None,  # item icon override
    "color": None,  # item color override
    # per-item appearance overrides (used by grid panel and potentially others)
    "color_mode": None,
    "color_seed": None,
    "text_color": None,
    "back_color": None,
    "color_pressed": None,
    "back_color_pressed": None,
    "power_color": None,
    "show_power_button": None,
}

# panel config
PANEL_CONFIG: dict[str, Any] = {
    "type": None,  # panel type
    "title": "",  # user-facing display name
    "show_in_navigation": True,  # whether this panel appears in navigation
    "key": None,  # internal identifier
    # show_home_button, show_sleep_button, show_notifications_button
    # are not defined here - HAUIPanel.show_button() already falls back
    # to the device-level setting when the key is absent from the panel config.
}

# default config
DEFAULT_CONFIG: dict[str, Any] = {
    # common settings
    "time_format": "%H:%M",
    "date_format": "%A, %d. %B %Y",
    "date_format_locale": "full",
    # device related settings
    "device": copy.deepcopy(DEVICE_CONFIG),
    # multi-device settings (populated at runtime from options)
    "devices": [],
    # connection related settings
    "connection": {
        "heartbeat_interval": 5.0,  # default heartbeat interval in seconds
        "overdue_factor": 2.0,  # Default 2 sec, when to timeout (interval * factor)
    },
    # navigation related settings
    "navigation": {
        "page_timeout": 10.0,  # Default 10 sec, wait for a page to open (sendme result)
    },
    # notification related settings
    "notification": {},
    # update related settings
    "update": {
        # set to false to disable automatic initial installation of tft files
        "auto_install": True,
        # set to true to automatically update display when a new release is available
        "auto_update": False,
        "tft_filename": "nspanel_haui.tft",  # TFT filename to use
        "check_on_connect": False,  # Defaults to false, set to true to check for updates on connect
        "on_connect_delay": 60,  # Defaults to 60 sec, delay before checking for updates on connect
        # set to 0 to disable, set to 86400 for daily checks
        "update_interval": 0,
    },
    # gesture related settings
    "gesture": {},
    # system panels configuration
    # this panels can be also overriden
    "sys_panels": [
        {
            # blank panel
            "type": "blank",
            "show_in_navigation": False,
            "key": "sys_blank",
        },
        {
            # system panel
            "type": "system",
            "show_in_navigation": False,
            "key": "sys_system",
        },
        {
            # panel for settings page
            "type": "system_settings",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "sys_settings",
            "show_home_button": False,
        },
        {
            # panel for about page
            "type": "system_about",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "sys_about",
            "show_home_button": False,
        },
        {
            # popup unlock
            "type": "popup_unlock",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_unlock",
        },
        {
            # popup notify
            "type": "popup_notify",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_notify",
        },
        {
            # popup notifs
            "type": "popup_notifs",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_notifs",
        },
        {
            # popup select
            "type": "popup_select",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_select",
        },
        {
            # popup light
            "type": "popup_light",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_light",
        },
        {
            # popup media
            "type": "popup_media_player",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_media_player",
        },
        {
            # popup vacuum
            "type": "popup_vacuum",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_vacuum",
        },
        {
            # popup climate
            "type": "popup_climate",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_climate",
        },
        {
            # popup timer
            "type": "popup_timer",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_timer",
        },
        {
            # popup cover
            "type": "popup_cover",
            "mode": "popup",
            "show_in_navigation": False,
            "key": "popup_cover",
        },
    ],
    # panels configuration
    "panels": [
        {
            "type": "clock",
        }
    ],
}

# Override the default device name (DEVICE_CONFIG uses "" as a template placeholder)
DEFAULT_CONFIG["device"]["name"] = "nspanel_haui"

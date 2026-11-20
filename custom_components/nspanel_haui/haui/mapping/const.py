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
    DISPLAY_OFF = "esphome.display_off"
    DISPLAY_ON = "esphome.display_on"
    PAGE = "esphome.page"
    COMPONENT = "esphome.component"
    TOUCH_START = "esphome.touch_start"
    TOUCH_END = "esphome.touch_end"
    GESTURE = "esphome.gesture"
    BUTTON_LEFT = "esphome.button_left"
    BUTTON_RIGHT = "esphome.button_right"
    RELAY_LEFT = "esphome.relay_left"
    RELAY_RIGHT = "esphome.relay_right"
    DISPLAY_STATE = "esphome.display_state"
    BUFFER_OVERFLOW = "esphome.buffer_overflow"


# Touch gestures the display reports (the values of ``ESPEvent.GESTURE``).
GESTURES: tuple[str, ...] = ("swipe_left", "swipe_right", "swipe_up", "swipe_down")


class GestureAction(StrEnum):
    """Values of a gesture's ``action`` that are not a panel key."""

    NONE = ""
    NEXT_PANEL = "next_panel"
    PREV_PANEL = "prev_panel"


# Automatic display switches the device settings own: key and ESPHome entity.
# Automatic page switching is hub-side and has no firmware switch.
AUTO_SWITCHES: dict[str, str] = {
    "auto_dimming": "Use Auto-Dimming",
    "auto_display_off": "Use Auto Display-Off",
}

# Page-hold key for automatic page switching; navigation enforces it.
AUTO_PAGE_HOLD = "auto_page"


class ESPAction(StrEnum):
    """ESPHome service actions that HA can call on the device."""

    SEND_COMMAND = "send_command"
    SEND_COMMANDS = "send_commands"
    GOTO_PAGE = "goto_page"
    SET_BRIGHTNESS = "set_brightness"
    UPLOAD_TFT_URL = "upload_tft_url"
    INSTALL_FIRMWARE_URL = "install_firmware_url"
    PLAY_RTTTL = "play_rtttl"
    PLAY_SOUND = "play_sound"
    RESET_LAST_INTERACTION = "reset_last_interaction"


class SysPanelKey(StrEnum):
    """Keys of the fixed system panels (``SYS_PANEL_MAPPING``); they cannot be edited.

    Each member's value is the panel key passed to ``navigation.open_panel()``.
    Using this enum instead of raw strings prevents typos and enables code
    navigation / refactoring.
    """

    SYS_SYSTEM = "sys_system"
    SYS_SETTINGS = "sys_settings"
    SYS_ABOUT = "sys_about"
    SYS_BLANK = "sys_blank"


class PopupPanelKey(StrEnum):
    """Keys of the popups (``POPUP_PANEL_MAPPING``), the system panels that can be edited.

    Each member's value is the panel key passed to ``navigation.open_panel()``.
    """

    POPUP_NOTIFY = "popup_notify"
    POPUP_SELECT = "popup_select"
    POPUP_LIGHT = "popup_light"
    POPUP_MEDIA_PLAYER = "popup_media_player"
    POPUP_VACUUM = "popup_vacuum"
    POPUP_CLIMATE = "popup_climate"
    POPUP_COVER = "popup_cover"
    POPUP_UNLOCK = "popup_unlock"
    POPUP_ALARM = "popup_alarm"
    POPUP_TIMER = "popup_timer"


# Hub-driven popups: an edited copy keeps no PIN or auto-close.
HUB_DRIVEN_PANELS: frozenset[str] = frozenset(
    {
        PopupPanelKey.POPUP_NOTIFY,
        PopupPanelKey.POPUP_SELECT,
        PopupPanelKey.POPUP_UNLOCK,
    }
)


class ESPResponse(StrEnum):
    """Responses published by the ESP device on the recv topic."""

    RES_DEVICE_STATE = "esphome.res_device_state"
    READ_RESPONSE = "esphome.read_response"
    SEND_NOTIFICATION = "esphome.send_notification"


class ESPRequest(StrEnum):
    """Requests that the hub sends to the ESP device on the cmd topic."""

    REQ_DEVICE_STATE = "esphome.req_device_state"
    REQ_VAL = "esphome.req_val"
    REQ_TXT = "esphome.req_txt"


class ESPCommand(StrEnum):
    """Commands that the hub sends to the ESP device on the cmd topic."""

    SEND_COMMAND = "esphome.send_command"
    SEND_COMMANDS = "esphome.send_commands"
    GOTO_PAGE = "esphome.goto_page"


class FirmwareUpdateChannel(StrEnum):
    """Release channel used by the update controller.

    ``stable`` points at GitHub's ``releases/latest`` (which excludes
    prereleases) and suppresses GitHub prerelease notifications; ``dev`` follows
    the manifest of the newest GitHub release, versioned dev prereleases
    included, and allows prerelease notifications.  An explicit
    ``firmware_manifest_url`` always overrides the manifest URL.
    """

    STABLE = "stable"
    DEV = "dev"


# Stable channel: GitHub releases/latest (skips prereleases); dev: the newest
# release in the GitHub release list.
FIRMWARE_MANIFEST_URL = (
    "https://github.com/happydasch/nspanel_haui/releases/latest/download/firmware-manifest.json"
)


class NotifEvent(StrEnum):
    """Notification events handled by the hub."""

    NOTIF_ADD = "notif_add"
    NOTIF_REMOVE = "notif_remove"
    NOTIF_CLEAR = "notif_clear"


# Sound names the firmware's ``play_sound`` script understands (see
# ``esphome/nspanel_haui/scripts_common.yaml``).  Keep both lists in sync.
SOUND_NAMES: frozenset[str] = frozenset(
    {
        "startup",
        "tone",
        "tone_up",
        "tone_down",
        "seq_up",
        "seq_down",
        "notification",
        "alert",
        "alert_fast",
        "elise",
    }
)
DEFAULT_NOTIFICATION_SOUND = "notification"


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

# panel config
PANEL_CONFIG: dict[str, Any] = {
    "type": None,  # panel type
    "title": "",  # user-facing display name
    "theme_id": "",  # empty follows the device theme
    "show_in_navigation": True,  # whether this panel appears in navigation
    # long press anywhere goes back (see HAUIPage._check_long_press_back)
    "long_press_back": False,
    "key": None,  # internal identifier
    # show_home_button/show_idle_button/show_notifications_button fall back to
    # the device setting when absent.
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
    # update related settings
    "update": {
        # Master switch for checks and every firmware/display update path.
        "enabled": True,
        # install the firmware's TFT automatically when stale; false asks first
        "auto_install": True,
        # check for updates on connect (disable with False)
        "check_on_connect": True,
        # seconds before the first update check on connect
        "on_connect_delay": 60,
        # 0 disables periodic checks; 3600 = hourly
        "update_interval": 3600,
        # install a newer firmware automatically (TFT follows after reboot);
        # requires update checks.
        "firmware_auto_update": False,
        # Manifest URL; empty uses the channel (stable by default, dev for
        # prereleases).
        "firmware_update_channel": FirmwareUpdateChannel.STABLE,
        "firmware_manifest_url": FIRMWARE_MANIFEST_URL,
        # seconds an automatic install waits, scheduled, before starting
        "install_delay": 600,
        # failed automatic attempts per version and the retry interval
        "max_attempts": 3,
        "retry_interval": 3600,
        # Firmware version the user skipped: never installed automatically.
        "skipped_firmware_version": "",
    },
    # gesture related settings
    "gesture": {},
    # system panels configuration - populated lazily from page descriptors
    "sys_panels": [],
    # panels configuration
    "panels": [
        {
            "type": "clock",
        }
    ],
}

# Override the default device name (DEVICE_CONFIG uses "" as a template placeholder)
DEFAULT_CONFIG["device"]["name"] = "nspanel_haui"

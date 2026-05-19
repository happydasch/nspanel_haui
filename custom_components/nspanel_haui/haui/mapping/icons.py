"""Icon constants for HAUIPage.

Consolidates all ``ICO_*`` :func:`~haui.utils.icon.get_icon` constants
that were previously scattered across ``HAUIPage`` and individual page
classes into one place.  Pages import individual constants as needed.
"""

from __future__ import annotations

from typing import Final

from ..utils.icon import get_icon

# Shared / base-page icons
ICO_DEFAULT: Final[str] = get_icon("mdi:alert-circle-outline")
ICO_NAV_PREV: Final[str] = get_icon("mdi:chevron-left")
ICO_NAV_NEXT: Final[str] = get_icon("mdi:chevron-right")
ICO_NAV_UP: Final[str] = get_icon("mdi:chevron-up")
ICO_NAV_CLOSE: Final[str] = get_icon("mdi:close")
ICO_NAV_HOME: Final[str] = get_icon("mdi:home-outline")
ICO_NAV_MESSAGE: Final[str] = get_icon("mdi:email-outline")
ICO_ZOOM: Final[str] = get_icon("mdi:loupe")
ICO_LOCKED: Final[str] = get_icon("mdi:lock-outline")
ICO_UNLOCKED: Final[str] = get_icon("mdi:lock-open-variant-outline")
ICO_PASSWORD: Final[str] = get_icon("mdi:circle-medium")
ICO_ENTITY_POWER: Final[str] = get_icon("mdi:power")
ICO_ENTITY_UNAVAILABLE: Final[str] = get_icon("mdi:cancel")
ICO_PREV_PAGE: Final[str] = get_icon("mdi:chevron-double-up")
ICO_NEXT_PAGE: Final[str] = get_icon("mdi:chevron-double-down")
ICO_PREV_MESSAGE: Final[str] = get_icon("mdi:chevron-double-left")
ICO_NEXT_MESSAGE: Final[str] = get_icon("mdi:chevron-double-right")
ICO_MESSAGE: Final[str] = get_icon("mdi:email")
ICO_SLEEP: Final[str] = get_icon("mdi:sleep")
ICO_ABOUT: Final[str] = get_icon("mdi:information-outline")

# ClimatePage icons
ICO_UP: Final[str] = get_icon("mdi:chevron-up")
ICO_DOWN: Final[str] = get_icon("mdi:chevron-down")
ICO_FAN: Final[str] = get_icon("mdi:fan")
ICO_PRESET: Final[str] = get_icon("mdi:view-list")
ICO_SWING: Final[str] = get_icon("mdi:arrow-all")
ICO_POWER: Final[str] = get_icon("mdi:power")

# LightPage icons
ICO_BRIGHTNESS: Final[str] = get_icon("mdi:brightness-6")
ICO_COLOR: Final[str] = get_icon("mdi:palette")
ICO_COLOR_TEMP: Final[str] = get_icon("mdi:thermometer")
ICO_EFFECT: Final[str] = get_icon("mdi:fire")

# MediaPage icons
ICO_PLAY: Final[str] = get_icon("mdi:play")
ICO_PAUSE: Final[str] = get_icon("mdi:pause")
ICO_STOP: Final[str] = get_icon("mdi:stop")
ICO_PREV: Final[str] = get_icon("mdi:skip-previous")
ICO_NEXT: Final[str] = get_icon("mdi:skip-next")
ICO_REPEAT: Final[str] = get_icon("mdi:repeat")
ICO_REPEAT_ONE: Final[str] = get_icon("mdi:repeat-once")
ICO_REPEAT_OFF: Final[str] = get_icon("mdi:repeat-off")
ICO_SHUFFLE: Final[str] = get_icon("mdi:shuffle")
ICO_SHUFFLE_DISABLED: Final[str] = get_icon("mdi:shuffle-disabled")
ICO_VOLUME_DOWN: Final[str] = get_icon("mdi:volume-minus")
ICO_VOLUME_UP: Final[str] = get_icon("mdi:volume-plus")
ICO_SELECT_SOURCE: Final[str] = get_icon("mdi:speaker")
ICO_SELECT_MEDIA: Final[str] = get_icon("mdi:playlist-music")
ICO_SELECT_GROUP: Final[str] = get_icon("mdi:group")

# VacuumPage icons
ICO_LOCATE: Final[str] = get_icon("mdi:map-marker")
ICO_HOME: Final[str] = get_icon("mdi:home")
ICO_BATTERY: Final[str] = get_icon("mdi:battery")

# TimerPage icons
ICO_START: Final[str] = get_icon("mdi:play")
ICO_RESET: Final[str] = get_icon("mdi:close")
ICO_TIMER_OFF: Final[str] = get_icon("mdi:timer-off-outline")
ICO_TIMER_FINISHED: Final[str] = get_icon("mdi:timer-check")

# QRPage icons
ICO_WIFI: Final[str] = get_icon("mdi:wifi")
ICO_KEY: Final[str] = get_icon("mdi:key")

# RowPage icons
ICO_COVER_UP: Final[str] = get_icon("mdi:chevron-up")
ICO_COVER_DOWN: Final[str] = get_icon("mdi:chevron-down")
ICO_COVER_STOP: Final[str] = get_icon("mdi:stop")

# ClockTwoPage icons
ICO_SPECIAL: Final[str] = get_icon("mdi:circle-medium")

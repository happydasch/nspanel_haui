COLORS = {
    # default colors
    "header_background": 6339,  # [24, 24, 24]
    "header_text": 65535,  # [255, 255, 255]
    "header_accent": 62694,  # [246, 157, 49]
    "background": 6339,  # [24, 24, 24]
    "text": 55002,  # [213, 218, 213]
    "text_inactive": 29582,  # [115, 115, 115] #737373
    "text_disabled": 12678,  # [49, 49, 49]
    "component_text": 65535,  # [255, 255, 255]
    "component_pressed": 12678,  # [49, 49, 49]
    "component_active": 19773,  # [74, 165, 238]
    "component_active_dark": 15416,  # [59, 134, 195] #3b86c3
    "component_accent": 62694,  # [246, 157, 49]
    "component_background": 8452,  # [34, 34, 34]
    # entity
    "entity_on": 65222,  # [253, 216, 53] #fdd835
    "entity_off": 17299,  # [68, 115, 158] #44739e
    "entity_unavailable": 29582,  # [115, 115, 115] #737373
}

# ──────────────────────────────────────────────────────────────────────────
# Domain color palettes
#
# These are fixed, non-overridable constants owned by their feature/page.
# They are NOT part of the global ``COLORS`` theme and are not exposed in the
# device color dialog. Each is keyed by the entity/condition state (prefix
# stripped) and imported directly by its page plus the shared entity-icon
# resolver in ``haui/utils/item.py``.
# ──────────────────────────────────────────────────────────────────────────

# weather conditions — used by the weather page forecast and by weather
# entity icons (e.g. on the clock page) via the entity-color resolver.
WEATHER_COLORS = {
    "default": 65535,  # [255, 255, 255] white: default
    "clear_night": 38060,  # [148, 148, 98] yellow grey: clear-night
    "sunny": 65504,  # [255, 255, 0] bright-yellow: sunny
    "partlycloudy": 38066,  # [148, 148, 148] 50% grey: partlycloudy
    "windy": 38066,  # [148, 148, 148] 50% grey: windy
    "windy_variant": 64495,  # [255, 125, 123] red grey: windy-variant
    "rainy": 38047,  # [98, 97, 255] light-blue: rainy
    "pouring": 27519,  # [49, 49, 255] blue: pouring
    "lightning": 65120,  # [255, 206, 0] yellow: lightning
    "lightning_rainy": 50400,  # [197, 157, 0] dark-yellow: lightning-rainy
    "hail": 65535,  # [255, 255, 255] white: hail
    "snowy": 65535,  # [255, 255, 255] white: snowy
    "snowy_rainy": 38079,  # [148, 148, 255] light-blue-grey: snowy-rainy
}

# alarm states — used by the alarm page armed indicator and by
# alarm_control_panel entity icons via the entity-color resolver.
ALARM_COLORS = {
    "armed": 55907,  # [223, 76, 30] #df4c1e
    "disarmed": 3334,  # [8, 161, 49] #8a131
    "arming": 62880,  # [244, 180, 0] #f4b400
}

# climate/HVAC modes — used by the climate page mode buttons and by climate
# entity icons via the entity-color resolver.
CLIMATE_COLORS = {
    "auto": 1024,  # [0, 129, 0] auto
    "heat_cool": 1024,  # [0, 129, 0] heat_cool
    "heat": 64512,  # [255, 129, 0] heat
    "off": 35921,  # [139, 139, 139] off
    "cool": 11487,  # [41, 153, 255] cool
    "dry": 60897,  # [238, 190, 8] dry
    "fan_only": 35921,  # [139, 139, 139] fan_only
}


class ColorTheme:
    """Per-device color theme that merges user overrides with COLORS defaults.

    Provides a single ``get(key)`` method so that callers always receive the
    overridden value (if set) or the built-in COLORS default.

    Only the global ``COLORS`` palette is overridable; domain palettes
    (weather/alarm/climate) are fixed constants and are not handled here.
    """

    __slots__ = ("_overrides",)

    def __init__(self, overrides: dict[str, int] | None = None) -> None:
        self._overrides = overrides if overrides is not None else {}

    def get(self, key: str) -> int:
        """Return the overridden color for *key*, falling back to COLORS.

        Args:
            key: A key from the ``COLORS`` dict (e.g. ``"background"``).

        Returns:
            RGB565 integer color value.
        """
        return self._overrides.get(key, COLORS[key])

    @property
    def all(self) -> dict[str, int]:
        """Return the complete merged palette (COLORS defaults + overrides)."""
        return {**COLORS, **self._overrides}


def make_color_theme(overrides: dict[str, int] | None = None) -> ColorTheme:
    """Factory that creates a :class:`ColorTheme` from optional overrides.

    Args:
        overrides: A dict mapping color keys to RGB565 ints, or ``None``.
    """
    return ColorTheme(overrides)

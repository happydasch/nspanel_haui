COLORS = {
    # default colors
    "header_background": 6339,  # [24, 24, 24]
    "header_text": 65535,  # [255, 255, 255]
    "background": 6339,  # [24, 24, 24]
    "text": 55002,  # [213, 218, 213]
    "text_inactive": 29582,  # [115, 115, 115] #737373
    "text_disabled": 12678,  # [49, 49, 49]
    "component_text": 65535,  # [255, 255, 255]
    "component_pressed": 12678,  # [49, 49, 49]
    "component_active": 19773,  # [74, 165, 238]
    "component_accent": 62694,  # [246, 157, 49]
    "component_background": 8452,  # [34, 34, 34]
    # weather
    "weather_default": 65535,  # [255, 255, 255] white: default
    "weather_clear_night": 38060,  # [148, 148, 98] yellow grey: clear-night
    "weather_sunny": 65504,  # [255, 255, 0] bright-yellow: sunny
    "weather_partlycloudy": 38066,  # [148, 148, 148] 50% grey: partlycloudy
    "weather_windy": 38066,  # [148, 148, 148] 50% grey: windy
    "weather_windy_variant": 64495,  # [255, 125, 123] red grey: windy-variant
    "weather_rainy": 38047,  # [98, 97, 255] light-blue: rainy
    "weather_pouring": 27519,  # [49, 49, 255] blue: pouring
    "weather_lightning": 65120,  # [255, 206, 0] yellow: lightning
    "weather_lightning_rainy": 50400,  # [197, 157, 0] dark-yellow: lightning-rainy
    "weather_hail": 65535,  # [255, 255, 255] white: hail
    "weather_snowy": 65535,  # [255, 255, 255] white: snowy
    "weather_snowy_rainy": 38079,  # [148, 148, 255] light-blue-grey: snowy-rainy
    # entity
    "entity_on": 65222,  # [253, 216, 53] #fdd835
    "entity_off": 17299,  # [68, 115, 158] #44739e
    "entity_unavailable": 29582,  # [115, 115, 115] #737373
    # alarm
    "alarm_armed": 55907,  # [223, 76, 30] #df4c1e
    "alarm_disarmed": 3334,  # [8, 161, 49] #8a131
    "alarm_arming": 62880,  # [244, 180, 0] #f4b400
    # climate
    "climate_auto": 1024,  # [0, 129, 0] auto
    "climate_heat_cool": 1024,  # [0, 129, 0] heat_cool
    "climate_heat": 64512,  # [255, 129, 0] heat
    "climate_off": 35921,  # [139, 139, 139] off
    "climate_cool": 11487,  # [41, 153, 255] cool
    "climate_dry": 60897,  # [238, 190, 8] dry
    "climate_fan_only": 35921,  # [139, 139, 139] fan_only
}


class ColorTheme:
    """Per-device color theme that merges user overrides with COLORS defaults.

    Provides a single ``get(key)`` method so that callers always receive the
    overridden value (if set) or the built-in COLORS default.
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

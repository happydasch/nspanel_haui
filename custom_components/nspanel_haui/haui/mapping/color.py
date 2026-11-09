from __future__ import annotations

import re
from typing import Any

from .background import scheme_background_picture_id

COLORS = {
    # default colors
    # 0.4 dark theme: page < header < cards < pressed, each one step lighter,
    # on 8-step greys so the 5/6/5-bit display renders them neutral.
    "header_background": 6339,  # [24, 24, 24]
    "header_text": 65535,  # [255, 255, 255]
    "header_accent": 62694,  # [246, 157, 49]
    "background": 4226,  # [16, 16, 16]
    "text": 59164,  # [224, 224, 224]
    "text_inactive": 29582,  # [115, 115, 115] #737373
    "text_disabled": 12678,  # [49, 49, 49]
    "component_text": 65535,  # [255, 255, 255]
    "component_pressed": 12678,  # [49, 49, 49]
    "component_active": 19773,  # [74, 165, 238]
    "component_active_dark": 15416,  # [59, 134, 195] #3b86c3
    "component_accent": 62694,  # [246, 157, 49]
    "component_background": 10565,  # [40, 40, 40]
    # entity
    "entity_on": 65222,  # [253, 216, 53] #fdd835
    "entity_off": 17299,  # [68, 115, 158] #44739e
    "entity_unavailable": 29582,  # [115, 115, 115] #737373
}

# ──────────────────────────────────────────────────────────────────────────
# Built-in domain colors seed the editable color schemes. Each scheme carries
# both dark- and light-background variants for the three stateful domains.
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


# Fixed icon colors on a light panel background. The original palettes above
# remain the dark-background variants.
WEATHER_COLORS_LIGHT = {
    "default": 16904,  # #424242
    "clear_night": 33698,  # #827717
    "sunny": 39840,  # #9e7700
    "partlycloudy": 25356,  # #616161
    "windy": 25356,  # #616161
    "windy_variant": 49477,  # #c62828
    "rainy": 4920,  # #1565c0
    "pouring": 2612,  # #0d47a1
    "lightning": 39840,  # #9e7700
    "lightning_rainy": 31401,  # #795548
    "hail": 16904,  # #424242
    "snowy": 16904,  # #424242
    "snowy_rainy": 17100,  # #455a64
}

ALARM_COLORS_LIGHT = {
    "armed": 49477,  # #c62828
    "disarmed": 11238,  # #2e7d32
    "arming": 39840,  # #9e7700
}

CLIMATE_COLORS_LIGHT = {
    "auto": 11238,  # #2e7d32
    "heat_cool": 11238,  # #2e7d32
    "heat": 47521,  # #bf360c
    "off": 25356,  # #616161
    "cool": 4920,  # #1565c0
    "dry": 39840,  # #9e7700
    "fan_only": 25356,  # #616161
}

_ICON_COLOR_PALETTES = {
    "dark": {
        "weather": WEATHER_COLORS,
        "alarm": ALARM_COLORS,
        "climate": CLIMATE_COLORS,
    },
    "light": {
        "weather": WEATHER_COLORS_LIGHT,
        "alarm": ALARM_COLORS_LIGHT,
        "climate": CLIMATE_COLORS_LIGHT,
    },
}


# Built-in schemes are the runtime source for both the editor's color picker
# and the page/entity color resolvers. Values use RGB565 throughout.
_LIGHT_COLOR_OVERRIDES = {
    "header_background": 63390,
    "header_text": 4226,
    "background": 65535,
    "text": 4226,
    "text_inactive": 29614,
    "text_disabled": 50712,
    "component_text": 4226,
    "component_pressed": 54970,
    "component_background": 61309,
}
_WHITE_COLOR_OVERRIDES = {**_LIGHT_COLOR_OVERRIDES, "header_background": 65535}
_BLACK_COLOR_OVERRIDES = {
    "header_background": 0,
    "background": 0,
    "component_background": 4226,
    "component_pressed": 8452,
}


def _builtin_color_scheme(name: str, overrides: dict[str, int]) -> dict[str, Any]:
    return {
        "name": name,
        "colors": {**COLORS, **overrides},
        "icons": _ICON_COLOR_PALETTES,
    }


BUILTIN_COLOR_SCHEMES: dict[str, dict] = {
    "dark": _builtin_color_scheme("Dark", {}),
    "light": _builtin_color_scheme("Light", _LIGHT_COLOR_OVERRIDES),
    "white": _builtin_color_scheme("White", _WHITE_COLOR_OVERRIDES),
    "black": _builtin_color_scheme("Black", _BLACK_COLOR_OVERRIDES),
}

COLOR_SCHEME_VERSION = 1
COLOR_SCHEME_KEYS: dict[str, Any] = {
    "colors": set(COLORS),
    "icons": {
        variant: {domain: set(palette) for domain, palette in _ICON_COLOR_PALETTES[variant].items()}
        for variant in _ICON_COLOR_PALETTES
    },
}


def validate_color_schemes(schemes: Any) -> dict[str, dict]:
    """Validate a mapping of custom scheme IDs to complete semantic palettes."""
    if not isinstance(schemes, dict):
        raise ValueError("color_schemes must be an object")
    validated: dict[str, dict] = {}
    for scheme_id, scheme in schemes.items():
        if not isinstance(scheme_id, str) or not scheme_id or scheme_id in BUILTIN_COLOR_SCHEMES:
            raise ValueError(f"Invalid or reserved color scheme ID: {scheme_id!r}")
        if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", scheme_id) is None:
            raise ValueError(f"Invalid color scheme ID: {scheme_id!r}")
        if not isinstance(scheme, dict) or not isinstance(scheme.get("name"), str):
            raise ValueError(f"Color scheme {scheme_id!r} needs a name")
        name = scheme["name"].strip()
        if not name or len(name) > 64:
            raise ValueError(f"Color scheme {scheme_id!r} needs a name of 1–64 characters")
        colors = scheme.get("colors")
        icons = scheme.get("icons")
        if not isinstance(colors, dict) or set(colors) != COLOR_SCHEME_KEYS["colors"]:
            raise ValueError(f"Color scheme {scheme_id!r} must define every semantic color")
        if not isinstance(icons, dict) or set(icons) != set(COLOR_SCHEME_KEYS["icons"]):
            raise ValueError(f"Color scheme {scheme_id!r} must define dark and light icon colors")
        normalized_colors = _validate_scheme_colors(colors, f"{scheme_id}.colors")
        normalized_icons: dict[str, dict[str, dict[str, int]]] = {}
        for variant, domains in COLOR_SCHEME_KEYS["icons"].items():
            values_by_domain = icons.get(variant)
            if not isinstance(values_by_domain, dict) or set(values_by_domain) != set(domains):
                raise ValueError(f"Color scheme {scheme_id!r} has incomplete {variant} icon colors")
            normalized_icons[variant] = {}
            for domain, keys in domains.items():
                values = values_by_domain.get(domain)
                if not isinstance(values, dict) or set(values) != keys:
                    raise ValueError(
                        f"Color scheme {scheme_id!r} has incomplete {variant} {domain} colors"
                    )
                normalized_icons[variant][domain] = _validate_scheme_colors(
                    values, f"{scheme_id}.icons.{variant}.{domain}"
                )
        validated[scheme_id] = {
            "name": name,
            "colors": normalized_colors,
            "icons": normalized_icons,
        }
    names = [scheme["name"].casefold() for scheme in validated.values()]
    if len(names) != len(set(names)):
        raise ValueError("Color scheme names must be unique")
    builtin_names = {scheme["name"].casefold() for scheme in BUILTIN_COLOR_SCHEMES.values()}
    if builtin_names.intersection(names):
        raise ValueError("Custom color scheme names must not duplicate built-in schemes")
    return validated


def _validate_scheme_colors(values: dict, path: str) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535:
            raise ValueError(f"{path}.{key} must be an RGB565 integer from 0 to 65535")
        normalized[key] = value
    return normalized


# Program.s globals the solid-colour pages paint themselves from in their
# Preinitialize event, before the display draws them, keyed by ``COLORS`` key.
# The hub sets them right before every page switch (``ColorTheme.display_commands``)
# so a page shows the device's theme from its first frame. The Preinitialize code
# is generated from the HMI by ``scripts/hmi_layout/gen_virtual_layout.py
# --theme-code``; Program.s declares each global with its ``COLORS`` default.
THEME_GLOBALS = {
    "background": "thmBg",
    "header_background": "thmHdrBg",
    "header_text": "thmHdrTxt",
    "component_pressed": "thmPressed",
    "component_background": "thmCompBg",
}


class ColorTheme:
    """Per-device color theme resolved from its selected semantic scheme."""

    __slots__ = ("_overrides", "scheme", "scheme_id", "palette")

    def __init__(
        self,
        overrides: dict[str, int],
        scheme: str = "dark",
        palette: dict | None = None,
        *,
        scheme_id: str | None = None,
    ) -> None:
        self._overrides = overrides
        self.scheme = scheme if scheme in ("dark", "light") else "dark"
        self.scheme_id = scheme_id or scheme
        self.palette = palette or BUILTIN_COLOR_SCHEMES.get(
            self.scheme_id, BUILTIN_COLOR_SCHEMES["dark"]
        )

    def get(self, key: str) -> int:
        """Return the device override or the selected scheme's semantic color."""
        return self._overrides.get(key, self.get_scheme_color(key))

    def get_scheme_color(self, key: str) -> int:
        """Return a selected-scheme color without applying legacy device overrides."""
        return self.palette["colors"].get(key, COLORS[key])

    def background_variant(self) -> str:
        """Return dark/light contrast based on the selected palette's background role."""
        color = self.get("background")
        red = ((color >> 11) & 0x1F) * 255 // 31
        green = ((color >> 5) & 0x3F) * 255 // 63
        blue = (color & 0x1F) * 255 // 31
        brightness = (2126 * red + 7152 * green + 722 * blue) // 10000
        return "light" if brightness >= 128 else "dark"

    def background_picture_id(self) -> int:
        """Return the solid HMI picture matching the active palette's brightness."""
        return scheme_background_picture_id(self.background_variant())

    def get_background_color(self, key: str, variant: str) -> int:
        """Return the fixed contrast palette paired with a page background."""
        scheme = BUILTIN_COLOR_SCHEMES[variant]
        return scheme["colors"].get(key, COLORS[key])

    def get_icon_color(self, domain: str, key: str, scheme: str | None = None) -> int | None:
        """Return the selected scheme's domain/state color for a dark or light background."""
        variant = scheme or self.scheme
        if variant not in ("dark", "light"):
            variant = self.scheme
        return self.palette["icons"].get(variant, {}).get(domain, {}).get(key)

    def display_commands(self) -> list[str]:
        """Nextion commands that set the display's theme globals (``THEME_GLOBALS``)."""
        return [f"{name}={self.get(key)}" for key, name in THEME_GLOBALS.items()]

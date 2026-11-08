"""Tests for haui/mapping/color.py — COLORS dict, ColorTheme, parse_color_value."""

from __future__ import annotations

from nspanel_haui.haui.mapping.background import BACKGROUND_COLOR_SCHEMES, BACKGROUNDS
from nspanel_haui.haui.mapping.color import (
    ALARM_COLORS,
    ALARM_COLORS_LIGHT,
    BUILTIN_COLOR_SCHEMES,
    CLIMATE_COLORS,
    CLIMATE_COLORS_LIGHT,
    COLORS,
    THEME_GLOBALS,
    WEATHER_COLORS,
    WEATHER_COLORS_LIGHT,
    ColorTheme,
)
from nspanel_haui.haui.utils.color import parse_color_value, rgb565_to_rgb


def test_backgrounds_have_an_explicit_contrast_scheme() -> None:
    assert set(BACKGROUND_COLOR_SCHEMES) == set(BACKGROUNDS)
    assert all(value in {"dark", "light"} for value in BACKGROUND_COLOR_SCHEMES.values())


# ============================================================================
# COLORS dict integrity
# ============================================================================


def test_colors_all_values_in_rgb565_range() -> None:
    """Every COLORS value must be a valid RGB565 int (0-65535)."""
    for key, value in COLORS.items():
        assert isinstance(key, str), f"Key {key!r} must be str"
        assert isinstance(value, int), f"{key} value {value!r} must be int"
        assert 0 <= value <= 65535, f"{key} value {value} is outside RGB565 range"


def test_colors_only_global_keys() -> None:
    """COLORS holds only the 15 global keys; domain colors live elsewhere."""
    defaults = {
        "background",
        "header_background",
        "header_text",
        "header_accent",
        "text",
        "text_inactive",
        "text_disabled",
        "component_text",
        "component_pressed",
        "component_active",
        "component_active_dark",
        "component_accent",
        "component_background",
    }
    entity = {"entity_on", "entity_off", "entity_unavailable"}
    assert COLORS.keys() == defaults | entity
    assert len(COLORS) == 16
    # domain colors must NOT leak into the global palette
    assert "weather_sunny" not in COLORS
    assert "alarm_armed" not in COLORS
    assert "climate_heat" not in COLORS


def test_domain_palettes_present_and_valid() -> None:
    """Weather/alarm/climate palettes have expected keys and valid RGB565 values."""
    assert len(WEATHER_COLORS) == 13
    assert {"default", "sunny", "clear_night"} <= WEATHER_COLORS.keys()
    assert ALARM_COLORS.keys() == {"armed", "disarmed", "arming"}
    assert len(CLIMATE_COLORS) == 7
    assert {"auto", "heat", "cool", "off", "heat_cool", "dry", "fan_only"} == CLIMATE_COLORS.keys()
    for palette in (WEATHER_COLORS, ALARM_COLORS, CLIMATE_COLORS):
        for key, value in palette.items():
            assert isinstance(value, int), f"{key} value {value!r} must be int"
            assert 0 <= value <= 65535, f"{key} value {value} outside RGB565 range"


def test_light_domain_palettes_have_matching_keys_and_valid_values() -> None:
    for dark, light in (
        (WEATHER_COLORS, WEATHER_COLORS_LIGHT),
        (ALARM_COLORS, ALARM_COLORS_LIGHT),
        (CLIMATE_COLORS, CLIMATE_COLORS_LIGHT),
    ):
        assert dark.keys() == light.keys()
        assert all(0 <= color <= 65535 for color in light.values())


# ============================================================================
# ColorTheme
# ============================================================================


class TestColorTheme:
    def test_get_returns_default_when_no_overrides(self) -> None:
        theme = ColorTheme({})
        assert theme.get("background") == COLORS["background"]
        assert theme.get("text") == COLORS["text"]

    def test_get_returns_override(self) -> None:
        theme = ColorTheme({"background": 0, "text": 65535})
        assert theme.get("background") == 0
        assert theme.get("text") == 65535

    def test_get_fallback_when_key_not_overridden(self) -> None:
        theme = ColorTheme({"background": 0})
        assert theme.get("text") == COLORS["text"]

    def test_fixed_icon_colors_follow_theme_scheme(self) -> None:
        dark = ColorTheme({})
        light = ColorTheme({}, "light")

        assert dark.get_icon_color("weather", "sunny") == WEATHER_COLORS["sunny"]
        assert light.get_icon_color("weather", "sunny") == WEATHER_COLORS_LIGHT["sunny"]
        assert light.get_icon_color("alarm", "armed") == ALARM_COLORS_LIGHT["armed"]
        assert light.get_icon_color("climate", "heat") == CLIMATE_COLORS_LIGHT["heat"]
        assert light.get_icon_color("climate", "unknown") is None
        assert light.get_icon_color("climate", "heat", "dark") == CLIMATE_COLORS["heat"]

    def test_selected_palette_controls_global_and_domain_colors(self) -> None:
        from nspanel_haui.haui.mapping.color import BUILTIN_COLOR_SCHEMES

        light = ColorTheme({}, "light")
        assert light.get("background") == BUILTIN_COLOR_SCHEMES["light"]["colors"]["background"]
        assert light.get_icon_color("weather", "sunny") == WEATHER_COLORS_LIGHT["sunny"]

        custom = {
            "name": "Custom",
            "colors": {**BUILTIN_COLOR_SCHEMES["dark"]["colors"], "background": 1234},
            "icons": {
                "dark": {
                    **BUILTIN_COLOR_SCHEMES["dark"]["icons"]["dark"],
                    "weather": {**WEATHER_COLORS, "sunny": 4321},
                },
                "light": BUILTIN_COLOR_SCHEMES["dark"]["icons"]["light"],
            },
        }
        theme = ColorTheme({}, "custom", custom)
        assert theme.get("background") == 1234
        assert theme.get_icon_color("weather", "sunny", "light") == 39840

    def test_white_builtin_scheme_has_white_page_and_header(self) -> None:
        scheme = BUILTIN_COLOR_SCHEMES["white"]["colors"]

        assert scheme["background"] == 65535
        assert scheme["header_background"] == 65535
        assert scheme["header_text"] == 4226

    def test_custom_schemes_are_validated_as_complete_rgb565_palettes(self) -> None:
        from copy import deepcopy

        import pytest
        from nspanel_haui.haui.mapping.color import BUILTIN_COLOR_SCHEMES, validate_color_schemes

        valid = deepcopy(BUILTIN_COLOR_SCHEMES["dark"])
        valid["name"] = "Custom"
        assert validate_color_schemes({"custom": valid}) == {"custom": valid}

        invalid = deepcopy(valid)
        invalid["colors"]["background"] = True
        with pytest.raises(ValueError, match="RGB565"):
            validate_color_schemes({"custom": invalid})

        with pytest.raises(ValueError, match="every semantic color"):
            validate_color_schemes({"custom": {"name": "Incomplete", "colors": {}, "icons": {}}})

    def test_background_picture_matches_selected_scheme_brightness(self) -> None:
        dark = ColorTheme({}, "dark")
        light = ColorTheme({}, "light")
        custom_light = ColorTheme(
            {},
            "custom",
            {
                "name": "Custom Light",
                "colors": {**COLORS, "background": 65535},
                "icons": BUILTIN_COLOR_SCHEMES["dark"]["icons"],
            },
        )

        assert dark.background_picture_id() == BACKGROUNDS["dark"]
        assert light.background_picture_id() == BACKGROUNDS["light"]
        assert custom_light.background_picture_id() == BACKGROUNDS["light"]
        assert all(theme.background_picture_id() != 0 for theme in (dark, light, custom_light))

    def test_display_commands_set_every_theme_global(self) -> None:
        """The display's theme globals get the device's colours, defaults included."""
        theme = ColorTheme({"background": 0, "component_pressed": 1234})

        commands = theme.display_commands()

        assert commands == [f"{name}={theme.get(key)}" for key, name in THEME_GLOBALS.items()]
        assert "thmBg=0" in commands
        assert "thmPressed=1234" in commands
        assert f"thmHdrBg={COLORS['header_background']}" in commands

    def test_theme_globals_name_palette_keys(self) -> None:
        assert set(THEME_GLOBALS) <= COLORS.keys()
        # Nextion variable names: letters and digits, at most 14 characters
        assert all(name.isalnum() and len(name) <= 14 for name in THEME_GLOBALS.values())


# ============================================================================
# parse_color_value
# ============================================================================


class TestParseColorValue:
    def test_returns_int_directly(self) -> None:
        assert parse_color_value(65535) == 65535
        assert parse_color_value(0) == 0

    def test_rgb_list(self) -> None:
        # [255, 255, 255] -> rgb565
        assert parse_color_value([255, 255, 255]) == 65535

    def test_rgb_tuple(self) -> None:
        assert parse_color_value((255, 255, 255)) == 65535

    def test_hex_string(self) -> None:
        assert parse_color_value("#FFFFFF") == 65535
        assert parse_color_value("#000000") == 0

    def test_hex_string_lowercase(self) -> None:
        assert parse_color_value("#ffffff") == 65535

    def test_int_string(self) -> None:
        assert parse_color_value("65535") == 65535
        assert parse_color_value("0") == 0

    def test_empty_string_returns_zero(self) -> None:
        assert parse_color_value("") == 0
        assert parse_color_value("  ") == 0

    def test_invalid_string_returns_zero(self) -> None:
        assert parse_color_value("not-a-color") == 0
        # the pre-editor "[r,g,b]" string format is no longer supported
        assert parse_color_value("[74,165,238]") == 0

    def test_none_value_returns_zero(self) -> None:
        # parse_color_value doesn't accept None in its type hint, but we handle it
        assert parse_color_value(None) == 0  # type: ignore[arg-type]

    def test_hex_roundtrip(self) -> None:
        """Parsing rgb565 -> hex -> color -> rgb565 is idempotent."""
        original = 55002  # a mid-range color
        r, g, b = rgb565_to_rgb(original)
        hex_str = f"#{r:02x}{g:02x}{b:02x}"
        result = parse_color_value(hex_str)
        assert result == original


# ============================================================================
# config_models color_overrides validation
# ============================================================================


class TestColorOverridesValidation:
    def test_color_scheme_defaults_to_dark_and_accepts_light(self) -> None:
        from nspanel_haui.haui.config_models import validate_device_config

        assert validate_device_config({}).color_scheme == "dark"
        assert validate_device_config({"color_scheme": "light"}).color_scheme == "light"

    def test_invalid_color_scheme_is_rejected(self) -> None:
        import pytest
        from nspanel_haui.haui.config_models import validate_device_config
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            validate_device_config({"color_scheme": "sepia"})

    def test_valid_overrides_pass_through(self) -> None:
        from nspanel_haui.haui.config_models import validate_device_config

        cfg = {"color_overrides": {"background": 0, "text": 65535}}
        result = validate_device_config(cfg)
        if result is not None:
            overrides = getattr(result, "color_overrides", None)
            assert overrides == {"background": 0, "text": 65535}

    def test_empty_overrides(self) -> None:
        from nspanel_haui.haui.config_models import validate_device_config

        result = validate_device_config({})
        if result is not None:
            overrides = getattr(result, "color_overrides", None)
            assert overrides == {}

    def test_non_global_keys_dropped(self) -> None:
        """Unknown and domain-color keys are dropped; only global keys survive."""
        from nspanel_haui.haui.config_models import validate_device_config

        cfg = {"color_overrides": {"nonexistent_key": 12345, "weather_sunny": 1, "text": 42}}
        result = validate_device_config(cfg)
        if result is not None:
            overrides = getattr(result, "color_overrides", None)
            assert overrides == {"text": 42}

    def test_out_of_range_clamped(self) -> None:
        from nspanel_haui.haui.config_models import validate_device_config

        cfg = {"color_overrides": {"background": -1, "text": 99999}}
        result = validate_device_config(cfg)
        if result is not None:
            overrides = getattr(result, "color_overrides", None)
            assert overrides["background"] == 0  # clamped
            assert overrides["text"] == 65535  # clamped

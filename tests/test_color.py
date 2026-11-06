"""Tests for haui/mapping/color.py — COLORS dict, ColorTheme, parse_color_value."""

from __future__ import annotations

from nspanel_haui.haui.mapping.color import (
    ALARM_COLORS,
    CLIMATE_COLORS,
    COLORS,
    THEME_GLOBALS,
    WEATHER_COLORS,
    ColorTheme,
)
from nspanel_haui.haui.utils.color import parse_color_value, rgb565_to_rgb

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

"""Tests for the colour tables, ``Theme``, colour parsing, palettes and item icon colours."""

from __future__ import annotations

import logging
import random
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from custom_components.nspanel_haui.haui.config_models import validate_device_config
from custom_components.nspanel_haui.haui.mapping.background import (
    BACKGROUND_VARIANTS,
    BACKGROUNDS,
)
from custom_components.nspanel_haui.haui.mapping.color import (
    ALARM_COLORS,
    ALARM_COLORS_LIGHT,
    BUILTIN_THEMES,
    CLIMATE_COLORS,
    CLIMATE_COLORS_LIGHT,
    COLORS,
    THEME_GLOBALS,
    WEATHER_COLORS,
    WEATHER_COLORS_LIGHT,
    Theme,
)
from custom_components.nspanel_haui.haui.utils.color import (
    generate_color_palette,
    parse_color_value,
    rgb565_to_rgb,
)
from custom_components.nspanel_haui.haui.utils.item import get_item_color


def test_backgrounds_have_an_explicit_contrast_variant() -> None:
    assert set(BACKGROUND_VARIANTS) == set(BACKGROUNDS)
    assert all(value in {"dark", "light"} for value in BACKGROUND_VARIANTS.values())


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
# Theme
# ============================================================================


class TestTheme:
    def test_get_returns_default_theme_colors(self) -> None:
        theme = Theme()
        assert theme.get("background") == COLORS["background"]
        assert theme.get("text") == COLORS["text"]

    def test_get_returns_selected_palette_color(self) -> None:
        theme = Theme("dark", {"colors": {"background": 0, "text": 65535}})
        assert theme.get("background") == 0
        assert theme.get("text") == 65535

    def test_get_falls_back_to_builtin_for_missing_palette_key(self) -> None:
        theme = Theme("dark", {"colors": {"background": 0}})
        assert theme.get("text") == COLORS["text"]

    def test_fixed_icon_colors_follow_theme_variant(self) -> None:
        dark = Theme()
        light = Theme("light")

        assert dark.get_icon_color("weather", "sunny") == WEATHER_COLORS["sunny"]
        assert light.get_icon_color("weather", "sunny") == WEATHER_COLORS_LIGHT["sunny"]
        assert light.get_icon_color("alarm", "armed") == ALARM_COLORS_LIGHT["armed"]
        assert light.get_icon_color("climate", "heat") == CLIMATE_COLORS_LIGHT["heat"]
        assert light.get_icon_color("climate", "unknown") is None
        assert light.get_icon_color("climate", "heat", "dark") == CLIMATE_COLORS["heat"]

    def test_selected_palette_controls_global_and_domain_colors(self) -> None:
        from custom_components.nspanel_haui.haui.mapping.color import BUILTIN_THEMES

        light = Theme("light")
        assert light.get("background") == BUILTIN_THEMES["light"]["colors"]["background"]
        assert light.get_icon_color("weather", "sunny") == WEATHER_COLORS_LIGHT["sunny"]

        custom = {
            "name": "Custom",
            "colors": {**BUILTIN_THEMES["dark"]["colors"], "background": 1234},
            "icons": {
                "dark": {
                    **BUILTIN_THEMES["dark"]["icons"]["dark"],
                    "weather": {**WEATHER_COLORS, "sunny": 4321},
                },
                "light": BUILTIN_THEMES["dark"]["icons"]["light"],
            },
        }
        theme = Theme("dark", custom, theme_id="custom")
        assert theme.get("background") == 1234
        assert theme.get_icon_color("weather", "sunny", "light") == 39840

    def test_white_builtin_theme_has_white_page_and_header(self) -> None:
        theme = BUILTIN_THEMES["white"]["colors"]

        assert theme["background"] == 65535
        assert theme["header_background"] == 65535
        assert theme["header_text"] == 4226

    def test_custom_themes_are_validated_as_complete_rgb565_palettes(self) -> None:
        from copy import deepcopy

        from custom_components.nspanel_haui.haui.mapping.color import (
            BUILTIN_THEMES,
            validate_themes,
        )

        valid = deepcopy(BUILTIN_THEMES["dark"])
        valid["name"] = "Custom"
        assert validate_themes({"custom": valid}) == {"custom": valid}

        invalid = deepcopy(valid)
        invalid["colors"]["background"] = True
        with pytest.raises(ValueError, match="RGB565"):
            validate_themes({"custom": invalid})

        with pytest.raises(ValueError, match="every semantic color"):
            validate_themes({"custom": {"name": "Incomplete", "colors": {}, "icons": {}}})

    def test_background_picture_matches_selected_theme_brightness(self) -> None:
        dark = Theme("dark")
        light = Theme("light")
        custom_light = Theme(
            "dark",
            {
                "name": "Custom Light",
                "colors": {**COLORS, "background": 65535},
                "icons": BUILTIN_THEMES["dark"]["icons"],
            },
            theme_id="custom-light",
        )

        assert dark.background_picture_id() == BACKGROUNDS["dark"]
        assert light.background_picture_id() == BACKGROUNDS["light"]
        assert custom_light.background_picture_id() == BACKGROUNDS["light"]
        assert all(theme.background_picture_id() != 0 for theme in (dark, light, custom_light))

    def test_display_commands_set_every_theme_global(self) -> None:
        """The display's theme globals get the device's colours, defaults included."""
        theme = Theme("dark", {"colors": {**COLORS, "background": 0, "component_pressed": 1234}})

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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (65535, 65535),
        ([255, 255, 255], 65535),
        ((255, 255, 255), 65535),
        ("#FFFFFF", 65535),
        ("#ffffff", 65535),
        ("65535", 65535),
    ],
)
def test_parse_color_value_reads_ints_rgb_triples_and_hex(value: Any, expected: int) -> None:
    assert parse_color_value(value) == expected


# "[74,165,238]" is the pre-editor string format, which is no longer supported.
@pytest.mark.parametrize("value", ["not-a-color", "#12345", "[74,165,238]", "", "  ", None])
def test_an_invalid_color_is_black_and_reported(
    value: Any, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert parse_color_value(value) == 0

    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    assert repr(value) in caplog.records[0].getMessage()


@pytest.mark.parametrize("value", [0, "0", "#000000", (0, 0, 0)])
def test_valid_black_is_not_reported(value: Any, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert parse_color_value(value) == 0

    assert caplog.records == []


def test_hex_roundtrip() -> None:
    """Parsing rgb565 -> hex -> color -> rgb565 is idempotent."""
    original = 55002  # a mid-range color
    r, g, b = rgb565_to_rgb(original)

    assert parse_color_value(f"#{r:02x}{g:02x}{b:02x}") == original


# ============================================================================
# config_models theme_variant validation
# ============================================================================


def test_theme_variant_defaults_to_dark_and_accepts_light() -> None:
    assert validate_device_config({}).theme_variant == "dark"
    assert validate_device_config({"theme_variant": "light"}).theme_variant == "light"


def test_invalid_theme_variant_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_device_config({"theme_variant": "sepia"})


# ============================================================================
# generated palettes
# ============================================================================


def test_palette_generation_leaves_global_rng_alone() -> None:
    random.seed(42)
    expected = random.random()

    random.seed(42)
    generate_color_palette((10, 20, 30), "vibrant", seed=5)
    generate_color_palette((10, 20, 30), "pastel")

    assert random.random() == expected


def test_palette_is_reproducible_for_a_seed() -> None:
    first = generate_color_palette((10, 20, 30), "vibrant", seed=938)
    second = generate_color_palette((10, 20, 30), "vibrant", seed=938)

    assert first == second


# ============================================================================
# item icon colours
# ============================================================================


class _Item:
    def __init__(self, domain: str, state: str, variant: str) -> None:
        self.app = SimpleNamespace(theme=Theme(variant))
        self._entity = SimpleNamespace(attributes={})
        self._domain = domain
        self._state = state

    def has_item(self) -> bool:
        return True

    def get_item(self) -> SimpleNamespace:
        return self._entity

    def get_item_type(self) -> str:
        return self._domain

    def get_item_state(self) -> str:
        return self._state

    def get_icon_color(self, domain: str, key: str, variant: str | None = None) -> int | None:
        return self.app.theme.get_icon_color(domain, key, variant)


@pytest.mark.parametrize(
    ("domain", "state", "light_color"),
    [
        ("weather", "sunny", 39840),
        ("climate", "heat", 47521),
        ("alarm_control_panel", "armed_home", 49477),
    ],
)
def test_domain_icon_colors_follow_light_variant(domain: str, state: str, light_color: int) -> None:
    item = _Item(domain, state, "light")

    assert get_item_color(item, default_color=123) == light_color


def test_panel_background_hint_does_not_override_selected_theme_variant() -> None:
    item = _Item("weather", "sunny", "light")

    assert get_item_color(item, default_color=123, icon_variant="dark") == 65504

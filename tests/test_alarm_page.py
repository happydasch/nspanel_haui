"""Tests for the alarm page keypad styling and content-button fill colors.

Covers the ``keypad_font`` / ``keypad_bg_color`` / ``keypad_text_color`` panel
options, the ``_style_keypad`` helper that applies them to every keypad button,
and ``get_button_colors`` filling enabled content buttons while keeping
disabled ones flat.
"""

import contextlib

from custom_components.nspanel_haui.haui.abstract.mixins.function_btn_mixin import (
    FunctionButtonMixin,
)
from custom_components.nspanel_haui.haui.mapping.color import COLORS
from custom_components.nspanel_haui.haui.mapping.descriptor import PageOption
from custom_components.nspanel_haui.haui.page.alarm import AlarmPage
from custom_components.nspanel_haui.haui.utils.color import parse_color_value


class _FakePanel:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get(self, key, default=None):
        return self._cfg.get(key, default)


# A device theme with its own background and component text colors.
_THEME = {**COLORS, "background": 4479, "component_text": 2016}


class _TestAlarmPage(AlarmPage):
    """AlarmPage with display transport replaced by a command recorder."""

    def __init__(self):
        self.commands = []

    def get_color(self, key):
        return _THEME[key]

    @property
    def rec_cmd(self):
        return contextlib.nullcontext()

    def send_cmd(self, cmd):
        self.commands.append(cmd)


class _ColorPage(FunctionButtonMixin):
    """Minimal host exposing the real theme palette."""

    def __init__(self):
        self._fnc_items = {}

    def log(self, *args, **kwargs):
        pass

    def get_color(self, key):
        return COLORS[key]


def _opt(key):
    return next(o for o in AlarmPage.DESCRIPTOR.options if o.key == key)


def test_keypad_color_options_use_the_device_scheme():
    font = _opt("keypad_font")
    option_keys = {option.key for option in AlarmPage.DESCRIPTOR.options}

    assert isinstance(font, PageOption)
    assert font.kind == "int"
    assert font.default == 2
    assert (
        not {
            "keypad_bg_color",
            "keypad_text_color",
            "arm_button_color",
            "arm_button_back_color",
            "disarm_button_color",
            "disarm_button_back_color",
        }
        & option_keys
    )


def test_style_keypad_applies_theme_colors_to_all_buttons():
    page = _TestAlarmPage()
    page._style_keypad(_FakePanel())

    names = [c.name for c in page._keypad_buttons]
    assert len(names) == 12
    for name in names:
        assert f"{name}.font=2" in page.commands
        assert f"{name}.bco={_THEME['background']}" in page.commands
        assert f"{name}.pco={_THEME['component_text']}" in page.commands


def test_style_keypad_honours_overrides_and_parses_string_color():
    page = _TestAlarmPage()
    page._style_keypad(
        _FakePanel(
            {
                "keypad_font": 5,
                "keypad_bg_color": "#ff0000",
                "keypad_text_color": 12345,
            }
        )
    )

    assert "bKey0.font=5" in page.commands
    assert f"bKey0.bco={parse_color_value('#ff0000')}" in page.commands
    assert "bKey0.pco=12345" in page.commands


def test_get_button_colors_lifts_enabled_buttons_when_pressed():
    page = _ColorPage()
    _color, _color_pressed, back_pressed = page.get_button_colors(True)
    assert back_pressed == COLORS["component_pressed"]


def test_get_button_colors_keeps_disabled_buttons_flat():
    page = _ColorPage()
    _color, _color_pressed, back_pressed = page.get_button_colors(False)
    assert back_pressed == COLORS["background"]

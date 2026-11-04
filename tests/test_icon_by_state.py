"""Pins get_icon_name_by_state for every entity type it handles."""

import pytest
from nspanel_haui.haui.utils.icon import get_icon_name_by_state


@pytest.mark.parametrize(
    ("item_type", "state", "device_class", "icon"),
    [
        ("script", "off", None, "script-text"),
        ("alarm-arm-fail", "", None, "progress-alert"),
        ("weather", "sunny", None, "weather-sunny"),
        ("weather", "no-such-state", None, None),
        ("light", "on", None, "lightbulb"),
        ("light", "off", None, "lightbulb-off"),
        ("input_boolean", "on", None, "check-circle-outline"),
        ("input_boolean", "off", None, "close-circle-outline"),
        ("lock", "unlocked", None, "lock-open"),
        ("lock", "locked", None, "lock"),
        ("sun", "above_horizon", None, "weather-sunset-up"),
        ("sun", "below_horizon", None, "weather-sunset-down"),
        ("alarm_control_panel", "armed_home", None, "shield-home"),
        ("alarm_control_panel", "no-such-state", None, None),
        ("climate", "heat", None, "fire"),
        ("climate", "no-such-state", None, None),
        ("cover", "closed", "garage", "garage"),
        ("cover", "open", "garage", "garage-open"),
        ("cover", "open", None, None),
        ("sensor", "21.5", "temperature", "thermometer"),
        ("sensor", "21.5", None, None),
        ("binary_sensor", "on", "motion", "motion-sensor"),
        ("binary_sensor", "off", "motion", "motion-sensor-off"),
        ("binary_sensor", "on", None, "checkbox-marked-circle"),
        ("binary_sensor", "off", None, "radiobox-blank"),
        ("switch", "on", None, None),
    ],
)
def test_icon_by_state(item_type, state, device_class, icon):
    assert get_icon_name_by_state(item_type, state, device_class) == icon

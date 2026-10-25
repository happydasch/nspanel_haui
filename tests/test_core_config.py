"""HAUIConfig keeps the validated config, not the raw input."""

from __future__ import annotations

import pytest
from nspanel_haui.haui.abstract.haui_config import HAUIConfig


class _App:
    pass


def test_runtime_device_color_overrides_are_clamped_and_coerced() -> None:
    config = {
        "device": {
            "color_overrides": {"background": 70000, "text": "123", "not_a_color": 5},
        },
    }

    cfg = HAUIConfig(_App(), config)

    assert cfg.get("device")["color_overrides"] == {"background": 65535, "text": 123}


def test_device_entry_color_overrides_are_clamped() -> None:
    config = {"devices": [{"name": "panel", "color_overrides": {"background": -1}}]}

    cfg = HAUIConfig(_App(), config)

    assert cfg.get("devices")[0]["color_overrides"] == {"background": 0}


def test_validation_keeps_unvalidated_device_keys() -> None:
    cfg = HAUIConfig(_App(), {"device": {"name": "panel", "page_settle_delay": 0.3}})

    device = cfg.get("device")
    assert device["name"] == "panel"
    assert device["page_settle_delay"] == 0.3
    assert device["panels"] == [{"type": "clock"}]


def test_invalid_device_config_raises() -> None:
    with pytest.raises(ValueError):
        HAUIConfig(_App(), {"device": {"timeout_display_off": "soon"}})

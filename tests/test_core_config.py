"""HAUIConfig keeps the validated config, not the raw input."""

from __future__ import annotations

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_config import HAUIConfig


class _App:
    pass


def test_validation_keeps_unvalidated_device_keys() -> None:
    cfg = HAUIConfig(_App(), {"device": {"name": "panel", "page_settle_delay": 0.3}})

    device = cfg.get("device")
    assert device["name"] == "panel"
    assert device["page_settle_delay"] == 0.3
    assert device["panels"] == [{"type": "clock"}]


def test_invalid_device_config_raises() -> None:
    with pytest.raises(ValueError):
        HAUIConfig(_App(), {"device": {"timeout_display_off": "soon"}})

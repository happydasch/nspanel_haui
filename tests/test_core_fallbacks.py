"""Bad config values are reported, not silently replaced."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pytest

from custom_components.nspanel_haui.haui.device import HAUIDevice
from custom_components.nspanel_haui.haui.utils.color import parse_color_value

# --- schedule -----------------------------------------------------------------


class _ESPHome:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, topic: str, payload: str) -> None:
        self.published.append((topic, payload))


class _App:
    def __init__(self) -> None:
        esphome = type("Ctrl", (), {})()
        esphome.esphome = _ESPHome()
        self.controller: dict[str, Any] = {"esphome": esphome}

    def now(self) -> datetime:
        return datetime(2026, 1, 1, 23, 0)

    def log(self, msg: str, **kwargs: Any) -> None:
        pass


def test_a_malformed_schedule_entry_raises_instead_of_being_skipped() -> None:
    """Saved settings are validated; an entry that slipped past must not be ignored."""
    app = _App()
    entry = {
        "start": "10pm",
        "end": "07:00",
        "sound": False,
        "brightness": 20,
        "display_off": True,
        "timeout_display_off": 30,
    }
    device = HAUIDevice(app, {"schedule": [entry]})

    with pytest.raises(ValueError, match="10pm"):
        device.play_sound("notification")

    assert app.controller["esphome"].esphome.published == []


# --- parse_color_value ----------------------------------------------------------


@pytest.mark.parametrize("value", ["not-a-color", "#12345", "", None])
def test_invalid_color_is_reported(value: Any, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert parse_color_value(value) == 0

    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    assert repr(value) in caplog.records[0].getMessage()


@pytest.mark.parametrize("value", [0, "0", "#000000", (0, 0, 0)])
def test_valid_black_is_not_reported(value: Any, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert parse_color_value(value) == 0

    assert caplog.records == []


# --- render_template ---------------------------------------------------------


class _TemplateApp:
    def __init__(self) -> None:
        self.rendered: list[str] = []

    def render_template(self, template: str) -> str:
        self.rendered.append(template)
        # the caller wraps templates in HTML comment markers
        return template.replace("<!--", "").replace("-->", "")


def test_template_prefix_is_no_longer_stripped() -> None:
    """A literal ``template:`` prefix is no longer treated as a marker.

    The legacy ``template:`` prefix was previously stripped from any string; a
    plain value starting with it must now pass through unchanged.
    """
    from custom_components.nspanel_haui.haui.abstract.haui_config_access import HAUIConfigAccess

    access = HAUIConfigAccess(_TemplateApp())

    out = access.render_template("template: plain text", parse_icons=False)

    assert out == "template: plain text"


def test_bare_template_still_renders() -> None:
    """Bare ``{{ ... }}``/``{% ... %}`` strings are still rendered."""
    from custom_components.nspanel_haui.haui.abstract.haui_config_access import HAUIConfigAccess

    app = _TemplateApp()
    access = HAUIConfigAccess(app)

    out = access.render_template("{{ states('sensor.x') }}", parse_icons=False)

    assert app.rendered  # went through app.render_template
    assert "states('sensor.x')" in out

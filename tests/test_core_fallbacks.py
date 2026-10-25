"""Bad config values are reported, not silently replaced."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.utils.color import parse_color_value

# --- quiet hours --------------------------------------------------------------


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
        self.logs: list[tuple[str, dict]] = []
        self.device: HAUIDevice | None = None

    def log(self, msg: str, **kwargs: Any) -> None:
        self.logs.append((msg, kwargs))


def _device(app: _App, start: str, end: str) -> HAUIDevice:
    device = HAUIDevice(
        app,
        {
            "debug_level": 0,
            "use_do_not_disturb": True,
            "quiet_hours_start": start,
            "quiet_hours_end": end,
        },
    )
    app.device = device
    return device


def test_malformed_quiet_hours_are_reported_and_sound_still_plays() -> None:
    app = _App()
    device = _device(app, "10pm", "07:00")

    device.play_sound("notification")

    assert app.controller["esphome"].esphome.published == [("play_sound", "notification")]
    warnings = [msg for msg, kw in app.logs if kw.get("level") == "WARNING"]
    assert len(warnings) == 1
    assert "10pm" in warnings[0]


def test_valid_quiet_hours_log_no_warning() -> None:
    app = _App()
    device = _device(app, "00:00", "23:59")

    device.play_sound("notification")

    assert [kw for _msg, kw in app.logs if kw.get("level") == "WARNING"] == []


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
    from nspanel_haui.haui.abstract.haui_config_access import HAUIConfigAccess

    access = HAUIConfigAccess(_TemplateApp())

    out = access.render_template("template: plain text", parse_icons=False)

    assert out == "template: plain text"


def test_bare_template_still_renders() -> None:
    """Bare ``{{ ... }}``/``{% ... %}`` strings are still rendered."""
    from nspanel_haui.haui.abstract.haui_config_access import HAUIConfigAccess

    app = _TemplateApp()
    access = HAUIConfigAccess(app)

    out = access.render_template("{{ states('sensor.x') }}", parse_icons=False)

    assert app.rendered  # went through app.render_template
    assert "states('sensor.x')" in out

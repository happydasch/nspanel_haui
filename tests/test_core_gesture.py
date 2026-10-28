"""Gesture sequences in HAUIGestureController."""

from __future__ import annotations

from typing import Any

from nspanel_haui.haui.controller.gesture import HAUIGestureController


class _Device:
    """Device settings as the controller reads them (``gesture_sequences`` live)."""

    def __init__(self, sequences: list[dict[str, Any]]) -> None:
        self.config: dict[str, Any] = {"gesture_sequences": sequences}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


class _Navigation:
    def __init__(self) -> None:
        self.opened: list[str] = []

    def open_panel(self, key: str) -> None:
        self.opened.append(key)


class _App:
    def __init__(self, sequences: list[dict[str, Any]]) -> None:
        self.device = _Device(sequences)
        self.navigation = _Navigation()
        self.controller = {"navigation": self.navigation}

    def log(self, *a: Any, **k: Any) -> None:
        pass


def _controller(sequences: list[dict[str, Any]]) -> tuple[HAUIGestureController, _App]:
    app = _App(sequences)
    return HAUIGestureController(app, {}), app


def test_sequence_that_is_not_the_first_configured_completes() -> None:
    """Active sequences are keyed by list position, so a disabled first entry is skipped."""
    ctrl, app = _controller(
        [
            {"timeframe": 0, "sequence": ["swipe_up"], "open": "never"},
            {"timeframe": 10, "sequence": ["swipe_left", "swipe_right"], "open": "settings"},
        ]
    )

    ctrl.process_gesture("swipe_left")
    ctrl.process_gesture("swipe_right")

    assert app.navigation.opened == ["settings"]


def test_single_gesture_sequence_completes_on_that_gesture() -> None:
    ctrl, app = _controller([{"timeframe": 5, "sequence": ["swipe_up"], "open": "about"}])

    ctrl.process_gesture("swipe_up")
    ctrl.process_gesture("swipe_up")

    assert app.navigation.opened == ["about", "about"]


def test_wrong_gesture_resets_the_sequence() -> None:
    ctrl, app = _controller(
        [{"timeframe": 10, "sequence": ["swipe_left", "swipe_right"], "open": "settings"}]
    )

    ctrl.process_gesture("swipe_left")
    ctrl.process_gesture("swipe_up")
    ctrl.process_gesture("swipe_right")

    assert app.navigation.opened == []


def test_saved_device_settings_apply_without_a_restart() -> None:
    """The controller reads gesture_sequences on every gesture (reload_config replaces them)."""
    ctrl, app = _controller([])

    ctrl.process_gesture("swipe_down")
    assert app.navigation.opened == []

    app.device.config["gesture_sequences"] = [
        {"timeframe": 5, "sequence": ["swipe_down"], "open": "lights"}
    ]
    ctrl.process_gesture("swipe_down")

    assert app.navigation.opened == ["lights"]

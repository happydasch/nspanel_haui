"""Gestures in HAUIGestureController: one or more swipes run one action."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.controller import gesture as gesture_module
from custom_components.nspanel_haui.haui.controller.gesture import HAUIGestureController
from custom_components.nspanel_haui.haui.device_config import DEVICE_CONFIG
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent, SysPanelKey


def _gesture(swipes: list[str], action: str, timeframe: int = 3) -> dict[str, Any]:
    return {"swipes": swipes, "action": action, "timeframe": timeframe}


class _Device:
    """Device settings as the controller reads them (``gestures`` live)."""

    def __init__(self, gestures: list[dict[str, Any]]) -> None:
        self.config: dict[str, Any] = {"gestures": gestures}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


class _Page:
    def __init__(self) -> None:
        self.panel: object | None = object()
        self.suppressed = False

    def is_gesture_suppressed(self) -> bool:
        return self.suppressed


class _Navigation:
    def __init__(self) -> None:
        self.page: _Page | None = _Page()
        self.actions: list[str] = []

    def open_next_panel(self) -> None:
        self.actions.append("next_panel")

    def open_prev_panel(self) -> None:
        self.actions.append("prev_panel")

    def open_panel(self, key: str) -> None:
        self.actions.append(key)


class _App:
    def __init__(self, gestures: list[dict[str, Any]]) -> None:
        self.device = _Device(gestures)
        self.navigation = _Navigation()
        self.controller = {"navigation": self.navigation}

    def log(self, *a: Any, **k: Any) -> None:
        pass


def _controller(gestures: list[dict[str, Any]]) -> tuple[HAUIGestureController, _App]:
    app = _App(gestures)
    ctrl = HAUIGestureController(app, {})
    ctrl.start()
    return ctrl, app


def _swipe(ctrl: HAUIGestureController, *swipes: str) -> None:
    for swipe in swipes:
        ctrl.process_event(HAUIEvent(ESPEvent.GESTURE, swipe))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [1000.0]
    monkeypatch.setattr(gesture_module.time, "monotonic", lambda: now[0])
    return now


def test_default_gestures_are_the_built_in_navigation() -> None:
    """Out of the box a swipe steps through the panels, or opens About or Settings."""
    ctrl, app = _controller(copy.deepcopy(DEVICE_CONFIG["gestures"]))

    _swipe(ctrl, "swipe_left", "swipe_right", "swipe_up", "swipe_down")

    assert app.navigation.actions == [
        "next_panel",
        "prev_panel",
        SysPanelKey.SYS_ABOUT,
        SysPanelKey.SYS_SETTINGS,
    ]


def test_a_swipe_without_a_gesture_does_nothing() -> None:
    ctrl, app = _controller([_gesture(["swipe_left"], "next_panel")])

    _swipe(ctrl, "swipe_up", "swipe_down")

    assert app.navigation.actions == []


def test_a_sequence_runs_instead_of_the_swipe_that_completes_it() -> None:
    """The swipe that ends a sequence opens its panel and nothing else.

    It used to run its own one-swipe action as well, which navigated straight
    away from the panel the sequence had just opened.
    """
    ctrl, app = _controller(
        [
            *copy.deepcopy(DEVICE_CONFIG["gestures"]),
            _gesture(["swipe_left", "swipe_right"], "lights"),
        ]
    )

    _swipe(ctrl, "swipe_left", "swipe_right")

    assert app.navigation.actions == ["next_panel", "lights"]


def test_the_longest_completed_gesture_wins_then_the_first_listed() -> None:
    ctrl, app = _controller(
        [
            _gesture(["swipe_up"], "up"),
            _gesture(["swipe_left", "swipe_up"], "left_up"),
            _gesture(["swipe_down", "swipe_left", "swipe_up"], "down_left_up"),
            _gesture(["swipe_right", "swipe_up"], "right_up_first"),
            _gesture(["swipe_right", "swipe_up"], "right_up_second"),
        ]
    )

    _swipe(ctrl, "swipe_down", "swipe_left", "swipe_up")
    _swipe(ctrl, "swipe_right", "swipe_up")

    assert app.navigation.actions == ["down_left_up", "right_up_first"]


def test_a_sequence_ends_within_its_time_limit(clock: list[float]) -> None:
    """The last swipe has to arrive within ``timeframe`` seconds of the first."""
    ctrl, app = _controller([_gesture(["swipe_left", "swipe_left", "swipe_up"], "lights", 3)])

    _swipe(ctrl, "swipe_left")
    clock[0] += 2
    _swipe(ctrl, "swipe_left")
    clock[0] += 1.5
    _swipe(ctrl, "swipe_up")
    assert app.navigation.actions == []

    _swipe(ctrl, "swipe_left")
    clock[0] += 1
    _swipe(ctrl, "swipe_left")
    clock[0] += 2
    _swipe(ctrl, "swipe_up")
    assert app.navigation.actions == ["lights"]


def test_a_wrong_swipe_breaks_the_sequence() -> None:
    ctrl, app = _controller([_gesture(["swipe_left", "swipe_right"], "lights")])

    _swipe(ctrl, "swipe_left", "swipe_up", "swipe_right")
    assert app.navigation.actions == []

    # a sequence starts again with any swipe that matches its first
    _swipe(ctrl, "swipe_left", "swipe_left", "swipe_right")
    assert app.navigation.actions == ["lights"]


def test_a_completed_sequence_forgets_its_swipes() -> None:
    """Its last swipe cannot also start or end another sequence."""
    ctrl, app = _controller(
        [
            _gesture(["swipe_left", "swipe_right"], "lights"),
            _gesture(["swipe_right", "swipe_left"], "climate"),
        ]
    )

    _swipe(ctrl, "swipe_left", "swipe_right", "swipe_left")

    assert app.navigation.actions == ["lights"]


def test_an_unfinished_entry_does_nothing() -> None:
    """An entry the editor added but has not given swipes or an action is skipped."""
    ctrl, app = _controller(
        [
            _gesture(["swipe_up"], ""),
            _gesture([], "lights"),
        ]
    )

    _swipe(ctrl, "swipe_up", "swipe_down")

    assert app.navigation.actions == []


def test_saved_device_settings_apply_without_a_restart() -> None:
    """The controller reads ``gestures`` on every swipe (reload_config replaces them)."""
    ctrl, app = _controller([])

    _swipe(ctrl, "swipe_down")
    assert app.navigation.actions == []

    app.device.config["gestures"] = [_gesture(["swipe_down"], "lights")]
    _swipe(ctrl, "swipe_down")

    assert app.navigation.actions == ["lights"]


def test_swipes_are_ignored_during_a_slider_drag() -> None:
    """A slider drag also reports a swipe; it must not navigate away."""
    ctrl, app = _controller(copy.deepcopy(DEVICE_CONFIG["gestures"]))
    assert app.navigation.page is not None
    app.navigation.page.suppressed = True

    _swipe(ctrl, "swipe_left", "swipe_right", "swipe_up", "swipe_down")

    assert app.navigation.actions == []


def test_swipes_are_ignored_without_a_panel() -> None:
    ctrl, app = _controller(copy.deepcopy(DEVICE_CONFIG["gestures"]))
    assert app.navigation.page is not None
    app.navigation.page.panel = None

    _swipe(ctrl, "swipe_left")
    app.navigation.page = None
    _swipe(ctrl, "swipe_left")

    assert app.navigation.actions == []

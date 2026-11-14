from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPEvent, GestureAction


class HAUIGestureController(HAUIBase):
    """Gesture Controller

    Runs the action of a gesture when its swipes arrive in order.  The gestures
    are the device setting ``gestures``
    (``[{"swipes": [...], "action": ..., "timeframe": s}]``), read on every
    swipe so a saved device config applies without a restart.

    A swipe runs at most one action: of the gestures that end with it, the one
    with the most swipes, and of those the first in the list.  A gesture of
    several swipes has to end within ``timeframe`` seconds of its first swipe;
    once it runs, its swipes are forgotten, so they cannot also complete
    another gesture.  An entry without swipes or action (one the editor just
    added) does nothing.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]) -> None:
        """Initialize for gesture controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Gesture Controller with config: {config}", level="DEBUG")
        # the latest swipes with their monotonic time, as many as the longest gesture has
        self._history: list[tuple[str, float]] = []

    # public

    def gestures(self) -> list[dict[str, Any]]:
        """The device's finished gestures, in their configured order."""
        return [
            gesture
            for gesture in self.app.device.get("gestures")
            if gesture["swipes"] and gesture["action"]
        ]

    def process_gesture(self, swipe: str) -> None:
        """Run the action of the gesture this swipe completes, if any.

        Args:
            swipe (str): Name of the swipe (one of ``GESTURES``)
        """
        gestures = self.gestures()
        if not gestures:
            self._history = []
            return
        now = time.monotonic()
        longest = max(len(gesture["swipes"]) for gesture in gestures)
        self._history = [*self._history, (swipe, now)][-longest:]
        completed = [gesture for gesture in gestures if self._completes(gesture, now)]
        if not completed:
            return
        # max() keeps the first of equally long gestures, so the list order decides
        gesture = max(completed, key=lambda gesture: len(gesture["swipes"]))
        if len(gesture["swipes"]) > 1:
            self._history = []
        self.log(f"Gesture {' → '.join(gesture['swipes'])} runs {gesture['action']}")
        self.run_action(gesture["action"])

    def run_action(self, action: str) -> None:
        """Run a gesture's action: step to the next or previous panel, or open a panel."""
        navigation = self.app.controller["navigation"]
        if action == GestureAction.NEXT_PANEL:
            navigation.open_next_panel()
        elif action == GestureAction.PREV_PANEL:
            navigation.open_prev_panel()
        else:
            navigation.open_panel(action)

    # internal

    def _completes(self, gesture: dict[str, Any], now: float) -> bool:
        """Whether the latest swipes are this gesture's swipes, within its time limit."""
        swipes = gesture["swipes"]
        recent = self._history[-len(swipes) :]
        if [name for name, _ in recent] != swipes:
            return False
        return now - recent[0][1] <= gesture["timeframe"]

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Processes an event.

        Args:
            event (Event): Event
        """
        if not self.is_started() or event.name != ESPEvent.GESTURE:
            return
        navigation = self.app.controller["navigation"]
        page = navigation.page
        if page is None or page.panel is None:
            return
        # a slider drag also produces a swipe gesture — ignore it so
        # adjusting a slider doesn't navigate away
        if page.is_gesture_suppressed():
            self.log("Ignoring gesture during slider interaction")
            return
        self.log(f"Got gesture: {event.as_str()}")
        self.process_gesture(event.as_str())

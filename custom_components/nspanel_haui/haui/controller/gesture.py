from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPEvent


class HAUIGestureController(HAUIBase):
    """Gesture Controller

    Provides access to advanced gesture control.
    Supports gesture sequences.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]) -> None:
        """Initialize for gesture controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.debug_log(f"Creating Gesture Controller with config: {config}")
        self._current_seq: dict[int, dict] = {}

    # public

    def process_gesture(self, gesture_name: str) -> None:
        """Processes the gesture with the given name.

        Args:
            gesture_name (str): Name of the gesture
        """
        # remove currently active sequences if they timed out
        time_now = int(time.time())
        for seq_index in range(len(self._current_seq)):
            time_start = self._current_seq[seq_index]["time_start"]
            time_max = self._current_seq[seq_index]["time_max"]
            if time_max < time_now:
                # stop processing if time passed max time for gesture
                self.log(f"Seqence timeout for {seq_index}")
                del self._current_seq[seq_index]
                continue

        # find all matching sequences for this gesture
        for seq_index, seq_data in enumerate(self.config.values()):
            # check timeframe, if no timeframe defined, skip this
            timeframe = int(seq_data.get("timeframe", 0))
            if not timeframe:
                continue
            # check sequence config
            gestures = seq_data.get("sequence", [])
            if len(gestures) == 0:
                self.log(f"No gestures for sequence {seq_index} defined")
                continue
            # check for sequence begin
            if seq_index not in self._current_seq:
                # current gesture is the first in sequence
                if gesture_name == gestures[0]:
                    # start seq
                    time_start = int(time.time())
                    time_max = int(time_start + timeframe)
                    self._current_seq[seq_index] = {
                        "time_start": time_start,
                        "time_max": time_max,
                        "index": 0,
                    }
                    self.log(f"Gesture sequence {seq_index} started")
            # check while in sequence
            else:
                # check if gesture is in sequence
                current_index = self._current_seq[seq_index]["index"] + 1
                if gesture_name != gestures[current_index]:
                    self.log(
                        f"Invalid gesture {gesture_name} ({gestures[current_index]}) at"
                        f" index {current_index} for sequence {seq_index} ({gestures}) occured"
                    )
                    # invalid gesture for this sequence
                    del self._current_seq[seq_index]
                else:
                    # current gesture is in sequence
                    if current_index < len(gestures) - 1:
                        # sequence is not yet complete
                        self._current_seq[seq_index]["index"] = current_index
                    else:
                        # complete sequence, last gesture in sequence
                        self.log(f"Gesture sequence {seq_index} completed")
                        # remove sequence from currently active seqences
                        # when completed
                        del self._current_seq[seq_index]
                        # process finished gesture sequence
                        self.process_gesture_sequence(seq_data)

    def process_gesture_sequence(self, seq_data: dict[str, Any]) -> None:
        """Processes a complete gesture sequence."""
        panel_key = seq_data.get("open", "")
        if panel_key == "":
            return
        # process the gesture
        navigation = self.app.controller["navigation"]
        navigation.open_panel(panel_key)

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Processes an event.

        Args:
            event (Event): Event
        """
        if not self.is_started():
            return
        # check for gesture
        if event.name == ESPEvent.GESTURE:
            # a slider drag also produces a swipe gesture — ignore it so
            # adjusting a slider doesn't trigger a gesture sequence
            navigation = self.app.controller.get("navigation")
            page = navigation.page if navigation is not None else None
            if page is not None and page.is_gesture_suppressed():
                return
            # process gesture
            if isinstance(event.value, str):
                self.process_gesture(event.value)

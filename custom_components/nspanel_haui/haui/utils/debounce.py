"""Debouncer for suppressing noisy state-change events (state flapping).

The delayed call is scheduled with the app's ``run_in``, so it runs on the
app's worker like every other timer callback.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class _Timers(Protocol):
    def run_in(self, cb: Callable[[dict[str, Any]], None], delay: float) -> str: ...
    def cancel_timer(self, handle: str) -> None: ...


class Debouncer:
    """Coalesces rapid calls per key into one call after ``delay`` seconds.

    Args:
        app: The app whose timers schedule the delayed calls.
        delay: Minimum delay (seconds) before the callback is executed.
    """

    def __init__(self, app: _Timers, delay: float = 0.3) -> None:
        self.delay = delay
        self._app = app
        self._handles: dict[str, str] = {}

    def call(self, key: str, func: Callable[[], None]) -> None:
        """Schedule *func* to be called after :attr:`delay` seconds.

        A call still pending for *key* is cancelled.
        """
        self.cancel(key)

        def _fire(_kwargs: dict[str, Any]) -> None:
            self._handles.pop(key, None)
            func()

        self._handles[key] = self._app.run_in(_fire, self.delay)

    def cancel(self, key: str) -> None:
        """Cancel the call pending for *key*, if any."""
        handle = self._handles.pop(key, None)
        if handle is not None:
            self._app.cancel_timer(handle)

    def clear_all(self) -> None:
        """Cancel all pending calls."""
        for key in list(self._handles):
            self.cancel(key)

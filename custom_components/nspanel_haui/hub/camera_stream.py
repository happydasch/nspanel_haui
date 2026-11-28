"""Run a camera as a stream of delta frames on one panel.

A Nextion has no framebuffer and no video path: a picture is a program of ``fill``
rectangles written straight to the display, so a stream is the hub's job - fetch a
snapshot, work out what moved, send only that (``haui/utils/image_stream.py``).
This module is the loop around it: one ``asyncio`` task per streamed panel that
fetches and plans on the event loop and the executor, and hands each frame to the
panel's worker, which owns every display command.

Three rules shape the loop, and all three come from the display's limits:

* **Never queue frames.** The firmware restarts its own draw program on a new
  call, so a frame sent while the panel is still painting would cut that frame
  short. A frame that arrives while a draw is in flight is dropped instead, and
  the next one is planned from the truth about the panel - the planner's painted
  model is updated only by what was actually sent.
* **The planner lives on the worker side of the decision.** Frames are planned in
  the executor (it is pure CPU: reduce the picture to a grid, merge the changed
  cells), but which frames are sent, and whether the stream may continue at all,
  is decided on the worker, where the page and the display state are owned.
* **Stop is a verdict, not an exception.** A page change, a sleeping display, a
  panel that is installing a TFT, an app that has stopped: each ends the stream
  the same way the service does, so there is one path to clean up and one place
  that records the last frame for the page replay.

A camera that fails is retried a few times and then ends the stream: a panel that
keeps redrawing a stale picture is worse than one that stops.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Final

from ..haui.utils.image_program import Rect
from ..haui.utils.image_stream import (
    DEAD_BAND,
    DEFAULT_CELL_PX,
    DEFAULT_FRAME_RUNS,
    MAX_FPS,
    MIN_FPS,
    REFRESH_EVERY,
    DeltaPlanner,
    ImageStreamError,
)

if TYPE_CHECKING:
    from .app import NSPanelHAUI

#: Snapshots a camera may fail to deliver before the stream ends. A camera that
#: misses one frame - it is reconnecting, or renegotiating with its doorbell - is
#: normal and the stream rides it out; one that misses this many in a row is not
#: coming back on its own.
MAX_CAMERA_FAILURES: Final = 5
#: Seconds one snapshot may take before it counts as a failure. A cloud camera can
#: legitimately take a couple of seconds; a stalled one must not hold the stream.
SNAPSHOT_TIMEOUT: Final = 10

#: The stream running on each panel, by app name. A panel shows one at a time:
#: a second start replaces the first, the way a second draw replaces the first.
_STREAMS: dict[str, CameraStream] = {}


class CameraStream:
    """One camera drawn continuously into one rectangle of one panel."""

    def __init__(
        self,
        hass: Any,
        app: NSPanelHAUI,
        *,
        entity_id: str,
        rect: Rect,
        fps: float,
        cell: int = DEFAULT_CELL_PX,
        band: int = DEAD_BAND,
        max_runs: int = DEFAULT_FRAME_RUNS,
        refresh_every: int = REFRESH_EVERY,
    ) -> None:
        """Prepare a stream; ``async_start`` puts it to work.

        Args:
            hass: Home Assistant, for the camera snapshot and the executor.
            app: The panel's app; every display command runs on its worker.
            entity_id: The camera entity to draw.
            rect: Where to draw, in display pixels.
            fps: Frames per second to aim for.
            cell: Starting cell size in display pixels.
            band: Per-channel dead band before a cell is repainted.
            max_runs: Runs one frame may cost.
            refresh_every: Frames between two full repaints, so the dead band
                cannot accumulate error; 0 disables them.
        """
        self.hass = hass
        self.app = app
        self.entity_id = entity_id
        self.rect = rect
        self.fps = min(MAX_FPS, max(MIN_FPS, fps))
        self.planner = DeltaPlanner(
            rect,
            cell=cell,
            band=band,
            max_runs=max_runs,
            refresh_every=refresh_every,
        )
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._page: str | None = None
        self._last_runs: list[str] = []
        self._failures = 0
        self.frames = 0
        self.skipped = 0

    @property
    def interval(self) -> float:
        """Seconds between two frames."""
        return 1.0 / self.fps

    async def async_start(self) -> None:
        """Begin streaming, replacing whatever this panel was streaming before.

        The page the stream belongs to is captured here: the picture is drawn over
        the page that is showing, so a page change ends it rather than leaving a
        video painted across a page it was never meant for.
        """
        await stop_stream(self.app)
        self._page = await self.app.async_run_on_worker(self._current_page)
        _STREAMS[self.app.name] = self
        self._task = self.hass.async_create_task(self._run())

    async def async_stop(self) -> None:
        """Stop the stream and leave the last frame recorded for late viewers."""
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError, Exception:  # noqa: BLE001 - a dead task must not block cleanup
                pass
            self._task = None
        if _STREAMS.get(self.app.name) is self:
            del _STREAMS[self.app.name]
        if self._last_runs:
            try:
                await self.app.async_run_on_worker(self._record_last_frame, self._last_runs)
            except Exception as exc:  # noqa: BLE001 - the app may already be gone
                self.app.log(f"camera stream: could not record the last frame: {exc}")
            self._last_runs = []
        self.app.log(
            f"camera stream from {self.entity_id} stopped: {self.frames} frame(s), "
            f"{self.skipped} skipped, cell {self.planner.cell} px"
        )

    async def _run(self) -> None:
        """Fetch, plan and send a frame, then wait out the rest of the interval."""
        interval = self.interval
        while not self._stopped.is_set():
            started = asyncio.get_running_loop().time()
            try:
                image = await self._snapshot()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - a background loop must survive any camera failure
                # Whatever the camera raised - Home Assistant's own error, a
                # timeout, a driver exception - it is a frame that did not arrive.
                # It is logged and counted, and the stream ends after too many.
                self._failures += 1
                self.app.log(
                    f"camera stream: {self.entity_id} gave no snapshot "
                    f"({self._failures}/{MAX_CAMERA_FAILURES}): {exc}",
                    level="WARNING",
                )
                if self._failures >= MAX_CAMERA_FAILURES:
                    self.app.log(
                        f"camera stream from {self.entity_id} stopped: the camera did not answer",
                        level="WARNING",
                    )
                    break
                await self._sleep_until(started + interval)
                continue
            self._failures = 0
            try:
                runs = await self.hass.async_add_executor_job(self.planner.plan, image)
            except ImageStreamError as exc:
                self.app.log(
                    f"camera stream: {self.entity_id} frame refused: {exc}", level="WARNING"
                )
                await self._sleep_until(started + interval)
                continue
            verdict = await self._send(runs)
            if verdict == "stop":
                break
            if verdict == "busy":
                self.skipped += 1
            else:
                self.frames += 1
            await self._sleep_until(started + interval)
        await self._finish()

    async def _snapshot(self) -> Any:
        """One frame from the camera, scaled by the camera where it supports it."""
        from homeassistant.components.camera import async_get_image

        return await async_get_image(
            self.hass,
            self.entity_id,
            timeout=SNAPSHOT_TIMEOUT,
            width=self.rect.w,
            height=self.rect.h,
        )

    async def _sleep_until(self, deadline: float) -> None:
        """Wait for ``deadline`` without ever sleeping past it, and stay cancellable."""
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            # The frame took longer than its slot: start the next one at once, so
            # a slow camera shows the newest picture instead of a backlog.
            return
        try:
            await asyncio.wait_for(self._stopped.wait(), timeout=remaining)
        except TimeoutError:
            pass

    async def _send(self, runs: list[str]) -> str:
        """Send one frame on the worker; return whether the stream goes on.

        Returns:
            ``"ok"`` when the frame was sent or there was nothing to send,
            ``"busy"`` when the panel was still drawing the previous one, and
            ``"stop"`` when the stream must end.

        Raises:
            Nothing: a stopped app ends the stream, which is a normal way for it
            to end (the config entry was unloaded).
        """
        try:
            return await self.app.async_run_on_worker(self._send_on_worker, runs)
        except Exception as exc:  # noqa: BLE001 - AppStoppedError and friends end the stream
            self.app.log(f"camera stream from {self.entity_id} ended: {exc}")
            return "stop"

    def _send_on_worker(self, runs: list[str]) -> str:
        """Decide and send, on the worker, where the page and display live."""
        if self._stopped.is_set():
            return "stop"
        if self._current_page() != self._page:
            self.app.log(f"camera stream from {self.entity_id}: the page changed, stopping")
            return "stop"
        if self.app.device.display_state == "off":
            self.app.log(f"camera stream from {self.entity_id}: the display is off, stopping")
            return "stop"
        esp = self.app.controller.get("esphome")
        if esp is None or not hasattr(esp, "draw_stream_frame"):
            self.app.log(
                f"camera stream from {self.entity_id}: no ESPHome draw path, stopping",
                level="WARNING",
            )
            return "stop"
        if esp.drawing:
            return "busy"
        if runs:
            esp.draw_stream_frame(runs)
            self._last_runs = runs
        return "ok"

    def _record_last_frame(self, runs: list[str]) -> None:
        """Record the final frame for the page replay and the Live preview."""
        esp = self.app.controller.get("esphome")
        if esp is not None and hasattr(esp, "record_stream_frame"):
            esp.record_stream_frame(runs)

    def _current_page(self) -> str | None:
        """The id of the page the panel is showing, if any."""
        navigation = self.app.controller.get("navigation")
        page = getattr(navigation, "page", None) if navigation is not None else None
        return getattr(page, "page_id", None) if page is not None else None

    async def _finish(self) -> None:
        """Tear the stream down once the loop has ended for its own reasons."""
        if _STREAMS.get(self.app.name) is self:
            del _STREAMS[self.app.name]
        self._stopped.set()
        if self._last_runs:
            try:
                await self.app.async_run_on_worker(self._record_last_frame, self._last_runs)
            except Exception:  # noqa: BLE001 - the app may already be gone
                pass
            self._last_runs = []


async def stop_stream(app: NSPanelHAUI) -> bool:
    """Stop the stream running on ``app``, if any.

    Returns:
        Whether a stream was running.
    """
    stream = _STREAMS.get(app.name)
    if stream is None:
        return False
    await stream.async_stop()
    return True


def stream_for(app: NSPanelHAUI) -> CameraStream | None:
    """The stream running on ``app``, for diagnostics and the stop service."""
    return _STREAMS.get(app.name)


async def stop_all_streams() -> None:
    """Stop every stream, for an integration unload."""
    for stream in list(_STREAMS.values()):
        await stream.async_stop()

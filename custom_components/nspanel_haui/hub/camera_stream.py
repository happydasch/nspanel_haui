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
  the next one is planned from the truth about the panel - the painted model
  advances only after a draw completes.
* **The planner lives on the worker side of the decision.** Frames are planned in
  the executor (it is pure CPU: reduce the picture to a grid, merge the changed
  cells), but which frames are sent, and whether the stream may continue at all,
  is decided on the worker, where the page and the display state are owned.
* **Stop is a verdict, not an exception.** A page change, a sleeping display, a
  panel that is installing a TFT, an app that has stopped: each ends the stream
  the same way the service does. Confirmed fills are already in the page replay;
  ending the stream never paints an old picture back over them.

A camera that fails is retried: a snapshot that does not arrive is one frame the
panel did not get, and after a few in a row the stream backs off and keeps trying.
Ending it instead would leave the panel frozen for as long as the outage lasts -
a doorbell that renegotiates, a camera integration that reloads - because nothing
would start it again until the page is set anew.

The same holds for a display that switches itself off: painting into a dark panel
is invisible work, so the loop idles instead of ending, and the frame after the
display comes back paints the rectangle whole (the panel may show anything by
then, and the planner's model has been idle for hours).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING, Any, Final

from ..haui.controller.esphome import DRAW_SLICE_GRACE
from ..haui.utils.image_program import ImageProgramError, Rect, decode_image
from ..haui.utils.image_stream import (
    DEAD_BAND,
    DEFAULT_CELL_PX,
    DEFAULT_FRAME_RUNS,
    FIRST_FRAME_RUNS,
    MAX_FPS,
    MIN_CELL_PX,
    MIN_FPS,
    REFRESH_EVERY,
    DeltaPlanner,
    ImageStreamError,
    PictureQuality,
)

if TYPE_CHECKING:
    from ..haui.abstract.haui_page import HAUIPage
    from .app import NSPanelHAUI

#: Snapshots a camera may miss in a row before the stream says so and slows down.
#: A camera that misses one frame - it is reconnecting, or renegotiating with its
#: doorbell - is normal and the stream rides it out at its own rate.
MAX_CAMERA_FAILURES: Final = 5
#: Seconds between attempts once a camera is ``MAX_CAMERA_FAILURES`` down. The
#: stream keeps running, so a camera that comes back paints again on its own; at
#: this cadence a dead one costs a request every half minute and a log line every
#: few minutes, instead of ending a stream nothing would restart.
CAMERA_RETRY_INTERVAL: Final = 30
#: Seconds between attempts a camera is allowed for one snapshot. A cloud camera can
#: legitimately take a couple of seconds; a stalled one must not hold the stream.
SNAPSHOT_TIMEOUT: Final = 10
#: Seconds a snapshot is reused across the streams of this hub. Two panels showing
#: the same camera at the same size asked it for a snapshot each, every frame, and
#: decoded both; within this window the second one reuses the first one's frame.
SNAPSHOT_SHARE_SECONDS: Final = 0.5
#: Seconds between two whole paints a *viewer* may ask for. A dashboard card draws
#: the page every few seconds and has no picture while the replay cannot describe
#: the area whole, so an unthrottled request per render would repaint the panel
#: continuously - and a whole paint of a camera rectangle is the visible flash the
#: camera page avoids everywhere else.
VIEWER_REPAINT_INTERVAL: Final = 10.0
#: Seconds a startup pass may stay unacknowledged before the loop gives up on it.
#: The panel answers each slice with a fence and the controller has its own per
#: slice timer, so this only catches a draw nobody will ever report - and the loop
#: must not wait for one for ever (`CameraStream._painted`).
STARTUP_ACK_TIMEOUT: Final = SNAPSHOT_TIMEOUT + DRAW_SLICE_GRACE

#: The stream running on each panel, by app name. A panel shows one at a time:
#: a second start replaces the first, the way a second draw replaces the first.
_STREAMS: dict[str, CameraStream] = {}
#: The snapshots in flight, by entity and requested size: one camera, one fetch per
#: ``SNAPSHOT_SHARE_SECONDS``, however many panels draw it. The owner's name is kept
#: so a stream never reuses its own frame (that would halve a stream's frame rate),
#: and the entries are pruned when they are past their window.
_SNAPSHOTS: dict[tuple[str, int, int], tuple[float, bytes, str]] = {}


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
        min_cell: int = MIN_CELL_PX,
        band: int = DEAD_BAND,
        max_runs: int = DEFAULT_FRAME_RUNS,
        first_runs: int = FIRST_FRAME_RUNS,
        refresh_every: int = REFRESH_EVERY,
        cover: bool = False,
        progressive: bool = False,
        external: bool = True,
        on_first_frame: Callable[[], None] | None = None,
    ) -> None:
        """Prepare a stream; ``async_start`` puts it to work.

        Args:
            hass: Home Assistant, for the camera snapshot and the executor.
            app: The panel's app; every display command runs on its worker.
            entity_id: The camera entity to draw.
            rect: Where to draw, in display pixels.
            fps: Frames per second to aim for.
            cell: Starting cell size in display pixels.
            min_cell: The finest cell size this stream sharpens to.
            band: Per-channel dead band before a cell is repainted.
            max_runs: Runs one update may cost.
            first_runs: Runs a full paint may cost; the detail of the picture is
                decided by the paint that shows it, not by the updates.
            refresh_every: Frames between two full repaints, so the dead band
                cannot accumulate error; 0 disables them.
            cover: Crop each frame to ``rect`` instead of letterboxing it.
            progressive: Start with bounded coarse passes before the normal grid.
            external: This is a service overlay, not the camera page’s own draw.
            on_first_frame: Hide the placeholder just before submitting the first
                draw, so the widget never repaints over the picture.
        """
        self.hass = hass
        self.app = app
        self.entity_id = entity_id
        self.rect = rect
        self.fps = min(MAX_FPS, max(MIN_FPS, fps))
        self.planner = DeltaPlanner(
            rect,
            cell=cell,
            min_cell=min_cell,
            band=band,
            max_runs=max_runs,
            first_runs=first_runs,
            refresh_every=refresh_every,
            cover=cover,
            progressive=progressive,
        )
        self._on_first_frame = on_first_frame
        self._progressive = progressive
        self._external = external
        #: The cell the page asked for, which the planner may coarsen past to keep
        #: up. Kept apart from ``planner.cell`` because it is what the page asked
        #: for: a re-render compares settings, and a stream that had to coarsen
        #: draws the same picture as one that did not.
        self.cell = self.planner.cell
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._page: HAUIPage | None = None
        self._failures = 0
        self._picture_started = False
        #: Set by ``repaint``: the next frame this stream sends paints the whole
        #: rectangle, because the panel may no longer show the picture the planner
        #: holds.
        self._repaint_pending = False
        #: Set by ``request_stop``: the panel asked for this stream to end. A page
        #: that is set again stops before it starts - both in one worker turn - so
        #: the request is withdrawn again (``cancel_stop``) and the stream it just
        #: kept survives (``_apply_stop``).
        self._stop_requested = False
        #: Draw failures the panel reported when this stream last looked; a change
        #: means the picture it painted is no longer what the panel shows.
        self._draw_failures = 0
        self._started_at = monotonic()
        self._completed = 0
        self._unchanged = 0
        self._failed_draws = 0
        #: Frames dropped because the display was dark; the frame after it comes
        #: back paints the rectangle whole.
        self._idle = 0
        #: When a viewer last asked for a whole paint (``repaint_for_viewer``).
        self._viewer_repaint_at = 0.0
        #: Frames refused because the picture moved while they were being planned;
        #: they were not sent, and the next one is planned from the new baseline.
        self._stale = 0
        self.frames = 0
        self.skipped = 0

    @property
    def interval(self) -> float:
        """Seconds between two frames."""
        return 1.0 / self.fps

    @property
    def signature(self) -> tuple[Any, ...]:
        """Everything that decides the picture this stream draws.

        Two streams with the same signature draw the same camera into the same
        rectangle with the same density, budgets and rate, so a page that asks
        for what is already running keeps the running one - and its planner,
        which holds the picture the display is showing.

        The cell here is the one the page asked for, not the planner's: a stream
        that coarsened to keep up with a busy scene still draws what the page
        wants, and restarting it would paint the whole rectangle again for a
        picture the display already shows.
        """
        return (
            self.entity_id,
            self.rect,
            self.fps,
            self.planner.cover,
            # The dead band decides which cells a delta repaints, and ``external``
            # whether this stream's frames also reach a sandbox panel: two streams
            # that differ in either draw something else.
            self.planner.band,
            self._external,
            self._progressive,
            self.planner.refresh_every,
            self.cell,
            self.planner.min_cell,
            self.planner.max_runs,
            self.planner.first_runs,
        )

    async def async_start(self) -> None:
        """Begin streaming, replacing whatever this panel was streaming before.

        The page the stream belongs to is captured here: the picture is drawn over
        the page that is showing, so a page change ends it rather than leaving a
        video painted across a page it was never meant for.

        The stop of the replaced stream is here and nowhere else, so every entry
        path - the camera page and the service - replaces by asking a stream to
        start, and no caller has to know that a panel shows one stream at a time.
        """
        await stop_stream(self.app)
        self._page = await self.app.async_run_on_worker(self._current_page)
        _STREAMS[self.app.name] = self
        self._task = self.hass.async_create_task(self._run())

    async def async_stop(self) -> None:
        """Stop fetching new frames; the page keeps the fills it received."""
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # Awaiting the task we just cancelled raises here, and that is the
                # normal path. Only a cancellation of *this* caller goes on.
                current = asyncio.current_task()
                if current is not None and current.cancelling():
                    raise
            except Exception as exc:  # noqa: BLE001 - a dead task must not block cleanup
                self.app.log(f"camera stream: the loop ended with {exc!r}", level="DEBUG")
            self._task = None
        if _STREAMS.get(self.app.name) is self:
            del _STREAMS[self.app.name]
        self.app.log(
            f"camera stream from {self.entity_id} stopped: {self.frames} frame(s), "
            f"{self._completed} completed, {self._unchanged} unchanged, "
            f"{self.skipped} busy skips, {self._idle} dark-display skips, "
            f"{self._stale} stale, {self._failed_draws} failed draws, "
            f"cell {self.planner.cell} px"
        )

    def request_stop(self) -> None:
        """Ask for this stream to end, before the loop can act on it (worker).

        A page that is set again stops its stream and starts it again in the same
        worker turn: the stop is only a request, so the start that keeps this
        stream withdraws it (``cancel_stop``) and the picture keeps running.
        """
        self._stop_requested = True

    def cancel_stop(self) -> None:
        """Withdraw a requested stop: the page kept this stream after all (worker)."""
        self._stop_requested = False

    async def _run(self) -> None:
        """Run the frame loop, and tear the stream down however it ends.

        A stream is the only thing that knows the panel's picture area is empty:
        a task that dies quietly leaves the page on its placeholder for ever and
        says nothing about why, so an unexpected error is logged with its
        traceback and the stream is still removed.
        """
        try:
            await self._frame_loop()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a background loop must not die silently
            self.app.log(
                f"camera stream from {self.entity_id} ended by an error: {exc!r}",
                level="ERROR",
                exc_info=True,
            )
        finally:
            await self._finish()

    async def _frame_loop(self) -> None:
        """Fetch, plan and send a frame, then wait out the rest of the interval."""
        interval = self.interval
        loop = asyncio.get_running_loop()
        startup_frame: bytes | None = None
        while not self._stopped.is_set():
            started = loop.time()
            # Asked before the snapshot: a display that is dark, or one still
            # painting, costs nothing at the camera. The worker also hands back the
            # planner to plan on, so the frame is planned against a picture taken
            # while it is still the worker's (``_prepare_on_worker``).
            status, planner = await self.app.async_run_on_worker(self._prepare_on_worker)
            if status == "stop":
                break
            if status != "ok":
                if status == "busy":
                    self.skipped += 1
                else:
                    self._idle += 1
                startup_frame = None
                await self._sleep_until(started + interval)
                continue
            try:
                frame = startup_frame if startup_frame is not None else await self._snapshot()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - a background loop must survive any camera failure
                # Whatever the camera raised - Home Assistant's own error, a
                # timeout, a driver exception - it is a frame that did not arrive.
                # The stream keeps running: nothing would start it again, and the
                # panel keeps the picture it has until the camera answers.
                self._failures += 1
                delay = interval
                if self._failures < MAX_CAMERA_FAILURES:
                    self.app.log(
                        f"camera stream: {self.entity_id} gave no snapshot "
                        f"({self._failures}/{MAX_CAMERA_FAILURES}): {exc}",
                        level="WARNING",
                    )
                else:
                    delay = max(interval, CAMERA_RETRY_INTERVAL)
                    if self._failures == MAX_CAMERA_FAILURES:
                        self.app.log(
                            f"camera stream: {self.entity_id} has not answered "
                            f"{self._failures} times; the panel keeps its picture and the "
                            f"stream tries again every {delay:.0f} s",
                            level="WARNING",
                        )
                await self._sleep_until(started + delay)
                continue
            if self._failures:
                self.app.log(
                    f"camera stream: {self.entity_id} answered again after "
                    f"{self._failures} missed snapshot(s)"
                )
            self._failures = 0
            snapshot_ready = monotonic()
            try:
                runs, full, planned = await self.hass.async_add_executor_job(
                    self._plan, frame, planner
                )
            except ImageStreamError as exc:
                self.app.log(
                    f"camera stream: {self.entity_id} frame refused: {exc}", level="WARNING"
                )
                await self._sleep_until(started + interval)
                continue
            # Startup refines the same image as soon as each layer drains. It
            # neither polls the camera repeatedly nor idles for the stream's FPS.
            painted: asyncio.Future[bool] | None = None
            on_done: Callable[[bool], None] | None = None
            if planned.starting_up:
                painted = loop.create_future()

                def _signal(ok: bool, future: asyncio.Future[bool] = painted) -> None:
                    def _resolve() -> None:
                        if not future.done():
                            future.set_result(ok)

                    loop.call_soon_threadsafe(_resolve)

                on_done = _signal
            verdict = await self._send(runs, full, planned, snapshot_ready, on_done)
            if verdict == "stop":
                break
            if verdict == "busy":
                self.skipped += 1
            elif verdict == "idle":
                self._idle += 1
            elif verdict == "stale":
                self._stale += 1
            elif verdict == "ok":
                self.frames += 1
                if painted is not None and await self._painted(painted):
                    startup_frame = frame
                    continue
            startup_frame = None
            await self._sleep_until(started + interval)

    async def _painted(self, painted: asyncio.Future[bool]) -> bool:
        """Wait for a startup pass to be acknowledged, but never for ever.

        The per-slice timer ends a pass on a real panel, and the virtual firmware
        answers too, but nothing here may depend on that: a controller replaced
        mid-pass, or a transport that swallows a draw, would leave the loop
        awaiting a future nobody will resolve - mid-startup, with the placeholder
        already gone. A timeout is a pass the panel never took, which is a failed
        draw like any other.
        """
        try:
            return await asyncio.wait_for(painted, timeout=STARTUP_ACK_TIMEOUT)
        except TimeoutError:
            self._failed_draws += 1
            self.repaint()
            self.app.log(
                f"camera stream from {self.entity_id}: no acknowledgement for a startup "
                f"pass within {STARTUP_ACK_TIMEOUT:.0f} s; painting it again",
                level="WARNING",
            )
            return False

    async def _snapshot(self) -> bytes:
        """One frame from the camera, in the camera's own encoding.

        ``camera.async_get_image`` hands back the picture's *bytes* - the JPEG or
        PNG the camera produced, scaled by the camera when it can - not pixels,
        so decoding belongs to the stream's own CPU step (``_plan``) and never to
        the event loop.

        A snapshot is shared with the hub's other streams of the same camera at the
        same size (``_SNAPSHOTS``): two panels drawing one camera asked it for a
        snapshot each, every frame, and decoded both.
        """
        from homeassistant.components.camera import async_get_image

        key = (self.entity_id, self.rect.w, self.rect.h)
        cached = _SNAPSHOTS.get(key)
        now = monotonic()
        if cached is not None and cached[2] != self.app.name:
            taken, content, _owner = cached
            if now - taken <= SNAPSHOT_SHARE_SECONDS:
                return content
        snapshot = await async_get_image(
            self.hass,
            self.entity_id,
            timeout=SNAPSHOT_TIMEOUT,
            width=self.rect.w,
            height=self.rect.h,
        )
        self._remember_snapshot(key, monotonic(), snapshot.content)
        return snapshot.content

    def _remember_snapshot(self, key: tuple[str, int, int], taken: float, content: bytes) -> None:
        """Keep a snapshot for the hub's other streams, and drop the ones past their window."""
        _SNAPSHOTS[key] = (taken, content, self.app.name)
        for stale in [k for k, entry in _SNAPSHOTS.items() if taken - entry[0] > 60]:
            del _SNAPSHOTS[stale]

    def _plan(self, frame: bytes, planner: DeltaPlanner) -> tuple[list[str], bool, DeltaPlanner]:
        """Decode one frame and plan the program that shows it (executor side).

        Args:
            frame: The encoded snapshot.
            planner: A copy of this stream's planner, taken on the worker
                (``DeltaPlanner.clone``) - planning must not read state the worker
                may be replacing while it runs.

        Returns:
            The program, whether it paints the whole rectangle, and the planner
            state that the program would leave on the display. That state is only
            committed on the worker if the program completes; a busy display drops
            this frame and must not advance the picture the next delta compares to.

        Raises:
            ImageStreamError: When the bytes are not a decodable image, or the
                picture has no pixels. To the loop both mean the same thing: this
                frame cannot be drawn, and the next one may be fine.
        """
        full_before = planner.full_paints
        try:
            runs = planner.plan(decode_image(frame))
        except ImageProgramError as exc:
            raise ImageStreamError(f"the frame could not be decoded: {exc}") from exc
        return runs, planner.full_paints > full_before, planner

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

    async def _send(
        self,
        runs: list[str],
        full: bool,
        planner: DeltaPlanner,
        snapshot_ready: float,
        on_done: Callable[[bool], None] | None,
    ) -> str:
        """Submit a planned frame if its baseline is still valid."""
        try:
            return await self.app.async_run_on_worker(
                self._send_on_worker, runs, full, planner, snapshot_ready, on_done
            )
        except Exception as exc:  # noqa: BLE001 - AppStoppedError and friends end the stream
            self.app.log(f"camera stream from {self.entity_id} ended: {exc}")
            return "stop"

    def _frame_status(self) -> str:
        """Check the page and draw slot on the worker, where they are owned.

        Returns:
            ``"stop"`` when this stream is over, ``"idle"`` while the display is
            dark (the stream keeps running and paints whole again when it wakes),
            ``"busy"`` while a pass is in flight, ``"ok"`` when a frame may go.
        """
        if self._stopped.is_set():
            return "stop"
        if self._current_page() is not self._page:
            self.app.log(f"camera stream from {self.entity_id}: the page changed, stopping")
            return "stop"
        if self.app.device.device_info.get("display_state") == "off":
            # Not a verdict: the display came back by itself before, and nothing
            # would restart this stream if it stopped here. Painting into a dark
            # panel is invisible work, so the frame waits (``_idle``).
            return "idle"
        update = self.app.controller.get("update")
        if update is not None and update.tft_install_active:
            # The panel is taking a new TFT: it answers no page ack, refuses every
            # program, and reboots into a display the page is drawn on again.
            self.app.log(
                f"camera stream from {self.entity_id}: a TFT install owns the display, stopping"
            )
            return "stop"
        esp = self.app.controller.get("esphome")
        if esp is None or not hasattr(esp, "draw_stream_frame"):
            self.app.log(
                f"camera stream from {self.entity_id}: no ESPHome draw path, stopping",
                level="WARNING",
            )
            return "stop"
        return "busy" if esp.drawing else "ok"

    def _invalidate_baseline(self) -> bool:
        """Apply pending invalidation before planning or using a delta."""
        failures = self.app.controller["esphome"].draw_failures
        if not self._repaint_pending and failures == self._draw_failures:
            return False
        self._repaint_pending = False
        self._draw_failures = failures
        self.planner.repaint()
        return True

    def _prepare_on_worker(self) -> tuple[str, DeltaPlanner | None]:
        """Decide whether this frame may be drawn, and what to plan it against.

        Returns:
            The verdict (see ``_frame_status``) and, when it is ``"ok"``, the copy
            of the planner the frame is to be planned on - taken here, on the
            worker, because planning runs in the executor and the worker may
            repaint or replace the planner while it does.
        """
        status = self._frame_status()
        if status == "ok":
            self._invalidate_baseline()
            return status, self.planner.clone()
        if status == "idle":
            # Whatever the panel shows when it comes back, the stream's model of it
            # is hours old: the first frame after the wake paints the rectangle whole.
            self._repaint_pending = True
        return status, None

    def _send_on_worker(
        self,
        runs: list[str],
        full: bool = True,
        planner: DeltaPlanner | None = None,
        snapshot_ready: float | None = None,
        on_done: Callable[[bool], None] | None = None,
    ) -> str:
        """Submit the frame, committing its picture only on completion."""
        status = self._frame_status()
        if status == "idle":
            # The display went dark while this frame was planned: the next one after
            # the wake paints the rectangle whole (``_prepare_on_worker``).
            self._repaint_pending = True
        if status != "ok":
            return status
        if self._invalidate_baseline() and not full:
            # A page repaint may have landed during planning.
            return "stale"
        if not runs:
            self._unchanged += 1
            if planner is not None:
                self.planner = planner
            return "ok"

        if not self._picture_started and self._on_first_frame is not None:
            # A widget visibility command can repaint the area under it, so it
            # has to precede the fills, not the final acknowledgement.
            self._on_first_frame()
        self._picture_started = True
        submitted_at = monotonic()

        def _complete(ok: bool) -> None:
            if on_done is not None:
                on_done(ok)
            if self._stopped.is_set() or self._current_page() is not self._page:
                return
            if not ok:
                self._failed_draws += 1
                self.repaint()
                return
            if planner is not None:
                self.planner = planner
            self._completed += 1
            if self._completed == 1 and snapshot_ready is not None:
                # The first completed draw is the only one whose timing says
                # anything about the stream: it is the one that put the picture
                # up. ``_completed`` already counts it, so no second flag.
                self.app.log(
                    f"camera stream from {self.entity_id}: first draw complete, "
                    f"start to snapshot {(snapshot_ready - self._started_at) * 1000:.0f} ms, "
                    f"snapshot to submit {(submitted_at - snapshot_ready) * 1000:.0f} ms, "
                    f"submit to completion {(monotonic() - submitted_at) * 1000:.0f} ms "
                    f"({len(runs)} fills)"
                )

        self.app.controller["esphome"].draw_stream_frame(
            runs, full=full, external=self._external, on_done=_complete
        )
        return "ok"

    def repaint(self) -> None:
        """Paint the whole rectangle on the next frame (worker).

        The planner's model is only true while the panel shows what this stream
        painted; a page that drew the page's own widgets over the rectangle, or a
        pass the panel did not take whole, leaves it a picture the display no
        longer has. A delta planned against that keeps the ghost for ever, so the
        next frame the stream sends paints the rectangle whole - the same paint
        the first frame of a stream is.

        The request is remembered on the stream, not on the planner: planning runs
        in the executor on a copy of the planner, so a flag set there could be
        overwritten by a frame that was planned before the request was made.
        """
        self._repaint_pending = True

    def repaint_if(self, rect: Rect) -> bool:
        """Ask for a whole paint when another program painted into this rectangle.

        Returns:
            Whether the paint touched this stream's rectangle, so the caller knows
            whether its program wiped part of the picture the planner holds.
        """
        if not self.rect.overlaps(rect):
            return False
        self.repaint()
        return True

    def repaint_for_viewer(self) -> bool:
        """Ask for a whole paint because a viewer has no picture of this rectangle.

        A dashboard card renders the page and needs the fills the panel received;
        the replay cannot describe the area once the stream's oldest fills were
        trimmed (``picture_commands``), so the stream paints it whole and the next
        render carries a picture instead of the page's placeholder.

        Coalesced twice, because a card renders on a schedule and this costs a full
        pass: a request never stacks on one already pending, and no two of them
        land within ``VIEWER_REPAINT_INTERVAL``. Real damage to the rectangle goes
        through ``repaint`` instead, which is neither coalesced nor delayed.

        Returns:
            Whether a paint was requested.
        """
        if self._repaint_pending:
            return False
        now = monotonic()
        if now - self._viewer_repaint_at < VIEWER_REPAINT_INTERVAL:
            return False
        self._viewer_repaint_at = now
        self.repaint()
        return True

    def _current_page(self) -> HAUIPage | None:
        """The loaded page instance; two configured panels can share one HMI id."""
        navigation = self.app.controller.get("navigation")
        return navigation.page if navigation is not None else None

    async def _finish(self) -> None:
        """Tear the stream down once the loop has ended for its own reasons."""
        if _STREAMS.get(self.app.name) is self:
            del _STREAMS[self.app.name]
        self._stopped.set()


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
    """The stream running on ``app``, if any.

    Every path that acts on a stream goes through ``stop_stream``, which only
    needs the verdict; this answers the question left - which stream, drawing
    what - for a test or a diagnostic run, without either reaching into the
    registry.
    """
    return _STREAMS.get(app.name)


def plan_still_frame(frame: bytes, rect: Rect, quality: PictureQuality) -> list[str]:
    """Plan one whole picture of a camera, at a panel's own quality (off the loop).

    A card render has no display to bring up to date: it replays one page once, so
    the picture it carries is the whole rectangle rather than a delta. Planning it
    on an empty planner makes it exactly that - a first paint, at the cell size and
    run budget of the quality a panel on that page would be started with - so the
    card, the preview and the docs screenshots show the picture the panel itself
    would draw.

    Pure and synchronous (decoding and planning are CPU), so a caller hands it to
    an executor instead of running it on the event loop.

    Args:
        frame: The camera's snapshot, in its own encoding (JPEG or PNG).
        rect: The page's picture area, in display pixels.
        quality: The panel's picture quality (``image_stream.QUALITY``).

    Returns:
        The ``fill`` instructions that paint the rectangle whole.

    Raises:
        ImageStreamError: When the bytes are not a decodable image, or the picture
            has no pixels. To a caller that means the same thing: this card has no
            picture and keeps the page's placeholder.
    """
    planner = DeltaPlanner(
        rect,
        cell=quality.cell,
        min_cell=quality.cell,
        max_runs=quality.max_runs,
        first_runs=quality.first_runs,
        refresh_every=0,
        cover=True,
    )
    try:
        return planner.plan(decode_image(frame))
    except ImageProgramError as exc:
        raise ImageStreamError(f"the frame could not be decoded: {exc}") from exc


async def stop_all_streams() -> None:
    """Stop every stream, for an integration unload."""
    for stream in list(_STREAMS.values()):
        await stream.async_stop()


def start_page_stream(
    app: NSPanelHAUI,
    *,
    entity_id: str,
    rect: Rect,
    quality: PictureQuality,
    on_first_frame: Callable[[], None] | None = None,
) -> None:
    """Show a camera on the panel's current page, replacing any other stream.

    Called from the app's worker (a page hands over its picture area while it is
    being shown), so the start is scheduled on the event loop as one step: it
    must not interleave with a service call. ``CameraStream.async_start`` stops
    the stream it replaces, so the replacement is that one step, not a stop this
    function also has to make. Nothing here waits for the loop, and nothing here
    touches the display - the loop reaches back into the worker for every
    command.

    A stream that already draws the same picture (``CameraStream.signature``) is
    left alone: its planner holds the picture the panel is showing, and replacing
    it would repaint a whole frame the panel already has. A page render therefore
    costs nothing once the picture is up.

    Args:
        app: The panel to draw on.
        entity_id: The camera entity to draw.
        rect: The page's picture area, in display pixels.
        quality: What the page's quality setting means - the density of the
            picture, its run budgets and its rate (``image_stream.QUALITY``).
        on_first_frame: Run on the worker once the panel shows a frame.
    """
    hass = app.hass

    def _build() -> CameraStream:
        """A stream for these settings; also how a re-render is compared."""
        return CameraStream(
            hass,
            app,
            entity_id=entity_id,
            rect=rect,
            fps=quality.fps,
            cell=quality.cell,
            # The quality is the density the page asked for: the stream may
            # coarsen when the display cannot keep up, never sharpen past it.
            min_cell=quality.cell,
            max_runs=quality.max_runs,
            first_runs=quality.first_runs,
            # The page hands over an area, not a presentation, so the two things
            # its picture is are settled here. Every frame is cropped to the
            # area: a camera's 16:9 image letterboxed into the portrait text
            # area would use a third of it and show the rest as bands. And the
            # area is painted whole exactly once, when the picture first
            # appears: a periodic full repaint is a visible flash of the
            # rectangle, and the dead band cannot drift, because a cell further
            # than ``band`` from what the panel shows is repainted on its own.
            cover=True,
            refresh_every=0,
            progressive=True,
            external=False,
            on_first_frame=on_first_frame,
        )

    wanted = _build()
    running = _STREAMS.get(app.name)
    if (
        running is not None
        and running._page is wanted._current_page()
        and running.signature == wanted.signature
    ):
        # A page that is being set again stops before it starts; both run in this
        # worker turn, and the stop it asked for is scheduled for the next. Taking
        # it back here is what keeps the picture: the stop would otherwise land on
        # the stream this start just decided to keep.
        running.cancel_stop()
        return

    async def _replace() -> None:
        await wanted.async_start()
        app.log(
            f"camera page: {entity_id} into {rect.w}x{rect.h} at "
            f"({rect.x}, {rect.y}), {wanted.fps:.1f} fps, "
            f"cell {wanted.cell} px"
        )

    _schedule(app, _replace)


async def _apply_stop(app: NSPanelHAUI, stream: CameraStream) -> None:
    """Stop a stream whose stop was requested and not withdrawn since.

    The request and its withdrawal both happen in one worker turn, and this runs
    on the event loop after that turn: a stream that a re-panel kept has already
    cleared the flag, and stopping it would freeze a picture nobody dropped.
    """
    if not stream._stop_requested:
        return
    stream.cancel_stop()
    if _STREAMS.get(app.name) is not stream:
        return
    await stream.async_stop()


def stop_page_stream(app: NSPanelHAUI) -> None:
    """Ask the stream a page started to end; called from the worker.

    The stop is a request until the loop acts on it, so the page that is set
    again in the same worker turn keeps its stream (``CameraStream.request_stop``).
    """
    stream = _STREAMS.get(app.name)
    if stream is None:
        return
    stream.request_stop()
    _schedule(app, lambda: _apply_stop(app, stream))


def repaint_page_stream(app: NSPanelHAUI, *, for_viewer: bool = False) -> None:
    """Ask the stream on ``app`` to paint its whole picture again (worker).

    For the page that owns the rectangle: a render puts the page's own widgets
    where the picture was, so replaying the frame the page remembers would paint a
    stale picture through a second path the stream's model knows nothing about.
    The stream paints the rectangle whole instead, and stays the only thing that
    draws there (``DeltaPlanner.repaint``).

    Args:
        app: The panel to ask.
        for_viewer: A viewer has no picture rather than the page having damaged
            one, so the request is coalesced (``CameraStream.repaint_for_viewer``).
    """
    stream = _STREAMS.get(app.name)
    if stream is None:
        return
    if for_viewer:
        stream.repaint_for_viewer()
    else:
        stream.repaint()


def repaint_rect(app: NSPanelHAUI, rect: Rect) -> None:
    """Tell the stream on ``app`` that another program painted into ``rect``.

    One owner per rectangle: a service image or a page's own draw that lands in
    the camera's area leaves the planner's model of the display wrong, and every
    delta after it would keep the ghost. Only a stream whose rectangle the paint
    overlaps is asked to repaint (``CameraStream.repaint_if``).
    """
    stream = _STREAMS.get(app.name)
    if stream is not None:
        stream.repaint_if(rect)


def _schedule(app: NSPanelHAUI, work: Callable[[], Any]) -> None:
    """Run ``work`` on the event loop as a task, from the worker or from the loop."""
    hass = app.hass
    try:
        hass.loop.call_soon_threadsafe(lambda: hass.async_create_task(work()))
    except RuntimeError:  # the loop is closed: the integration is going away
        app.log("camera page: the event loop is closed, nothing scheduled")

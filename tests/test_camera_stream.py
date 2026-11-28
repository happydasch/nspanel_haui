"""The camera stream: what the panel receives, and every way a stream ends.

These tests drive the loop the way Home Assistant does - snapshots on the event
loop, frames on the panel's worker - against a fake app, so they pin the behaviour
a user sees: a frame is skipped while the panel is still drawing, a still scene
sends nothing, a page change or a sleeping display stops the stream, and a camera
that keeps failing ends it instead of leaving a stale picture on the wall.
"""

from __future__ import annotations

import asyncio
import io
import sys
import types
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock


# The runner imports Home Assistant lazily, so nothing has to be stubbed before it.
class _CameraUnavailable(Exception):
    """Whatever a camera raises when it cannot deliver a snapshot."""


import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from custom_components.nspanel_haui.haui.utils.image_program import Rect  # noqa: E402
from custom_components.nspanel_haui.haui.utils.image_stream import (  # noqa: E402
    DEFAULT_FRAME_RUNS,
    DEFAULT_QUALITY,
    FIRST_FRAME_RUNS,
    QUALITY,
    ImageStreamError,
    PictureQuality,
)
from custom_components.nspanel_haui.hub import camera_stream  # noqa: E402
from custom_components.nspanel_haui.hub.camera_stream import (  # noqa: E402
    MAX_CAMERA_FAILURES,
    CameraStream,
)

RECT = Rect(0, 0, 64, 48)


def _frame(colour: tuple[int, int, int] = (30, 60, 90)) -> bytes:
    """One camera snapshot as a camera delivers it: an encoded picture.

    ``camera.async_get_image`` hands back bytes, not pixels, so the stream is fed
    bytes here too - a test that hands it a decoded picture hides the decode step
    (and once hid the fact that it was missing).
    """
    buffer = io.BytesIO()
    Image.new("RGB", (128, 96), colour).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _no_streams_left_behind():
    """Every test starts and ends with no stream registered for any panel."""
    camera_stream._STREAMS.clear()
    yield
    camera_stream._STREAMS.clear()


def _app(*, page: str = "home", display_state: str = "on", drawing: bool = False) -> Any:
    """A panel app whose worker runs the callback inline."""
    controller = MagicMock()
    controller.drawing = drawing
    controller.draw_failures = 0
    controller.draw_stream_frame.side_effect = lambda runs, *, on_done, **kwargs: on_done(True)
    navigation = MagicMock()
    navigation.page = MagicMock(page_id=page)
    app = MagicMock()
    app.name = "panel"
    app.controller = {"navigation": navigation, "esphome": controller}
    # The state the firmware reports, which is what the stream reads: an absent one
    # is not "off" (``haui/device.py``).
    app.device.device_info = {"display_state": display_state}
    app.async_run_on_worker = AsyncMock(side_effect=lambda fn, *args: fn(*args))
    app.log = MagicMock()
    return app


def _hass() -> Any:
    """A Home Assistant whose executor and task factory run inline."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *args: fn(*args))
    hass.async_create_task = MagicMock(side_effect=lambda coro: MagicMock())
    return hass


def _stream(app: Any, **kwargs: Any) -> CameraStream:
    """A stream for ``app``, registered the way ``async_start`` registers it.

    Settings the caller leaves out are ``CameraStream``'s own. A test that models
    the camera page's stream passes what ``start_page_stream`` fixes for it
    (``cover=True``, ``refresh_every=0``), because that stream must compare equal
    to the one the page asks for.
    """
    stream = CameraStream(
        _hass(),
        app,
        entity_id="camera.front_door",
        rect=RECT,
        fps=kwargs.pop("fps", 4.0),
        refresh_every=0,
        **kwargs,
    )
    stream._page = app.controller["navigation"].page
    camera_stream._STREAMS[app.name] = stream
    return stream


def test_a_frame_is_drawn_once_and_remembered_for_the_last_record():
    """The stream hands its program to the panel, and keeps it for the replay."""
    app = _app()
    stream = _stream(app)
    runs = ["fill 0,0,64,48,1024"]

    assert stream._send_on_worker(runs) == "ok"

    app.controller["esphome"].draw_stream_frame.assert_called_once_with(
        runs, full=True, external=True, on_done=ANY
    )


def test_a_frame_is_skipped_while_the_panel_is_still_drawing():
    """A frame that arrives mid-draw is dropped, never queued behind it."""
    app = _app(drawing=True)
    stream = _stream(app)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "busy"

    app.controller["esphome"].draw_stream_frame.assert_not_called()

    current = stream.planner
    _, _, planned = stream._plan(_frame(), stream.planner.clone())
    assert planned is not current
    assert current.frames == 0
    assert not current.painted

    assert stream._send_on_worker(["fill 0,0,64,48,1024"], planner=planned) == "busy"

    assert stream.planner is current
    assert current.frames == 0
    assert not current.painted


def test_a_pass_the_panel_lost_makes_the_next_frame_a_full_paint():
    """A picture the panel only half received is painted whole again.

    A slice the display never took leaves the runs that did arrive on the screen -
    a band of the picture, not the picture - and every delta after it is planned
    against a model that says otherwise, so nothing would ever fill the rest in.
    """
    app = _app()
    stream = _stream(app)
    stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone()))
    assert stream.planner.painted

    app.controller["esphome"].draw_failures = 1
    stream._send_on_worker([], False, stream._plan(_frame(), stream.planner.clone())[2])

    runs, full, _planned = stream._plan(_frame(), stream.planner.clone())  # the same picture again

    assert full, "the next frame paints the rectangle whole"
    assert runs[0] == f"fill {RECT.x},{RECT.y},{RECT.w},{RECT.h},{runs[0].split(',')[4]}"


def test_the_page_that_owns_the_rectangle_can_ask_for_the_picture_whole():
    """A page that is drawn again puts its own widgets over the picture.

    The page does not replay the frame it remembers - that is a second paint path,
    stale, and cut short by the pass already in flight - it asks the stream, and
    the next frame the stream sends paints the rectangle whole.
    """
    app = _app()
    stream = _stream(app)
    stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone()))

    camera_stream.repaint_page_stream(app)
    assert stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone())) == "stale"
    _runs, full, _planned = stream._plan(_frame(), stream.planner.clone())

    assert full


def test_no_stream_means_nothing_to_repaint():
    """A page that renders with no stream running asks nobody; its own start paints."""
    app = _app()

    camera_stream.repaint_page_stream(app)  # a no-op, not an error


@pytest.mark.parametrize("next_page", ["home", "settings"])
def test_a_page_change_ends_the_stream(next_page):
    """The picture belongs to the page it was started on."""
    app = _app(page="home")
    stream = _stream(app)
    app.controller["navigation"].page = MagicMock(page_id=next_page)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"


def test_a_sleeping_display_costs_nothing_and_wakes_whole():
    """A dark panel is not a verdict: the stream waits, then paints whole again.

    Ending the stream here left the panel frozen - a camera page is not re-rendered
    by a wake, so nothing would start it again. The frame after the wake must paint
    the rectangle whole: the panel may show anything after hours of being dark, and
    the planner's model of it is that old too.
    """
    app = _app(display_state="off")
    stream = _stream(app)

    assert stream._prepare_on_worker() == ("idle", None)
    app.controller["esphome"].draw_stream_frame.assert_not_called()
    assert camera_stream.stream_for(app) is stream, "the stream is still running"
    assert stream._repaint_pending, "the frame after the wake paints the rectangle whole"

    app.device.device_info["display_state"] = "on"
    runs, full, _planned = stream._plan(_frame(), stream.planner.clone())
    assert full and runs, "so the picture comes back at once, not as a delta"


def test_a_reported_state_that_is_missing_is_not_off():
    """A panel that has not said anything yet may be lit; it is not dark either."""
    app = _app(display_state="")
    stream = _stream(app)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "ok"


def test_a_panel_without_the_draw_path_ends_the_stream_instead_of_spinning():
    """A firmware too old to draw must not look like a running stream."""
    app = _app()
    del app.controller["esphome"].draw_stream_frame

    assert _stream(app)._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"


def test_a_stream_stops_during_a_tft_install():
    """The panel took an upload: it refuses programs, and its page is drawn again after.

    The firmware answers ``ok=false`` to everything while ``haui_disp`` is
    updating, so a stream that kept going would spend the whole install
    repainting into a refused display, one pass at a time.
    """
    app = _app()
    app.controller["update"] = types.SimpleNamespace(tft_install_active=True)
    stream = _stream(app)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"
    app.controller["esphome"].draw_stream_frame.assert_not_called()

    app.controller["update"].tft_install_active = False
    assert _stream(app)._send_on_worker(["fill 0,0,64,48,1024"]) == "ok"


def test_an_image_over_the_picture_makes_the_stream_repaint_whole():
    """One owner per rectangle: another program in it leaves the model wrong.

    A service image or a page's own draw into the picture area is not part of the
    planner's model, so every delta after it would keep the ghost of what it
    painted. The stream paints the rectangle whole instead.
    """
    app = _app()
    stream = _stream(app)
    stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone()))
    assert stream.planner.painted

    assert camera_stream.repaint_rect(app, Rect(0, 0, 8, 8)) is None  # it asked the stream
    assert stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone())) == "stale"

    assert stream._plan(_frame(), stream.planner.clone())[1], (
        "the next frame paints the rectangle whole"
    )


def test_a_viewer_asks_for_a_whole_paint_but_not_on_every_render():
    """A card renders on a schedule; a whole paint per render would flash the panel.

    The request is coalesced: never two pending, and no two within
    ``VIEWER_REPAINT_INTERVAL``. Real damage to the rectangle goes through
    ``repaint`` instead, which is neither.
    """
    app = _app()
    stream = _stream(app)

    assert stream.repaint_for_viewer() is True
    assert stream._repaint_pending
    assert stream.repaint_for_viewer() is False, "one pending paint is enough"

    stream._repaint_pending = False
    stream._viewer_repaint_at = 0.0
    assert stream.repaint_for_viewer() is True

    assert stream.repaint_for_viewer() is False, "and the next render waits its turn"


def test_the_page_that_owns_the_rectangle_is_not_put_off_by_the_viewer_window():
    """A page render damaged the picture: that repaint is never coalesced away."""
    app = _app()
    stream = _stream(app)
    stream.repaint_for_viewer()
    stream._repaint_pending = False

    camera_stream.repaint_page_stream(app)

    assert stream._repaint_pending


def test_an_image_in_another_rectangle_leaves_the_stream_alone():
    """A program that never touches the picture costs the stream nothing."""
    app = _app()
    stream = _stream(app)
    stream._send_on_worker(*stream._plan(_frame(), stream.planner.clone()))

    camera_stream.repaint_rect(app, Rect(100, 100, 8, 8))

    runs, full, _planned = stream._plan(_frame(), stream.planner.clone())
    assert not runs and not full, "the picture the panel shows is still the stream's"


def test_the_placeholder_goes_away_once_the_first_frame_is_drawn():
    """The page keeps its placeholder until a real frame has painted over it."""
    app = _app()
    hidden = []
    stream = _stream(app, on_first_frame=lambda: hidden.append("hidden"))

    stream._send_on_worker(["fill 0,0,64,48,1024"])
    stream._send_on_worker(["fill 0,0,8,8,2048"])

    assert hidden == ["hidden"]


def test_an_empty_frame_leaves_the_placeholder_alone():
    """An idle camera sends nothing, so nothing has painted over the placeholder."""
    app = _app()
    hidden = []
    stream = _stream(app, on_first_frame=lambda: hidden.append("hidden"))

    assert stream._send_on_worker([]) == "ok"

    assert hidden == []


def test_a_delta_does_not_claim_to_cover_the_whole_picture():
    """Replay must preserve the untouched pixels between a delta's fills."""
    app = _app()
    stream = _stream(app)
    whole = ["fill 0,0,64,48,1024", "fill 0,0,8,8,2048"]
    delta = ["fill 24,16,8,8,3999"]

    stream._send_on_worker(whole, full=True)
    stream._send_on_worker(delta, full=False)

    app.controller["esphome"].draw_stream_frame.assert_called_with(
        delta, full=False, external=True, on_done=ANY
    )


@pytest.mark.asyncio
async def test_the_page_stream_fixes_its_own_presentation(monkeypatch):
    """The page hands over an area, not a presentation, so its stream is both.

    Frames are cropped to that area - a camera's 16:9 image letterboxed into the
    portrait text area would use a third of it and show the rest as bands - and
    the area is painted whole exactly once. A periodic full paint is a visible
    flash of the whole area, and the dead band cannot drift: a cell further than
    the band from what the panel shows is repainted by itself.
    """
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass
    made: list[dict[str, Any]] = []

    class _RecordingStream:
        def __init__(self, stream_hass: Any, stream_app: Any, **kwargs: Any) -> None:
            made.append(kwargs)
            self.fps = kwargs["fps"]
            self.cell = kwargs["cell"]
            self.planner = types.SimpleNamespace(cell=kwargs["cell"])

        async def async_start(self) -> None:
            made[0]["started"] = True

    monkeypatch.setattr(camera_stream, "CameraStream", _RecordingStream)

    camera_stream.start_page_stream(
        app, entity_id="camera.front_door", rect=RECT, quality=QUALITY[DEFAULT_QUALITY]
    )
    assert len(created) == 1
    await created[0]

    assert made[0]["cover"] is True
    assert made[0]["refresh_every"] == 0


def _loop_hass() -> tuple[Any, list[Any]]:
    """A Home Assistant that runs scheduled callbacks now and hands back its tasks."""
    created: list[Any] = []
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = MagicMock(side_effect=lambda fn: fn())
    hass.async_create_task = MagicMock(side_effect=lambda coro: created.append(coro) or MagicMock())
    return hass, created


@pytest.mark.asyncio
async def test_a_page_start_is_scheduled_on_the_loop_not_run_on_the_worker(monkeypatch):
    """A page hands over its rectangle from the worker; the stream starts on the loop."""
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass
    made: list[dict[str, Any]] = []
    quality = PictureQuality(cell=3, fps=3.0, max_runs=900, first_runs=4000)

    class _RecordingStream:
        def __init__(self, stream_hass: Any, stream_app: Any, **kwargs: Any) -> None:
            made.append(kwargs)
            self.fps = kwargs["fps"]
            self.cell = kwargs["cell"]
            self.planner = types.SimpleNamespace(cell=kwargs["cell"])

        async def async_start(self) -> None:
            made[0]["started"] = True

    monkeypatch.setattr(camera_stream, "CameraStream", _RecordingStream)

    camera_stream.start_page_stream(
        app,
        entity_id="camera.front_door",
        rect=RECT,
        quality=quality,
        on_first_frame=lambda: None,
    )

    assert len(created) == 1, "the worker scheduled the work instead of awaiting it"
    await created[0]
    assert made[0]["entity_id"] == "camera.front_door"
    assert made[0]["rect"] == RECT
    # the quality is the whole picture: density, both budgets and the rate
    assert made[0]["cell"] == 3
    assert made[0]["min_cell"] == 3, "the stream never sharpens past the chosen density"
    assert made[0]["max_runs"] == 900
    assert made[0]["first_runs"] == 4000
    assert made[0]["fps"] == 3.0
    assert made[0]["started"] is True


def test_a_page_that_asks_for_the_picture_already_running_keeps_it():
    """A re-render must not restart the stream: its planner holds the picture.

    A new stream starts from a full paint, which is a flash of the whole area for
    a picture the display already shows.
    """
    app = _app()
    app.hass = _loop_hass()[0]
    quality = PictureQuality(
        cell=4, fps=4.0, max_runs=DEFAULT_FRAME_RUNS, first_runs=FIRST_FRAME_RUNS
    )
    running = _stream(
        app, fps=4.0, cell=4, min_cell=4, cover=True, progressive=True, external=False
    )

    camera_stream.start_page_stream(app, entity_id="camera.front_door", rect=RECT, quality=quality)

    assert camera_stream.stream_for(app) is running
    app.hass.async_create_task.assert_not_called()


@pytest.mark.asyncio
async def test_a_page_that_keeps_its_stream_survives_the_stop_it_scheduled():
    """A page that is set again stops before it starts, both in one worker turn.

    The stop is only a request until the loop acts on it, and this worker turn
    withdraws it. Without that the stop lands on the stream the same turn just
    decided to keep: the video freezes on its last frame, with no stream left to
    paint and no placeholder either.
    """
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass
    quality = PictureQuality(
        cell=4, fps=4.0, max_runs=DEFAULT_FRAME_RUNS, first_runs=FIRST_FRAME_RUNS
    )
    running = _stream(
        app, fps=4.0, cell=4, min_cell=4, cover=True, progressive=True, external=False
    )

    camera_stream.stop_page_stream(app)
    camera_stream.start_page_stream(app, entity_id="camera.front_door", rect=RECT, quality=quality)

    assert camera_stream.stream_for(app) is running
    for work in created:
        await work
    assert camera_stream.stream_for(app) is running, "the stop it asked for was withdrawn"


@pytest.mark.asyncio
async def test_a_start_stops_the_stream_it_replaces_once(monkeypatch):
    """Replacing is the start's own job, so both entry paths get it for free.

    The camera page and the service both replace by asking a stream to start;
    neither stops the old one first, which would be the same lookup twice.
    """
    app = _app()
    hass = _hass()
    # The loop would run the frame loop; here the task is accepted and dropped.
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    app.hass = hass
    replaced = _stream(app)
    stopped: list[CameraStream] = []
    real_stop = CameraStream.async_stop

    async def _counting_stop(stream: CameraStream) -> None:
        stopped.append(stream)
        await real_stop(stream)

    monkeypatch.setattr(CameraStream, "async_stop", _counting_stop)
    wanted = CameraStream(hass, app, entity_id="camera.back_door", rect=RECT, fps=2.0)

    await wanted.async_start()

    assert stopped == [replaced], "the replaced stream stopped exactly once"
    assert camera_stream.stream_for(app) is wanted


@pytest.mark.parametrize(
    "change",
    [
        {"cell": 3},
        {"min_cell": 2},
        {"max_runs": 900},
        {"first_runs": 4000},
        {"fps": 2.0},
        {"cover": True},
        {"refresh_every": 5},
    ],
)
def test_anything_that_changes_the_picture_starts_the_stream_again(change):
    """A re-render keeps the stream only when it asks for the same picture.

    The signature is what says so, so every setting that decides what the panel
    shows has to be in it - a denser picture, another budget or another rate is a
    new stream, started from a full paint.
    """
    app = _app()
    running = _stream(app, fps=4.0, cell=4, min_cell=4)
    wanted = CameraStream(
        _hass(),
        app,
        entity_id="camera.front_door",
        rect=RECT,
        **{"fps": 4.0, "cell": 4, "min_cell": 4, **change},
    )

    assert wanted.signature != running.signature


def test_a_stream_that_had_to_coarsen_still_draws_what_the_page_asked_for():
    """The planner's cell grows when the display cannot keep up with the picture.

    That is the stream adapting to the panel, not a different picture: the page
    asks for the quality it stored, and a re-render asking for the same thing must
    keep the stream - starting it again paints the whole rectangle (a full paint
    clears the area first) for a picture the display already shows.
    """
    app = _app()
    running = _stream(app, fps=4.0, cell=4, min_cell=4)
    running.planner.cell = 6

    wanted = CameraStream(
        _hass(),
        app,
        entity_id="camera.front_door",
        rect=RECT,
        fps=4.0,
        cell=4,
        min_cell=4,
        refresh_every=0,
    )

    assert wanted.signature == running.signature


@pytest.mark.asyncio
async def test_leaving_the_page_stops_the_stream_from_the_worker():
    """The page's cleanup is scheduled too: it must not wait for the loop."""
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass
    _stream(app)

    camera_stream.stop_page_stream(app)

    assert len(created) == 1
    await created[0]
    assert camera_stream.stream_for(app) is None


def test_leaving_a_page_with_no_stream_schedules_nothing():
    """Nothing to stop is nothing to schedule: no task for every page that leaves."""
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass

    camera_stream.stop_page_stream(app)

    assert created == []


@pytest.mark.asyncio
async def test_startup_waits_for_each_ack_and_reuses_one_snapshot():
    app = _app()
    stream = _stream(app, fps=1, progressive=True)
    stream._snapshot = AsyncMock(return_value=_frame())
    draws: asyncio.Queue = asyncio.Queue()
    esp = app.controller["esphome"]
    esp.draw_stream_frame.side_effect = lambda runs, *, on_done, **kwargs: draws.put_nowait(
        (runs, on_done)
    )

    task = asyncio.create_task(stream._run())
    try:
        for _ in range(4):
            _runs, ack = await asyncio.wait_for(draws.get(), timeout=0.5)
            assert stream._snapshot.await_count == 1
            await asyncio.sleep(0)
            assert draws.empty()
            ack(True)
        assert any("first draw complete" in call.args[0] for call in app.log.call_args_list)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_the_loop_sends_only_what_changed():
    """An unchanged frame costs nothing; a changed one is one program."""
    app = _app()
    stream = _stream(app, fps=50)
    stream._snapshot = AsyncMock(side_effect=[_frame(), _frame(), _frame((200, 40, 40))])

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if stream._snapshot.await_count >= 3:
            break
    stream._stopped.set()
    await task

    esp = app.controller["esphome"]
    assert esp.draw_stream_frame.call_count == 2, "one full paint, then only the change"
    assert stream.frames == 3, "the unchanged frame still counted as a frame, but sent nothing"


@pytest.mark.asyncio
async def test_a_camera_that_stops_answering_keeps_trying_instead_of_ending(monkeypatch):
    """A camera that is gone must not leave the panel frozen for good.

    Ending the stream left a stale picture on the wall until someone re-opened the
    page: a cloud camera that reconnects, or an integration that reloads, never got
    a second chance. The stream backs off and keeps trying at
    ``CAMERA_RETRY_INTERVAL``, and the picture it already painted stays.
    """
    monkeypatch.setattr(camera_stream, "CAMERA_RETRY_INTERVAL", 0.05)
    app = _app()
    stream = _stream(app, fps=50)
    stream._snapshot = AsyncMock(side_effect=_CameraUnavailable("camera unavailable"))

    task = asyncio.create_task(stream._run())
    for _ in range(400):
        await asyncio.sleep(0.01)
        if stream._snapshot.await_count > MAX_CAMERA_FAILURES:
            break
    still_running = camera_stream.stream_for(app) is stream
    stream._stopped.set()
    await task

    assert still_running, "the stream is still there after the camera went away"
    assert stream._snapshot.await_count > MAX_CAMERA_FAILURES, "and it asked again"
    app.controller["esphome"].draw_stream_frame.assert_not_called()
    assert any("tries again every" in call.args[0] for call in app.log.call_args_list), (
        "the panel keeps its picture, and the log says why"
    )


@pytest.mark.asyncio
async def test_a_recovered_camera_answers_with_a_frame(monkeypatch):
    """A snapshot that arrives after the outage paints, and the next frames follow."""
    monkeypatch.setattr(camera_stream, "CAMERA_RETRY_INTERVAL", 0.05)
    app = _app()
    stream = _stream(app, fps=50, progressive=True)
    stream._snapshot = AsyncMock(
        side_effect=[_CameraUnavailable("camera unavailable"), _frame(), _frame((200, 40, 40))]
    )

    task = asyncio.create_task(stream._run())
    for _ in range(400):
        await asyncio.sleep(0.01)
        if app.controller["esphome"].draw_stream_frame.called:
            break
    stream._stopped.set()
    await task

    assert app.controller["esphome"].draw_stream_frame.called, "the camera came back and painted"
    assert any("answered again" in call.args[0] for call in app.log.call_args_list)


@pytest.mark.asyncio
async def test_two_panels_drawing_one_camera_share_a_snapshot(monkeypatch):
    """One camera, one fetch per share window, however many panels draw it."""
    calls: list[str] = []

    async def _async_get_image(hass: Any, entity_id: str, **kwargs: Any) -> Any:
        calls.append(entity_id)
        return types.SimpleNamespace(content_type="image/png", content=_frame())

    module = types.ModuleType("homeassistant.components.camera")
    module.async_get_image = _async_get_image
    monkeypatch.setitem(sys.modules, "homeassistant.components.camera", module)

    first = _stream(_app())
    # A second panel, which is what makes the share possible at all: a stream never
    # reuses a frame it fetched itself.
    second_app = _app()
    second_app.name = "panel-2"
    second = _stream(second_app)

    assert await first._snapshot() == await second._snapshot()
    assert len(calls) == 1, "the second panel reused the first panel's frame"

    # A stream never reuses its own frame: that would halve its frame rate.
    await first._snapshot()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_a_snapshot_is_the_encoded_bytes_home_assistant_returns(monkeypatch):
    """``camera.async_get_image`` hands back the picture's bytes, not pixels.

    The stream must decode them before planning: a frame that reached the planner
    still encoded failed there, and a failure there is not a camera failure, so
    the stream died on its first frame and the page kept its placeholder.
    """
    asked: list[dict[str, Any]] = []

    async def _async_get_image(hass: Any, entity_id: str, **kwargs: Any) -> Any:
        asked.append({"entity_id": entity_id, **kwargs})
        return types.SimpleNamespace(content_type="image/png", content=_frame())

    module = types.ModuleType("homeassistant.components.camera")
    module.async_get_image = _async_get_image
    monkeypatch.setitem(sys.modules, "homeassistant.components.camera", module)

    app = _app()
    stream = _stream(app, fps=50)

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if app.controller["esphome"].draw_stream_frame.called:
            break
    stream._stopped.set()
    await task

    assert asked and asked[0]["entity_id"] == "camera.front_door"
    runs = app.controller["esphome"].draw_stream_frame.call_args.args[0]
    assert runs[0].startswith("fill "), "the first frame paints the whole rectangle"
    assert stream.frames >= 1


@pytest.mark.asyncio
async def test_a_frame_the_decoder_cannot_read_does_not_end_the_stream():
    """A truncated snapshot is one bad frame, not a dead stream."""
    app = _app()
    hidden: list[str] = []
    stream = _stream(app, fps=50, on_first_frame=lambda: hidden.append("hidden"))
    stream._snapshot = AsyncMock(side_effect=[b"not an image", _frame()])

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if stream._snapshot.await_count >= 2 and app.controller["esphome"].draw_stream_frame.called:
            break
    stream._stopped.set()
    await task

    assert app.controller["esphome"].draw_stream_frame.call_count == 1, (
        "the next frame still went out"
    )
    assert hidden == ["hidden"], "so the placeholder does go away"
    assert any("frame refused" in call.args[0] for call in app.log.call_args_list), (
        "and the refusal is logged"
    )


@pytest.mark.parametrize("change", [{"band": 12}, {"external": True}])
def test_the_signature_covers_the_dead_band_and_the_sandbox_flag(change):
    """Both decide what reaches the display, so a stream that differs is another."""
    app = _app()
    running = _stream(app, fps=4.0, cell=4, min_cell=4, external=False)
    wanted = CameraStream(
        _hass(),
        app,
        entity_id="camera.front_door",
        rect=RECT,
        fps=4.0,
        cell=4,
        min_cell=4,
        refresh_every=0,
        **change,
    )

    assert wanted.signature != running.signature


@pytest.mark.asyncio
async def test_a_startup_pass_that_never_completes_does_not_wedge_the_loop(monkeypatch):
    """A draw nobody reports must not leave the stream awaiting a future for ever.

    The per-slice timer ends a pass on a real panel, but the loop cannot depend on
    it: a controller replaced mid-pass, or a transport that swallows a draw, would
    stop the picture mid-startup with the placeholder already gone - and nothing
    would ever say so.
    """
    monkeypatch.setattr(camera_stream, "STARTUP_ACK_TIMEOUT", 0.05)
    app = _app()
    stream = _stream(app, fps=50, progressive=True)
    stream._snapshot = AsyncMock(return_value=_frame())
    esp = app.controller["esphome"]
    esp.draw_stream_frame.side_effect = lambda runs, *, on_done, **kwargs: None

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if esp.draw_stream_frame.call_count >= 2:
            break
    stream._stopped.set()
    await task

    assert esp.draw_stream_frame.call_count >= 2, "the loop gave up on the pass and went on"
    assert any("no acknowledgement" in call.args[0] for call in app.log.call_args_list)


@pytest.mark.asyncio
async def test_an_unexpected_error_ends_the_stream_and_says_so():
    """A dead task would leave the page on its placeholder for ever, silently."""
    app = _app()
    stream = _stream(app, fps=50)
    stream._snapshot = AsyncMock(return_value=_frame())
    stream.planner.plan = MagicMock(side_effect=RuntimeError("boom"))

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if camera_stream.stream_for(app) is None:
            break
    await asyncio.wait_for(task, timeout=5)

    assert camera_stream.stream_for(app) is None, "the panel is free to start another stream"
    error = [call for call in app.log.call_args_list if call.kwargs.get("level") == "ERROR"]
    assert error, "the reason reaches the log"
    assert "boom" in error[0].args[0]


# a card's picture: one whole paint, planned for the panel


def _detailed_frame() -> bytes:
    """A snapshot with detail in it: a flat picture cannot show a quality setting."""
    image = Image.new("RGB", (240, 135))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            pixels[x, y] = ((x * 7 + y * 3) % 256, (x * 2) % 256, (y * 5) % 256)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _inside(rect: Rect, run: str) -> bool:
    """Whether a ``fill`` instruction stays inside ``rect``."""
    x, y, w, h = (int(value) for value in run[len("fill ") :].split(",")[:4])
    return rect.x <= x and rect.y <= y and x + w <= rect.right and y + h <= rect.bottom


def test_a_card_picture_is_the_whole_rectangle_in_one_paint():
    """A card replays one page once, so its picture is a first paint, not a delta."""
    rect = Rect(12, 65, 260, 240)

    runs = camera_stream.plan_still_frame(_detailed_frame(), rect, QUALITY["mid"])

    assert runs, "the card has a picture to draw"
    assert runs[0].startswith(f"fill {rect.x},{rect.y},{rect.w},{rect.h},"), (
        "the first run covers the area, so nothing of what was there shows through"
    )
    assert all(_inside(rect, run) for run in runs), "and nothing is painted outside it"
    assert len(runs) <= QUALITY["mid"].first_runs


def test_a_card_picture_follows_the_quality_the_panel_is_set_to():
    """The card shows what the panel would draw: a finer setting is a denser picture."""
    rect = Rect(12, 65, 260, 240)
    frame = _detailed_frame()

    counts = {
        name: len(camera_stream.plan_still_frame(frame, rect, QUALITY[name]))
        for name in ("high", "mid", "low")
    }

    assert counts["low"] < counts["mid"] < counts["high"], counts


def test_a_card_picture_that_is_not_an_image_is_refused():
    """A camera that answers with something undecodable is a card with no picture."""
    with pytest.raises(ImageStreamError):
        camera_stream.plan_still_frame(b"not a picture", RECT, QUALITY[DEFAULT_QUALITY])

"""The camera stream: what the panel receives, and every way a stream ends.

These tests drive the loop the way Home Assistant does - snapshots on the event
loop, frames on the panel's worker - against a fake app, so they pin the behaviour
a user sees: a frame is skipped while the panel is still drawing, a still scene
sends nothing, a page change or a sleeping display stops the stream, and a camera
that keeps failing ends it instead of leaving a stale picture on the wall.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock


# The runner imports Home Assistant lazily, so nothing has to be stubbed before it.
class _CameraUnavailable(Exception):
    """Whatever a camera raises when it cannot deliver a snapshot."""


import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from custom_components.nspanel_haui.haui.utils.image_program import Rect  # noqa: E402
from custom_components.nspanel_haui.hub import camera_stream  # noqa: E402
from custom_components.nspanel_haui.hub.camera_stream import (  # noqa: E402
    MAX_CAMERA_FAILURES,
    CameraStream,
)

RECT = Rect(0, 0, 64, 48)


def _frame(colour: tuple[int, int, int] = (30, 60, 90)) -> Image.Image:
    """One camera snapshot: a flat picture is enough to see what was sent."""
    return Image.new("RGB", (128, 96), colour)


def _app(*, page: str = "home", display_state: str = "on", drawing: bool = False) -> Any:
    """A panel app whose worker runs the callback inline."""
    controller = MagicMock()
    controller.drawing = drawing
    navigation = MagicMock()
    navigation.page = MagicMock(page_id=page)
    app = MagicMock()
    app.name = "panel"
    app.controller = {"navigation": navigation, "esphome": controller}
    app.device.display_state = display_state
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
    """A stream for ``app`` that starts on the page the fake panel shows."""
    stream = CameraStream(
        _hass(),
        app,
        entity_id="camera.front_door",
        rect=RECT,
        fps=kwargs.pop("fps", 4.0),
        refresh_every=0,
        **kwargs,
    )
    stream._page = app.controller["navigation"].page.page_id
    return stream


def test_a_frame_is_drawn_once_and_remembered_for_the_last_record():
    """The stream hands its program to the panel, and keeps it for the replay."""
    app = _app()
    stream = _stream(app)
    runs = ["fill 0,0,64,48,1024"]

    assert stream._send_on_worker(runs) == "ok"

    app.controller["esphome"].draw_stream_frame.assert_called_once_with(runs)
    assert stream._last_runs == runs


def test_a_frame_is_skipped_while_the_panel_is_still_drawing():
    """A frame that arrives mid-draw is dropped, never queued behind it."""
    app = _app(drawing=True)
    stream = _stream(app)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "busy"

    app.controller["esphome"].draw_stream_frame.assert_not_called()
    assert stream._last_runs == []


def test_a_page_change_ends_the_stream():
    """The picture belongs to the page it was started on."""
    app = _app(page="home")
    stream = _stream(app)
    app.controller["navigation"].page = MagicMock(page_id="settings")

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"


def test_a_sleeping_display_ends_the_stream():
    """Painting into a dark panel wastes the link and the camera."""
    app = _app(display_state="off")
    stream = _stream(app)

    assert stream._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"


def test_a_panel_without_the_draw_path_ends_the_stream_instead_of_spinning():
    """A firmware too old to draw must not look like a running stream."""
    app = _app()
    del app.controller["esphome"].draw_stream_frame

    assert _stream(app)._send_on_worker(["fill 0,0,64,48,1024"]) == "stop"


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

    class _RecordingStream:
        def __init__(self, stream_hass: Any, stream_app: Any, **kwargs: Any) -> None:
            made.append(kwargs)
            self.fps = kwargs["fps"]

        async def async_start(self) -> None:
            made[0]["started"] = True

    monkeypatch.setattr(camera_stream, "CameraStream", _RecordingStream)

    camera_stream.start_page_stream(
        app, entity_id="camera.front_door", rect=RECT, fps=3.0, on_first_frame=lambda: None
    )

    assert len(created) == 1, "the worker scheduled the work instead of awaiting it"
    await created[0]
    assert made[0]["entity_id"] == "camera.front_door"
    assert made[0]["rect"] == RECT
    assert made[0]["fps"] == 3.0
    assert made[0]["started"] is True


@pytest.mark.asyncio
async def test_leaving_the_page_stops_the_stream_from_the_worker():
    """The page's cleanup is scheduled too: it must not wait for the loop."""
    app = _app()
    hass, created = _loop_hass()
    app.hass = hass

    camera_stream.stop_page_stream(app)

    assert len(created) == 1
    await created[0]
    assert camera_stream.stream_for(app) is None


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
    assert esp.record_stream_frame.call_count == 1, "the last frame is recorded once"
    assert stream.frames == 3, "the unchanged frame still counted as a frame, but sent nothing"


@pytest.mark.asyncio
async def test_a_camera_that_keeps_failing_ends_the_stream():
    """A camera that is gone must not leave the panel repainting nothing forever."""
    app = _app()
    stream = _stream(app, fps=50)
    stream._snapshot = AsyncMock(side_effect=_CameraUnavailable("camera unavailable"))

    task = asyncio.create_task(stream._run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if stream._snapshot.await_count >= MAX_CAMERA_FAILURES:
            break
    stream._stopped.set()
    await task

    assert stream._snapshot.await_count == MAX_CAMERA_FAILURES
    app.controller["esphome"].draw_stream_frame.assert_not_called()
    assert camera_stream.stream_for(app) is None

"""The ESPHome controller's record of what the shown page was sent (``page_commands``).

A Live viewer that attaches late replays it on a freshly loaded page, so it must
end on the screen the panel shows, and stay small while a page is shown for days.
"""

from __future__ import annotations

import types
from typing import Any

from test_connection import DummyApp

from custom_components.nspanel_haui.haui.controller.esphome import HAUIESPHomeController
from custom_components.nspanel_haui.haui.utils.draw_wire import (
    DRAW_SLICE_CHARS,
    LEGACY_SLICE_RUNS,
    decode_program,
    pack_run,
)
from custom_components.nspanel_haui.haui.utils.image_program import Rect


class _App(DummyApp):
    def __init__(self) -> None:
        super().__init__()
        self.previewed: list[tuple[str, Any]] = []

    def publish_preview_output(self, command: str, value: Any, *, external: bool = False) -> None:
        self.previewed.append((command, value))


class _Proxy:
    def __init__(self) -> None:
        self.connected = True

    def publish(self, name: str, value: Any = "") -> bool:
        return self.connected


def _controller() -> tuple[HAUIESPHomeController, _Proxy]:
    proxy = _Proxy()
    return HAUIESPHomeController(_App(), {"device_name": "kitchen"}, proxy, lambda e: None), proxy


def test_the_last_write_to_each_target_is_kept_in_the_order_written() -> None:
    ctrl, _proxy = _controller()

    ctrl.send_cmd("send_commands", ['a.txt="1"', 'b.txt="2"', "vis a,0", "tsw a,0"])
    ctrl.send_cmd("send_command", 'a.txt="3"')
    ctrl.send_cmd("send_command", "vis a,1")

    assert ctrl.page_commands() == ['b.txt="2"', "tsw a,0", 'a.txt="3"', "vis a,1"]


def test_drawing_keeps_its_place_after_the_picture_it_draws_on() -> None:
    # Setting a picture paints over earlier drawing on it; a replay in the
    # order of the last writes ends on the same screen.
    ctrl, _proxy = _controller()

    for command in ("p.pic=1", "cirs 10,10,6,0", "p.pic=1", "cirs 20,20,6,0", "cirs 20,20,6,0"):
        ctrl.send_cmd("send_command", command, force=True)

    assert ctrl.page_commands() == ["cirs 10,10,6,0", "p.pic=1", "cirs 20,20,6,0"]


def test_a_page_switch_starts_the_record_over() -> None:
    ctrl, _proxy = _controller()
    ctrl.send_cmd("send_command", 'a.txt="1"')

    ctrl.send_cmd("goto_page", "6")
    ctrl.send_cmd("send_command", 'c.txt="2"')

    assert ctrl.page_commands() == ['c.txt="2"']


def test_a_command_the_panel_did_not_get_is_not_recorded() -> None:
    ctrl, proxy = _controller()
    proxy.connected = False

    ctrl.send_cmd("send_command", 'a.txt="1"')

    assert ctrl.page_commands() == []


def test_a_command_the_panel_did_not_get_is_sent_again() -> None:
    ctrl, proxy = _controller()
    proxy.connected = False
    ctrl.send_cmd("send_command", 'a.txt="1"')

    proxy.connected = True
    ctrl.send_cmd("send_command", 'a.txt="1"')

    assert ctrl.page_commands() == ['a.txt="1"']


# ── image drawing ────────────────────────────────────────────────────────────


class _DrawingProxy(_Proxy):
    """Records the draw programs it is handed."""

    def __init__(self) -> None:
        super().__init__()
        self.programs: list[str] = []

    def publish(self, name: str, value: Any = "") -> bool:
        if name == "draw_runs":
            self.programs.append(str(value))
        return super().publish(name, value)


def _drawing(
    *, draw_format: int | None = None
) -> tuple[HAUIESPHomeController, _DrawingProxy, _App]:
    proxy = _DrawingProxy()
    app = _App()
    if draw_format is not None:
        app.device.device_info = {"draw_format": draw_format}
    controller = HAUIESPHomeController(app, {"device_name": "kitchen"}, proxy, lambda e: None)
    return controller, proxy, app


def _runs(count: int) -> list[str]:
    """Distinct spans, as a real image produces: the replay keeps one per target."""
    return [f"fill {index % 480},{index // 480},8,8,65535" for index in range(count)]


def _sent(proxy: _DrawingProxy) -> list[list[str]]:
    """What the panel actually receives, decoded back to display commands."""
    return [decode_program(program) for program in proxy.programs]


def test_an_image_is_sent_one_slice_at_a_time() -> None:
    """The panel stages one slice, reports it, and only then gets the next."""
    controller, proxy, _app = _drawing()
    runs = _runs(1200)

    controller.send_cmd("draw_runs", runs)

    assert len(proxy.programs) == 1, "a slice at a time, not the whole pass at once"
    assert len(proxy.programs[0]) <= DRAW_SLICE_CHARS

    while controller._draw_slices:
        controller.on_draw_report(True)

    assert len(proxy.programs) > 1
    assert [run for part in _sent(proxy) for run in part] == runs


def test_a_simulated_panel_waits_for_the_fence_like_a_real_one() -> None:
    """The virtual firmware answers a slice too, so the preview shows a busy display.

    Painting as it records - the shortcut this replaces - hid two states the panel
    lives in: ``drawing`` was never true, so a frame arriving mid-draw was never
    skipped, and every pass was confirmed instantly, so a lost or refused slice
    could not happen in the preview at all.
    """
    controller, proxy, app = _drawing()
    runs = _runs(1200)

    controller.send_cmd("draw_runs", runs)

    assert len(proxy.programs) == 1, "one slice at a time, as on the panel"
    assert controller.drawing
    assert controller._draw_timer is not None, "the fence is waited for, not bypassed"

    controller.on_draw_report(True)

    assert len(proxy.programs) == 2, "the next slice follows the report"


def test_a_slice_that_never_reports_is_followed_by_the_next_one() -> None:
    """A report lost to a busy panel must not wedge the rest of the image."""
    controller, proxy, app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))
    assert len(proxy.programs) == 1
    ((callback, _kwargs),) = app.timers.values()

    callback()

    assert len(proxy.programs) == 2
    assert any("no report for a slice" in message for message, _ in app.logged)


def test_a_camera_frame_can_follow_a_draw_that_lost_its_final_report() -> None:
    controller, proxy, app = _drawing(draw_format=2)
    results: list[bool] = []
    controller.draw_stream_frame(_runs(12), on_done=results.append)
    ((callback, kwargs),) = app.timers.values()

    callback(**kwargs)

    assert not controller.drawing
    assert controller.draw_failures == 1
    assert results == [False]
    controller.draw_stream_frame(_runs(16), on_done=results.append)
    assert _sent(proxy)[-1] == _runs(16)
    controller.on_draw_report(True)
    assert results == [False, True]


def test_a_refused_publish_releases_the_draw_slot(monkeypatch) -> None:
    controller, proxy, app = _drawing(draw_format=2)
    results: list[bool] = []
    monkeypatch.setattr(proxy, "publish", lambda *_args: False)
    controller.draw_stream_frame(_runs(12), on_done=results.append)

    assert not controller.drawing
    assert not app.timers
    assert controller.draw_failures == 1
    assert results == [False]


def test_a_cancelled_camera_draw_is_not_acknowledged() -> None:
    controller, _proxy, _app = _drawing(draw_format=2)
    results: list[bool] = []
    controller.draw_stream_frame(_runs(12), on_done=results.append)

    controller.cancel_draw()
    controller.on_draw_report(True)

    assert not controller.drawing
    assert results == [False]


def test_a_refused_slice_re_sends_the_whole_image_once() -> None:
    """A slice the panel did not take leaves gaps: paint the picture again.

    Whatever the panel dropped - a lost acknowledgment, a run an overrun display
    truncated - the pass is re-sent from its first run, and only a second failure
    drops the rest instead of looping.
    """
    controller, proxy, app = _drawing()
    runs = _runs(1200)
    controller.send_cmd("draw_runs", runs)
    assert len(proxy.programs) == 1

    controller.on_draw_report(False)

    assert len(proxy.programs) == 2
    assert _sent(proxy)[1][0] == runs[0], "the retry starts the picture over"
    assert any("re-sending the image once" in message for message, _ in app.logged)

    controller.on_draw_report(False)

    assert len(proxy.programs) == 2, "a second failure stops instead of looping"
    assert controller._draw_slices == []
    assert any("refused a slice again" in message for message, _ in app.logged)


def test_live_and_late_replay_follow_acknowledged_slices_only() -> None:
    controller, proxy, app = _drawing(draw_format=2)
    controller.send_cmd("draw_runs", _runs(1200))
    first = decode_program(proxy.programs[0])

    assert app.previewed == []
    assert controller.page_commands() == []
    controller.on_draw_report(True, runs=len(first) - 1)
    assert app.previewed == []
    assert controller.page_commands() == []
    controller.on_draw_report(True, runs=len(first))

    assert app.previewed == [("draw_runs", first)]
    assert controller.page_commands() == first
    controller.cancel_draw()
    controller.on_draw_report(True)
    assert app.previewed == [("draw_runs", first)]
    assert controller.page_commands() == first


def test_a_refused_image_is_not_mirrored_or_replayed() -> None:
    controller, proxy, app = _drawing()
    proxy.connected = False
    controller.send_cmd("draw_runs", ["fill 10,10,40,40,65535"])

    assert app.previewed == []
    assert controller.page_commands() == []


def test_a_clear_removes_only_the_image_it_covers_from_the_replay() -> None:
    controller, _proxy, _app = _drawing(draw_format=2)
    first = ["fill 10,10,40,40,65535", "fill 20,20,10,10,255"]
    elsewhere = ["fill 200,10,40,40,255"]
    cleared = ["fill 10,10,40,40,4660"]

    for program in (first, elsewhere, cleared):
        controller.send_cmd("draw_runs", program)
        controller.on_draw_report(True)

    assert controller.page_commands() == [*elsewhere, *cleared]


def test_sparse_fills_do_not_erase_the_area_between_them_from_replay() -> None:
    controller, _proxy, _app = _drawing(draw_format=2)
    middle = "fill 20,20,10,10,255"
    edges = ["fill 10,20,10,10,0", "fill 30,20,10,10,0"]
    controller.send_cmd("draw_runs", [middle])
    controller.on_draw_report(True)
    controller.send_cmd("draw_runs", edges)
    controller.on_draw_report(True)
    assert controller.page_commands() == [middle, *edges]


def test_camera_replay_keeps_the_latest_colours_and_their_order() -> None:
    controller, _proxy, app = _drawing(draw_format=2)
    background = "fill 0,52,480,268,12000"
    first = "fill 40,60,20,20,65535"
    latest = "fill 40,60,20,20,2016"
    controller.draw_stream_frame([background, first])
    controller.on_draw_report(True)
    controller.send_cmd("send_command", 'tHeader.txt="Updated"')
    controller.draw_stream_frame([latest], full=False)

    assert controller.page_commands() == [background, first, 'tHeader.txt="Updated"']
    controller.on_draw_report(True)

    assert app.previewed[-1] == ("draw_runs", [latest])
    assert controller.page_commands() == [background, 'tHeader.txt="Updated"', latest]
    assert controller.picture_commands(0, 52, 480, 268) == [background, latest]


def test_an_empty_stream_frame_is_not_published() -> None:
    """A still scene sends nothing, and a viewer has nothing to repaint."""
    controller, _proxy, app = _drawing()

    controller.draw_stream_frame([])

    assert app.previewed == []
    assert not controller.drawing


def test_a_short_draw_is_a_single_slice() -> None:
    controller, proxy, _app = _drawing()

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert _sent(proxy) == [["fill 20,40,120,120,4226"]]


def test_a_panel_that_reports_the_packed_format_is_sent_base_36_runs() -> None:
    """Format 2 decodes ``x,y,w,h,colour``, so that is what the panel gets."""
    controller, proxy, _app = _drawing(draw_format=2)

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert proxy.programs == [pack_run("fill 20,40,120,120,4226")]


def test_a_panel_that_reports_no_format_is_sent_display_instructions() -> None:
    """Firmware older than the packing refuses a run it cannot decode.

    Sending it the base-36 form painted nothing at all - the panel counted every
    run as rejected and reported ``ok: false`` - so silence means the display
    instructions themselves.
    """
    controller, proxy, _app = _drawing()

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert proxy.programs == ["fill 20,40,120,120,4226"]


def test_a_panel_without_the_acknowledged_draw_warns_once() -> None:
    """A format-1 firmware streams at the pacer's pace and can drop fills.

    That is invisible in the draw's own report - every run was handed to the
    queue - so the hub says it once instead of leaving thin gaps and stray strips
    in the picture unexplained.
    """
    controller, _proxy, app = _drawing()

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])
    controller.send_cmd("draw_runs", ["fill 20,60,120,120,4226"])

    warnings = [message for message, _ in app.logged if "draw_format 1" in message]
    assert len(warnings) == 1


def test_a_panel_with_the_acknowledged_draw_is_not_warned_about() -> None:
    controller, _proxy, app = _drawing(draw_format=2)

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert not [message for message, _ in app.logged if "draw_format 1" in message]


def test_a_panel_without_the_acknowledged_draw_gets_short_slices() -> None:
    """Its slices are cut by count, so the display catches up before the next one.

    A format-1 firmware streams a slice at the pacer's fixed pace whatever the
    display needs, and its receive buffer holds about 40 instructions: a full
    8 000-character slice overruns it and runs are lost.
    """
    controller, proxy, _app = _drawing()
    runs = _runs(400)

    controller.send_cmd("draw_runs", runs)
    while controller._draw_slices:
        controller.on_draw_report(True)

    assert len(proxy.programs) == 400 // LEGACY_SLICE_RUNS + 1
    assert [run for part in _sent(proxy) for run in part] == runs


def test_a_panel_with_the_acknowledged_draw_gets_full_slices() -> None:
    """It paces itself with a window of fills, so only the length has to fit."""
    controller, proxy, _app = _drawing(draw_format=2)
    runs = _runs(400)

    controller.send_cmd("draw_runs", runs)

    assert len(proxy.programs) == 1
    assert len(proxy.programs[0]) <= DRAW_SLICE_CHARS


def test_a_page_switch_cancels_the_draw_in_flight() -> None:
    """The page owns the display: the rest of the image must not follow it."""
    controller, _proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))
    assert controller._draw_slices

    controller.send_cmd("goto_page", "6")

    assert controller._draw_slices == []
    assert controller._draw_runs == []
    assert controller._draw_timer is None


# ── a picture the panel may not have ─────────────────────────────────────────


def test_a_draw_is_refused_during_a_tft_install() -> None:
    """The panel took an upload: a program written into it would corrupt the transfer."""
    controller, proxy, app = _drawing(draw_format=2)
    app.controller["update"] = types.SimpleNamespace(tft_install_active=True)

    assert not controller.draw_stream_frame(_runs(12))
    assert not controller.drawing, "a refused pass must not hold the draw slot"
    assert not proxy.programs, "nothing reached the panel"

    app.controller["update"].tft_install_active = False
    assert controller.draw_stream_frame(_runs(12))
    assert proxy.programs, "and the next one does"


def test_an_overlay_reports_the_rectangle_it_painted() -> None:
    """Whoever owns that area has to paint it whole again (``app.paint_rect``)."""
    controller, _proxy, app = _drawing(draw_format=2)
    painted: list[Rect] = []
    app.paint_rect = painted.append
    rect = Rect(10, 20, 40, 30)

    controller.draw_overlay(["fill 10,20,40,30,4660"], rect=rect)

    assert painted == [rect]


def test_an_overlay_the_display_refused_reports_no_rectangle() -> None:
    controller, _proxy, app = _drawing(draw_format=2)
    painted: list[tuple[int, int, int, int]] = []
    app.paint_rect = painted.append
    app.controller["update"] = types.SimpleNamespace(tft_install_active=True)

    controller.draw_overlay(["fill 10,20,40,30,4660"], rect=Rect(10, 20, 40, 30))

    assert painted == [], "a pass that never painted may not claim the rectangle"


def test_a_delta_paints_prune_what_they_cover() -> None:
    """A pass repaints what its first fill covers, whether or not it is a whole one.

    A delta planned against a picture that a partial paint covered would keep both
    rectangles for ever, and every later viewer would replay both.
    """
    controller, _proxy, _app = _drawing(draw_format=2)
    background = "fill 0,52,480,268,12000"
    stale = "fill 40,60,20,20,65535"
    controller.draw_stream_frame([background, stale])
    controller.on_draw_report(True)

    covering = "fill 40,60,40,40,2016"
    controller.draw_stream_frame([covering], full=False)
    controller.on_draw_report(True)

    assert controller.page_commands() == [background, covering]


def test_the_picture_does_not_grow_for_the_length_of_a_stream() -> None:
    """A camera page never repaints its rectangle whole, so the replay must be bounded.

    Every distinct fill rectangle a moving scene produces would otherwise stay in
    the replay for the length of the stream, and a late viewer is sent all of it in
    one message. When the oldest fills go, the replay says so - and one whole paint
    of the area makes it describable again.
    """
    controller, _proxy, _app = _drawing(draw_format=2)
    area = (0, 0, 64, 48)
    whole = f"fill 0,0,{area[2]},{area[3]},1024"
    controller.draw_stream_frame([whole])
    controller.on_draw_report(True)
    assert controller.picture_commands(*area) == [whole]

    sent = 0
    while controller.picture_commands(*area) and sent < 20_000:
        # A delta of many cells, as a moving scene produces: one pass, not one
        # fill per pass, or the test would spend its time in the replay's scans.
        controller.draw_stream_frame(
            [f"fill {n % 40},{n // 40},8,8,2048" for n in range(sent, sent + 200)],
            full=False,
        )
        controller.on_draw_report(True)
        sent += 200

    assert sent < 20_000, "the replay dropped its oldest fills instead of growing for ever"
    assert controller.picture_commands(*area) == [], "so it no longer describes the picture"
    assert whole not in controller.page_commands(), "the oldest fills were the ones dropped"

    controller.draw_stream_frame([whole])
    controller.on_draw_report(True)

    assert controller.picture_commands(*area) == [whole], "one whole paint describes it again"


def test_a_page_fill_tells_the_owner_of_that_rectangle() -> None:
    """A fill from anywhere else wipes what a camera stream holds there.

    ``draw_overlay`` and ``draw_runs`` already tell ``app.paint_rect``; a page's own
    ``fill`` reaches the replay through the same recorder, so it has to say so too -
    otherwise every delta after it keeps the ghost of the wiped area.
    """
    controller, _proxy, app = _drawing(draw_format=2)

    controller.send_cmd("send_command", "fill 10,10,40,40,65535")

    assert app.painted == [Rect(10, 10, 40, 40)]


def test_a_draw_program_does_not_ask_the_stream_to_repaint_itself() -> None:
    """The stream's own fills must not read as damage to its own rectangle."""
    controller, _proxy, app = _drawing(draw_format=2)

    controller.draw_stream_frame(["fill 10,10,40,40,65535"], full=True)
    controller.on_draw_report(True)

    assert controller.page_commands() == ["fill 10,10,40,40,65535"]
    assert app.painted == [], "its own program is not another painter"


def test_an_excluded_rectangle_leaves_the_other_commands_alone() -> None:
    """A viewer seeds a page's widgets without the picture it re-runs separately."""
    controller, _proxy, _app = _drawing(draw_format=2)
    controller.draw_stream_frame(["fill 10,20,40,40,65535", "fill 200,10,40,40,255"])
    controller.on_draw_report(True)
    controller.send_cmd("send_command", 'tHeader.txt="Camera"')

    commands = controller.page_commands(exclude=Rect(10, 20, 40, 40))

    assert commands == ["fill 200,10,40,40,255", 'tHeader.txt="Camera"']


def test_a_pass_the_panel_took_whole_is_not_a_failure() -> None:
    """Nothing to repaint: the counter stays where it was for a clean pass."""
    controller, _proxy, _app = _drawing()

    controller.send_cmd("draw_runs", _runs(1200))
    while controller._draw_slices:
        controller.on_draw_report(True)

    assert controller.draw_failures == 0


def test_a_slice_the_panel_never_took_is_a_failure() -> None:
    """The panel keeps the runs it got, so part of the picture is missing."""
    controller, proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))

    proxy.connected = False
    controller.on_draw_report(True)

    assert controller.draw_failures == 1


def test_a_slice_the_panel_refused_twice_is_a_failure() -> None:
    """The retry is the last chance; after it the picture has gaps."""
    controller, _proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))

    controller.on_draw_report(False)  # re-sent once
    assert controller.draw_failures == 0
    controller.on_draw_report(False)  # dropped

    assert controller.draw_failures == 1


def test_a_pass_cut_short_by_another_pass_is_a_failure() -> None:
    """The firmware restarts its own programme, so the rest of the first is lost."""
    controller, _proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert controller.draw_failures == 1


def test_a_late_report_after_a_page_switch_is_ignored() -> None:
    """The firmware cancels its own stream too; a report can still be in flight."""
    controller, proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))
    sent = len(proxy.programs)

    controller.send_cmd("goto_page", "6")
    controller.on_draw_report(True)

    assert len(proxy.programs) == sent
    assert controller._draw_slices == []


def test_a_late_failure_after_the_last_slice_does_not_repaint() -> None:
    """A finished pass is forgotten, so a stale report cannot start it again."""
    controller, proxy, _app = _drawing()
    controller.send_cmd("draw_runs", _runs(10))
    controller.on_draw_report(True)
    sent = len(proxy.programs)

    controller.on_draw_report(False)

    assert len(proxy.programs) == sent

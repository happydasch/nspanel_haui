"""The ESPHome controller's record of what the shown page was sent (``page_commands``).

A Live viewer that attaches late replays it on a freshly loaded page, so it must
end on the screen the panel shows, and stay small while a page is shown for days.
"""

from __future__ import annotations

from typing import Any

from test_connection import DummyApp

from custom_components.nspanel_haui.haui.controller.esphome import HAUIESPHomeController
from custom_components.nspanel_haui.haui.utils.draw_wire import (
    DRAW_SLICE_CHARS,
    unpack_run,
)


class _App(DummyApp):
    def __init__(self) -> None:
        super().__init__()
        self.previewed: list[tuple[str, Any]] = []

    def publish_preview_output(self, command: str, value: Any) -> None:
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
    """Records the draw programs it is handed; ``simulated`` skips the fence."""

    def __init__(self, *, simulated: bool = False) -> None:
        super().__init__()
        self.simulated = simulated
        self.programs: list[str] = []

    def publish(self, name: str, value: Any = "") -> bool:
        if name == "draw_runs":
            self.programs.append(str(value))
        return super().publish(name, value)


def _drawing(*, simulated: bool = False) -> tuple[HAUIESPHomeController, _DrawingProxy, _App]:
    proxy = _DrawingProxy(simulated=simulated)
    app = _App()
    controller = HAUIESPHomeController(app, {"device_name": "kitchen"}, proxy, lambda e: None)
    return controller, proxy, app


def _runs(count: int) -> list[str]:
    """Distinct spans, as a real image produces: the replay keeps one per target."""
    return [f"fill {index % 480},{index // 480},8,8,65535" for index in range(count)]


def _sent(proxy: _DrawingProxy) -> list[list[str]]:
    """What the panel actually receives, decoded back to display commands."""
    return [[unpack_run(run) for run in program.split(";")] for program in proxy.programs]


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


def test_a_simulated_panel_is_sent_every_slice_without_a_fence() -> None:
    """The Simulated preview paints as it records, so nothing has to wait."""
    controller, proxy, _app = _drawing(simulated=True)
    runs = _runs(1200)

    controller.send_cmd("draw_runs", runs)

    assert len(proxy.programs) > 1
    assert [run for slice_ in _sent(proxy) for run in slice_] == runs
    assert controller._draw_timer is None


def test_a_slice_that_never_reports_is_followed_by_the_next_one() -> None:
    """A report lost to a busy panel must not wedge the rest of the image."""
    controller, proxy, app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))
    assert len(proxy.programs) == 1
    ((callback, _kwargs),) = app.timers.values()

    callback()

    assert len(proxy.programs) == 2
    assert any("no report for a slice" in message for message, _ in app.logged)


def test_a_refused_slice_drops_the_rest_of_the_image() -> None:
    """Painting the rest over a half-drawn picture is worse than stopping."""
    controller, proxy, app = _drawing()
    controller.send_cmd("draw_runs", _runs(1200))

    controller.on_draw_report(False)

    assert len(proxy.programs) == 1
    assert controller._draw_slices == []
    assert app.timers == {}
    assert any("refused a slice" in message for message, _ in app.logged)


def test_the_page_replay_keeps_the_whole_pass_not_just_the_first_slice() -> None:
    """A viewer attaching late must see the finished picture, not a band of it."""
    controller, _proxy, _app = _drawing()
    runs = _runs(1200)

    controller.send_cmd("draw_runs", runs)

    assert controller.page_commands() == runs


def test_the_preview_hears_about_a_pass_once_and_gets_every_run() -> None:
    """The previews slice the pass themselves, so they need all of it, once."""
    controller, _proxy, app = _drawing()
    runs = _runs(1200)

    controller.send_cmd("draw_runs", runs)

    assert app.previewed == [("draw_runs", runs)]


def test_a_short_draw_is_a_single_slice() -> None:
    controller, proxy, _app = _drawing()

    controller.send_cmd("draw_runs", ["fill 20,40,120,120,4226"])

    assert _sent(proxy) == [["fill 20,40,120,120,4226"]]

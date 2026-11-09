"""The ESPHome controller's record of what the shown page was sent (``page_commands``).

A Live viewer that attaches late replays it on a freshly loaded page, so it must
end on the screen the panel shows, and stay small while a page is shown for days.
"""

from __future__ import annotations

from typing import Any

from test_connection import DummyApp

from custom_components.nspanel_haui.haui.controller.esphome import HAUIESPHomeController


class _App(DummyApp):
    def publish_preview_output(self, command: str, value: Any) -> None:
        pass


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

"""A TFT install owns the display: no display command reaches it meanwhile.

Field evidence (v0.5.4 on a panel): the install cleared the upload, then the page-ack
timeout re-sent ``goto_page`` and re-rendered the whole panel into the transfer, and
the panel failed the upload three times. The hub holds every command until the
install ends; the panel reboots afterwards and is drawn again on reconnect.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support.page_app import PageApp  # noqa: E402

from custom_components.nspanel_haui.haui.abstract.component import Component  # noqa: E402
from custom_components.nspanel_haui.haui.abstract.haui_base import HAUIBase  # noqa: E402


class FakeUpdateController:
    """Only what the guard reads: whether a TFT upload is in flight."""

    def __init__(self, installing: bool = False) -> None:
        self.installing = installing

    @property
    def tft_install_active(self) -> bool:
        return self.installing


def _make(installing: bool) -> tuple[PageApp, FakeUpdateController, HAUIBase]:
    app = PageApp({})
    update = FakeUpdateController(installing)
    app.controller["update"] = update
    return app, update, HAUIBase(app, {})  # type: ignore[arg-type]


def test_no_display_command_reaches_the_panel_during_an_install() -> None:
    app, _update, base = _make(installing=True)

    base.send_cmd("page grid")
    base.send_cmds(['t0.txt="a"', 't1.txt="b"'])
    base.set_component_text(_component("t2"), "c")

    assert app.cmds == []


def test_commands_flow_again_the_moment_the_install_ends() -> None:
    app, update, base = _make(installing=True)
    base.send_cmd("page grid")
    assert app.cmds == []

    update.installing = False

    base.send_cmd("page grid")
    base.send_cmds(['t0.txt="a"'])
    assert app.cmds == ["page grid", 't0.txt="a"']


def test_a_recorded_page_still_collects_its_commands_during_an_install() -> None:
    """Recording is what a page would draw; the flush is what the guard holds."""
    app, _update, base = _make(installing=True)

    base.start_rec_cmd()
    base.send_cmd("page grid")
    recorded = base.stop_rec_cmd(send_commands=True)

    assert recorded == ["page grid"]
    assert app.cmds == []


def test_without_an_update_controller_the_display_is_never_held() -> None:
    """Early start-up and the virtual panel have no update controller."""
    app = PageApp({})
    base = HAUIBase(app, {})  # type: ignore[arg-type]

    base.send_cmd("page grid")

    assert app.cmds == ["page grid"]


def _component(name: str) -> Component:
    """A component that only carries its Nextion name, which is all the setter uses."""
    return Component(id=0, name=name)

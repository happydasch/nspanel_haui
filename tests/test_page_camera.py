"""The camera page: which camera it shows, where the picture goes, and when.

The page hands its picture area to the hub's stream and keeps a placeholder up
until the first frame arrives; the frames themselves are the stream's (see
``tests/test_camera_stream.py``). Assertions are on the display commands and on
what the page asks the hub for.
"""

import json
from pathlib import Path

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.page.camera import (
    PICTURE_RECT,
    QUALITY_CHOICES,
    CameraPage,
    picture_rect,
    quality_profile,
)
from custom_components.nspanel_haui.haui.utils.image_program import Rect
from custom_components.nspanel_haui.haui.utils.image_stream import DEFAULT_QUALITY, QUALITY

CAMERA = "camera.door"
LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"


def _show(*, portrait: bool = False, item: dict | None = None, **panel_cfg):
    app = PageApp({CAMERA: Entity("streaming", {"friendly_name": "Front Door"})}, portrait=portrait)
    cfg = {"type": "camera", "item": item if item is not None else {"item": CAMERA}}
    cfg.update(panel_cfg)
    panel = HAUIPanel(app, cfg)
    page = CameraPage(app, {"page_id": 20})
    page.set_panel(panel)
    return app, page


# what the page hands to the stream


def test_page_streams_the_selected_camera_into_its_picture_area():
    app, _page = _show()

    assert len(app.camera_streams) == 1
    started = app.camera_streams[0]
    assert started["entity_id"] == CAMERA
    assert started["rect"] == PICTURE_RECT["landscape"]
    assert started["quality"] == QUALITY[DEFAULT_QUALITY], "the panel's default quality"


def test_portrait_panel_paints_the_portrait_picture_area():
    app, page = _show(portrait=True)

    assert app.camera_streams[0]["rect"] == PICTURE_RECT["portrait"]
    assert page.picture_rect == PICTURE_RECT["portrait"]
    # the picture is the info page's text area, inside the display
    rect = app.camera_streams[0]["rect"]
    assert rect.x + rect.w <= 320
    assert rect.y + rect.h <= 480


def test_quality_option_reaches_the_stream():
    """The panel's quality is what decides the density of the picture."""
    app, _page = _show(quality="low")

    assert app.camera_streams[0]["quality"] == QUALITY["low"]


def test_every_quality_the_editor_offers_has_a_profile():
    """A choice without a profile is a panel that cannot draw its picture."""
    offered = [value for value, _label in QUALITY_CHOICES]

    assert DEFAULT_QUALITY in offered, "the default is one of the choices"
    for value in offered:
        assert value in QUALITY, f"{value!r} is offered but has no profile"
    assert [profile.cell for profile in QUALITY.values()], "each profile sets a density"
    # Finer means smaller cells: the setting a user picks says so.
    assert QUALITY["high"].cell < QUALITY[DEFAULT_QUALITY].cell < QUALITY["low"].cell


def test_an_unknown_quality_falls_back_and_says_so(monkeypatch):
    """Only a hand-edited config can hold one; the page still has to draw."""
    logged: list[tuple[str, str]] = []
    monkeypatch.setattr(
        CameraPage,
        "log",
        lambda self, message, **kwargs: logged.append((message, kwargs.get("level", ""))),
    )

    app, _page = _show(quality="ultra")

    assert app.camera_streams[0]["quality"] == QUALITY[DEFAULT_QUALITY]
    assert any(
        "unknown picture quality" in message and level == "WARNING" for message, level in logged
    ), "a value the editor does not offer is not silently swallowed"


def test_a_refresh_neither_paints_the_picture_nor_starts_a_stream():
    """A refresh repaints widgets, not the page: the picture is still on the display.

    Painting it again would flash the whole area for a picture the panel already
    shows, and the page would repaint itself whenever anything refreshes it - a
    notification, a snapshot restore, a drain recovery. The stream is the panel's,
    not the render's: it was asked for when the panel started.
    """
    app, page = _show()
    app.camera_frame = ["fill 0,0,480,268,1024"]
    page.hide_placeholder()  # the first frame arrived
    app.camera_paints.clear()
    app.cmds.clear()

    page.refresh_panel()

    assert app.camera_paints == [], "a refresh draws no picture"
    assert not [cmd for cmd in app.cmds if "tText" in cmd], (
        "and does not put the placeholder back over the picture"
    )
    assert len(app.camera_streams) == 1, "the stream was started by the panel"


def test_the_picture_is_painted_once_even_across_many_renders():
    """Two refreshes in a row must not paint the frame twice either."""
    app, page = _show()
    app.camera_frame = ["fill 0,0,480,268,1024"]
    page.set_panel(page.panel)  # the first render: the frame is painted
    app.camera_paints.clear()

    page.refresh_panel()
    page.refresh_panel()

    assert app.camera_paints == []


# title and placeholder


def test_header_shows_the_camera_name():
    app, _page = _show()

    assert 'tTitle.txt="Front Door"' in app.cmds


def test_header_keeps_the_panel_title_when_it_has_one():
    app, _page = _show(title="Doorbell")

    assert 'tTitle.txt="Doorbell"' in app.cmds


def test_placeholder_says_the_picture_is_not_there_yet():
    app, _page = _show()

    assert "vis tText,1" in app.cmds
    assert 'tText.txt="Waiting for the camera"' in app.cmds


def test_a_render_with_a_frame_paints_the_picture_instead_of_the_placeholder():
    """The render is what a preview and a card replay, so the picture is part of it."""
    app = PageApp({CAMERA: Entity("streaming", {"friendly_name": "Front Door"})})
    app.camera_frame = ["fill 0,0,480,268,1024"]
    panel = HAUIPanel(app, {"type": "camera", "item": {"item": CAMERA}})
    page = CameraPage(app, {"page_id": 20})

    page.set_panel(panel)

    assert app.camera_paints == [["fill 0,0,480,268,1024"]]
    assert "vis tText,0" in app.cmds, "the placeholder is hidden under the picture"
    assert 'tText.txt="Waiting for the camera"' not in app.cmds


def test_a_page_drawn_again_repaints_its_picture_whole():
    """A page that is drawn again shows its own background where the picture was.

    The frame the stream painted last may be minutes old - the deltas since are
    planned against a newer picture - so the page asks the stream for a whole
    paint instead of replaying it.
    """
    app, page = _show()
    app.camera_frame = ["fill 0,0,480,268,1024"]
    page.hide_placeholder()  # a picture is up
    app.camera_paints.clear()
    app.cmds.clear()

    page.set_panel(page.panel)

    assert app.camera_paints == [["fill 0,0,480,268,1024"]]
    assert "vis tText,1" not in app.cmds, "and never puts the placeholder back over it"


def test_page_without_a_camera_says_so_and_streams_nothing():
    app, _page = _show(item={})

    assert app.camera_streams == []
    assert 'tText.txt="No camera selected"' in app.cmds


def test_the_page_names_the_camera_a_card_reads():
    """A card tells whose picture the device holds by the camera the page started for."""
    _app, page = _show()

    assert page.entity_id == CAMERA

    _app, page = _show(item={})

    assert page.entity_id == "", "a panel with no camera holds nobody's picture"


def test_the_picture_area_and_quality_have_one_definition():
    """The page and a card render plan the same area at the same quality."""
    assert picture_rect(False) == PICTURE_RECT["landscape"]
    assert picture_rect(True) == PICTURE_RECT["portrait"]
    assert quality_profile("low") is QUALITY["low"]
    assert quality_profile(None) is QUALITY[DEFAULT_QUALITY], "nothing stored is the default"
    assert quality_profile("ultra") is QUALITY[DEFAULT_QUALITY], "and so is a value nobody offers"


def test_first_frame_takes_the_placeholder_away():
    app, page = _show()
    app.cmds.clear()

    page.hide_placeholder()

    assert app.cmds == ["vis tText,0"]


# lifecycle


def test_leaving_the_page_stops_the_stream():
    app, page = _show()

    page.set_panel(None)

    assert app.camera_stream_stops == 1


def test_page_descriptor_claims_the_info_page():
    assert CameraPage.DESCRIPTOR.page_name == "info"
    assert CameraPage.DESCRIPTOR.page_id == 20
    assert CameraPage.DESCRIPTOR.type_key == "camera"


def test_the_picture_rectangle_is_the_text_area_both_hmis_compile():
    """The picture goes where the info page's big text area is, per display model."""
    app, page = _show()

    for orientation in ("landscape", "portrait"):
        app.device.is_portrait = orientation == "portrait"
        layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
        info = next(p for p in layout["pages"].values() if p["name"] == "info")
        text = next(c["attrs"] for c in info["components"] if c["name"] == "tText")

        assert page.picture_rect == Rect(text["x"], text["y"], text["w"], text["h"]), orientation
        assert PICTURE_RECT[orientation] == page.picture_rect

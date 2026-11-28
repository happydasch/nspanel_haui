"""The camera page: which camera it shows, where the picture goes, and when.

The page hands its picture area to the hub's stream and keeps a placeholder up
until the first frame arrives; the frames themselves are the stream's (see
``tests/test_camera_stream.py``). Assertions are on the display commands and on
what the page asks the hub for.
"""

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.page.camera import PICTURE_RECT, CameraPage
from custom_components.nspanel_haui.haui.utils.image_program import Rect

CAMERA = "camera.door"


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
    assert started["fps"] == 2.0


def test_portrait_panel_paints_the_portrait_picture_area():
    app, page = _show(portrait=True)

    assert app.camera_streams[0]["rect"] == PICTURE_RECT["portrait"]
    assert page.picture_rect == PICTURE_RECT["portrait"]
    # the rectangle is the info page's text area, inside the display
    rect = app.camera_streams[0]["rect"]
    assert rect.x + rect.w <= 320
    assert rect.y + rect.h <= 480


def test_fps_option_reaches_the_stream():
    app, _page = _show(fps=5.5)

    assert app.camera_streams[0]["fps"] == 5.5


def test_render_restarts_the_stream_so_the_picture_starts_from_nothing():
    app, page = _show()

    page.refresh_panel()

    # A second start: the planner of the first one holds a picture the page
    # background has just painted over.
    assert len(app.camera_streams) == 2


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


def test_page_without_a_camera_says_so_and_streams_nothing():
    app, _page = _show(item={})

    assert app.camera_streams == []
    assert 'tText.txt="No camera selected"' in app.cmds


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


def test_picture_area_is_the_info_page_text_widget():
    assert CameraPage.COMPONENTS.picture_area.name == "tText"
    # the stream paints over the widget, so the rect must be the widget's own
    landscape = PICTURE_RECT["landscape"]
    portrait = PICTURE_RECT["portrait"]
    assert (landscape.x, landscape.y, landscape.w, landscape.h) == (12, 70, 426, 170)
    assert (portrait.x, portrait.y, portrait.w, portrait.h) == (12, 55, 296, 335)
    assert isinstance(landscape, Rect)

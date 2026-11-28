"""The camera page: one camera's picture kept current on the panel.

The picture is not part of the render. A Nextion has no image buffer and the page
API can only replay commands, so the frame itself is a program of ``fill``
rectangles that the hub's stream draws into the page's picture area after the page
is up (``hub/camera_stream.py``). The page therefore owns three things: the
picture area it hands over, the title and the placeholder that says the picture is
not there yet.

Both sizes carry the same widgets: the info page's text area (``tText``) is the
picture, and its six mode buttons stay hidden until a page has a use for them.
"""

from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..utils.image_program import Rect

#: Where the picture area (``tText``) sits, per orientation.  Read here instead of
#: from the widget: the rect must be known before anything is drawn, and the pixel
#: values are the HMI's (``scripts/hmi_layout`` keeps them in step with the TFT).
PICTURE_RECT: dict[str, Rect] = {
    "landscape": Rect(12, 70, 426, 170),
    "portrait": Rect(12, 55, 296, 335),
}


class CameraPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="camera",
        page_name="info",
        page_id=20,
        label=_("Camera"),
        description=_("One camera's live picture, refreshed several times a second."),
        category="entities",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="camera",
                required=True,
                description=_("Camera whose picture the page shows."),
                section=_("Camera"),
            ),
            PageOption(
                key="fps",
                kind="float",
                default=2.0,
                label=_("Frames per second"),
                description=_("Snapshots per second; more helps a moving camera."),
                section=_("Camera"),
                min=0.1,
                max=10.0,
            ),
        ],
        icon="mdi:video-outline",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        # the info page's text area, handed to the camera stream as its rectangle
        picture_area=Component(8, "tText"),
        mode_1=Component(9, "btMode1"),
        mode_2=Component(10, "btMode2"),
        mode_3=Component(11, "btMode3"),
        mode_4=Component(12, "btMode4"),
        mode_5=Component(13, "btMode5"),
        mode_6=Component(14, "btMode6"),
    )

    # panel

    def prepare(self) -> None:
        self._entity_id = ""
        self._title = ""

    def start_panel(self, panel: HAUIPanel) -> None:
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )
        item = self._resolve_panel_item(panel)
        self._entity_id = item.get_item_id() if item is not None else ""
        self._title = panel.get_title(item.get_name() if item is not None else "")
        self.set_title(self._title)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_title(self._title)
        # The placeholder is shown until the first frame arrives: a page that is
        # still empty says so instead of looking like a broken camera.
        self.show_component(self.COMPONENTS.picture_area)
        # ``component_text`` is the role the theme code gives this widget, so the
        # placeholder matches the body text of every other solid page.
        self.set_component_text_color(
            self.COMPONENTS.picture_area, self.get_color("component_text")
        )
        self.set_component_text(
            self.COMPONENTS.picture_area,
            self.translate("Waiting for the camera")
            if self._entity_id
            else self.translate("No camera selected"),
        )
        # Every render repaints the page background over the last frame, and the
        # stream's planner holds what it painted: only a fresh stream - which
        # starts from an empty model and so paints the whole rectangle - brings
        # the picture back without leaving the rest of it blank.
        self._start_stream(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        self.app.stop_camera_page_stream()

    # stream

    def _start_stream(self, panel: HAUIPanel) -> None:
        """Hand this panel's picture area to the hub's camera stream."""
        if not self._entity_id:
            self.log("camera page has no camera entity", level="WARNING")
            return
        self.app.start_camera_page_stream(
            entity_id=self._entity_id,
            rect=self.picture_rect,
            fps=self.option(panel, "fps"),
            on_first_frame=self.hide_placeholder,
        )

    @property
    def picture_rect(self) -> Rect:
        """The rectangle of the picture area on this device's display."""
        return PICTURE_RECT["portrait" if self.app.device.is_portrait else "landscape"]

    def hide_placeholder(self) -> None:
        """Take the placeholder away once the stream has drawn its first frame."""
        with self.rec_cmd:
            self.hide_component(self.COMPONENTS.picture_area)

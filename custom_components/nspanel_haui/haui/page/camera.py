"""The camera page: one camera's picture kept current on the panel.

The picture is not part of the render's widget commands. A Nextion has no image
buffer and the page API can only replay commands, so the frame itself is a program
of ``fill`` rectangles that the hub's stream draws into the page's picture area
after the page is up (``hub/camera_stream.py``). The page therefore owns the
picture area it hands over, the title, the quality the picture is drawn at, and
the placeholder that says the picture is not there yet.

The area is the info page's big text widget, the way the media page's cover art
goes where its icon widget is: the coordinates are the ones that widget was
compiled at, so the picture lands in the page's text area and the header, the
mode buttons and the page's own margins stay as they are. Frames are cropped to
fill that area instead of letterboxed, because a camera's 16:9 image in a
portrait panel's tall area would otherwise spend most of it on empty bands.
"""

from __future__ import annotations

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..utils.image_program import Rect
from ..utils.image_stream import DEFAULT_QUALITY, QUALITY, PictureQuality

#: Where the picture goes: the info page's big text area (``tText``), in the
#: display pixels of each HMI. The page hands this rectangle to the hub instead of
#: asking the display for it - a Nextion reads back a widget's ``.txt`` and
#: ``.val``, never its position or size - so the values are the ones its layout was
#: compiled from, and ``tests/test_page_camera.py`` checks them against both
#: generated layouts.
PICTURE_RECT: dict[str, Rect] = {
    "landscape": Rect(12, 70, 426, 170),
    "portrait": Rect(12, 55, 296, 335),
}

#: What the panel editor offers, in the order it lists it. The values are the
#: profiles in ``image_stream.QUALITY``; the labels say what they buy, because
#: "high" on its own does not tell a user that the picture is a third as grainy
#: and arrives half as often.
QUALITY_CHOICES: list[tuple[str, str]] = [
    ("high", _("High (finest picture, slower)")),
    ("mid", _("Medium")),
    ("low", _("Low (coarsest picture, fastest)")),
]


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
                key="quality",
                kind="select",
                default=DEFAULT_QUALITY,
                label=_("Picture quality"),
                description=_("How fine the picture is, and how often a frame arrives."),
                section=_("Camera"),
                choices=QUALITY_CHOICES,
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
        #: Whether this page has put its picture on the display. A refresh
        #: repaints widgets, not the page background, so once the picture is up it
        #: stays up - drawing it again would flash the whole area for no gain.
        self._picture_shown = False

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
        # The stream belongs to the panel, not to a render: it is asked for once,
        # here, when the page that will show it is up. A start that asks for the
        # picture already running is a no-op, so a panel that is set again keeps
        # the stream - and its planner, which is the model of what the display
        # shows.
        self._start_stream(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_title(self._title)
        if not self._picture_shown:
            # This page has just been drawn, so the picture area shows whatever
            # the page's own widgets put there. The picture is the stream's, and
            # the stream paints the rectangle whole to put it back: replaying the
            # frame the page remembers would be a second paint path - stale, and
            # cut short by the pass already in flight.
            if self.app.camera_page_frame():
                self.hide_placeholder()
            else:
                self.show_placeholder()
            self.app.repaint_camera_page_frame()

    def show_placeholder(self) -> None:
        """Say that the picture is not there yet, over an empty area."""
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
            quality=self.quality(panel),
            on_first_frame=self.hide_placeholder,
        )

    def quality(self, panel: HAUIPanel) -> PictureQuality:
        """The picture quality this panel is set to, with its density and budgets.

        A value the editor does not offer can only come from a hand-edited
        config; the page still has to draw something, so it says so and falls
        back to the default.
        """
        value = str(self.option(panel, "quality"))
        quality = QUALITY.get(value)
        if quality is None:
            self.log(
                f"camera page: unknown picture quality {value!r}, using {DEFAULT_QUALITY}",
                level="WARNING",
            )
            quality = QUALITY[DEFAULT_QUALITY]
        return quality

    @property
    def picture_rect(self) -> Rect:
        """The rectangle of the picture area on this device's display."""
        return PICTURE_RECT["portrait" if self.app.device.is_portrait else "landscape"]

    def hide_placeholder(self) -> None:
        """Take the placeholder away: the picture is on the display now."""
        self._picture_shown = True
        with self.rec_cmd:
            self.hide_component(self.COMPONENTS.picture_area)

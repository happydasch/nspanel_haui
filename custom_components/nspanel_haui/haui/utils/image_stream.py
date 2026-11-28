"""Turn a sequence of pictures into delta draw programs, for a camera stream.

The display has no framebuffer, no refresh control and no delta instruction: every
update is ``fill`` rectangles written straight to the screen (see
``docs/develop/nextion.md``). A stream therefore has to be built on the hub, and
the only question that decides whether it works is *what counts as changed*.

Comparing a frame with the previous frame does not work on camera data. Sensor
noise and a flickering light change almost every cell of the picture every frame -
measured on a textured scene at grid cell 8 px, a 2 % brightness flicker alone
repainted 11 % of the cells, and that is 293 runs per frame, i.e. a picture every
second, which is a slideshow and not a stream.

What works is comparing a frame with **a model of what the panel is showing**: the
hub keeps the cell colours it last painted and repaints a cell only when its real
colour has moved away from the painted one by more than a dead band (``DEAD_BAND``).
A cell whose colour jitters inside the band costs nothing however much it jitters,
so noise and flicker disappear (12 runs per frame instead of 293 on the same
sequence) while a moving subject still shows: it is only its edges that change,
because the flat interior of a walking person does not move relative to itself.

Three things follow, and they are the whole design:

* The painted model must be **the truth about the display**, so it is updated by
  what the program actually paints (a span applied to the grid), never by the
  frame. A frame that is skipped - the panel was still drawing - changes nothing.
* A program may be **empty**. An idle camera sends nothing at all rather than
  repainting what is already right; the caller checks for that before publishing.
* The dead band accumulates error, so a full repaint is forced every
  ``refresh_every`` frames, and whenever the grid resolution changes.

The rectangle is rasterised exactly as ``show_image`` does it (``fit_image``): same
letterbox, same canvas colour, so a stream and a still of the same picture agree.

Pure and synchronous, no Home Assistant: the caller fetches and decodes the frame,
this decides what to paint.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, cast

from PIL import Image

from .color import rgb565_to_rgb, rgb_to_rgb565
from .image_program import Rect, fit_image

#: Per-channel distance a cell must move beyond before it is repainted. Eight is
#: what ``image_program`` merges neighbours by; a stream needs more, because a
#: camera's noise and its flickering light sit on top of every reading and are not
#: picture. Sixteen already removes both; twenty-four leaves room for a brighter
#: room or a noisier sensor without repainting the frame, and is still a quarter of
#: a channel, so what it hides is invisible on the panel.
DEAD_BAND: Final = 24
#: Cell sizes a stream may use, in display pixels. Two is fine detail for a small
#: rectangle, twenty-four is a full-page mosaic that keeps a panning camera at a
#: frame or two a second.
MIN_CELL_PX: Final = 2
MAX_CELL_PX: Final = 24
#: The cell a stream starts at: fine enough that a person walking across a
#: full-page rectangle is clearly a person, coarse enough that a frame is a
#: handful of runs.
DEFAULT_CELL_PX: Final = 8
#: Runs one frame may cost. A frame over this is made coarser before it is sent
#: rather than dribbling out for a second, because a stream's whole point is that
#: the next frame arrives; at the display's measured ~1-3 ms per fill this is
#: 0.4-1.2 s in the worst case, and a typical frame costs a tenth of it.
DEFAULT_FRAME_RUNS: Final = 400
MIN_FRAME_RUNS: Final = 40
MAX_FRAME_RUNS: Final = 2400
#: Frames per second a stream may ask for. Two is a comfortable ceiling for this
#: display - a full-page frame is 0.2-1 s of painting - but the range is wide
#: because a small rectangle is much cheaper than a full page, and a stream drops
#: a frame the panel cannot draw instead of queueing it.
MIN_FPS: Final = 0.1
MAX_FPS: Final = 10.0
#: Frames between two full repaints. The dead band lets a slow drift through - a
#: wall that darkens one step at a time never crosses it - and a full paint costs
#: about one still image, so this is a compromise: at 3 fps a minute of streaming
#: is 180 frames, and three full paints.
REFRESH_EVERY: Final = 60
#: Frames a resolution change waits for, so a scene that hovers at the budget does
#: not flip the cell size every frame.
CELL_SETTLE_FRAMES: Final = 2


class ImageStreamError(ValueError):
    """A stream frame could not be planned."""


@dataclass(slots=True)
class _Span:
    """A rectangle of one colour, in **cell** units, grown as rows repeat it."""

    x: int
    y: int
    w: int
    h: int
    rgb565: int

    def run(self, rect: Rect, cell: int) -> str:
        """This span as the display instruction that paints it, in display pixels.

        A span counts cells because that is what the merge compares; the display
        wants pixels, so the last cell of a row or column is clipped to the
        rectangle rather than painted past its edge.
        """
        left = rect.x + self.x * cell
        top = rect.y + self.y * cell
        width = min(self.w * cell, rect.right - left)
        height = min(self.h * cell, rect.bottom - top)
        return f"fill {left},{top},{width},{height},{self.rgb565}"


class DeltaPlanner:
    """Plan the runs that bring the panel from what it shows to the newest frame.

    One planner per streamed rectangle. It is stateful on purpose: the grid it
    keeps *is* the model of the display, so the caller must send every program it
    returns and no other draw into the same rectangle - the two would disagree and
    the picture would keep a ghost of the other program.

    Attributes:
        cell: Cell size in display pixels currently used.
        runs: Runs the last program carried.
        frames: Programs returned so far, empty ones included.
        full_paints: Times a whole rectangle was repainted.
    """

    def __init__(
        self,
        rect: Rect,
        *,
        cell: int = DEFAULT_CELL_PX,
        band: int = DEAD_BAND,
        max_runs: int = DEFAULT_FRAME_RUNS,
        refresh_every: int = REFRESH_EVERY,
    ) -> None:
        """Start a stream into ``rect``.

        Args:
            rect: The rectangle to paint, in display pixels.
            cell: Starting cell size; clamped to ``MIN_CELL_PX``-``MAX_CELL_PX``.
            band: Per-channel dead band before a cell is repainted, 0-255.
            max_runs: Runs one frame may cost; a frame over it is made coarser.
            refresh_every: Frames between two full repaints; 0 disables them.

        Raises:
            ImageStreamError: When a size or a band is outside its range.
        """
        if not 0 <= band <= 255:
            raise ImageStreamError(f"dead band {band} is outside 0-255")
        if not MIN_FRAME_RUNS <= max_runs <= MAX_FRAME_RUNS:
            raise ImageStreamError(
                f"{max_runs} runs a frame is outside {MIN_FRAME_RUNS}-{MAX_FRAME_RUNS}"
            )
        if refresh_every < 0:
            raise ImageStreamError(f"refresh_every {refresh_every} is negative")
        self.rect = rect
        self.band = band
        self.max_runs = max_runs
        self.refresh_every = refresh_every
        self.cell = min(MAX_CELL_PX, max(MIN_CELL_PX, cell))
        self.runs = 0
        self.frames = 0
        self.full_paints = 0
        #: The colours the panel shows, one RGB565 per cell; ``None`` until the
        #: first frame, which is then a full paint by definition.
        self._painted: list[list[int]] | None = None
        #: Frames left before a full repaint; 0 means "the next one is full".
        self._until_refresh = 0
        #: Frames spent waiting before a resolution change is worth making.
        self._settle = 0

    @property
    def painted(self) -> bool:
        """Whether the panel is showing a frame of this stream yet."""
        return self._painted is not None

    def plan(self, image: Image.Image) -> list[str]:
        """The program that shows ``image``, and the painted model updated to it.

        Args:
            image: The decoded frame. It is letterboxed into the rectangle exactly
                as ``show_image`` would draw it.

        Returns:
            The ``fill`` instructions to send, in the order they paint (top to
            bottom), so a partial update reads as a slow scan rather than random
            blocks. An empty list means the panel already shows this frame and
            nothing should be sent.

        Raises:
            ImageStreamError: When the frame has no pixels.
        """
        if image.width < 1 or image.height < 1:
            raise ImageStreamError("the frame has no pixels")
        canvas, colour = fit_image(image, self.rect)
        # The cell size is decided *before* the program is sent, never after: a
        # frame over the budget is replanned coarser here, so the panel receives one
        # program at the resolution it can keep up with instead of a fine one
        # followed by a full repaint of the same picture.
        while True:
            grid = _grid(canvas, self.rect, self.cell)
            resized = self._painted is not None and _shape(self._painted) != _shape(grid)
            refresh_due = self.refresh_every > 0 and self._until_refresh <= 0
            full = self._painted is None or resized or refresh_due
            painted = self._painted
            if full or painted is None:
                clearing = _canvas_colour(grid, colour)
                spans = [
                    _Span(0, 0, len(grid[0]), len(grid), clearing),
                    *_without(_full(grid), clearing),
                ]
            else:
                spans = _spans(grid, painted, self.band)
            if len(spans) <= self.max_runs or self.cell >= MAX_CELL_PX:
                break
            self.cell += 1
            self._painted = None
            self._until_refresh = 0
        if full:
            self.full_paints += 1
            self._until_refresh = self.refresh_every
        else:
            self._until_refresh -= 1
        self._painted = _painted_after(grid, spans, self._painted, self.rect, self.cell)
        self.frames += 1
        runs = [span.run(self.rect, self.cell) for span in spans]
        self.runs = len(runs)
        self._refine()
        return runs

    def _refine(self) -> None:
        """Sharpen the picture while it is well inside the budget, with a settle delay.

        Only refining happens here - a frame over the budget was already replanned
        coarser by ``plan``. Sharpening throws the painted model away, so the next
        frame is a full paint: it is worth doing only when it is clearly affordable,
        and only after ``CELL_SETTLE_FRAMES`` frames well under the budget, so a
        scene that hovers near the limit cannot oscillate between two cell sizes.
        """
        if self._painted is None or self.cell == MIN_CELL_PX:
            return
        # An empty frame says nothing about the budget: the picture is already
        # right, so refining would only force a full repaint to sharpen nothing.
        if not self.runs or self.runs * 4 > self.max_runs:
            self._settle = 0
            return
        self._settle += 1
        if self._settle >= CELL_SETTLE_FRAMES:
            self._settle = 0
            # The painted grid no longer has this resolution, so the next frame is
            # a full paint by itself (``plan`` sees the shape change).
            self.cell -= 1


def _shape(grid: list[list[int]]) -> tuple[int, int]:
    """The grid's ``(columns, rows)``, which is all a resolution change changes."""
    return (len(grid[0]), len(grid)) if grid and grid[0] else (0, 0)


def _grid(canvas: Image.Image, rect: Rect, cell: int) -> list[list[int]]:
    """The cell colours the display would show, one RGB565 per cell.

    ``BOX`` averages each cell, which is what keeps 1-px noise from costing a run
    of its own - the same reduction ``image_program`` draws at.
    """
    cols = math.ceil(rect.w / cell)
    rows = math.ceil(rect.h / cell)
    small = canvas.resize((cols, rows), Image.Resampling.BOX)
    return [
        [
            rgb_to_rgb565(cast("tuple[int, int, int]", small.getpixel((col, row))))
            for col in range(cols)
        ]
        for row in range(rows)
    ]


def _far(a: int, b: int, band: int) -> bool:
    """Whether two RGB565 colours differ by more than ``band`` on any channel."""
    red, green, blue = rgb565_to_rgb(a)
    other_red, other_green, other_blue = rgb565_to_rgb(b)
    return (
        abs(red - other_red) > band
        or abs(green - other_green) > band
        or abs(blue - other_blue) > band
    )


def _full(grid: list[list[int]]) -> list[_Span]:
    """Every cell of ``grid`` as spans, merged - a paint with no reference."""
    return _merged(grid, None, 0)


def _spans(grid: list[list[int]], painted: list[list[int]], band: int) -> list[_Span]:
    """Spans over the cells that moved away from what the panel shows.

    A cell is repainted when ``_far`` from its painted colour. Spans grow across a
    row of equal colour and down into the next row when the span repeats, which is
    what keeps a moving edge to a handful of runs instead of one per cell. Only
    changed cells join a span: an unchanged neighbour is already right on the
    panel, so painting it would be wasted traffic.
    """
    return _merged(grid, painted, band)


def _merged(
    grid: list[list[int]],
    painted: list[list[int]] | None,
    band: int,
) -> list[_Span]:
    """Merge ``grid`` into spans, skipping what ``painted`` already covers.

    The one merge both paint kinds need: equal cells within a row, then a span the
    next row repeats. ``painted`` is ``None`` for a full paint.
    """
    spans: list[_Span] = []
    previous: list[_Span] = []
    for row, cells in enumerate(grid):
        current: list[_Span] = []
        for col, colour in enumerate(cells):
            if painted is not None and not _far(painted[row][col], colour, band):
                continue
            if current and current[-1].rgb565 == colour and current[-1].x + current[-1].w == col:
                current[-1].w += 1
                continue
            current.append(_Span(col, row, 1, 1, colour))
        grown: list[_Span] = []
        for span in current:
            above = next(
                (
                    candidate
                    for candidate in previous
                    if candidate.x == span.x
                    and candidate.w == span.w
                    and candidate.y + candidate.h == span.y
                    and candidate.rgb565 == span.rgb565
                ),
                None,
            )
            if above is not None:
                above.h += span.h
                grown.append(above)
                continue
            grown.append(span)
            spans.append(span)
        previous = grown
    return spans


def _canvas_colour(grid: list[list[int]], fallback: int) -> int:
    """The colour a full paint clears the rectangle to: the most common cell.

    Counted on the grid, not on pixels: the clearing fill exists to cover the cells
    that would otherwise be painted one by one, so the colour that covers the most
    cells is the one that saves the most runs. Ties go to the highest value, so the
    answer never depends on the order the cells were counted in.
    """
    tally: dict[int, int] = {}
    for cells in grid:
        for colour in cells:
            tally[colour] = tally.get(colour, 0) + 1
    if not tally:
        return fallback
    return max(tally.items(), key=lambda item: (item[1], item[0]))[0]


def _without(spans: list[_Span], clearing: int) -> list[_Span]:
    """The spans of a full paint that the clearing fill does not already cover.

    Dropping them is what makes the clear worth sending; a whole span is dropped
    or kept, never halved, because a half span breaks the merges that made it one
    run.
    """
    return [span for span in spans if span.rgb565 != clearing]


def _painted_after(
    grid: list[list[int]],
    spans: list[_Span],
    painted: list[list[int]] | None,
    rect: Rect,
    cell: int,
) -> list[list[int]]:
    """The grid the panel shows once ``spans`` are painted.

    Cells no span covers keep the colour they had: they were inside the dead band,
    so the panel still shows what it showed, and that - not the frame - is what the
    next frame is compared against.
    """
    if painted is None or _shape(painted) != _shape(grid):
        painted = [row[:] for row in grid]
    for span in spans:
        top = span.y * cell
        left = span.x * cell
        bottom = min(rect.h, (span.y + span.h) * cell)
        right = min(rect.w, (span.x + span.w) * cell)
        for row in range(top // cell, min(len(painted), math.ceil(bottom / cell))):
            for col in range(left // cell, min(len(painted[row]), math.ceil(right / cell))):
                painted[row][col] = span.rgb565
    return painted

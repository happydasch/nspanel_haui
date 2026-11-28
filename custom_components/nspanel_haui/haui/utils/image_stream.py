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
* The model is true only while the panel shows what the stream painted, so the
  rectangle is painted whole again whenever that stopped being true: when the
  grid resolution changes, every ``refresh_every`` frames (the dead band lets a
  slow drift through - a wall that darkens one step at a time never crosses it),
  and whenever the caller says so (``DeltaPlanner.repaint``): a page that drew
  its own widgets over the rectangle, a pass the panel dropped before it
  finished. Without that, a delta would keep the ghost of what is no longer
  there, because nothing else ever clears the rectangle again.

The rectangle is rasterised exactly as ``show_image`` does it (``fit_image``): same
letterbox or crop, same canvas colour, so a stream and a still of the same picture
agree.

Pure and synchronous, no Home Assistant: the caller fetches and decodes the frame,
this decides what to paint.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Final, cast

from PIL import Image

from .color import rgb565_to_rgb, rgb_to_rgb565
from .image_program import Rect, cover_image, fill_run, fit_image

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
#: The cell a stream starts at. Four is the point where a 3.5" panel shows a face
#: or a number plate as itself: at the eight a stream used to start at, a doorbell
#: picture is 60 blocks across and nothing in it is recognisable.
DEFAULT_CELL_PX: Final = 4
#: Runs one *update* may cost. A frame over this is made coarser before it is sent
#: rather than dribbling out for a second, because a stream's whole point is that
#: the next frame arrives. It is the budget for what changed, not for the picture:
#: a full paint has its own (``FIRST_FRAME_RUNS``).
DEFAULT_FRAME_RUNS: Final = 1200
MIN_FRAME_RUNS: Final = 40
MAX_FRAME_RUNS: Final = 2400
#: Runs a **full paint** may cost - the first frame of a stream, a repaint after a
#: resolution change and the periodic refresh. A full paint is where the picture's
#: detail comes from, and it happens once per stream (a few times an hour), so it
#: may spend the wire's whole band: 6 000 runs is about 1.6 s at the ~3 700 fills a
#: second a panel takes, and it buys a picture at cell 3-4 instead of a mosaic.
FIRST_FRAME_RUNS: Final = 6000
MAX_FIRST_FRAME_RUNS: Final = 12000
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
#: Frames a stream waits after a refinement painted the rectangle whole before it
#: tries another one. Sharpening costs a full paint, and a moving scene produces
#: cheap deltas on its own - without this, a stream walked from cell 4 to cell 2 in
#: three frames and paid two whole paints for it, which reads as a flash.
REFINE_COOLDOWN: Final = 8
#: Startup grids and their run limits. The first starts with one background fill.
_STARTUP_PASSES: Final = ((32, 160), (16, 400), (8, 1200))


@dataclass(frozen=True, slots=True)
class PictureQuality:
    """One setting of a panel's picture quality, as a stream takes it.

    The quality is the *density* of the picture: the cell size the stream paints
    at and never sharpens past. Everything else follows from it, because drawing
    time is what limits a stream - a finer picture is more rectangles per frame,
    so a finer quality aims at fewer frames a second and spends more of the wire
    on the one paint that shows the picture.

    Attributes:
        cell: Cell size in display pixels; also the finest the picture gets.
        fps: Frames a second the stream aims for.
        max_runs: Runs one update may cost before it is painted coarser.
        first_runs: Runs the paint that shows the picture may cost.
    """

    cell: int
    fps: float
    max_runs: int
    first_runs: int


#: The three quality presets. These are work limits, not throughput guarantees:
#: the real fill rate depends on the panel and the shape of the draw.
QUALITY: dict[str, PictureQuality] = {
    "high": PictureQuality(
        cell=2, fps=1.0, max_runs=MAX_FRAME_RUNS, first_runs=MAX_FIRST_FRAME_RUNS
    ),
    "mid": PictureQuality(
        cell=3, fps=2.0, max_runs=DEFAULT_FRAME_RUNS, first_runs=FIRST_FRAME_RUNS
    ),
    "low": PictureQuality(cell=6, fps=4.0, max_runs=600, first_runs=3000),
}
#: The quality a panel uses when it has none stored.
DEFAULT_QUALITY: Final = "mid"


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
        return fill_run(left, top, width, height, self.rgb565)


class DeltaPlanner:
    """Plan the runs that bring the panel from what it shows to the newest frame.

    One planner per streamed rectangle. It is stateful on purpose: the grid it
    keeps *is* the model of the display, so the caller must send every program it
    returns and no other draw into the same rectangle - the two would disagree and
    the picture would keep a ghost of the other program.

    Attributes:
        cell: Cell size in display pixels currently used.
        min_cell: The finest cell this stream sharpens to.
        runs: Runs the last program carried.
        frames: Programs returned so far, empty ones included.
        full_paints: Times a whole rectangle was repainted.
    """

    def __init__(
        self,
        rect: Rect,
        *,
        cell: int = DEFAULT_CELL_PX,
        min_cell: int = MIN_CELL_PX,
        band: int = DEAD_BAND,
        max_runs: int = DEFAULT_FRAME_RUNS,
        first_runs: int = FIRST_FRAME_RUNS,
        refresh_every: int = REFRESH_EVERY,
        cover: bool = False,
        progressive: bool = False,
    ) -> None:
        """Start a stream into ``rect``.

        Args:
            rect: The rectangle to paint, in display pixels.
            cell: Starting cell size; clamped to ``MIN_CELL_PX``-``MAX_CELL_PX``.
            min_cell: The finest cell the stream sharpens to - a picture quality
                pins the density it was asked for instead of finding its own.
            band: Per-channel dead band before a cell is repainted, 0-255.
            max_runs: Runs one update may cost; a frame over it is made coarser.
            first_runs: Runs a full paint may cost - more than an update, because
                the detail of the picture is decided by the paint that shows it.
            refresh_every: Frames between two full repaints; 0 disables them.
            cover: Crop the frame to the rectangle instead of letterboxing it.
            progressive: Paint coarse layers before reaching the requested grid.

        Raises:
            ImageStreamError: When a size or a band is outside its range.
        """
        if not 0 <= band <= 255:
            raise ImageStreamError(f"dead band {band} is outside 0-255")
        if not MIN_FRAME_RUNS <= max_runs <= MAX_FRAME_RUNS:
            raise ImageStreamError(
                f"{max_runs} runs a frame is outside {MIN_FRAME_RUNS}-{MAX_FRAME_RUNS}"
            )
        if not max_runs <= first_runs <= MAX_FIRST_FRAME_RUNS:
            raise ImageStreamError(
                f"{first_runs} runs a full paint is outside {max_runs}-{MAX_FIRST_FRAME_RUNS}"
            )
        if refresh_every < 0:
            raise ImageStreamError(f"refresh_every {refresh_every} is negative")
        self.rect = rect
        self.band = band
        self.max_runs = max_runs
        self.first_runs = first_runs
        self.refresh_every = refresh_every
        self.cover = cover
        self._startup_pass = 0 if progressive else len(_STARTUP_PASSES)
        self._startup_cell: int | None = None
        self.cell = min(MAX_CELL_PX, max(MIN_CELL_PX, cell))
        self.min_cell = min(self.cell, max(MIN_CELL_PX, min_cell))
        self.runs = 0
        self.frames = 0
        self.full_paints = 0
        #: The colours the panel shows, one RGB565 per cell; ``None`` until the
        #: first frame, which is then a full paint by definition.
        self._painted: list[list[int]] | None = None
        #: Set when the panel may no longer show the painted model: the next
        #: frame is then a full paint (``repaint``).
        self._repaint = False
        #: Frames left before a full repaint; 0 means "the next one is full".
        self._until_refresh = 0
        #: Frames spent waiting before a resolution change is worth making.
        self._settle = 0
        #: ``frames`` before which no refinement is worth another full paint.
        self._refine_after = 0

    def clone(self) -> DeltaPlanner:
        """A copy to plan one frame on, leaving this planner untouched.

        A frame is planned off the worker (it is pure CPU), while the worker may
        repaint or replace the planner meanwhile - so the frame gets its own copy
        and the worker commits it only when the program arrives whole
        (``CameraStream._send_on_worker``). This is what that copy is, and it is a
        shallow one on purpose: the grid is the only mutable state, and copying it
        row by row costs a fraction of ``copy.deepcopy`` (0.1-0.7 ms a frame
        against 3-4 ms of planning, measured at cell 2-6).

        Returns:
            An independent planner with the same settings and painted model.
        """
        other = copy.copy(self)
        other._painted = [row[:] for row in self._painted] if self._painted is not None else None
        return other

    @property
    def painted(self) -> bool:
        """Whether the panel is showing a frame of this stream yet."""
        return self._painted is not None

    @property
    def starting_up(self) -> bool:
        """Whether the last planned picture was a coarse startup layer."""
        return self._startup_cell is not None

    def repaint(self) -> None:
        """Paint the rectangle whole on the next frame: the panel may not show it.

        The painted model is what makes a delta cheap, and it is only true while
        the panel still shows what this planner painted. Anything else that
        touched the rectangle - a page that drew its own widgets over it, a pass
        the panel dropped before it finished, another program into the same area
        - breaks that, and a delta planned against it keeps the ghost of what is
        no longer there, for ever: a stream reruns the clear only when it is
        asked to. This is how it is asked.

        During startup the layer being painted is repeated rather than skipped:
        the panel just showed it cannot keep up, and the full-detail paint is the
        slowest one there is.
        """
        self._repaint = True
        if self._startup_cell is not None:
            self._startup_pass = max(0, self._startup_pass - 1)
            self._startup_cell = None

    def plan(self, image: Image.Image) -> list[str]:
        """The program that shows ``image``, and the painted model updated to it.

        Args:
            image: The decoded frame. It is fitted into the rectangle exactly as
                ``show_image`` would draw it (``cover`` crops instead of
                letterboxing).

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
        # Only the fitted picture is used here: a stream clears with the most
        # common cell of its own grid (``_full_spans``) and never letterboxes a
        # frame it crops, so the picture's own dominant colour - a sampled
        # histogram per frame - would be computed and thrown away.
        if self.cover:
            canvas = cover_image(image, self.rect, resample=Image.Resampling.BOX)
        else:
            canvas, _colour = fit_image(image, self.rect)
        if (startup := self._plan_startup(canvas)) is not None:
            return startup
        # The cell size is decided *before* the program is sent, never after: a
        # frame over the budget is replanned coarser here, so the panel receives one
        # program at the resolution it can keep up with instead of a fine one
        # followed by a full repaint of the same picture. A full paint has the
        # larger budget - it is the picture, and it happens rarely - while an update
        # only pays for what changed and must leave room for the next one.
        while True:
            grid = _grid(canvas, self.rect, self.cell)
            refresh_due = self.refresh_every > 0 and self._until_refresh <= 0
            full = self._painted is None or self._repaint or refresh_due
            if full and self._startup_cell is not None:
                # Paint over the coarse image instead of clearing it for every pass.
                spans = _merged(grid)
                # A clear can sometimes fit a finer grid. Keep that quality rather
                # than coarsening just to avoid the clear.
                if len(spans) > self.first_runs:
                    spans = _full_spans(grid)
            else:
                spans = _full_spans(grid) if full else _merged(grid, self._painted, self.band)
            budget = self.first_runs if full else self.max_runs
            if len(spans) <= budget or self.cell >= MAX_CELL_PX:
                break
            self.cell += 1
            self._painted = None
            self._until_refresh = 0
        if not full and self._should_refine(len(spans)):
            finer_grid = _grid(canvas, self.rect, self.cell - 1)
            finer_spans = _full_spans(finer_grid)
            if len(finer_spans) <= self.first_runs:
                self.cell -= 1
                grid, spans, full = finer_grid, finer_spans, True
                self._refine_after = self.frames + REFINE_COOLDOWN
        if full:
            self._startup_cell = None
            self._settle = 0
            self._repaint = False
            self.full_paints += 1
            self._until_refresh = self.refresh_every
        else:
            self._until_refresh -= 1
        self._painted = _painted_after(grid, spans, self._painted, self.rect, self.cell)
        self.frames += 1
        runs = [span.run(self.rect, self.cell) for span in spans]
        self.runs = len(runs)
        return runs

    def _plan_startup(self, canvas: Image.Image) -> list[str] | None:
        """Cover the rectangle in stages without changing the requested detail."""
        while self._startup_pass < len(_STARTUP_PASSES):
            target, budget = _STARTUP_PASSES[self._startup_pass]
            self._startup_pass += 1
            cell = target
            if cell <= self.cell:
                break
            while self._startup_cell is None or cell < self._startup_cell:
                grid = _grid(canvas, self.rect, cell)
                spans = _full_spans(grid) if self._startup_cell is None else _merged(grid)
                if len(spans) <= budget:
                    self._startup_cell = cell
                    self.frames += 1
                    self.full_paints += 1
                    self.runs = len(spans)
                    return [span.run(self.rect, cell) for span in spans]
                cell += 1
        return None

    def _should_refine(self, runs: int) -> bool:
        """Probe a finer grid only after several cheap, non-empty deltas.

        Sharpening costs a full paint, and a scene that keeps moving produces the
        cheap deltas this looks for anyway - so a refinement buys itself a
        ``REFINE_COOLDOWN`` before another is worth considering. Without it a
        stream walked from cell 4 to cell 2 within three frames and paid two whole
        paints for it: on a 426x170 rectangle that is a visible flash, twice.
        """
        if self.cell <= self.min_cell or not runs or runs * 4 > self.max_runs:
            self._settle = 0
            return False
        if self.frames < self._refine_after:
            return False
        self._settle += 1
        if self._settle < CELL_SETTLE_FRAMES:
            return False
        # A cheap delta does not prove a finer full paint fits. Test this frame
        # without invalidating the current picture or rebuilding it at the old size.
        self._settle = 0
        return True


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


def _merged(
    grid: list[list[int]],
    painted: list[list[int]] | None = None,
    band: int = 0,
) -> list[_Span]:
    """Merge ``grid`` into spans, skipping what ``painted`` already covers.

    The one merge both paint kinds need: equal cells within a row, then a span the
    next row repeats. ``painted`` is ``None`` for a full paint; otherwise a cell is
    repainted only when ``_far`` from its painted colour, so an unchanged
    neighbour - already right on the panel - never joins a span, and what is
    painted is only what changed.

    Deliberately not ``image_program._spans``: that one merges *neighbours within a
    colour tolerance* on source colours, which is right for a still image painted
    once, and wrong here - a span merged with tolerance would paint a colour the
    grid does not hold, so the model the next frame compares against would drift
    from the display by the tolerance every frame. This one merges exact display
    colours only, and skips the cells a dead band already covers; the two agree on
    a full paint of the same grid, which is what
    ``tests/test_image_stream.py::test_the_two_merges_agree_on_a_full_paint`` pins.
    """
    spans: list[_Span] = []
    previous: dict[tuple[int, int], _Span] = {}
    for row, cells in enumerate(grid):
        current: list[_Span] = []
        for col, colour in enumerate(cells):
            if painted is not None and not _far(painted[row][col], colour, band):
                continue
            if current and current[-1].rgb565 == colour and current[-1].x + current[-1].w == col:
                current[-1].w += 1
                continue
            current.append(_Span(col, row, 1, 1, colour))
        # A span grows down into the row above it when that row has one with the
        # same width and colour: a flat block is then one run, not one per row.
        grown: dict[tuple[int, int], _Span] = {}
        for span in current:
            above = previous.get((span.x, span.w))
            if above is not None and above.rgb565 == span.rgb565:
                above.h += span.h
                grown[(above.x, above.w)] = above
                continue
            grown[(span.x, span.w)] = span
            spans.append(span)
        previous = grown
    return spans


def _full_spans(grid: list[list[int]]) -> list[_Span]:
    """Clear to the dominant colour, then paint the cells that differ."""
    clearing = _canvas_colour(grid)
    return [
        _Span(0, 0, len(grid[0]), len(grid), clearing),
        *(span for span in _merged(grid) if span.rgb565 != clearing),
    ]


def _canvas_colour(grid: list[list[int]]) -> int:
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
    return max(tally.items(), key=lambda item: (item[1], item[0]))[0]


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

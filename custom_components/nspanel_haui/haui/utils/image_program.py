"""Rasterise an image into a bounded program of Nextion ``fill`` instructions.

A run is one ``fill x1,y1,x2,y2,color`` instruction covering a rectangle of equal
colour, and its count is what an image costs: the panel paints them one after
another, so a budget of runs is a budget of time - at most
``draw_wire.COMMAND_SPACING_MS`` per run, the pace this plans against, while the
firmware streams a draw faster than that at the display's own
acknowledgement rate. This module's job is to spend that count without
pretending the result is a photograph: runs buy detail, so the same budget gives
a sharp icon and a coarse mosaic for a full page.

The grid is never finer than one pixel per cell, so the best a rectangle can get
is the image at the display's own resolution - and the budget is what caps how
close a large rectangle gets to it. Length is no longer a limit: the program is
sent in slices (``draw_wire.DRAW_SLICE_CHARS``), so more runs cost time and
nothing else.

The rectangle is painted in two steps. One ``fill`` covers all of it in the
picture's own most common colour (``_dominant_colour``) - the letterbox margins
and the largest flat area come free that way - and only the blocks that colour
does not already cover follow. Dropping those blocks is what a canvas buys, and
the picture's own colour is the best one available, so it is found rather than
fixed.

Pure and synchronous, no Home Assistant and no asyncio: the service calls it in
the executor, the firmware streams what it returns.
"""

from __future__ import annotations

import io
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, cast

from PIL import Image, UnidentifiedImageError

from .color import rgb565_to_rgb, rgb_to_rgb565
from .draw_wire import COMMAND_SPACING_MS, pack_program

# Latency is at most ``runs * COMMAND_SPACING_MS`` (the pacer's pace, see
# ``draw_wire``), so the run budget is a time budget in the worst case.
TARGET_DRAW_MS: Final = 600
RUN_BUDGET: Final = TARGET_DRAW_MS // COMMAND_SPACING_MS
# The ``quality`` service option's range: a coarser image in 0.12 s, or as fine
# as a caller is willing to wait. The top is a time budget, not a format or
# memory limit - the program is sliced (``draw_wire``) - planned at the pacer's
# 2 ms per run (``COMMAND_SPACING_MS``): 12 000 runs is 24 s at that pace, and a
# draw is streamed at the display's own, faster rate. The grid still cannot get
# finer than one rectangle per display pixel (a full 480x320 page at that detail
# is 153 600 pixels, so its cell size is always what the budget allows). Raise it
# only together with the service range in ``services.yaml``, ``strings.json`` and
# the translations.
MIN_RUN_BUDGET: Final = 60
MAX_RUN_BUDGET: Final = 12000
# Per-channel delta that still merges into one run. Flat art, gradients and
# anti-aliased edges are where the runs are, and this is cheap detail to lose.
COLOUR_TOLERANCE: Final = 8
# Above this a cell reads as a mosaic. The service logs a warning instead of
# pretending a full-page photograph is supported.
MAX_RECOMMENDED_CELL_PX: Final = 12
# The progressive pass: a coarse version in ~0.12 s, then the full program.
PROGRESSIVE_RUNS: Final = 60
# The canvas the picture is composited onto is its own most common colour
# (``_dominant_colour``): the margins a letterbox leaves are then the colour it
# already is, and every block that colour covers costs no run at all - one
# clearing fill paints them (``_compile``). The histogram is counted on a sample
# of at most this many pixels a side, so it costs the same whatever the size of
# the picture and counts cells rather than single pixels, which is the scale a
# program is drawn at.
CANVAS_SAMPLE: Final = 64
# Bits kept per channel while counting: four leaves a bucket 16 wide, which is
# the +/-``COLOUR_TOLERANCE`` a cell may differ from the canvas by and still be
# counted as a block the clear already paints.
CANVAS_BUCKET_BITS: Final = 4
# Ceiling on the source image's pixel count. Pillow's own decompression-bomb
# guard sits far above this (89 million by default), and a small PNG can decode
# to gigabytes; the service downloads up to 4 MiB, so the dimension check is what
# bounds memory before ``load()``.
MAX_SOURCE_PIXELS: Final = 16_000_000

# Display geometry of the two TFTs (``nextion/nspanel_haui*.HMI``).
LANDSCAPE_SIZE: Final = (480, 320)
PORTRAIT_SIZE: Final = (320, 480)


class ImageProgramError(Exception):
    """An image could not be turned into a draw program."""


@dataclass(frozen=True, slots=True)
class Rect:
    """A rectangle to paint into, in display pixels, half-open like the display."""

    x: int
    y: int
    w: int
    h: int

    def __post_init__(self) -> None:
        if self.w < 1 or self.h < 1:
            raise ImageProgramError(f"rect {self.w}x{self.h} has no area to draw into")
        if self.x < 0 or self.y < 0:
            raise ImageProgramError(f"rect at ({self.x}, {self.y}) is off the display")

    @property
    def right(self) -> int:
        """First column past the rectangle."""
        return self.x + self.w

    @property
    def bottom(self) -> int:
        """First row past the rectangle."""
        return self.y + self.h

    def overlaps(self, other: Rect) -> bool:
        """Whether the two rectangles share a pixel; both are half-open."""
        return (
            self.x < other.right
            and other.x < self.right
            and self.y < other.bottom
            and other.y < self.bottom
        )


def display_size(portrait: bool) -> tuple[int, int]:
    """The visible area of a panel's display, in its own orientation."""
    return PORTRAIT_SIZE if portrait else LANDSCAPE_SIZE


@dataclass(slots=True)
class _Span:
    """A rectangle of one colour, grown as rows repeat it."""

    x: int
    y: int
    w: int
    h: int
    rgb: tuple[int, int, int]


def _close(a: tuple[int, int, int], b: tuple[int, int, int], tolerance: int) -> bool:
    """Whether two colours may become one run."""
    return (
        abs(a[0] - b[0]) <= tolerance
        and abs(a[1] - b[1]) <= tolerance
        and abs(a[2] - b[2]) <= tolerance
    )


def decode_image(data: bytes) -> Image.Image:
    """Decode image bytes into an RGB image.

    The dimensions are checked before ``load()``: a 4 MiB file can describe a
    canvas far larger than the panel will ever use, and decoding it would spend
    the executor's memory on pixels no draw could address.

    Public because a camera stream receives the same encoded bytes - Home
    Assistant's ``camera.async_get_image`` hands back the picture's JPEG, not
    pixels - and must decode one frame per tick without re-encoding it just to
    reach this function through ``image_plan``. Call it off the event loop.

    Raises:
        ImageProgramError: When the bytes are not a decodable image, or the
            image decodes to more than ``MAX_SOURCE_PIXELS`` pixels.
    """
    if not data:
        raise ImageProgramError("the image is empty")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            width, height = opened.size
            if width * height > MAX_SOURCE_PIXELS:
                raise ImageProgramError(
                    f"the image is {width}x{height} pixels, over the {MAX_SOURCE_PIXELS} pixel cap"
                )
            opened.load()
            image = opened.convert("RGB")
    except Image.DecompressionBombError as exc:
        raise ImageProgramError(f"the image is too large to decode: {exc}") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageProgramError(f"the image could not be decoded: {exc}") from exc
    if image.width < 1 or image.height < 1:
        raise ImageProgramError("the image has no pixels")
    return image


def _dominant_colour(picture: Image.Image) -> int:
    """The picture's most common colour, as the display's RGB565.

    Counted on a sample (``CANVAS_SAMPLE``) with ``CANVAS_BUCKET_BITS`` per
    channel, so the answer is the colour of the largest area at the scale the
    program is drawn at instead of the one pixel value that happens to repeat,
    and the cost does not grow with the picture. The bucket's mean is the colour:
    it sits in the middle of the values that filled it, which is what the
    tolerance around the canvas covers.

    Ties go to the highest bucket, so the answer never depends on the order the
    picture's colours happened to be counted in.

    Returns:
        The colour as RGB565, the value a ``fill`` instruction carries.
    """
    scale = min(1.0, CANVAS_SAMPLE / max(picture.width, picture.height))
    cols = max(1, round(picture.width * scale))
    rows = max(1, round(picture.height * scale))
    sample = picture.resize((cols, rows), Image.Resampling.BOX)
    shift = 8 - CANVAS_BUCKET_BITS
    # count, then the sums the bucket's mean comes from.
    tally: dict[tuple[int, int, int], list[int]] = {}
    raw = sample.tobytes()
    for index in range(0, len(raw), 3):
        red, green, blue = raw[index], raw[index + 1], raw[index + 2]
        key = (red >> shift, green >> shift, blue >> shift)
        entry = tally.get(key)
        if entry is None:
            tally[key] = [1, red, green, blue]
        else:
            entry[0] += 1
            entry[1] += red
            entry[2] += green
            entry[3] += blue
    _key, (count, red, green, blue) = max(tally.items(), key=lambda item: (item[1][0], item[0]))
    return rgb_to_rgb565((red // count, green // count, blue // count))


def fit_image(image: Image.Image, rect: Rect, *, cover: bool = False) -> tuple[Image.Image, int]:
    """Composite ``image`` into ``rect``, letterboxed or cropped to fill, on its own colour.

    The margins take the picture's most common colour (``_dominant_colour``)
    rather than a fixed one: they are then the colour the picture already is, so
    the clearing fill paints them and they cost no run of their own. Opaque, too
    - a PNG with alpha must not punch through the page's widgets.

    Public because a camera stream composites one frame per tick and must not
    re-encode it just to reach this through the bytes path: same letterbox or
    crop, same canvas colour, so a stream frame looks exactly like a still of the
    same picture.

    Args:
        image: The decoded picture, any mode Pillow can convert to RGB.
        rect: Where the picture goes, in display pixels.
        cover: Crop the picture to the rectangle instead of letterboxing it. A
            camera page is the case for it: the panel's picture area is far
            taller than a camera's frame, and margins there would spend the
            display's few pixels on empty bands instead of on the picture.

    Returns:
        The fitted canvas (``rect.w`` x ``rect.h``) and the colour it is cleared
        to, as RGB565.
    """
    image = image.convert("RGB")
    if cover:
        scale = max(rect.w / image.width, rect.h / image.height)
        width = max(rect.w, round(image.width * scale))
        height = max(rect.h, round(image.height * scale))
        picture = image.resize((width, height), Image.Resampling.LANCZOS)
        left = (width - rect.w) // 2
        top = (height - rect.h) // 2
        cropped = picture.crop((left, top, left + rect.w, top + rect.h))
        return cropped, _dominant_colour(cropped)
    scale = min(rect.w / image.width, rect.h / image.height)
    width = max(1, min(rect.w, round(image.width * scale)))
    height = max(1, min(rect.h, round(image.height * scale)))
    picture = image.resize((width, height), Image.Resampling.LANCZOS)
    colour = _dominant_colour(picture)
    canvas = Image.new("RGB", (rect.w, rect.h), rgb565_to_rgb(colour))
    canvas.paste(picture, ((rect.w - width) // 2, (rect.h - height) // 2))
    return canvas, colour


def _cells(canvas: Image.Image, cols: int, rows: int) -> list[list[tuple[int, int, int]]]:
    """Average the canvas down to one colour per grid cell.

    ``BOX`` averages each cell, so 1-px noise cannot cost a run of its own, and
    the averages are kept as they are: the display shows 65 536 colours, so a
    gradient stays a gradient instead of banding into a poster. The run budget is
    spent on cell size alone (``_compile``).
    """
    small = canvas.resize((cols, rows), Image.Resampling.BOX)
    return [
        [cast("tuple[int, int, int]", small.getpixel((col, row))) for col in range(cols)]
        for row in range(rows)
    ]


def _spans(
    cells: list[list[tuple[int, int, int]]],
    rect: Rect,
    cell: int,
    tolerance: int,
    canvas: tuple[int, int, int],
) -> list[_Span]:
    """Merge the cell grid into rectangles, top to bottom.

    Three merges, in the order that buys the most runs: equal cells within a row,
    a row span the next row repeats (vertical, so a flat block is one run and not
    one per row), and neighbours within ``tolerance``.

    The spans that ``canvas`` already covers are dropped at the end - the
    clearing fill in front of the program paints them (``_compile``), and
    dropping them is the whole point of choosing the canvas. Whole spans, never
    cells: a flat area is one span wherever it is, and breaking a span up to drop
    a piece of it would cost the merges that made it cheap.
    """
    spans: list[_Span] = []
    previous: dict[tuple[int, int], _Span] = {}
    for row, row_cells in enumerate(cells):
        y = rect.y + row * cell
        if y >= rect.bottom:
            break
        height = min(cell, rect.bottom - y)
        current: list[_Span] = []
        for col, rgb in enumerate(row_cells):
            x = rect.x + col * cell
            if x >= rect.right:
                break
            width = min(cell, rect.right - x)
            if current and _close(current[-1].rgb, rgb, tolerance):
                current[-1].w += width
                continue
            current.append(_Span(x, y, width, height, rgb))
        # A span grows down into the row above it when that row has one with the
        # same width and a colour within tolerance: a flat block is then one run.
        merged: dict[tuple[int, int], _Span] = {}
        for span in current:
            above = previous.get((span.x, span.w))
            if above is not None and _close(above.rgb, span.rgb, tolerance):
                above.h += span.h
                merged[(above.x, above.w)] = above
                continue
            merged[(span.x, span.w)] = span
            spans.append(span)
        # Grown spans are already in ``spans``; only new ones are appended.
        previous = merged
    spans.sort(key=lambda span: (span.y, span.x))
    return [span for span in spans if not _close(span.rgb, canvas, tolerance)]


def fill_run(x: int, y: int, w: int, h: int, colour: int) -> str:
    """One Nextion ``fill`` instruction: a rectangle of one RGB565 colour.

    The wire format lives here and nowhere else, so a still image
    (``clear_run``, ``_program``) and a stream frame (``image_stream``) cannot
    disagree about it. ``fill`` takes ``x,y,w,h`` - width and height, not a
    second corner (``fill 20,20,150,50,1024`` paints 150x50 from (20,20), per the
    instruction set). ``draw`` and ``line`` use corners; ``fill`` does not.
    """
    return f"fill {x},{y},{w},{h},{colour}"


def clear_run(rect: Rect, colour: int) -> str:
    """One ``fill`` covering the whole rectangle.

    The cheapest run there is, and the one an image program starts with: it
    paints the canvas colour over everything the blocks after it do not cover.
    ``clear_image`` sends it alone, in the page's background colour.
    """
    return fill_run(rect.x, rect.y, rect.w, rect.h, colour)


def _program(spans: Iterable[_Span]) -> list[str]:
    """``fill`` instructions for the spans, top to bottom, left to right."""
    return [fill_run(span.x, span.y, span.w, span.h, rgb_to_rgb565(span.rgb)) for span in spans]


def _compile(
    canvas: Image.Image,
    rect: Rect,
    colour: int,
    *,
    budget: int,
    max_cell: int | None = None,
) -> tuple[list[str], int] | None:
    """Find the finest grid whose program fits ``budget`` runs and the firmware.

    Cell size is searched by bisection - the coarsest limit is a single cell, so
    a fitting size always exists - and the search floor is one display pixel: the
    grid is never finer than the rectangle, so the best possible result is the
    image at the screen's own resolution. Every cell keeps the colour the display
    can show, which is where the remaining detail is. The result is verified,
    never truncated: a grid over the budget is made coarser instead.

    The program is the clearing fill in ``colour`` followed by the blocks of the
    grid that colour does not already cover, and the clear counts as one of the
    budget's runs. Dropping the covered cells is what makes the grid affordable:
    at the same budget it is finer than a grid that paints every cell.

    ``max_cell`` caps how coarse the grid may get: the progressive full pass may
    not be coarser than the coarse pass it paints over. Only a pass that cannot
    fit at that cap returns ``None`` - a caller with a share of the budget left
    can then drop it instead of replacing a good coarse picture with a worse
    one.

    Returns:
        The ``fill`` instructions and the cell size in display pixels, or
        ``None`` when no grid at ``max_cell`` or below fits ``budget``.
    """
    worst = max(rect.w, rect.h)
    if max_cell is not None:
        worst = max(1, min(worst, max_cell))
    base = rgb565_to_rgb(colour)
    cache: dict[int, tuple[list[str], int] | None] = {}

    def attempt(cell: int) -> tuple[list[str], int] | None:
        if cell not in cache:
            cols = math.ceil(rect.w / cell)
            rows = math.ceil(rect.h / cell)
            cache[cell] = None
            spans = _spans(_cells(canvas, cols, rows), rect, cell, COLOUR_TOLERANCE, base)
            program = [clear_run(rect, colour), *_program(spans)]
            if len(program) <= budget:
                cache[cell] = (program, cell)
        return cache[cell]

    low, high = 1, worst
    while low < high:
        middle = (low + high) // 2
        if attempt(middle) is not None:
            high = middle
        else:
            low = middle + 1
    return attempt(low)


def image_plan(
    data: bytes,
    rect: Rect,
    *,
    budget: int = RUN_BUDGET,
    progressive: bool = False,
    tolerance: int = COLOUR_TOLERANCE,
) -> tuple[list[list[str]], int]:
    """The draw programs for ``data`` and the cell size the finest one is drawn at.

    Args:
        data: The encoded image (any format Pillow decodes).
        rect: Where to paint, in display pixels.
        budget: Total run budget for the draw; latency is at most
            ``budget * COMMAND_SPACING_MS``. With ``progressive`` the coarse
            pass's runs come out of the full pass's share, so the two together
            stay inside it. The grid never gets finer than one pixel per cell,
            so at the top of the range a small rectangle is drawn at the
            display's own resolution.
        progressive: Also return a coarse pass, so the image appears in ~0.12 s
            and sharpens. Its cells are larger than the full program's, so it is
            not a prefix of it - the full pass paints over it.
        tolerance: Per-channel delta that still merges into one run.

    Returns:
        The programs (``[full]``, or ``[coarse, full]`` with ``progressive``,
        each a list of ``fill`` instructions that covers its whole rectangle:
        one clearing fill in the picture's canvas colour, then the blocks that
        colour does not cover) and the cell size of the finest pass. When
        nothing finer than the coarse pass fits what it left of the budget, that
        pass is the picture and only it is returned.

    Raises:
        ImageProgramError: When the image cannot be decoded, the rect has no
            area, or the budget is outside the service option's range.
    """
    if not MIN_RUN_BUDGET <= budget <= MAX_RUN_BUDGET:
        raise ImageProgramError(
            f"budget {budget} is outside the {MIN_RUN_BUDGET}-{MAX_RUN_BUDGET} run range"
        )
    canvas, colour = fit_image(decode_image(data), rect)
    if progressive:
        compiled = _compile(canvas, rect, colour, budget=min(PROGRESSIVE_RUNS, budget))
        if compiled is None:  # pragma: no cover - a single cell fits every budget
            raise ImageProgramError(f"no grid fits {min(PROGRESSIVE_RUNS, budget)} runs")
        coarse, coarse_cell = compiled
        full = _compile(canvas, rect, colour, budget=budget - len(coarse), max_cell=coarse_cell)
        if full is not None and full[1] < coarse_cell:
            return [coarse, full[0]], full[1]
        # The coarse pass is already at the finest grid or nothing finer fits
        # what it left: sending it twice would paint the same picture twice.
        return [coarse], coarse_cell
    compiled = _compile(canvas, rect, colour, budget=budget)
    if compiled is None:  # pragma: no cover - a single cell fits every budget
        raise ImageProgramError(f"no grid fits {budget} runs")
    return [compiled[0]], compiled[1]


def image_runs(
    data: bytes,
    rect: Rect,
    *,
    budget: int = RUN_BUDGET,
    progressive: bool = False,
    tolerance: int = COLOUR_TOLERANCE,
) -> list[list[str]]:
    """Draw programs that paint ``data`` into ``rect``; ``image_plan`` adds the cell."""
    programs, _cell = image_plan(
        data,
        rect,
        budget=budget,
        progressive=progressive,
        tolerance=tolerance,
    )
    return programs


def program_length(runs: Iterable[str]) -> int:
    """Characters the panel receives for ``runs``: the packed program (``draw_wire``)."""
    return len(pack_program(runs))

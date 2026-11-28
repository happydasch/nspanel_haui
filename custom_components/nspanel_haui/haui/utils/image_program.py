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

Every pass starts by filling the whole rectangle with the backdrop colour, since
a pass skips the cells that already show it: without that fill an older image or
a widget underneath would show through the new picture.

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
# The colour an image is drawn on, as RGB565: the rectangle is painted black
# before the runs go down, so an older image, a widget or a picture background
# cannot show through the cells a pass skips.
BACKDROP: Final = 0x0000

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


def _decode(data: bytes) -> Image.Image:
    """Decode image bytes into an RGB image.

    Raises:
        ImageProgramError: When the bytes are not a decodable image.
    """
    if not data:
        raise ImageProgramError("the image is empty")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            image = opened.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageProgramError(f"the image could not be decoded: {exc}") from exc
    if image.width < 1 or image.height < 1:
        raise ImageProgramError("the image has no pixels")
    return image


def _fit(image: Image.Image, rect: Rect, background: tuple[int, int, int]) -> Image.Image:
    """Letterbox ``image`` into ``rect`` on the page's background colour.

    The margins are background coloured on purpose: the rasteriser skips cells
    that already match the page, so a letterboxed image costs nothing outside its
    own aspect ratio. Opaque, too - a PNG with alpha must not punch through the
    page's widgets.
    """
    scale = min(rect.w / image.width, rect.h / image.height)
    width = max(1, min(rect.w, round(image.width * scale)))
    height = max(1, min(rect.h, round(image.height * scale)))
    canvas = Image.new("RGB", (rect.w, rect.h), background)
    canvas.paste(
        image.resize((width, height), Image.Resampling.LANCZOS),
        ((rect.w - width) // 2, (rect.h - height) // 2),
    )
    return canvas


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
    background: tuple[int, int, int],
    tolerance: int,
) -> list[_Span]:
    """Merge the cell grid into rectangles, top to bottom.

    Three merges, in the order that buys the most runs: equal cells within a row,
    a row span the next row repeats (vertical, so a flat block is one run and not
    one per row), and neighbours within ``tolerance``. Cells that already match
    the page background are dropped entirely - the page shows that colour.
    """
    spans: list[_Span] = []
    previous: list[_Span] = []
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
        merged: list[_Span] = []
        for span in current:
            above = next(
                (
                    candidate
                    for candidate in previous
                    if candidate.x == span.x
                    and candidate.w == span.w
                    and candidate.y + candidate.h == span.y
                    and _close(candidate.rgb, span.rgb, tolerance)
                ),
                None,
            )
            if above is not None:
                above.h += span.h
                merged.append(above)
                continue
            merged.append(span)
            if not _close(span.rgb, background, tolerance):
                spans.append(span)
        # Grown spans are already in ``spans``; only new ones are appended.
        previous = merged
    spans.sort(key=lambda span: (span.y, span.x))
    return spans


def backdrop_run(rect: Rect, colour: int) -> str:
    """One ``fill`` covering the whole rectangle: what an image is drawn on.

    A pass skips every cell that already matches its backdrop, so the rectangle
    has to be painted before the runs go down: the area may hold an older image,
    a widget the page drew, or a picture background, and a skipped cell does not
    overwrite any of it. One flat fill is one run, the cheapest there is.
    """
    return f"fill {rect.x},{rect.y},{rect.w},{rect.h},{colour}"


def _program(spans: Iterable[_Span]) -> list[str]:
    """``fill`` instructions for the spans, top to bottom, left to right.

    The Nextion's ``fill`` takes ``x,y,w,h,color`` — width and height, not a
    second corner (``fill 20,20,150,50,1024`` paints 150x50 from (20,20), per
    the instruction set). ``draw`` and ``line`` use corners; ``fill`` does not.
    """
    return [f"fill {span.x},{span.y},{span.w},{span.h},{rgb_to_rgb565(span.rgb)}" for span in spans]


def _compile(
    canvas: Image.Image,
    rect: Rect,
    *,
    budget: int,
    background: tuple[int, int, int],
) -> tuple[list[str], int]:
    """Find the finest grid whose program fits ``budget`` runs and the firmware.

    Cell size is searched by bisection - the coarsest limit is a single cell, so
    a fitting size always exists - and the search floor is one display pixel: the
    grid is never finer than the rectangle, so the best possible result is the
    image at the screen's own resolution. Every cell keeps the colour the display
    can show, which is where the remaining detail is. The result is verified,
    never truncated: a grid over the budget is made coarser instead.

    Returns:
        The ``fill`` instructions and the cell size in display pixels.
    """
    worst = max(rect.w, rect.h)
    cache: dict[int, tuple[list[str], int] | None] = {}

    def attempt(cell: int) -> tuple[list[str], int] | None:
        if cell not in cache:
            cols = math.ceil(rect.w / cell)
            rows = math.ceil(rect.h / cell)
            cache[cell] = None
            spans = _spans(_cells(canvas, cols, rows), rect, cell, background, COLOUR_TOLERANCE)
            program = _program(spans)
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
    found = attempt(low)
    if found is None:  # pragma: no cover - the single-cell grid always fits
        raise ImageProgramError(f"no grid fits {budget} runs")
    return found


def image_plan(
    data: bytes,
    rect: Rect,
    *,
    background: int,
    budget: int = RUN_BUDGET,
    progressive: bool = False,
    tolerance: int = COLOUR_TOLERANCE,
) -> tuple[list[list[str]], int]:
    """The draw programs for ``data`` and the cell size the finest one is drawn at.

    Args:
        data: The encoded image (any format Pillow decodes).
        rect: Where to paint, in display pixels.
        background: The backdrop the rectangle is painted in first, as RGB565.
            The image is composited onto it, and cells that already match it are
            skipped - which is why the rectangle is filled with it before the
            first run, instead of leaving whatever was on the page there.
        budget: Run budget; latency is at most ``budget * COMMAND_SPACING_MS``.
            The grid never gets finer than one pixel per cell, so at the top of
            the range a small rectangle is drawn at the display's own
            resolution.
        progressive: Also return a coarse pass, so the image appears in ~0.12 s
            and sharpens. Its cells are larger than the full program's, so it is
            not a prefix of it - the full pass paints over it.
        tolerance: Per-channel delta that still merges into one run.

    Returns:
        The programs (``[full]``, or ``[coarse, full]`` with ``progressive``,
        each a list of ``fill`` instructions starting with the backdrop) and the
        cell size of the full pass in display pixels.

    Raises:
        ImageProgramError: When the image cannot be decoded, the rect has no
            area, or the budget is outside the service option's range.
    """
    if not MIN_RUN_BUDGET <= budget <= MAX_RUN_BUDGET:
        raise ImageProgramError(
            f"budget {budget} is outside the {MIN_RUN_BUDGET}-{MAX_RUN_BUDGET} run range"
        )
    background_rgb = rgb565_to_rgb(background)
    canvas = _fit(_decode(data), rect, background_rgb)
    full, cell = _compile(canvas, rect, budget=budget, background=background_rgb)
    if progressive:
        coarse, _coarse_cell = _compile(
            canvas, rect, budget=min(PROGRESSIVE_RUNS, budget), background=background_rgb
        )
        coarse.insert(0, backdrop_run(rect, background))
        return [coarse, full], cell
    full.insert(0, backdrop_run(rect, background))
    return [full], cell


def image_runs(
    data: bytes,
    rect: Rect,
    *,
    background: int,
    budget: int = RUN_BUDGET,
    progressive: bool = False,
    tolerance: int = COLOUR_TOLERANCE,
) -> list[list[str]]:
    """Draw programs that paint ``data`` into ``rect``; ``image_plan`` adds the cell."""
    programs, _cell = image_plan(
        data,
        rect,
        background=background,
        budget=budget,
        progressive=progressive,
        tolerance=tolerance,
    )
    return programs


def program_length(runs: Iterable[str]) -> int:
    """Characters the panel receives for ``runs``: the packed program (``draw_wire``)."""
    return len(pack_program(runs))

#!/usr/bin/env python3
"""Render what ``nspanel_haui.show_image`` would paint, without a panel.

An image on the panel is not a picture: it is a bounded program of Nextion
``fill`` rectangles (``haui/utils/image_program.py``), so what matters before a
call is the run count (at most ``runs * COMMAND_SPACING_MS``, the pace the hub
plans for, while the firmware streams a draw at the display's own rate) and
whether the result still reads as the logo or icon it came from. This replays the
real rasteriser over a local file and draws every ``fill`` onto a canvas the size
of the display, next to the ideal fit for comparison.

Usage:
    python -m scripts.image_program.gen_image_preview logo.png
    python -m scripts.image_program.gen_image_preview logo.png \\
        --x 20 --y 60 --w 160 --h 160 --budget 300 --progressive --portrait

Prints one line per pass (runs, program characters, panel latency, cell size)
and writes ``.dev/image-preview.png``: the ideal fit first, then one tile per
pass. A cell over ``MAX_RECOMMENDED_CELL_PX`` is the mosaic the action warns
about, so raise ``--budget`` or shrink the rectangle.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from custom_components.nspanel_haui.haui.utils.color import (  # noqa: E402
    rgb565_to_rgb,
    rgb_to_rgb565,
)
from custom_components.nspanel_haui.haui.utils.draw_wire import (  # noqa: E402
    COMMAND_SPACING_MS,
    DRAW_SLICE_CHARS,
    program_slices,
)
from custom_components.nspanel_haui.haui.utils.image_program import (  # noqa: E402
    MAX_RECOMMENDED_CELL_PX,
    MIN_RUN_BUDGET,
    RUN_BUDGET,
    ImageProgramError,
    Rect,
    decode_image,
    display_size,
    fit_image,
    image_plan,
    program_length,
)

# What the page shows outside the rectangle. This renderer models the picture
# only - the page's own background belongs to the panel - and the rectangle itself
# is always covered by the program's clearing fill.
PAGE_RGB = rgb565_to_rgb(0x0000)
DEFAULT_OUTPUT = ROOT / ".dev" / "image-preview.png"
# RGB565 keeps each channel to itself, so the colours the display can show are one
# 256-entry table per bit depth: ``fill`` carries a packed colour, and a picture
# the panel draws can never be finer than this.
_RED = [rgb565_to_rgb(rgb_to_rgb565((value, 0, 0)))[0] for value in range(256)]
_GREEN = [rgb565_to_rgb(rgb_to_rgb565((0, value, 0)))[1] for value in range(256)]
_BLUE = [rgb565_to_rgb(rgb_to_rgb565((0, 0, value)))[2] for value in range(256)]


def in_display_colours(image: Image.Image) -> Image.Image:
    """``image`` in the colours the panel can show, so a tile is not flattered.

    The reference tile is judged next to the passes, and the passes are drawn from
    packed RGB565 fills: comparing them against the source's 8-bit colours would
    call a correct draw wrong.
    """
    red, green, blue = image.split()
    return Image.merge(
        "RGB",
        (red.point(_RED), green.point(_GREEN), blue.point(_BLUE)),
    )


def load_image(source: str) -> bytes:
    """The image bytes, from a URL or from a file.

    Args:
        source: An ``http(s)`` URL or a path to an image file.

    Returns:
        The encoded image, ready for ``image_runs``.

    Raises:
        OSError: When the file cannot be read.
    """
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=15) as response:
            return response.read()
    return Path(source).read_bytes()


def paint(portrait: bool, runs: list[str]) -> Image.Image:
    """A display-sized canvas with every ``fill`` of one pass drawn on it.

    The runs are replayed in the order the panel receives them, the clearing fill
    in front of a pass included, so the tile is what the display shows and not a
    second rasteriser that could disagree with it.

    Args:
        portrait: Draw on the 320x480 display instead of the 480x320 one.
        runs: ``fill x,y,w,h,color`` instructions, as the rasteriser emits them.

    Returns:
        The canvas, in RGB like the display.
    """
    canvas = Image.new("RGB", display_size(portrait), PAGE_RGB)
    draw = ImageDraw.Draw(canvas)
    for run in runs:
        _keyword, geometry = run.split(" ")
        x, y, w, h, colour = (int(part) for part in geometry.split(","))
        # ``fill`` takes width and height, not a second corner.
        draw.rectangle((x, y, x + w - 1, y + h - 1), fill=rgb565_to_rgb(colour))
    return canvas


def ideal_tile(data: bytes, rect: Rect, portrait: bool) -> Image.Image:
    """The image as it would look if the rectangle had no run budget.

    The reference the passes are judged against: the rasteriser's own fit - the
    picture on its canvas colour, margins included - in the colours the display
    can show (``in_display_colours``), so the comparison is about the budget and
    not about the fitting or the panel's colour depth.
    """
    canvas = Image.new("RGB", display_size(portrait), PAGE_RGB)
    fitted, _colour = fit_image(decode_image(data), rect)
    canvas.paste(in_display_colours(fitted), (rect.x, rect.y))
    return canvas


def render_preview(
    *,
    data: bytes,
    rect: Rect,
    budget: int,
    progressive: bool,
    portrait: bool,
    scale: int,
    out: Path,
) -> list[tuple[str, list[str]]]:
    """Rasterise an image, write the comparison sheet and report the passes.

    Args:
        data: The encoded image.
        rect: Where the call would paint it.
        budget: The service's ``quality`` option.
        progressive: Whether the call draws the coarse pass too.
        portrait: Draw on the portrait display.
        scale: Integer zoom of the saved tiles, so a 1 px cell is visible.
        out: Where to write the sheet.

    Returns:
        ``[(pass name, runs)]``, coarse first when ``progressive`` is set.

    Raises:
        ImageProgramError: When the rectangle does not fit the display (the
            service refuses it too), the image cannot be decoded, or the budget
            is outside the service option's range.
    """
    width, height = display_size(portrait)
    if rect.right > width or rect.bottom > height:
        raise ImageProgramError(
            f"a {rect.w}x{rect.h} rectangle at ({rect.x}, {rect.y}) does not fit the "
            f"{width}x{height} display"
        )
    started = time.perf_counter()
    programs, cell = image_plan(data, rect, budget=budget, progressive=progressive)
    elapsed_ms = (time.perf_counter() - started) * 1000

    passes = [
        ("coarse" if progressive and index == 0 else "full", runs)
        for index, runs in enumerate(programs)
    ]
    for name, runs in passes:
        slices = program_slices(runs)
        print(
            f"{name:6} {len(runs):4} runs  {program_length(runs):6} chars  "
            f"~{len(runs) * COMMAND_SPACING_MS} ms planned, "
            f"{len(slices)} slice(s)" + (f"  drawn in {cell} px blocks" if name == "full" else "")
        )
        for part in slices:
            if program_length(part) > DRAW_SLICE_CHARS:
                print(
                    f"       a slice is over the {DRAW_SLICE_CHARS}-character slice the "
                    "panel stages"
                )
    # The coarse pass is coarse on purpose; only the final image is judged.
    if cell > MAX_RECOMMENDED_CELL_PX:
        print(
            f"       a mosaic at {cell} px per block: draw it smaller, or use a picture "
            "background for a full-page image"
        )
    print(f"rasterised in {elapsed_ms:.0f} ms here, rect at ({rect.x}, {rect.y}) {rect.w}x{rect.h}")

    frames = [ideal_tile(data, rect, portrait), *(paint(portrait, runs) for _n, runs in passes)]
    sheet = Image.new(
        "RGB",
        (len(frames) * width * scale + (len(frames) - 1) * 8, height * scale),
        "black",
    )
    for index, frame in enumerate(frames):
        sheet.paste(
            frame.resize((width * scale, height * scale), Image.NEAREST),
            (index * (width * scale + 8), 0),
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"wrote {out} — tiles: ideal fit | " + " | ".join(name for name, _r in passes))
    return passes


def main(argv: list[str] | None = None) -> int:
    """Run the renderer from the command line.

    Args:
        argv: Arguments to parse; ``sys.argv[1:]`` when None.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="path or http(s) URL of the image to rasterise")
    parser.add_argument("--x", type=int, default=20, help="left edge (default 20)")
    parser.add_argument("--y", type=int, default=20, help="top edge (default 20)")
    parser.add_argument("--w", type=int, default=160, help="rectangle width (default 160)")
    parser.add_argument("--h", type=int, default=160, help="rectangle height (default 160)")
    parser.add_argument(
        "--budget",
        type=int,
        default=RUN_BUDGET,
        help=f"the service's quality option, at least {MIN_RUN_BUDGET} (default {RUN_BUDGET})",
    )
    parser.add_argument(
        "--progressive", action="store_true", help="render the coarse pass the way the call does"
    )
    parser.add_argument("--portrait", action="store_true", help="320x480 instead of 480x320")
    parser.add_argument("--scale", type=int, default=2, help="zoom of the saved tiles (default 2)")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"sheet to write (default {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    rect = Rect(args.x, args.y, args.w, args.h)
    try:
        data = load_image(args.image)
        render_preview(
            data=data,
            rect=rect,
            budget=args.budget,
            progressive=args.progressive,
            portrait=args.portrait,
            scale=max(1, args.scale),
            out=args.out,
        )
    except (ImageProgramError, OSError) as exc:
        print(f"{args.image}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

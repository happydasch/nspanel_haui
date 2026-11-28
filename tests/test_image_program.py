"""The image rasteriser: run counts, RGB565 packing and the failure paths.

The program a hub sends is the wire contract between the rasteriser here, the
firmware's draw_runs action and the virtual panel, so the goldens below pin
exact instruction strings.
"""

from __future__ import annotations

import io
import random

import pytest
from PIL import Image, ImageDraw

from custom_components.nspanel_haui.haui.utils import image_program
from custom_components.nspanel_haui.haui.utils.color import rgb565_to_rgb, rgb_to_rgb565
from custom_components.nspanel_haui.haui.utils.draw_wire import (
    DRAW_SLICE_CHARS,
    program_slices,
)
from custom_components.nspanel_haui.haui.utils.image_program import (
    COLOUR_TOLERANCE,
    LANDSCAPE_SIZE,
    MAX_RECOMMENDED_CELL_PX,
    MAX_RUN_BUDGET,
    MIN_RUN_BUDGET,
    PORTRAIT_SIZE,
    PROGRESSIVE_RUNS,
    RUN_BUDGET,
    ImageProgramError,
    Rect,
    clear_run,
    display_size,
    image_plan,
    image_runs,
    program_length,
)

RED = rgb_to_rgb565((255, 0, 0))
GREEN = rgb_to_rgb565((0, 255, 0))
BLUE = rgb_to_rgb565((0, 0, 255))
WHITE = rgb_to_rgb565((255, 255, 255))
BLACK = rgb_to_rgb565((0, 0, 0))


def _png(image: Image.Image) -> bytes:
    """Encode an image the way a URL would deliver it."""
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _logo(size: int = 100) -> bytes:
    """Flat art at the size it is drawn: big axis-aligned blocks, hard edges.

    This is what the feature is for — a logo, an icon, a graphic — and it is where
    merging pays. Anti-aliased curves and photographs have no repeated row to
    merge, so they cost closer to one run per cell instead.
    """
    image = Image.new("RGB", (size, size), (250, 250, 250))
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((6, 6, size - 7, size - 7), fill=(30, 30, 40))
    drawing.rectangle((12, 12, size - 13, 30), fill=(200, 30, 30))
    drawing.rectangle((12, 40, 60, size - 13), fill=(20, 60, 200))
    drawing.rectangle((66, 40, size - 13, size - 13), fill=(20, 160, 90))
    return _png(image)


def _photo(size: int = 96) -> bytes:
    """A gradient: no two rows repeat, so vertical merging cannot help."""
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    assert pixels is not None
    for y in range(size):
        for x in range(size):
            pixels[x, y] = ((x * 255) // size, (y * 255) // size, ((x + y) * 255) // (2 * size))
    return _png(image)


def _row_baseline(data: bytes) -> int:
    """Runs a per-row rasteriser would emit: one per colour change in every row."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    pixels = image.load()
    assert pixels is not None
    baseline = image.height
    for y in range(image.height):
        for x in range(1, image.width):
            if pixels[x, y] != pixels[x - 1, y]:
                baseline += 1
    return baseline


def _painted(program: list[str], rect: Rect) -> set[tuple[int, int]]:
    """Every pixel the program's ``fill`` instructions cover."""
    covered: set[tuple[int, int]] = set()
    for run in program:
        _keyword, geometry = run.split(" ")
        x, y, w, h, _colour = (int(part) for part in geometry.split(","))
        for py in range(y, y + h):
            for px in range(x, x + w):
                covered.add((px, py))
    assert all(rect.x <= px < rect.right and rect.y <= py < rect.bottom for px, py in covered)
    return covered


def _canvas(
    programs: list[list[str]], rect: Rect, colour: int = BLACK
) -> list[list[tuple[int, int, int]]]:
    """Paint programs onto a canvas in order, the way the display does."""
    pixels = [[rgb565_to_rgb(colour)] * rect.w for _ in range(rect.h)]
    for program in programs:
        for run in program:
            _keyword, geometry = run.split(" ")
            x, y, w, h, fill = (int(part) for part in geometry.split(","))
            rgb = rgb565_to_rgb(fill)
            for py in range(y - rect.y, y - rect.y + h):
                for px in range(x - rect.x, x - rect.x + w):
                    pixels[py][px] = rgb
    return pixels


def test_a_picture_is_the_canvas_and_the_blocks_that_differ_from_it():
    """Two steps, and the second one is short: the field costs no runs at all.

    The canvas is the picture's own most common colour, so the blocks of that
    colour are one clearing fill instead of one run per block - here a 100x100
    field around a 10x10 mark is two instructions, not a grid.
    """
    image = Image.new("RGB", (100, 100), (250, 250, 250))
    ImageDraw.Draw(image).rectangle((10, 10, 19, 19), fill=(255, 0, 0))
    rect = Rect(0, 0, 100, 100)

    (program,) = image_runs(_png(image), rect)

    assert program == [clear_run(rect, 65503), f"fill 10,10,10,10,{RED}"]
    assert _painted(program, rect) == {
        (x, y) for y in range(rect.y, rect.bottom) for x in range(rect.x, rect.right)
    }


@pytest.mark.parametrize(
    "field,mark,canvas",
    [
        pytest.param((20, 40, 90), (250, 250, 250), rgb_to_rgb565((20, 40, 90)), id="dark"),
        pytest.param((250, 250, 250), (20, 40, 90), rgb_to_rgb565((250, 250, 250)), id="light"),
        pytest.param((0, 0, 0), (255, 0, 0), BLACK, id="black"),
    ],
)
def test_the_canvas_is_found_in_the_picture_instead_of_being_fixed(field, mark, canvas):
    """Whatever the picture is mostly made of, not whatever the last one was."""
    image = Image.new("RGB", (40, 40), field)
    ImageDraw.Draw(image).rectangle((4, 4, 9, 9), fill=mark)
    rect = Rect(0, 0, 40, 40)

    (program,) = image_runs(_png(image), rect)

    assert program[0] == clear_run(rect, canvas)


def test_the_letterbox_margins_cost_nothing():
    """A 4x2 image in a 4x4 rectangle: the margins are the colour it already is.

    They used to be a fixed colour drawn as runs of their own; the canvas of a
    picture that does not fill its rectangle is now that picture's own colour, so
    one clearing fill covers them and the whole rectangle is one instruction.
    """
    image = Image.new("RGB", (4, 2), (255, 0, 0))

    (program,) = image_runs(_png(image), Rect(0, 0, 4, 4))

    assert program == [clear_run(Rect(0, 0, 4, 4), RED)]


def test_a_flat_image_becomes_one_run_per_colour_block():
    """A 4x4 of four quadrants: the goldens the firmware and the panel must match.

    Four blocks, four runs - the biggest of them is the clearing fill, and the
    block it covers is dropped from the grid instead of painted twice.
    """
    image = Image.new("RGB", (4, 4))
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((0, 0, 1, 1), fill=(255, 0, 0))
    drawing.rectangle((2, 0, 3, 1), fill=(0, 255, 0))
    drawing.rectangle((0, 2, 1, 3), fill=(0, 0, 255))
    drawing.rectangle((2, 2, 3, 3), fill=(255, 255, 255))

    (program,) = image_runs(_png(image), Rect(0, 0, 4, 4))

    assert program == [
        f"fill 0,0,4,4,{WHITE}",
        f"fill 0,0,2,2,{RED}",
        f"fill 2,0,2,2,{GREEN}",
        f"fill 0,2,2,2,{BLUE}",
    ]


def test_a_single_colour_image_is_one_run():
    """Nothing to merge further: the rectangle is one flat block."""
    image = Image.new("RGB", (32, 32), (0, 0, 0))

    (program,) = image_runs(_png(image), Rect(0, 0, 32, 32))

    assert program == [f"fill 0,0,32,32,{BLACK}"]
    # The clear service still paints one flat fill, the cheapest run there is.
    assert clear_run(Rect(20, 30, 8, 4), BLACK) == "fill 20,30,8,4,0"


@pytest.mark.parametrize(
    "data,rect",
    [
        pytest.param(_logo(), Rect(10, 10, 100, 100), id="flat logo"),
        pytest.param(_logo(), Rect(0, 0, 480, 320), id="logo full page"),
        pytest.param(_photo(), Rect(40, 40, 200, 150), id="photo"),
        pytest.param(_photo(64), Rect(0, 0, 320, 480), id="portrait full page"),
    ],
)
def test_every_image_lands_under_the_run_budget(data, rect):
    """Merging, tolerance and a coarser grid are the levers — never truncation."""
    (program,) = image_runs(data, rect)

    assert 0 < len(program) <= RUN_BUDGET
    # A default pass is one slice: the wire length is what the panel is sent.
    assert len(program_slices(program)) == 1
    assert program_length(program) <= DRAW_SLICE_CHARS


@pytest.mark.parametrize(
    "data,rect",
    [
        pytest.param(_logo(), Rect(20, 20, 100, 100), id="logo at its own size"),
        pytest.param(_logo(), Rect(10, 10, 200, 150), id="logo scaled up"),
        pytest.param(_photo(), Rect(40, 40, 200, 150), id="photo"),
    ],
)
def test_the_merging_cuts_the_program_well_under_a_row_by_row_rasteriser(data, rect):
    """Vertical and tolerance merging are why an image is not one run per row."""
    (program,) = image_runs(data, rect)
    baseline = _row_baseline(data)

    assert len(program) <= 0.4 * baseline, f"{len(program)} runs vs baseline {baseline}"


def test_neighbouring_colours_within_the_tolerance_become_one_run():
    """Cheap fidelity: a band of near-identical colours is one rectangle."""
    image = Image.new("RGB", (8, 4), (100, 100, 100))
    band = ImageDraw.Draw(image)
    band.rectangle((4, 0, 7, 3), fill=(100 + COLOUR_TOLERANCE - 1, 100, 100))

    (program,) = image_runs(_png(image), Rect(0, 0, 8, 4))

    assert program == [f"fill 0,0,8,4,{rgb_to_rgb565((100, 100, 100))}"]


def test_a_real_difference_is_kept_as_two_runs():
    """The tolerance must not swallow a visible edge."""
    image = Image.new("RGB", (8, 4), (100, 100, 100))
    edge = ImageDraw.Draw(image)
    edge.rectangle((4, 0, 7, 3), fill=(100 + COLOUR_TOLERANCE + 20, 100, 100))

    (program,) = image_runs(_png(image), Rect(0, 0, 8, 4))

    assert len(program) == 2


def test_the_progressive_pass_is_coarse_first_and_within_the_total_budget():
    """Pass one appears in ~0.12 s; pass two refines the same rectangle."""
    coarse, full = image_runs(_logo(), Rect(0, 0, 200, 150), progressive=True)

    assert 0 < len(coarse) <= PROGRESSIVE_RUNS
    assert len(full) > len(coarse)
    # ``quality`` is the whole draw: the coarse pass's runs come out of the
    # full pass's share instead of being extra.
    assert len(coarse) + len(full) <= RUN_BUDGET
    # Both passes cover the rectangle on their own (each starts with its own
    # clearing fill), so the full one paints over the coarse one and the picture
    # never blinks out.
    assert _painted(coarse, Rect(0, 0, 200, 150)) == _painted(full, Rect(0, 0, 200, 150))
    assert all(run.startswith("fill ") for run in [*coarse, *full])


def test_a_coarse_pass_already_at_the_finest_grid_is_the_only_pass():
    """Sending the same picture twice is not progressive, it is twice the cost."""
    image = Image.new("RGB", (8, 8), (0, 0, 0))

    programs, cell = image_plan(_png(image), Rect(0, 0, 8, 8), progressive=True)

    assert programs == [["fill 0,0,8,8,0"]]
    assert cell == 1


def test_the_progressive_full_pass_repaints_every_block():
    """Nothing of the coarse approximation survives: every block is repainted.

    The full pass starts with its own clearing fill, so the coarse pass's colour
    is wiped from the whole rectangle before the finer blocks go down - a grey
    halo around a logo drawn on black cannot be left behind. A checkerboard makes
    the difference visible at every pixel: one coarse cell averages mid-grey
    while the one-pixel grid keeps black and white.
    """
    image = Image.new("RGB", (32, 32), (0, 0, 0))
    drawing = ImageDraw.Draw(image)
    for y in range(32):
        for x in range(32):
            if (x + y) % 2:
                drawing.point((x, y), fill=(255, 255, 255))
    rect = Rect(0, 0, 32, 32)

    coarse, full = image_runs(_png(image), rect, budget=MAX_RUN_BUDGET, progressive=True)

    expected = [
        [rgb565_to_rgb(WHITE) if (x + y) % 2 else rgb565_to_rgb(BLACK) for x in range(rect.w)]
        for y in range(rect.h)
    ]
    assert _canvas([coarse, full], rect) == expected


def test_an_image_over_the_source_pixel_cap_is_refused(monkeypatch):
    """A small file can describe a huge canvas; refuse it before decoding."""
    monkeypatch.setattr(image_program, "MAX_SOURCE_PIXELS", 64)
    image = Image.new("RGB", (9, 9), (255, 0, 0))

    with pytest.raises(ImageProgramError, match="pixel cap"):
        image_runs(_png(image), Rect(0, 0, 9, 9))


def test_pillows_decompression_bomb_is_an_image_program_error(monkeypatch):
    def explode(*_args, **_kwargs):
        raise Image.DecompressionBombError("too many pixels")

    monkeypatch.setattr(Image, "open", explode)

    with pytest.raises(ImageProgramError, match="too large"):
        image_runs(b"not decoded", Rect(0, 0, 4, 4))


def test_progressive_off_returns_the_full_program_only():
    programs = image_runs(_logo(), Rect(0, 0, 100, 100), progressive=False)

    assert len(programs) == 1


@pytest.mark.parametrize(
    "data,rect,budget",
    [
        pytest.param(b"", Rect(0, 0, 10, 10), RUN_BUDGET, id="empty bytes"),
        pytest.param(b"not an image", Rect(0, 0, 10, 10), RUN_BUDGET, id="not an image"),
        pytest.param(_logo(), Rect(0, 0, 10, 10), MIN_RUN_BUDGET - 1, id="budget too small"),
        pytest.param(_logo(), Rect(0, 0, 10, 10), MAX_RUN_BUDGET + 1, id="budget too large"),
    ],
)
def test_an_input_that_cannot_be_drawn_raises(data, rect, budget):
    with pytest.raises(ImageProgramError):
        image_runs(data, rect, budget=budget)


def test_a_rect_off_the_display_raises():
    with pytest.raises(ImageProgramError, match="off the display"):
        Rect(-1, 0, 10, 10)


def test_a_one_pixel_image_is_one_run():
    image = Image.new("RGB", (1, 1), (255, 0, 0))

    assert image_runs(_png(image), Rect(5, 5, 1, 1)) == [[f"fill 5,5,1,1,{RED}"]]


def test_noise_is_coarsened_instead_of_truncated():
    """Random pixels can never fit the budget one run each, so the grid grows."""
    rng = random.Random(1234)
    image = Image.new("RGB", (48, 48))
    pixels = image.load()
    assert pixels is not None
    for y in range(48):
        for x in range(48):
            pixels[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))

    (program,) = image_runs(_png(image), Rect(0, 0, 48, 48), budget=60)

    assert 0 < len(program) <= 60


def test_every_run_stays_inside_its_rectangle():
    """A run outside the rect would paint over a widget the caller did not name."""
    rect = Rect(30, 20, 60, 40)

    (program,) = image_runs(_photo(), rect, budget=120)

    for run in program:
        geometry = run.split(" ")[1].split(",")
        x, y, w, h = (int(part) for part in geometry[:4])
        assert rect.x <= x and x + w <= rect.right
        assert rect.y <= y and y + h <= rect.bottom


def test_a_gradient_keeps_the_colours_the_display_can_show():
    """65 536 colours, not a 16-colour poster: the banding was the palette's."""
    image = Image.new("RGB", (64, 1))
    pixels = image.load()
    assert pixels is not None
    for x in range(64):
        # Ten steps over a 16-colour palette would collapse these; RGB565 keeps them.
        pixels[x, 0] = (x * 4, 0, 0)

    (program,) = image_runs(_png(image), Rect(0, 0, 64, 1), budget=MIN_RUN_BUDGET)

    colours = {int(run.rsplit(",", 1)[1]) for run in program}
    assert len(colours) == len(program)


def test_the_top_of_the_range_draws_at_the_displays_own_resolution():
    """The finest cell is one pixel, so a diagonal keeps every pixel of its 40."""
    image = Image.new("RGB", (40, 40), (250, 250, 250))
    drawing = ImageDraw.Draw(image)
    for step in range(40):
        drawing.point((step, step), fill=(0, 0, 255))
    rect = Rect(0, 0, 40, 40)

    (program,), cell = image_plan(_png(image), rect, budget=MAX_RUN_BUDGET)

    assert cell == 1
    # One run per diagonal pixel: a coarser grid averages the line into the field.
    rows = {run.split(" ")[1].split(",")[1] for run in program}
    assert len(rows) == 40


def test_the_top_of_the_range_is_sent_in_slices_the_panel_can_hold():
    """However fine ``quality`` asks for, no slice outgrows the panel."""
    (program,) = image_runs(_photo(), Rect(0, 0, 480, 320), budget=MAX_RUN_BUDGET)

    assert len(program) <= MAX_RUN_BUDGET
    slices = program_slices(program)
    assert len(slices) > 1, "a full-page image at the top of the range needs several calls"
    assert [run for part in slices for run in part] == program
    for part in slices:
        assert program_length(part) <= DRAW_SLICE_CHARS


def test_the_display_size_follows_the_orientation():
    assert display_size(portrait=False) == LANDSCAPE_SIZE
    assert display_size(portrait=True) == PORTRAIT_SIZE


def test_the_plan_reports_the_cell_the_image_is_drawn_in():
    """The service warns from this figure instead of promising a photograph."""
    (_coarse, _full), cell = image_plan(
        _photo(), Rect(0, 0, 480, 320), budget=RUN_BUDGET, progressive=True
    )
    (_only,), fine = image_plan(_photo(), Rect(0, 0, 100, 100), budget=RUN_BUDGET)

    assert cell >= MAX_RECOMMENDED_CELL_PX
    assert fine < MAX_RECOMMENDED_CELL_PX

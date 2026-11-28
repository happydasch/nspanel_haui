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

from custom_components.nspanel_haui.haui.utils.color import rgb_to_rgb565
from custom_components.nspanel_haui.haui.utils.draw_wire import (
    DRAW_SLICE_CHARS,
    program_slices,
)
from custom_components.nspanel_haui.haui.utils.image_program import (
    BACKDROP,
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
    backdrop_run,
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


def _content(program: list[str], rect: Rect, background: int = BLACK) -> list[str]:
    """The runs that paint the picture, without the backdrop fill every pass opens with."""
    assert program[0] == backdrop_run(rect, background), "a pass paints its rectangle first"
    return program[1:]


def test_a_flat_image_becomes_one_run_per_colour_block():
    """A 4x4 of four quadrants: the goldens the firmware and the panel must match."""
    image = Image.new("RGB", (4, 4))
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((0, 0, 1, 1), fill=(255, 0, 0))
    drawing.rectangle((2, 0, 3, 1), fill=(0, 255, 0))
    drawing.rectangle((0, 2, 1, 3), fill=(0, 0, 255))
    drawing.rectangle((2, 2, 3, 3), fill=(255, 255, 255))

    (program,) = image_runs(_png(image), Rect(0, 0, 4, 4), background=BLACK)

    assert _content(program, Rect(0, 0, 4, 4)) == [
        f"fill 0,0,2,2,{RED}",
        f"fill 2,0,2,2,{GREEN}",
        f"fill 0,2,2,2,{BLUE}",
        f"fill 2,2,2,2,{WHITE}",
    ]


def test_the_letterbox_margins_cost_no_run():
    """A 4x2 image in a 4x4 rectangle keeps its aspect: two margins, one run."""
    image = Image.new("RGB", (4, 2), (255, 0, 0))

    (program,) = image_runs(_png(image), Rect(0, 0, 4, 4), background=BLACK)

    assert _content(program, Rect(0, 0, 4, 4)) == [f"fill 0,1,4,2,{RED}"]


def test_an_image_of_the_backdrop_colour_is_the_backdrop_alone():
    """Nothing to paint over it, but the rectangle itself still gets painted."""
    image = Image.new("RGB", (32, 32), (0, 0, 0))

    assert image_runs(_png(image), Rect(0, 0, 32, 32), background=BLACK) == [
        [backdrop_run(Rect(0, 0, 32, 32), BLACK)]
    ]


def test_a_pass_paints_its_whole_rectangle_before_the_image():
    """A skipped cell keeps whatever was on the page, so the area is filled first."""
    image = Image.new("RGB", (8, 4), (255, 0, 0))

    (program,) = image_runs(_png(image), Rect(20, 30, 8, 4), background=WHITE)

    assert program[0] == f"fill 20,30,8,4,{WHITE}"
    assert program[1] == f"fill 20,30,8,4,{RED}"
    # The service draws on black, in one run, before anything else.
    assert backdrop_run(Rect(20, 30, 8, 4), BACKDROP) == "fill 20,30,8,4,0"


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
    (program,) = image_runs(data, rect, background=BLACK)

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
    (program,) = image_runs(data, rect, background=BLACK)
    baseline = _row_baseline(data)

    assert len(program) <= 0.4 * baseline, f"{len(program)} runs vs baseline {baseline}"


def test_neighbouring_colours_within_the_tolerance_become_one_run():
    """Cheap fidelity: a band of near-identical colours is one rectangle."""
    image = Image.new("RGB", (8, 4), (100, 100, 100))
    band = ImageDraw.Draw(image)
    band.rectangle((4, 0, 7, 3), fill=(100 + COLOUR_TOLERANCE - 1, 100, 100))

    (program,) = image_runs(_png(image), Rect(0, 0, 8, 4), background=BLACK)

    assert _content(program, Rect(0, 0, 8, 4)) == [f"fill 0,0,8,4,{rgb_to_rgb565((100, 100, 100))}"]


def test_a_real_difference_is_kept_as_two_runs():
    """The tolerance must not swallow a visible edge."""
    image = Image.new("RGB", (8, 4), (100, 100, 100))
    edge = ImageDraw.Draw(image)
    edge.rectangle((4, 0, 7, 3), fill=(100 + COLOUR_TOLERANCE + 20, 100, 100))

    (program,) = image_runs(_png(image), Rect(0, 0, 8, 4), background=BLACK)

    assert len(_content(program, Rect(0, 0, 8, 4))) == 2


def test_the_progressive_pass_is_coarse_first_and_within_its_own_budget():
    """Pass one appears in ~0.12 s; pass two refines the same rectangle."""
    coarse, full = image_runs(_logo(), Rect(0, 0, 200, 150), background=BLACK, progressive=True)

    assert 0 < len(coarse) <= PROGRESSIVE_RUNS
    assert len(full) > len(coarse)
    # The coarse pass clears the rectangle; the full pass paints over it, and
    # must not clear again or the finished picture would blink out first.
    assert coarse[0] == backdrop_run(Rect(0, 0, 200, 150), BLACK)
    assert full[0] != backdrop_run(Rect(0, 0, 200, 150), BLACK)
    assert all(run.startswith("fill ") for run in [*coarse, *full])


def test_progressive_off_returns_the_full_program_only():
    programs = image_runs(_logo(), Rect(0, 0, 100, 100), background=BLACK, progressive=False)

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
        image_runs(data, rect, background=BLACK, budget=budget)


def test_a_rect_off_the_display_raises():
    with pytest.raises(ImageProgramError, match="off the display"):
        Rect(-1, 0, 10, 10)


def test_a_one_pixel_image_is_one_run():
    image = Image.new("RGB", (1, 1), (255, 0, 0))

    assert image_runs(_png(image), Rect(5, 5, 1, 1), background=BLACK) == [
        [f"fill 5,5,1,1,{BLACK}", f"fill 5,5,1,1,{RED}"]
    ]


def test_noise_is_coarsened_instead_of_truncated():
    """Random pixels can never fit the budget one run each, so the grid grows."""
    rng = random.Random(1234)
    image = Image.new("RGB", (48, 48))
    pixels = image.load()
    assert pixels is not None
    for y in range(48):
        for x in range(48):
            pixels[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))

    (program,) = image_runs(_png(image), Rect(0, 0, 48, 48), background=BLACK, budget=60)

    assert 0 < len(program) <= 60


def test_every_run_stays_inside_its_rectangle():
    """A run outside the rect would paint over a widget the caller did not name."""
    rect = Rect(30, 20, 60, 40)

    (program,) = image_runs(_photo(), rect, background=BLACK, budget=120)

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

    (program,) = image_runs(_png(image), Rect(0, 0, 64, 1), background=BLACK, budget=MIN_RUN_BUDGET)

    colours = {int(run.rsplit(",", 1)[1]) for run in program}
    assert len(colours) == len(program)


def test_the_top_of_the_range_draws_at_the_displays_own_resolution():
    """The finest cell is one pixel, so a diagonal keeps every pixel of its 40."""
    image = Image.new("RGB", (40, 40), (250, 250, 250))
    drawing = ImageDraw.Draw(image)
    for step in range(40):
        drawing.point((step, step), fill=(0, 0, 255))
    data = _png(image)

    def rows(budget: int) -> set[str]:
        (program,) = image_runs(data, Rect(0, 0, 40, 40), background=BLACK, budget=budget)
        return {run.split(" ")[1].split(",")[1] for run in program}

    # One row per cell: a coarse grid averages the diagonal away.
    assert len(rows(MAX_RUN_BUDGET)) == 40
    assert len(rows(MIN_RUN_BUDGET)) < 40


def test_the_top_of_the_range_is_sent_in_slices_the_panel_can_hold():
    """However fine ``quality`` asks for, no slice outgrows the panel."""
    (program,) = image_runs(_photo(), Rect(0, 0, 480, 320), background=BLACK, budget=MAX_RUN_BUDGET)

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
        _photo(), Rect(0, 0, 480, 320), background=BLACK, budget=MIN_RUN_BUDGET, progressive=True
    )
    (_only,), fine = image_plan(_photo(), Rect(0, 0, 100, 100), background=BLACK, budget=RUN_BUDGET)

    assert cell >= MAX_RECOMMENDED_CELL_PX
    assert fine < MAX_RECOMMENDED_CELL_PX

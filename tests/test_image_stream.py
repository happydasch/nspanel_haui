"""The delta planner: what a camera stream actually sends to the panel.

These tests drive the planner the way a stream does - a sequence of frames - and
assert the properties the feature rests on: an idle camera sends nothing, a moving
subject costs runs proportional to what moved, noise and flicker inside the dead
band never reach the display, and a frame over the budget makes the picture
coarser instead of slower.
"""

from __future__ import annotations

import math
import random

import pytest
from PIL import Image, ImageDraw

from custom_components.nspanel_haui.haui.utils.color import rgb_to_rgb565
from custom_components.nspanel_haui.haui.utils.image_program import Rect, fit_image
from custom_components.nspanel_haui.haui.utils.image_stream import (
    DEFAULT_CELL_PX,
    DEFAULT_FRAME_RUNS,
    FIRST_FRAME_RUNS,
    MAX_CELL_PX,
    MIN_CELL_PX,
    MIN_FRAME_RUNS,
    DeltaPlanner,
    ImageStreamError,
)

RECT = Rect(0, 0, 240, 160)
SRC = (480, 320)


def _scene(subject_x: int = 100, subject_y: int = 160, flicker: float = 0.0) -> Image.Image:
    """A room with one person in it: textured wall, flat floor, a subject to move."""
    rnd = random.Random(7)
    wall = Image.new("RGB", (24, 18))
    wall.putdata(
        [
            (rnd.randrange(80, 150), rnd.randrange(90, 140), rnd.randrange(100, 160))
            for _ in range(24 * 18)
        ]
    )
    image = wall.resize(SRC, Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 260, SRC[0], SRC[1]], fill=(60, 60, 64))
    draw.rectangle(
        [subject_x - 20, subject_y - 20, subject_x + 20, subject_y + 90], fill=(50, 70, 120)
    )
    if flicker:
        pixels = image.load()
        for y in range(SRC[1]):
            for x in range(SRC[0]):
                red, green, blue = pixels[x, y]
                pixels[x, y] = (
                    min(255, int(red * (1 + flicker))),
                    min(255, int(green * (1 + flicker))),
                    min(255, int(blue * (1 + flicker))),
                )
    return image


def _noisy(image: Image.Image, sigma: float, seed: int) -> Image.Image:
    """Add sensor noise: what makes frame-to-frame diffing unusable."""
    rnd = random.Random(seed)
    noisy = image.copy()
    pixels = noisy.load()
    for y in range(0, SRC[1]):
        for x in range(0, SRC[0]):
            red, green, blue = pixels[x, y]
            shift = rnd.gauss(0, sigma)
            pixels[x, y] = (
                max(0, min(255, int(red + shift))),
                max(0, min(255, int(green + shift))),
                max(0, min(255, int(blue + shift))),
            )
    return noisy


def test_the_first_frame_paints_the_rectangle_and_an_identical_one_sends_nothing():
    """A stream starts with a still image and then costs nothing while nothing moves."""
    planner = DeltaPlanner(RECT, refresh_every=0)

    first = planner.plan(_scene())

    assert planner.full_paints == 1
    assert first, "the first frame has to paint something"
    assert first[0] == f"fill {RECT.x},{RECT.y},{RECT.w},{RECT.h},{first[0].split(',')[4]}"
    assert planner.plan(_scene()) == []


def test_a_moving_subject_costs_runs_for_its_edges_not_the_whole_rectangle():
    """What moves is painted; the flat interior that did not move is not."""
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    planner.plan(_scene(subject_x=100))

    moved = planner.plan(_scene(subject_x=116))

    house = math.ceil(RECT.w / planner.cell) * math.ceil(RECT.h / planner.cell)
    assert moved, "a subject that walked 16 px must be repainted somewhere"
    assert len(moved) < house // 4, f"{len(moved)} runs for a 16 px move is not a delta"


def test_noise_and_flicker_inside_the_dead_band_never_reach_the_display():
    """The whole point of the painted model: jitter is not a change."""
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    planner.plan(_scene())

    jittered = planner.plan(_noisy(_scene(flicker=0.02), sigma=4, seed=1))

    assert len(jittered) <= 4, f"{len(jittered)} runs for a flickering, noisy subject"


def test_a_frame_over_the_budget_is_replanned_coarser_before_it_is_sent():
    """A stream never spends more than its budget; it loses detail instead."""
    planner = DeltaPlanner(RECT, cell=4, max_runs=300, first_runs=300, refresh_every=0)

    runs = planner.plan(_scene())

    assert planner.cell > 4, "a frame over the budget has to be replanned coarser"
    assert len(runs) <= 300 or planner.cell == MAX_CELL_PX
    assert runs[0].startswith(f"fill {RECT.x},{RECT.y},{RECT.w},{RECT.h},"), (
        "the replanned frame is still one full paint, not a fine one plus a repaint"
    )
    assert planner.full_paints == 1


def test_an_update_never_exceeds_its_own_budget():
    """A delta is what has to be cheap; the full paint that showed the picture is not."""
    planner = DeltaPlanner(RECT, cell=2, max_runs=120, refresh_every=0)

    for step in range(6):
        before = planner.full_paints
        runs = planner.plan(_noisy(_scene(subject_x=100 + step * 12), sigma=20, seed=step))
        budget = planner.first_runs if planner.full_paints > before else planner.max_runs
        assert len(runs) <= budget or planner.cell == MAX_CELL_PX, (
            f"frame {step}: {len(runs)} runs at cell {planner.cell}, budget {budget}"
        )


def test_an_idle_camera_keeps_its_cell_size_and_stops_sending():
    """Nothing to sharpen means nothing to repaint, so the resolution settles."""
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    planner.plan(_scene())
    settled = planner.cell

    for _ in range(6):
        assert planner.plan(_scene()) == []

    assert planner.cell == settled
    assert planner.full_paints == 1


def test_a_full_repaint_comes_round_on_its_own_so_band_error_cannot_accumulate():
    """A slowly darkening wall crosses no dead band, so it is washed out eventually."""
    planner = DeltaPlanner(RECT, cell=8, refresh_every=2)
    planner.plan(_scene())
    assert planner.full_paints == 1

    for step in range(1, 5):
        planner.plan(_scene(flicker=step / 200))

    assert planner.full_paints >= 2, "the periodic refresh never came round"


def test_a_repaint_paints_the_whole_rectangle_again():
    """A picture the panel may no longer show is not left to the deltas.

    The clear is what only a full paint sends, and a stream never sends one by
    itself: without this, anything that painted over the rectangle - a page's own
    widgets, a pass the panel dropped - left the deltas composing on top of it.
    """
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    first = planner.plan(_scene())
    assert planner.plan(_scene()) == [], "nothing moved, so nothing is sent"

    planner.repaint()
    again = planner.plan(_scene())

    assert again[0] == first[0], "the same clear covers the same rectangle"
    assert again[0].startswith(f"fill {RECT.x},{RECT.y},{RECT.w},{RECT.h},")
    assert planner.full_paints == 2
    assert planner.plan(_scene()) == [], "and the picture is current again"


def test_a_repaint_during_startup_repeats_the_current_layer():
    """A pass that failed mid-startup is painted again, at the same coarseness.

    Jumping to the full-detail picture would be the slowest paint there is, on a
    panel that has just shown it cannot keep up with a coarse one.
    """
    image = _scene()
    planner = DeltaPlanner(RECT, cell=4, min_cell=4, refresh_every=0, progressive=True)
    first = planner.plan(image)
    assert planner.starting_up

    planner.repaint()
    repeated = planner.plan(image)

    assert planner.starting_up, "the coarse layer is being painted again"
    assert repeated == first, "the layer that was not acknowledged, sent again"


def _coverage(runs: list[str], rect: Rect) -> Image.Image:
    """Every pixel of ``rect`` the program paints, in the order it paints them."""
    mask = Image.new("L", (rect.w, rect.h), 0)  # the page, before the program
    draw = ImageDraw.Draw(mask)
    for run in runs:
        x, y, width, height, _colour = (int(field) for field in run[len("fill ") :].split(","))
        draw.rectangle(
            [x - rect.x, y - rect.y, x - rect.x + width - 1, y - rect.y + height - 1], fill=1
        )
    return mask


@pytest.mark.parametrize("rect", [Rect(0, 52, 480, 268), Rect(0, 52, 320, 428)])
def test_progressive_start_covers_the_panel_and_keeps_the_requested_detail(rect):
    image = _scene()
    settings = dict(cell=4, min_cell=4, refresh_every=0, cover=True)
    planner = DeltaPlanner(rect, **settings, progressive=True)
    normal = DeltaPlanner(rect, **settings)

    first = planner.plan(image)
    backdrop = f"fill {rect.x},{rect.y},{rect.w},{rect.h},"
    assert first[0].startswith(backdrop)
    short_passes = [first]
    while planner.starting_up:
        short_passes.append(planner.plan(image))

    assert len(short_passes) == 4
    counts = [len(runs) for runs in short_passes]
    assert counts == sorted(set(counts)), "each layer adds detail"
    assert counts[0] < counts[-1] / 10
    for runs in short_passes[1:]:
        assert not runs[0].startswith(backdrop), "refine over the existing image"
        assert _coverage(runs, rect).getextrema() == (1, 1)

    def painted(runs):
        pixels = Image.new("I", (rect.w, rect.h))
        draw = ImageDraw.Draw(pixels)
        for run in runs:
            x, y, w, h, colour = map(int, run.removeprefix("fill ").split(","))
            draw.rectangle((x - rect.x, y - rect.y, x - rect.x + w - 1, y - rect.y + h - 1), colour)
        return pixels.tobytes()

    assert painted(short_passes[-1]) == painted(normal.plan(image))
    assert planner.plan(image) == []


def test_a_full_paint_leaves_no_pixel_of_the_rectangle_unpainted():
    """The picture is the whole area, background included - what a delta needs.

    A frame that showed only the cells it thought had changed would leave the
    page's own background showing through wherever it did not paint, so a full
    paint has to cover every pixel: the clear first, the blocks over it.
    """
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)

    first = planner.plan(_scene())
    planner.repaint()
    again = planner.plan(_scene(subject_x=140))

    for runs, where in ((first, "the first frame"), (again, "a repaint")):
        assert _coverage(runs, RECT).getextrema() == (1, 1), f"{where} left a gap"


def test_every_painted_run_is_inside_the_rectangle_and_ordered_top_to_bottom():
    """A program must not paint outside its rectangle, and reads as a scan."""
    planner = DeltaPlanner(Rect(16, 8, 120, 80), cell=6, refresh_every=0)
    runs = planner.plan(_scene())

    tops = []
    for run in runs:
        x, y, width, height, _colour = (int(field) for field in run[len("fill ") :].split(","))
        assert x >= 16 and y >= 8
        assert x + width <= 136 and y + height <= 88
        tops.append(y)

    assert tops == sorted(tops)


def test_a_painted_run_carries_the_display_colour_of_the_cell():
    """The wire wants RGB565: the value a fill instruction carries on the panel."""
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    image = Image.new("RGB", SRC, (255, 0, 0))

    runs = planner.plan(image)

    assert len(runs) == 1
    assert runs[0].endswith(f",{rgb_to_rgb565((255, 0, 0))}")


@pytest.mark.parametrize("cell", [MIN_CELL_PX - 5, MIN_CELL_PX, DEFAULT_CELL_PX, 999])
def test_the_cell_size_is_clamped_instead_of_refused(cell):
    """A caller that asks for an unusable detail level gets the nearest usable one."""
    planner = DeltaPlanner(RECT, cell=cell)

    assert MIN_CELL_PX <= planner.cell <= MAX_CELL_PX


def _dot(x: int) -> Image.Image:
    """A picture that changes in one small place: cheap enough to sharpen on."""
    image = Image.new("RGB", (240, 160), (30, 40, 50))
    ImageDraw.Draw(image).rectangle([x, 40, x + 12, 52], fill=(240, 240, 240))
    return image


def test_a_pinned_density_is_the_finest_the_picture_gets():
    """A quality pins its density: the picture never sharpens past what was asked.

    Sharpening throws the painted model away and costs a full paint, so a stream
    asked for a coarse picture must not spend that on detail nobody chose. The
    service's ``cell`` is a starting point; a panel's quality is not.
    """
    planner = DeltaPlanner(
        RECT, cell=6, min_cell=6, max_runs=DEFAULT_FRAME_RUNS, first_runs=FIRST_FRAME_RUNS
    )

    for x in range(0, 40, 2):
        planner.plan(_dot(x))

    assert planner.cell == 6


def test_a_stream_that_chose_its_own_density_sharpens_while_it_is_cheap():
    """Without a pinned density the stream finds the detail the budget allows."""
    planner = DeltaPlanner(RECT, cell=6, max_runs=DEFAULT_FRAME_RUNS, first_runs=FIRST_FRAME_RUNS)

    for x in range(0, 40, 2):
        planner.plan(_dot(x))

    assert planner.cell < 6, "a calm scene is painted finer than it started"
    assert planner.cell >= MIN_CELL_PX


def test_a_finer_grid_that_cannot_fit_keeps_the_current_picture():
    """A cheap moving patch must not send the unchanged background over and over."""
    rect = Rect(0, 0, 96, 64)
    background = Image.new("RGB", (96, 64))
    for y in range(0, 64, 4):
        for x in range(0, 96, 4):
            ImageDraw.Draw(background).rectangle(
                (x, y, x + 3, y + 3),
                fill=((41 * x + 17 * y) % 256, (23 * x + 43 * y) % 256, 112),
            )
    planner = DeltaPlanner(rect, cell=8, min_cell=7, max_runs=64, first_runs=110, refresh_every=0)
    planner.plan(background)

    for x in range(0, 80, 8):
        frame = background.copy()
        ImageDraw.Draw(frame).rectangle((x, 24, x + 7, 31), fill="white")
        assert 0 < len(planner.plan(frame)) <= 4, "send the patch, not a full repaint"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"band": -1}, "dead band"),
        ({"band": 256}, "dead band"),
        ({"max_runs": MIN_FRAME_RUNS - 1}, "runs a frame"),
        ({"max_runs": 100_000}, "runs a frame"),
        ({"max_runs": 800, "first_runs": 400}, "runs a full paint"),
        ({"refresh_every": -1}, "refresh_every"),
    ],
)
def test_an_impossible_setting_is_refused_by_name(kwargs, message):
    """A settings mistake fails where it is made, not as a wrong picture."""
    with pytest.raises(ImageStreamError, match=message):
        DeltaPlanner(RECT, **kwargs)


def test_the_defaults_are_one_frame_of_a_full_page_rectangle():
    """The defaults have to be sendable in one draw without tuning."""
    planner = DeltaPlanner(Rect(0, 0, 480, 320))

    assert planner.cell == DEFAULT_CELL_PX
    assert planner.max_runs == DEFAULT_FRAME_RUNS
    assert planner.first_runs > planner.max_runs, "the picture gets the larger budget"


def test_a_full_paint_spends_more_than_an_update_so_the_picture_is_sharp():
    """The picture's detail comes from the frame that shows it, not from a delta."""
    rect = Rect(0, 0, 480, 268)
    sharp = DeltaPlanner(rect, cell=3, max_runs=400, first_runs=FIRST_FRAME_RUNS)
    thrifty = DeltaPlanner(rect, cell=3, max_runs=400, first_runs=400)

    runs = sharp.plan(_scene())
    thrifty.plan(_scene())

    assert len(runs) > thrifty.max_runs, "more than an update may cost - it is the picture"
    assert len(runs) <= FIRST_FRAME_RUNS
    assert sharp.cell < thrifty.cell, "the larger budget keeps the finer picture"


def test_a_cropped_frame_fills_the_rectangle_instead_of_banding_it():
    """A landscape frame in a tall area: crop to the picture, do not paint bands."""
    rect = Rect(0, 0, 120, 200)
    frame = Image.new("RGB", (320, 180), (0, 0, 200))
    ImageDraw.Draw(frame).rectangle([0, 0, 9, 179], fill=(255, 0, 0))

    covered, _ = fit_image(frame, rect, cover=True)
    letterboxed, _ = fit_image(frame, rect, cover=False)

    def reds(image: Image.Image) -> int:
        red, green, _blue = image.split()
        return sum(
            1 for r, g in zip(red.tobytes(), green.tobytes(), strict=True) if r > 200 and g < 60
        )

    assert covered.size == (rect.w, rect.h)
    assert reds(covered) == 0, "the crop takes the picture's middle as the whole area"
    assert reds(letterboxed) > 0, "the letterbox keeps the picture's full width"


def test_a_clone_plans_without_touching_the_planner_it_came_from():
    """A frame is planned on a copy, so the worker's planner is not written off it.

    Planning runs in the executor while the worker may repaint or replace the
    planner; the copy is what a clone is for, and it must share nothing planning
    writes.
    """
    planner = DeltaPlanner(RECT, cell=8, refresh_every=0)
    planner.plan(_scene())

    copy = planner.clone()
    copy.plan(_scene(subject_x=170))
    copy.repaint()

    assert planner._painted != copy._painted, "the copy moved on its own"
    assert not planner._repaint, "and a repaint asked of the copy is not the original's"
    assert planner.frames + 1 == copy.frames


def test_a_refinement_waits_before_sharpening_again():
    """Two whole paints within a few frames is a visible flash, so a refine buys a pause.

    A scene that keeps a cheap patch moving produced exactly that: cell 4 to cell 2
    within a handful of frames, two full repaints, for detail nobody had time to
    see. Sharpening has to wait for a pause of its own.
    """
    planner = DeltaPlanner(RECT, cell=4, min_cell=MIN_CELL_PX, refresh_every=0)
    planner.plan(_scene())
    paints: list[int] = []
    for step, x in enumerate(range(0, 80, 2)):
        before = planner.full_paints
        planner.plan(_dot(x))
        if planner.full_paints > before:
            paints.append(step)

    assert len(paints) > 1, f"the fixture has to sharpen twice to mean anything ({paints})"
    assert all(later - earlier >= 5 for earlier, later in zip(paints, paints[1:], strict=False)), (
        f"refinements at frames {paints} are back to back"
    )


def test_the_stream_merge_never_mixes_two_display_colours():
    """The stream's merge is exact, and that is what keeps its model true.

    It is a separate function from ``image_program._spans`` on purpose: a still
    image may merge neighbours within a colour tolerance because it is painted
    once, while a span here that carried a colour its cells do not have would make
    the model the next frame compares against drift from the display by that
    tolerance, every frame.
    """
    from custom_components.nspanel_haui.haui.utils.image_stream import _merged

    rnd = random.Random(11)
    grid = [[rgb_to_rgb565((rnd.randrange(0, 40, 8), 32, 64)) for _ in range(9)] for _ in range(6)]

    spans = _merged(grid)

    assert spans, "the fixture has to merge into something"
    for span in spans:
        for row in range(span.y, span.y + span.h):
            for col in range(span.x, span.x + span.w):
                assert grid[row][col] == span.rgb565, (
                    f"the span at ({span.x}, {span.y}) paints {span.rgb565} over {grid[row][col]}"
                )

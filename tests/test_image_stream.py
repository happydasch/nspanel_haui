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
from custom_components.nspanel_haui.haui.utils.image_program import Rect
from custom_components.nspanel_haui.haui.utils.image_stream import (
    DEFAULT_CELL_PX,
    DEFAULT_FRAME_RUNS,
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
    planner = DeltaPlanner(RECT, cell=4, max_runs=300, refresh_every=0)

    runs = planner.plan(_scene())

    assert planner.cell > 4, "a frame over the budget has to be replanned coarser"
    assert len(runs) <= 300 or planner.cell == MAX_CELL_PX
    assert runs[0].startswith(f"fill {RECT.x},{RECT.y},{RECT.w},{RECT.h},"), (
        "the replanned frame is still one full paint, not a fine one plus a repaint"
    )
    assert planner.full_paints == 1


def test_no_program_ever_exceeds_the_budget_before_the_cell_is_as_coarse_as_it_goes():
    """The budget holds for every frame of a busy sequence, not just the first."""
    planner = DeltaPlanner(RECT, cell=2, max_runs=120, refresh_every=0)

    for step in range(6):
        runs = planner.plan(_noisy(_scene(subject_x=100 + step * 12), sigma=20, seed=step))
        assert len(runs) <= 120 or planner.cell == MAX_CELL_PX, (
            f"frame {step}: {len(runs)} runs at cell {planner.cell}"
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


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"band": -1}, "dead band"),
        ({"band": 256}, "dead band"),
        ({"max_runs": MIN_FRAME_RUNS - 1}, "runs a frame"),
        ({"max_runs": 100_000}, "runs a frame"),
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

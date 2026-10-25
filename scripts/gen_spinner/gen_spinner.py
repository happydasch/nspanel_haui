"""Render the spinner sprite sheets the system page animates.

The system page shows a Material-style indeterminate circular progress
indicator (``hSpinner``, 140 x 140) over the ``system`` background. The
display cannot blend, so every frame is drawn onto the crop of the system
background tile at the spinner's position, per orientation:

* landscape: ``nextion/images/bkg/landscape/system.png`` at (155, 80)
* portrait:  ``nextion/images/bkg/portrait/system.png`` at (90, 135)

The 60 frames go into two 1400 x 420 sheets of 3 x 10 frames (pictures 10
and 11 in the HMI; the page's timer shows frames 0..29 from the first sheet
and 30..59 from the second), written to ``nextion/images/spinner_<orientation>_1.png``
and ``_2.png``. Re-run after changing the ``system`` background tile or the
spinner position.

Based on
https://github.com/material-components/material-components-android/tree/master/lib/java/com/google/android/material/progressindicator

Usage::

    python scripts/gen_spinner/gen_spinner.py [landscape|portrait ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BKG_DIR = ROOT / "nextion" / "images" / "bkg"
OUT_DIR = ROOT / "nextion" / "images"

# spinner position on the system page per orientation
POSITIONS = {
    "landscape": (155, 80),
    "portrait": (90, 135),
}

# Constants for animation timing.
TOTAL_CYCLES = 4
TOTAL_DURATION_IN_MS = 5400
DURATION_TO_EXPAND_IN_MS = 667
DURATION_TO_COLLAPSE_IN_MS = 667
DELAY_TO_EXPAND_IN_MS = [0, 1350, 2700, 4050]
DELAY_TO_COLLAPSE_IN_MS = [667, 2017, 3367, 4717]
DELAY_TO_FADE_IN_MS = [1000, 2350, 3700, 5050]

# Constants for animation values.
TAIL_DEGREES_OFFSET = -20
EXTRA_DEGREES_PER_CYCLE = 270
CONSTANT_ROTATION_DEGREES = 1520

FRAME_SIZE = 140
ARC_RADIUS = 60
ARC_WIDTH = 6
ARC_COLOR = (75, 166, 238)  # component_active
NUM_FRAMES = 60
FRAMES_PER_ROW = 10
ROWS_PER_SHEET = 3
ROTATION = -90


def get_fraction_in_range(playtime, start, duration):
    return (playtime - start) / duration


def fast_out_slow_in(x):
    # fast_out_slow_in values
    VALUES = [
        0.0000,
        0.0001,
        0.0002,
        0.0005,
        0.0009,
        0.0014,
        0.0020,
        0.0027,
        0.0036,
        0.0046,
        0.0058,
        0.0071,
        0.0085,
        0.0101,
        0.0118,
        0.0137,
        0.0158,
        0.0180,
        0.0205,
        0.0231,
        0.0259,
        0.0289,
        0.0321,
        0.0355,
        0.0391,
        0.0430,
        0.0471,
        0.0514,
        0.0560,
        0.0608,
        0.0660,
        0.0714,
        0.0771,
        0.0830,
        0.0893,
        0.0959,
        0.1029,
        0.1101,
        0.1177,
        0.1257,
        0.1339,
        0.1426,
        0.1516,
        0.1610,
        0.1707,
        0.1808,
        0.1913,
        0.2021,
        0.2133,
        0.2248,
        0.2366,
        0.2487,
        0.2611,
        0.2738,
        0.2867,
        0.2998,
        0.3131,
        0.3265,
        0.3400,
        0.3536,
        0.3673,
        0.3810,
        0.3946,
        0.4082,
        0.4217,
        0.4352,
        0.4485,
        0.4616,
        0.4746,
        0.4874,
        0.5000,
        0.5124,
        0.5246,
        0.5365,
        0.5482,
        0.5597,
        0.5710,
        0.5820,
        0.5928,
        0.6033,
        0.6136,
        0.6237,
        0.6335,
        0.6431,
        0.6525,
        0.6616,
        0.6706,
        0.6793,
        0.6878,
        0.6961,
        0.7043,
        0.7122,
        0.7199,
        0.7275,
        0.7349,
        0.7421,
        0.7491,
        0.7559,
        0.7626,
        0.7692,
        0.7756,
        0.7818,
        0.7879,
        0.7938,
        0.7996,
        0.8053,
        0.8108,
        0.8162,
        0.8215,
        0.8266,
        0.8317,
        0.8366,
        0.8414,
        0.8461,
        0.8507,
        0.8551,
        0.8595,
        0.8638,
        0.8679,
        0.8720,
        0.8760,
        0.8798,
        0.8836,
        0.8873,
        0.8909,
        0.8945,
        0.8979,
        0.9013,
        0.9046,
        0.9078,
        0.9109,
        0.9139,
        0.9169,
        0.9198,
        0.9227,
        0.9254,
        0.9281,
        0.9307,
        0.9333,
        0.9358,
        0.9382,
        0.9406,
        0.9429,
        0.9452,
        0.9474,
        0.9495,
        0.9516,
        0.9536,
        0.9556,
        0.9575,
        0.9594,
        0.9612,
        0.9629,
        0.9646,
        0.9663,
        0.9679,
        0.9695,
        0.9710,
        0.9725,
        0.9739,
        0.9753,
        0.9766,
        0.9779,
        0.9791,
        0.9803,
        0.9815,
        0.9826,
        0.9837,
        0.9848,
        0.9858,
        0.9867,
        0.9877,
        0.9885,
        0.9894,
        0.9902,
        0.9910,
        0.9917,
        0.9924,
        0.9931,
        0.9937,
        0.9944,
        0.9949,
        0.9955,
        0.9960,
        0.9964,
        0.9969,
        0.9973,
        0.9977,
        0.9980,
        0.9984,
        0.9986,
        0.9989,
        0.9991,
        0.9993,
        0.9995,
        0.9997,
        0.9998,
        0.9999,
        0.9999,
        1.0000,
        1.0000,
    ]
    step_size = 1 / (len(VALUES) - 1)
    if x <= 0:
        return 0
    elif x >= 1:
        return 1
    position = min(x * (len(VALUES) - 1), len(VALUES) - 2)
    quantized = position * step_size
    diff = x - quantized
    weight = diff / step_size
    return VALUES[int(position)] + weight * (VALUES[int(position + 1)] - VALUES[int(position)])


def segment_positions(frame: int) -> tuple[float, float]:
    """Start and end angle of the arc in ``frame``."""
    playtime = (TOTAL_DURATION_IN_MS / NUM_FRAMES) * frame
    animation_fraction = (1 / TOTAL_DURATION_IN_MS) * (TOTAL_DURATION_IN_MS / NUM_FRAMES)
    end_fraction = fast_out_slow_in(animation_fraction * frame - TOTAL_DURATION_IN_MS)
    # constant rotation
    tail = CONSTANT_ROTATION_DEGREES * animation_fraction + TAIL_DEGREES_OFFSET
    head = CONSTANT_ROTATION_DEGREES * animation_fraction
    # cycle specific rotation
    for cycle_index in range(TOTAL_CYCLES):
        fraction = get_fraction_in_range(
            playtime, DELAY_TO_EXPAND_IN_MS[cycle_index], DURATION_TO_EXPAND_IN_MS
        )
        head += fast_out_slow_in(fraction) * EXTRA_DEGREES_PER_CYCLE
        fraction = get_fraction_in_range(
            playtime, DELAY_TO_COLLAPSE_IN_MS[cycle_index], DURATION_TO_COLLAPSE_IN_MS
        )
        tail += fast_out_slow_in(fraction) * EXTRA_DEGREES_PER_CYCLE
    # closes the gap between head and tail for the complete end
    tail += (head - tail) * end_fraction
    return (tail + ROTATION) % 360, (head + ROTATION) % 360


def draw_frame(background: Image.Image, frame: int) -> Image.Image:
    im = background.copy()
    c = FRAME_SIZE / 2
    start, end = segment_positions(frame)
    ImageDraw.Draw(im).arc(
        (
            c - ARC_RADIUS - ARC_WIDTH / 2,
            c - ARC_RADIUS - ARC_WIDTH / 2,
            c + ARC_RADIUS + ARC_WIDTH / 2,
            c + ARC_RADIUS + ARC_WIDTH / 2,
        ),
        start,
        end,
        fill=ARC_COLOR,
        width=ARC_WIDTH,
    )
    return im


def render(orientation: str) -> None:
    x, y = POSITIONS[orientation]
    tile = Image.open(BKG_DIR / orientation / "system.png").convert("RGB")
    background = tile.crop((x, y, x + FRAME_SIZE, y + FRAME_SIZE))
    per_sheet = FRAMES_PER_ROW * ROWS_PER_SHEET
    for sheet_no in range(NUM_FRAMES // per_sheet):
        sheet = Image.new("RGB", (FRAMES_PER_ROW * FRAME_SIZE, ROWS_PER_SHEET * FRAME_SIZE))
        for i in range(per_sheet):
            frame = draw_frame(background, sheet_no * per_sheet + i)
            sheet.paste(
                frame, ((i % FRAMES_PER_ROW) * FRAME_SIZE, (i // FRAMES_PER_ROW) * FRAME_SIZE)
            )
        out = OUT_DIR / f"spinner_{orientation}_{sheet_no + 1}.png"
        sheet.save(out, optimize=True)
        print(f"{out.relative_to(ROOT)}  {sheet.size[0]}x{sheet.size[1]}")


def main() -> None:
    names = sys.argv[1:] or list(POSITIONS)
    unknown = [n for n in names if n not in POSITIONS]
    if unknown:
        raise SystemExit(f"unknown orientation {unknown}; choose from {list(POSITIONS)}")
    for name in names:
        render(name)


if __name__ == "__main__":
    main()

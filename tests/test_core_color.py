"""haui/utils/color.py behaviour not covered by test_color.py."""

from __future__ import annotations

import random

from nspanel_haui.haui.utils.color import generate_color_palette


def test_palette_generation_leaves_global_rng_alone() -> None:
    random.seed(42)
    expected = random.random()

    random.seed(42)
    generate_color_palette((10, 20, 30), "vibrant", seed=5)
    generate_color_palette((10, 20, 30), "pastel")

    assert random.random() == expected


def test_palette_is_reproducible_for_a_seed() -> None:
    first = generate_color_palette((10, 20, 30), "vibrant", seed=938)
    second = generate_color_palette((10, 20, 30), "vibrant", seed=938)

    assert first == second

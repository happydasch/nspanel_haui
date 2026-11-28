"""The draw program's wire format: the hub packs, the panel unpacks (image.yaml)."""

from __future__ import annotations

import pytest

from custom_components.nspanel_haui.haui.utils.draw_wire import (
    DRAW_SLICE_CHARS,
    DrawWireError,
    base36,
    pack_program,
    pack_run,
    parse_base36,
    program_slices,
    unpack_run,
)


def test_a_run_costs_a_third_less_on_the_wire_than_its_display_command() -> None:
    """The panel decodes five base-36 numbers instead of reading a fill command."""
    run = "fill 120,64,8,8,65535"

    assert pack_run(run) == "3c,1s,8,8,1ekf"
    assert len(pack_run(run)) < len(run) * 0.7


@pytest.mark.parametrize(
    "value,text",
    [
        pytest.param(0, "0", id="zero"),
        pytest.param(9, "9", id="last digit"),
        pytest.param(10, "a", id="first letter"),
        pytest.param(120, "3c", id="a coordinate"),
        pytest.param(65535, "1ekf", id="a whole RGB565 colour"),
    ],
)
def test_base36_round_trips(value: int, text: str) -> None:
    assert base36(value) == text
    assert parse_base36(text) == value
    assert parse_base36(text.upper()) == value


def test_every_run_survives_the_round_trip() -> None:
    """The C++ decoder in image.yaml mirrors this; the panel must get the run back."""
    runs = [
        "fill 0,0,1,1,0",
        "fill 479,319,1,1,65535",
        "fill 480,320,480,320,65535",
        "fill 5,5,1,1,4226",
    ]

    assert [unpack_run(pack_run(run)) for run in runs] == runs


@pytest.mark.parametrize(
    "run",
    [
        pytest.param("cirs 10,10,6,0", id="not a fill"),
        pytest.param("fill 1,2,3,4", id="four numbers"),
        pytest.param("fill 1,2,3,4,5,6", id="six numbers"),
        pytest.param("fill 1,2,3,4,-5", id="negative"),
        pytest.param("fill 1,2,3,x,5", id="not a number"),
    ],
)
def test_a_run_the_panel_could_not_draw_is_refused_here(run: str) -> None:
    with pytest.raises(DrawWireError):
        pack_run(run)


def test_a_program_joins_its_runs_with_semicolons() -> None:
    assert pack_program(["fill 1,2,3,4,5", "fill 6,7,8,9,10"]) == "1,2,3,4,5;6,7,8,9,a"


def test_a_pass_is_cut_into_slices_the_panel_can_stage() -> None:
    """Keep RAM flat: one slice in the panel at a time, in painting order."""
    runs = [f"fill {index % 480},{index % 320},8,8,65535" for index in range(2000)]

    slices = program_slices(runs)

    assert len(slices) > 1
    assert [run for part in slices for run in part] == runs
    for part in slices:
        assert 0 < len(pack_program(part)) <= DRAW_SLICE_CHARS


def test_a_slice_is_never_empty_and_a_short_pass_is_one_slice() -> None:
    assert program_slices([]) == []
    assert program_slices(["fill 1,2,3,4,5"]) == [["fill 1,2,3,4,5"]]


def test_a_run_longer_than_a_slice_is_refused() -> None:
    """A run cannot be split across two calls, so it fails instead of truncating."""
    with pytest.raises(DrawWireError):
        program_slices(["fill 65535,65535,65535,65535,65535"], max_chars=10)

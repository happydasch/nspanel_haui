"""Tests for the image-preview renderer (``scripts/image_program``).

The script exists to judge a rectangle and a ``quality`` budget offline, so the
tests pin what the sheet contains — one tile per pass plus the reference — and
stop there: the rasteriser's own numbers are ``tests/test_image_program.py``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from custom_components.nspanel_haui.haui.utils.image_program import Rect, display_size
from scripts.image_program.gen_image_preview import (
    load_image,
    main,
    render_preview,
)


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    image = Image.new("RGB", size, (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _checkerboard_png(size: int = 40) -> bytes:
    """A PNG with no flat area: every grid costs close to one run per cell."""
    image = Image.new("RGB", (size, size), (0, 0, 0))
    drawing = ImageDraw.Draw(image)
    for y in range(size):
        for x in range(size):
            if (x + y) % 2:
                drawing.point((x, y), fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _render(tmp_path: Path, **overrides):
    kwargs = {
        "data": _png_bytes(),
        "rect": Rect(10, 10, 40, 40),
        "budget": 300,
        "progressive": False,
        "portrait": False,
        "scale": 1,
        "out": tmp_path / "sheet.png",
    }
    kwargs.update(overrides)
    return render_preview(**kwargs)


def test_a_render_writes_the_reference_and_one_tile_per_pass(tmp_path):
    out = tmp_path / "sheet.png"

    passes = _render(tmp_path)

    assert [name for name, _runs in passes] == ["full"]
    assert all(run.startswith("fill ") for run in passes[0][1])
    # The reference tile, then the pass.
    width, height = display_size(False)
    with Image.open(out) as sheet:
        assert sheet.size == (width * 2 + 8, height)


def test_a_progressive_render_draws_the_coarse_pass_first(tmp_path):
    passes = _render(tmp_path, data=_checkerboard_png(), progressive=True, budget=600)

    names = [name for name, _runs in passes]
    assert names == ["coarse", "full"]
    # The coarse pass is the cheaper program; the full one may not be smaller.
    coarse, full = passes[0][1], passes[1][1]
    assert 0 < len(coarse) <= 60
    assert len(full) >= len(coarse)
    # Each pass starts with its own clearing fill of the whole rectangle, so the
    # full pass paints over the coarse one and the tile never blanks out.
    assert all(run.startswith("fill ") for run in [*coarse, *full])
    assert coarse[0].split(",")[2:4] == full[0].split(",")[2:4]


def test_the_pass_tile_is_the_picture_the_panel_would_paint(tmp_path):
    """The sheet's pass tile is the program replayed, not a second rasteriser.

    Flat art at one pixel per cell is what the display shows exactly, so the tile
    has to be the reference tile pixel for pixel - a clearing fill in the wrong
    colour, or a block the program leaves out, fails here before a panel sees it.
    """
    image = Image.new("RGB", (20, 20), (250, 250, 250))
    ImageDraw.Draw(image).rectangle((10, 0, 19, 9), fill=(200, 30, 30))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    data = buffer.getvalue()
    out = tmp_path / "sheet.png"

    _render(tmp_path, data=data, rect=Rect(0, 0, 20, 20), budget=300, scale=1, out=out)

    width, height = display_size(False)
    with Image.open(out) as sheet:
        reference = sheet.crop((0, 0, width, height))
        painted = sheet.crop((width + 8, 0, 2 * width + 8, height))
        assert painted.tobytes() == reference.tobytes()


def test_a_portrait_render_uses_the_portrait_display(tmp_path):
    out = tmp_path / "portrait.png"

    _render(tmp_path, portrait=True, out=out)

    width, height = display_size(True)
    with Image.open(out) as sheet:
        assert sheet.size == (width * 2 + 8, height)


def test_a_rect_off_the_display_is_refused(tmp_path):
    from custom_components.nspanel_haui.haui.utils.image_program import ImageProgramError

    with pytest.raises(ImageProgramError):
        _render(tmp_path, rect=Rect(470, 10, 40, 40))


def test_the_command_line_writes_the_sheet_and_returns_zero(tmp_path):
    source = tmp_path / "logo.png"
    source.write_bytes(_png_bytes())
    out = tmp_path / "cli.png"

    assert main([str(source), "--out", str(out), "--w", "40", "--h", "40", "--scale", "1"]) == 0

    assert out.is_file()


def test_the_command_line_fails_on_a_file_that_is_no_image(tmp_path, capsys):
    source = tmp_path / "notes.txt"
    source.write_text("not an image")

    assert main([str(source), "--out", str(tmp_path / "x.png")]) == 1

    # The reason is the whole point of the exit status being 1, not a traceback.
    assert "could not be decoded" in capsys.readouterr().err


def test_a_local_file_is_read_from_disk(tmp_path):
    """A path is loaded as it is; ``load_image`` only fetches ``http(s)``."""
    source = tmp_path / "logo.png"
    source.write_bytes(_png_bytes())

    assert load_image(str(source)) == source.read_bytes()

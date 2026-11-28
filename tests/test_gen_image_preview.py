"""Tests for the image-preview renderer (``scripts/image_program``).

The script exists to judge a rectangle and a ``quality`` budget offline, so the
tests pin what the sheet contains — one tile per pass plus the reference — and
stop there: the rasteriser's own numbers are ``tests/test_image_program.py``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from custom_components.nspanel_haui.haui.utils.image_program import Rect, display_size
from scripts.image_program.gen_image_preview import (
    DEFAULT_BACKGROUND,
    load_image,
    main,
    render_preview,
)


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    image = Image.new("RGB", size, (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _render(tmp_path: Path, **overrides):
    kwargs = {
        "data": _png_bytes(),
        "rect": Rect(10, 10, 40, 40),
        "background": DEFAULT_BACKGROUND,
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
    passes = _render(tmp_path, progressive=True, budget=600)

    names = [name for name, _runs in passes]
    assert names == ["coarse", "full"]
    # The coarse pass is the cheaper program; the full one may not be smaller.
    coarse, full = passes[0][1], passes[1][1]
    # Only the first pass clears the rectangle: clearing again would blank the
    # coarse picture before the full one paints over it.
    assert coarse[0] == f"fill 10,10,40,40,{DEFAULT_BACKGROUND}"
    assert full[0] != coarse[0]
    assert 0 < len(coarse) <= 60
    assert len(full) + 1 >= len(coarse)


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

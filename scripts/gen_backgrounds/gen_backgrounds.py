"""Render the display background tiles from the source pictures.

Reads every picture in ``nextion/src_images/bkg/`` and writes one dimmed,
cover-cropped PNG per orientation to ``nextion/images/bkg/<orientation>/``:

* ``landscape``: 480 x 320 (EU panel, US panel mounted horizontally)
* ``portrait``:  320 x 480 (US panel mounted vertically)

The output file name is the source file's stem, which must match the key
used in ``haui/mapping/background.py`` (``system`` is the ``modern`` picture).
The tiles are then imported as picture resources in the Nextion Editor.

Usage::

    python scripts/gen_backgrounds/gen_backgrounds.py [--only NAME ...]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "nextion" / "src_images" / "bkg"
OUT_DIR = ROOT / "nextion" / "images" / "bkg"
SOURCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

SIZES = {
    "landscape": (480, 320),
    "portrait": (320, 480),
}

# Tiles sit behind text on the clock/weather pages, so they are blended
# towards a dark gray. 0 keeps the source as is, 1 is a flat gray.
DIM_COLOR = (35, 35, 35)
DIM_ALPHA = 0.8

# Per-picture overrides: ``focus`` is the point (x, y as fractions of the
# source) the crop window is centred on, ``dim`` replaces DIM_ALPHA.
OVERRIDES: dict[str, dict] = {
    # already a dark picture, keep more of it
    "system": {"dim": 0.55},
    # more mountain, less empty sky
    "winter": {"focus": (0.5, 0.56)},
}


def cover_crop(img: Image.Image, size: tuple[int, int], focus: tuple[float, float]) -> Image.Image:
    """Scales the image to cover ``size`` and crops the window centred on ``focus``."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    sw, sh = round(img.width * scale), round(img.height * scale)
    scaled = img.resize((sw, sh), Image.LANCZOS)
    left = min(max(round(focus[0] * sw - tw / 2), 0), sw - tw)
    top = min(max(round(focus[1] * sh - th / 2), 0), sh - th)
    return scaled.crop((left, top, left + tw, top + th))


def dim(img: Image.Image, alpha: float) -> Image.Image:
    return Image.blend(img, Image.new("RGB", img.size, DIM_COLOR), alpha)


def render(source: Path) -> None:
    opts = OVERRIDES.get(source.stem, {})
    focus = opts.get("focus", (0.5, 0.5))
    alpha = opts.get("dim", DIM_ALPHA)
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    for orientation, size in SIZES.items():
        out = OUT_DIR / orientation / f"{source.stem}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        dim(cover_crop(img, size, focus), alpha).save(out, optimize=True)
        print(f"{out.relative_to(ROOT)}  {size[0]}x{size[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--only", nargs="*", metavar="NAME", help="render only these tiles")
    args = parser.parse_args()
    sources = sorted(p for p in SRC_DIR.iterdir() if p.suffix.lower() in SOURCE_SUFFIXES)
    if args.only:
        sources = [p for p in sources if p.stem in args.only]
    if not sources:
        raise SystemExit(f"no source pictures found in {SRC_DIR}")
    for source in sources:
        render(source)


if __name__ == "__main__":
    main()

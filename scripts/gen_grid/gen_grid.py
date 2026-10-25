"""Render the design-aid grids ``nextion/images/grid_landscape.png`` and
``grid_portrait.png``.

The grids are page backgrounds for the Nextion Editor that show the layout
rules of each orientation: header, 12 px side margins, content area, the
bottom function-button bar of the portrait layout
(``scripts/gen_portrait/portrait_layout.py``), column and row guides, icon
and image placeholder sizes, font-size samples, the display centers and the
theme colors of ``haui/mapping/color.py`` as RGB565 values. The landscape
grid also marks the 30 px strip the EU bezel hides.

Usage::

    python scripts/gen_grid/gen_grid.py [landscape|portrait ...]
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "nextion" / "images"
FONT_DIR = ROOT / "scripts" / "gen_fonts" / "Roboto"
COLOR_PY = ROOT / "custom_components" / "nspanel_haui" / "haui" / "mapping" / "color.py"

GAP = 2
BAR_W, BAR_PITCH = 10, 13
CELL_H, CELL_PITCH = 10, 12
FONT_SAMPLES = (20, 24, 32, 48)
ICON_SIZES = ((16, 12), (22, 16), (28, 20), (44, 32), (88, 64))
IMAGE_SIZE = (117, 85)

# colors of the original landscape grid
BG = (63, 63, 63)
BAND = (92, 92, 92)
BAND_TOP = (74, 74, 74)
MARGIN_BG = (42, 42, 42)
GUIDE = (121, 121, 121)
OUTLINE = (126, 126, 126)
CELL = (159, 159, 159)
CELL_OVERLAP = (207, 207, 207)
TEXT = (207, 207, 207)
TEXT_DARK = (42, 42, 42)
WHITE = (255, 255, 255)
SAMPLE = (121, 121, 121)
HIDDEN = (255, 99, 77)


@dataclass(frozen=True)
class Spec:
    name: str
    size: tuple[int, int]
    visible_w: int
    header_h: int
    margin: int
    area: tuple[int, int, int, int]  # content area x, y, w, h (the row guides)
    outline_h: int  # outlined height: landscape keeps 20 px more than the rows
    bottom_bar: bool
    columns: tuple[int, ...]
    rows: tuple[int, ...]
    centers: tuple[tuple[str, int, int], ...]  # label, x, y
    center_label_right: int
    center_label_y: int
    icons_x: int
    icons_bottom: int
    image_pos: tuple[int, int]
    samples_x: int
    samples_baselines: tuple[int, ...]  # one baseline per line of samples
    samples_per_line: tuple[int, ...]  # how many samples go on each line
    size_label_y: int
    block_y: int
    bar_labels_top: bool

    @property
    def area_right(self) -> int:
        return self.area[0] + self.area[2] - 1


LANDSCAPE = Spec(
    name="landscape",
    size=(480, 320),
    visible_w=450,
    header_h=50,
    margin=12,
    area=(12, 50, 426, 240),
    outline_h=260,
    bottom_bar=False,
    columns=(2, 3, 4, 5),
    rows=(2, 3, 4, 5),
    centers=(("Display Center", 225, 160), ("Area Center", 225, 170), ("Full Center", 225, 180)),
    center_label_right=215,
    center_label_y=153,
    icons_x=163,
    icons_bottom=122,
    image_pos=(260, 128),
    samples_x=90,
    samples_baselines=(309,),
    samples_per_line=(4,),
    size_label_y=204,
    block_y=221,
    bar_labels_top=False,
)
PORTRAIT = Spec(
    name="portrait",
    size=(320, 480),
    visible_w=320,
    header_h=50,
    margin=12,
    area=(12, 50, 296, 380),
    outline_h=380,
    bottom_bar=True,
    columns=(2, 3, 4, 5),
    rows=(2, 3, 4, 5, 6),
    centers=(("Display Center", 160, 240), ("Area Center", 160, 240)),
    center_label_right=150,
    center_label_y=244,
    icons_x=24,
    icons_bottom=146,
    image_pos=(121, 148),
    samples_x=24,
    samples_baselines=(306, 352),
    samples_per_line=(3, 1),
    size_label_y=356,
    block_y=370,
    bar_labels_top=True,
)
SPECS = {s.name: s for s in (LANDSCAPE, PORTRAIT)}


def theme_colors() -> list[int]:
    """Distinct RGB565 values of the theme, in the order ``COLORS`` lists them."""
    module_spec = importlib.util.spec_from_file_location("haui_color", COLOR_PY)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return list(dict.fromkeys(module.COLORS.values()))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def rgb565(value: int) -> tuple[int, int, int]:
    r, g, b = value >> 11, (value >> 5) & 0x3F, value & 0x1F
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def split(total: int, count: int) -> list[tuple[int, int]]:
    """Returns (start, size) of ``count`` cells filling ``total`` px with 2 px gaps.

    The remainder widens the first gaps, like the original landscape grid.
    """
    size = (total - (count - 1) * GAP) // count
    extra = total - count * size - (count - 1) * GAP
    cells, pos = [], 0
    for i in range(count):
        cells.append((pos, size))
        pos += size + GAP + (1 if i < extra else 0)
    return cells


def text_w(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> int:
    return round(draw.textlength(text, font=fnt))


def placeholder(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    """Image placeholder: rounded outline with a mountain icon."""
    border = max(2, w // 15)
    draw.rounded_rectangle(
        (x, y, x + w - 1, y + h - 1), radius=max(2, w // 10), outline=OUTLINE, width=border
    )
    ix, iy = x + border + 2, y + border + 2
    iw, ih = w - 2 * border - 4, h - 2 * border - 4
    base = iy + ih - 1
    draw.polygon([(ix, base), (ix + iw * 0.42, iy + ih * 0.35), (ix + iw * 0.7, base)], fill=GUIDE)
    draw.polygon(
        [(ix + iw * 0.45, base), (ix + iw * 0.72, iy + ih * 0.15), (ix + iw, base)], fill=GUIDE
    )


def swatch(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: int,
    fnt: ImageFont.FreeTypeFont,
) -> None:
    color = rgb565(value)
    draw.rectangle(box, fill=color)
    text_color = TEXT_DARK if sum(color) > 380 else TEXT
    draw.text(
        ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2),
        str(value),
        font=fnt,
        fill=text_color,
        anchor="mm",
    )


def render(spec: Spec, swatches: list[int]) -> Path:
    width, height = spec.size
    ax, ay, aw, ah = spec.area
    bar_y = ay + spec.outline_h  # first row below the content: margin band or bottom bar
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    f13, f13b, f12, f11, f10 = font(13), font(13, bold=True), font(12), font(11), font(10)

    # bands: header with its 11 px top strip, side margins, bottom margin or bar
    d.rectangle((0, 0, spec.visible_w - 1, spec.header_h - 1), fill=BAND)
    d.rectangle((0, 0, spec.visible_w - 1, 10), fill=BAND_TOP)
    d.rectangle((0, 11, spec.visible_w - 1, 12), fill=OUTLINE)
    d.rectangle((0, ay, ax - 2, bar_y - 1), fill=MARGIN_BG)
    d.rectangle((spec.area_right + 1, ay, spec.visible_w - 1, bar_y - 1), fill=MARGIN_BG)
    if spec.bottom_bar:
        d.rectangle((0, bar_y, width - 1, height - 1), fill=BAND)
    else:
        d.rectangle((ax + 1, bar_y + 1, spec.area_right, height - 1), fill=MARGIN_BG)

    # column guides for every column count, full height
    columns = {n: [(ax + s, w) for s, w in split(aw, n)] for n in spec.columns}
    for cells in columns.values():
        for start, w in cells[:-1]:
            d.rectangle((start + w, 0, start + w + 1, height - 1), fill=GUIDE)
    # area center line, half marker and the content outline
    d.rectangle((ax + spec.margin, ay + ah // 2 - 1, spec.area_right, ay + ah // 2), fill=GUIDE)
    d.rectangle((spec.margin - 1, 0, spec.margin, spec.header_h - 1), fill=WHITE)
    d.rectangle((ax, ay, spec.area_right, ay + spec.outline_h - 1), outline=WHITE)
    half = spec.outline_h // 2
    d.rectangle((ax + 10, ay, ax + 11, ay + half), fill=WHITE)

    # labels
    extra = "" if spec.outline_h == ah else f"+{height - ay - ah}"
    d.text((14, 14), f"Top Area: {spec.header_h}px", font=f13, fill=TEXT)
    d.text((14, 31), f"Main Area: {aw}, {ah}{extra} ({ax}, {ay})", font=f13, fill=TEXT)
    visible = f"Visible: {spec.visible_w}x{height}px"
    d.text((spec.area_right - 1 - text_w(d, visible, f13b), 14), visible, font=f13b, fill=WHITE)
    d.text((26, 55), f"Half: {half} ({ay + half})", font=f13, fill=TEXT)
    size_label = f"Width: {aw}px, Height: {ah}px"
    if spec.outline_h != ah:
        size_label += f" ({spec.outline_h}px)"
    d.text((14, spec.size_label_y), size_label, font=f13, fill=TEXT)
    if spec.bottom_bar:
        d.text(
            (14, bar_y - 13), f"Bottom Bar: {height - bar_y}px (0, {bar_y})", font=f11, fill=TEXT
        )

    # icon and image placeholders
    x = spec.icons_x
    for w, h in ICON_SIZES:
        placeholder(d, x, spec.icons_bottom - h, w, h)
        x += w + 4
    placeholder(d, *spec.image_pos, *IMAGE_SIZE)

    # centers: labels right-aligned, a tick on each center and a line through them
    y = spec.center_label_y
    for label, cx, cy in spec.centers:
        text = f"{label} ({cx}, {cy})"
        d.text((spec.center_label_right - text_w(d, text, f11), y), text, font=f11, fill=TEXT)
        d.line((cx - 5, cy, cx + 5, cy), fill=TEXT)
        y += 13
    ys = [cy for _, _, cy in spec.centers]
    d.line((spec.centers[0][1], min(ys) - 6, spec.centers[0][1], max(ys) + 6), fill=TEXT)

    # font-size samples
    sizes = iter(FONT_SAMPLES)
    for baseline, count in zip(spec.samples_baselines, spec.samples_per_line, strict=True):
        x = spec.samples_x
        for _ in range(count):
            size = next(sizes)
            fnt = font(size)
            d.text((x, baseline), f"{size}px", font=fnt, fill=SAMPLE, anchor="ls")
            x += text_w(d, f"{size}px", fnt) + 8

    # column block: one row of cells per column count
    cell_rects = []
    for i, n in enumerate(spec.columns):
        y = spec.block_y + i * CELL_PITCH
        for start, w in columns[n]:
            cell_rects.append((start, y, start + w - 1, y + CELL_H - 1))
            d.rectangle(cell_rects[-1], fill=CELL)
        label_end = 0
        for j, (start, w) in enumerate(columns[n]):
            label = f"{n} Columns ({w}px)" if j == 0 else f"{start}px"
            if j and start < label_end + 4:
                continue  # the previous label runs into this cell
            d.text((start + 3, y - 1), label, font=f10, fill=TEXT_DARK)
            label_end = start + 3 + text_w(d, label, f10)

    # row-height bars at the right, one bar per row count; lighter where they cross cells
    bx = spec.area_right - 5 - BAR_W + 1 - BAR_PITCH * (len(spec.rows) - 1)
    for n in spec.rows:
        rows = split(ah, n)
        for start, h in rows:
            bar = (bx, ay + start, bx + BAR_W - 1, ay + start + h - 1)
            d.rectangle(bar, fill=CELL)
            for cell in cell_rects:
                overlap = (
                    max(bar[0], cell[0]),
                    max(bar[1], cell[1]),
                    min(bar[2], cell[2]),
                    min(bar[3], cell[3]),
                )
                if overlap[0] <= overlap[2] and overlap[1] <= overlap[3]:
                    d.rectangle(overlap, fill=CELL_OVERLAP)
        label = f"{rows[0][1]}px"
        tw = text_w(d, label, f10)
        tile = Image.new("RGB", (tw + 2, BAR_W), CELL)
        ImageDraw.Draw(tile).text((1, -1), label, font=f10, fill=TEXT_DARK)
        ty = ay + 4 if spec.bar_labels_top else ay + ah - 4 - tw - 2
        img.paste(tile.rotate(90, expand=True), (bx, ty))
        bx += BAR_PITCH

    # theme colors: in the hidden strip (landscape) or the bottom bar (portrait)
    if spec.bottom_bar:
        per_row = (len(swatches) + 1) // 2
        for i, value in enumerate(swatches):
            row, col = divmod(i, per_row)
            count = per_row if row == 0 else len(swatches) - per_row
            w = width // count
            x0, y0 = col * w, bar_y + 1 + row * 25
            swatch(d, (x0, y0, x0 + w - 2, y0 + 23), value, f12)
    else:
        d.rectangle((spec.visible_w, 0, width - 1, height - 1), fill=HIDDEN)
        for i, value in enumerate(swatches):
            swatch(d, (spec.visible_w, i * 15, width - 1, i * 15 + 14), value, f10)

    out = OUT_DIR / f"grid_{spec.name}.png"
    img.save(out, optimize=True)
    print(f"{out.relative_to(ROOT)}  {width}x{height}")
    return out


def main() -> None:
    names = sys.argv[1:] or list(SPECS)
    unknown = [n for n in names if n not in SPECS]
    if unknown:
        raise SystemExit(f"unknown orientation {unknown}; choose from {list(SPECS)}")
    swatches = theme_colors()
    for name in names:
        render(SPECS[name], swatches)


if __name__ == "__main__":
    main()

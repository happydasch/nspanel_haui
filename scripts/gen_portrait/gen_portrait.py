#!/usr/bin/env python3
"""Apply a widget layout spec to a Nextion HMI project in place.

The Nextion Editor stores every widget attribute as a length-prefixed record
(``<u32 len><16-byte name><value>``) inside the page blocks of the ``.HMI``
file, with ints as 4-byte little-endian values.  Rewriting ``x``/``y``/``w``/
``h`` (and the derived ``endx``/``endy``) or other int attributes in place
therefore changes no record length and no offset, so the file stays
structurally identical.

Every page block starts with a 32-bit content stamp that the editor checks
("Version mismatch" / "Loading Page Failed" when it is stale).  The stamp is
``CRC32(message) ^ K(block length)`` where the message is every byte after the
stamp widened to a big-endian u32 followed by 40 zero bytes, CRC-32 MSB-first
with init 0 and no final XOR (see https://github.com/vladtsvetkov880-hub/
nextion-hmi-format, ``docs/block-stamp.md``).  ``K`` is a length-dependent
constant that is not understood, but an in-place patch keeps the block length,
so ``new_stamp = old_stamp ^ CRC32(old message) ^ CRC32(new message)``.

A spec is a module next to this script exposing ``WIDTH``, ``HEIGHT``,
``HMI_NAME``, ``LAYOUT`` (``{page: {widget: (x, y, w, h)}}``), ``ATTRS``
(``{page: {widget: {attr: int}}}``), ``PARTIAL`` and ``check_bounds()``:

- ``portrait_layout`` (default) — the complete 320x480 layout; every visual
  widget of every page must be listed.
- ``landscape_layout`` — partial refinements of the 480x320 layout; unlisted
  widgets keep their geometry.

A spec may also name a ``SIBLING_HMI``: the two projects must then hold the
same widgets, and the sibling's touch settings (``sendkey`` — Send Component
ID) are copied onto every widget, so a touch toggled in the landscape project
reaches the portrait TFT too (the hub addresses both by the same names).

Usage::

    python scripts/gen_portrait/gen_portrait.py --check                     # report only
    python scripts/gen_portrait/gen_portrait.py                             # portrait HMI
    python scripts/gen_portrait/gen_portrait.py --spec landscape_layout     # landscape HMI
    python scripts/gen_portrait/gen_portrait.py -i IN.HMI -o OUT.HMI        # explicit files

``--check`` and the patch both fail when the HMI's widgets and the spec
disagree (a listed widget missing in the HMI, or — for a complete spec — a
visual widget missing in the spec), so a spec cannot silently drift.
"""

from __future__ import annotations

import argparse
import importlib
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
Rect = tuple[int, int, int, int]

HMI_CONTENT_FMT = "<16sII?bbb"
PAGE_HEADER_FMT = "<IIIII?bbb16s16b"
PAGE_COMPONENT_FMT = "<III"
PAGE_TYPE = 121
GEOMETRY_ATTRS = ("x", "y", "w", "h", "endx", "endy")
SIBLING_ATTRS = ("sendkey",)  # copied from the sibling HMI onto every widget

STAMP_POLY = 0x04C11DB7
STAMP_TAIL = bytes(40)


def _make_stamp_table() -> list[int]:
    table = []
    for byte in range(256):
        crc = byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ STAMP_POLY) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1)
        table.append(crc & 0xFFFFFFFF)
    return table


STAMP_TABLE = _make_stamp_table()


def block_crc(block: bytes) -> int:
    """CRC-32 (MSB-first, init 0) of a block's stamp message, without the ``K`` term."""
    message = bytearray()
    for byte in block[4:]:
        message += b"\x00\x00\x00" + bytes((byte,))
    message += STAMP_TAIL
    crc = 0
    for byte in message:
        crc = STAMP_TABLE[((crc >> 24) ^ byte) & 0xFF] ^ ((crc << 8) & 0xFFFFFFFF)
    return crc


@dataclass
class Widget:
    """One component of a page with the absolute offsets of its int attributes."""

    name: str
    type_id: int
    attrs: dict[str, int] = field(default_factory=dict)
    offsets: dict[str, int] = field(default_factory=dict)
    sizes: dict[str, int] = field(default_factory=dict)

    @property
    def is_visual(self) -> bool:
        return "x" in self.attrs


@dataclass
class PageBlock:
    """One ``*.pa`` block of the HMI: its byte range and parsed components."""

    name: str
    start: int
    size: int
    widgets: list[Widget]

    @property
    def end(self) -> int:
        return self.start + self.size

    def widget(self, name: str) -> Widget:
        return next(w for w in self.widgets if w.name == name)


def _parse_component(raw: bytes, start: int, size: int) -> Widget:
    """Walk one component's property records and remember where each int lives."""
    records: list[tuple[int, int]] = []  # (absolute offset of data, length)
    index = start
    end = start + size
    while index < end:
        (length,) = struct.unpack_from("<I", raw, index)
        records.append((index + 4, length))
        index += 4 + length
    widget = Widget(name="", type_id=-1)
    i = 0
    while i < len(records):
        off, length = records[i]
        label = raw[off : off + length]
        i += 1
        if not label:  # components end with one empty record
            continue
        group, _, count = label.rpartition(b"-")
        count = int(count)
        if group == b"att":
            for off, length in records[i : i + count]:
                att_name = raw[off : off + 16].rstrip(b"\x00").decode("iso_8859_1")
                value = raw[off + 16 : off + length]
                if att_name == "objname":
                    widget.name = value.decode("iso_8859_1")
                elif len(value) <= 4:
                    widget.attrs[att_name] = int.from_bytes(value, "little")
                    widget.offsets[att_name] = off + 16
                    widget.sizes[att_name] = len(value)
        i += count
    widget.type_id = widget.attrs.get("type", -1)
    if not widget.name:
        raise ValueError(f"component at offset {start} has no objname")
    return widget


def parse_pages(raw: bytes) -> dict[str, PageBlock]:
    """Return ``{page_name: PageBlock}`` for every page block of the HMI."""
    (count,) = struct.unpack_from("<I", raw, 0)
    entry_size = struct.calcsize(HMI_CONTENT_FMT)
    header_size = struct.calcsize(PAGE_HEADER_FMT)
    pages: dict[str, PageBlock] = {}
    for i in range(count):
        entry = struct.unpack_from(HMI_CONTENT_FMT, raw, 4 + i * entry_size)
        name, start, size, deleted = entry[:4]
        if deleted or not name.rstrip(b"\x00").endswith(b".pa"):
            continue
        (comp_count,) = struct.unpack_from("<I", raw, start + 12)
        widgets = []
        for c in range(comp_count):
            comp_off, comp_size, _ = struct.unpack_from(
                PAGE_COMPONENT_FMT, raw, start + header_size + c * 12
            )
            widgets.append(_parse_component(raw, start + header_size + comp_off, comp_size))
        page = next(w for w in widgets if w.type_id == PAGE_TYPE)
        pages[page.name] = PageBlock(page.name, start, size, widgets)
    return pages


def load_spec(name: str) -> ModuleType:
    """Import a layout spec module that lives next to this script."""
    return importlib.import_module(name)


Pages = dict[str, PageBlock]


def _expected(
    spec: ModuleType, page: str, widget: Widget, sibling: Pages | None = None
) -> dict[str, int] | None:
    """The attribute values the spec wants for ``widget``, or None when it is unlisted."""
    if widget.type_id == PAGE_TYPE:
        rect: Rect | None = (0, 0, spec.WIDTH, spec.HEIGHT)
    else:
        rect = spec.LAYOUT.get(page, {}).get(widget.name)
    want: dict[str, int] = {}
    if rect is not None:
        x, y, w, h = rect
        want.update({"x": x, "y": y, "w": w, "h": h, "endx": x + w - 1, "endy": y + h - 1})
    want.update(spec.ATTRS.get(page, {}).get(widget.name, {}))
    if sibling is not None and page in sibling:
        twin = next((w for w in sibling[page].widgets if w.name == widget.name), None)
        if twin is not None:
            for att in SIBLING_ATTRS:
                if att in twin.attrs and att in widget.offsets:
                    want[att] = twin.attrs[att]
    return want or None


def check_coverage(pages: Pages, spec: ModuleType, sibling: Pages | None = None) -> list[str]:
    """Describe every mismatch between the HMI's widgets, the spec and the sibling HMI."""
    problems = [f"spec: {p}" for p in spec.check_bounds()]
    if sibling is not None:
        for page in sorted(set(pages) ^ set(sibling)):
            problems.append(f"{page}: page exists in only one of the sibling HMIs")
        for page in sorted(set(pages) & set(sibling)):
            mine = {w.name for w in pages[page].widgets}
            theirs = {w.name for w in sibling[page].widgets}
            for name in sorted(mine ^ theirs):
                problems.append(f"{page}.{name}: widget exists in only one of the sibling HMIs")
    for page in sorted((set(spec.LAYOUT) | set(spec.ATTRS)) - set(pages)):
        problems.append(f"{page}: in the spec but not in the HMI")
    for page, block in pages.items():
        by_name = {w.name: w for w in block.widgets}
        listed = set(spec.LAYOUT.get(page, {})) | set(spec.ATTRS.get(page, {}))
        for name in sorted(listed - set(by_name)):
            problems.append(f"{page}.{name}: in the spec but not in the HMI")
        for name, attrs in spec.ATTRS.get(page, {}).items():
            for att in attrs:
                if name in by_name and att not in by_name[name].offsets:
                    problems.append(f"{page}.{name}: has no int attribute {att!r}")
        if spec.PARTIAL:
            continue
        if page not in spec.LAYOUT:
            problems.append(f"{page}: page is not in the spec")
            continue
        visual = {w.name for w in block.widgets if w.is_visual and w.type_id != PAGE_TYPE}
        for name in sorted(visual - set(spec.LAYOUT[page])):
            problems.append(f"{page}.{name}: visual widget missing in the spec")
    return problems


def _write_attr(raw: bytearray, widget: Widget, att: str, value: int) -> None:
    if att not in widget.offsets:
        raise ValueError(f"{widget.name}: attribute {att!r} not present")
    size = widget.sizes[att]
    raw[widget.offsets[att] : widget.offsets[att] + size] = value.to_bytes(size, "little")
    widget.attrs[att] = value


def _write_geometry(raw: bytearray, widget: Widget, rect: Rect) -> None:
    x, y, w, h = rect
    values = {"x": x, "y": y, "w": w, "h": h, "endx": x + w - 1, "endy": y + h - 1}
    for att, value in values.items():
        _write_attr(raw, widget, att, value)


def _restamp(raw: bytearray, block: PageBlock, old_crc: int) -> None:
    """Replace a page block's content stamp after its bytes changed (same length)."""
    (old_stamp,) = struct.unpack_from("<I", raw, block.start)
    new_crc = block_crc(raw[block.start : block.end])
    struct.pack_into("<I", raw, block.start, old_stamp ^ old_crc ^ new_crc)


def apply_layout(
    raw: bytearray, pages: Pages, spec: ModuleType, sibling: Pages | None = None
) -> int:
    """Write the spec's geometry and attributes into ``raw``; returns widgets changed."""
    changed = 0
    for page, block in pages.items():
        old_crc = block_crc(raw[block.start : block.end])
        touched = False
        for widget in block.widgets:
            want = _expected(spec, page, widget, sibling)
            if want is None:
                continue
            before = dict(widget.attrs)
            for att, value in want.items():
                _write_attr(raw, widget, att, value)
            if widget.attrs != before:
                changed += 1
                touched = True
        if touched:
            _restamp(raw, block, old_crc)
    return changed


def verify(raw: bytes, spec: ModuleType, sibling: Pages | None = None) -> list[str]:
    """Re-parse ``raw`` and report every listed widget whose attributes differ from the spec."""
    problems = []
    for page, block in parse_pages(raw).items():
        for widget in block.widgets:
            want = _expected(spec, page, widget, sibling)
            if want is None:
                continue
            got = {att: widget.attrs[att] for att in want}
            if got != want:
                problems.append(f"{page}.{widget.name}: got {got}, want {want}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--spec", default="portrait_layout", help="layout spec module (default: portrait_layout)"
    )
    parser.add_argument("-i", "--input", type=Path, help="HMI to read (default: the spec's HMI)")
    parser.add_argument("-o", "--output", type=Path, help="HMI to write (default: --input)")
    parser.add_argument(
        "--sibling",
        type=Path,
        help="sibling HMI whose touch settings are copied (default: the spec's SIBLING_HMI)",
    )
    parser.add_argument("--check", action="store_true", help="only report spec coverage")
    args = parser.parse_args(argv)

    spec = load_spec(args.spec)
    source = args.input or ROOT / "nextion" / spec.HMI_NAME
    raw = bytearray(source.read_bytes())
    pages = parse_pages(raw)
    sibling_name = getattr(spec, "SIBLING_HMI", None)
    sibling_path = args.sibling or (ROOT / "nextion" / sibling_name if sibling_name else None)
    sibling = parse_pages(sibling_path.read_bytes()) if sibling_path else None
    problems = check_coverage(pages, spec, sibling)
    if problems:
        print("\n".join(problems))
        return 1
    with_sibling = f" and with {sibling_path.name}" if sibling_path else ""
    print(f"{source}: {len(pages)} pages, spec {args.spec} consistent with the HMI{with_sibling}")
    if args.check:
        # Verify attribute values too (alignment, font, …), not just widget
        # coverage: a spec-only change must not pass the release gate while
        # the committed HMI still carries the old value (#64 alignment, #60 font).
        problems = verify(raw, spec, sibling)
        if problems:
            print("\n".join(problems))
            return 1
        return 0

    changed = apply_layout(raw, pages, spec, sibling)
    problems = verify(raw, spec, sibling)
    if problems:
        print("\n".join(problems))
        return 1
    output = args.output or source
    output.write_bytes(raw)
    print(f"{output}: wrote {changed} widgets from {args.spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

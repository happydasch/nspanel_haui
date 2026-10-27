#!/usr/bin/env python3
"""Set the ``system.tftVersion`` text of the Nextion HMI files to a version.

The release process used to require opening the Nextion Editor just to type the
new version into the ``system`` page's ``tftVersion`` variable.  This script
performs that edit directly on the HMI binary: it finds the live ``tftVersion``
widget on the ``system`` page, replaces its ``txt`` attribute with the requested
version and restamps the page's content stamp so the HMI stays valid.

The ``tftVersion`` widget is a text variable, so its value is a *text* attribute
(``txt``) that ``gen_portrait.py`` skips when collecting integer attributes.
The record layout is ``[4-byte length][16-byte name][value bytes]`` and the
length covers name + value.  A same-length replacement (``0.4.1`` -> ``0.4.2``)
is an in-place overwrite; a longer or shorter version would resize the record
and shift the rest of the page block, so the script refuses it — bump a version
with a different length in the Nextion Editor.

Deleted page blocks (``deleted=True``) also contain stale ``tftVersion`` text and
are ignored: only active page blocks are edited.

Usage:
    python scripts/bump_tft_version.py [--version X.Y.Z] [--check] [--hmi PATH]

Exit code 0 when every HMI carries the requested version (or was updated), 1
when an HMI needs a length-changing edit or its widget cannot be found.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "nspanel_haui" / "manifest.json"
DEFAULT_HMIS = (
    ROOT / "nextion" / "nspanel_haui.HMI",
    ROOT / "nextion" / "nspanel_haui_portrait.HMI",
)

# Import the HMI parser/restamper next to this script's sibling directory.
sys.path.insert(0, str(ROOT / "scripts" / "gen_portrait"))
import gen_portrait as gp  # noqa: E402

TARGET_WIDGET = "tftVersion"
TARGET_PAGE = "system"
TXT_NAME = "txt"
NAME_WIDTH = 16


def _active_pages(raw: bytes) -> dict[str, gp.PageBlock]:
    """Return ``{page_name: PageBlock}`` for the active (non-deleted) pages."""
    return gp.parse_pages(raw)


def _find_txt_record(raw: bytes, block: gp.PageBlock) -> tuple[int, int] | None:
    """Return ``(length_field_offset, value_offset)`` of the ``tftVersion`` ``txt``.

    Text attributes are not in ``Widget.offsets`` (the parser only tracks integer
    attributes), so the record is located from the widget's ``objname`` value:
    find the widget name inside the page block, verify the 16-byte name field
    before it is ``objname``, then walk records forward to ``txt``.
    """
    needle = TARGET_WIDGET.encode("iso_8859_1")
    pos = block.start
    while pos < block.end:
        pos = raw.find(needle, pos, block.end)
        if pos < 0:
            return None
        # The objname value starts 20 bytes after its record's length field, so
        # its 16-byte name field sits at ``pos - 16``.
        if pos >= NAME_WIDTH + 4 and raw[pos - NAME_WIDTH : pos].rstrip(b"\x00") == b"objname":
            index = pos - NAME_WIDTH - 4
            while index < block.end:
                (length,) = struct.unpack_from("<I", raw, index)
                if length == 0 or length > 400:
                    return None
                name = raw[index + 4 : index + NAME_WIDTH].rstrip(b"\x00")
                if name == TXT_NAME.encode():
                    return index, index + 4 + NAME_WIDTH
                index += 4 + length
        pos += 1
    return None


def _read_text(raw: bytes, value_off: int, length_field_off: int) -> str:
    (length,) = struct.unpack_from("<I", raw, length_field_off)
    value = raw[value_off : length_field_off + 4 + length]
    return value.decode("iso_8859_1", "replace")


def bump_hmi(path: Path, version: str, check: bool = False) -> tuple[bool, str]:
    """Set ``tftVersion`` to ``version`` in ``path``.

    Returns ``(ok, message)``; ``ok`` is False when the edit cannot be made
    (widget missing, length change needed) so the caller can report and fail.
    """
    raw = bytearray(path.read_bytes())
    pages = _active_pages(bytes(raw))
    block = pages.get(TARGET_PAGE)
    if block is None:
        return False, f"{path.name}: page {TARGET_PAGE!r} not found"
    located = _find_txt_record(bytes(raw), block)
    if located is None:
        return False, f"{path.name}: widget {TARGET_WIDGET!r} has no {TXT_NAME!r} attribute"
    length_field_off, value_off = located
    (length,) = struct.unpack_from("<I", raw, length_field_off)
    current = _read_text(bytes(raw), value_off, length_field_off)
    if current == version:
        return True, f"{path.name}: already {version!r}"
    if len(current) != len(version):
        return (
            False,
            f"{path.name}: {TARGET_WIDGET}.{TXT_NAME} is {current!r} ({len(current)} chars), "
            f"cannot write {version!r} ({len(version)} chars) in place — "
            "bump a same-length version here or use the Nextion Editor",
        )
    if check:
        return (
            False,
            f"{path.name}: would set {TARGET_WIDGET}.{TXT_NAME} "
            f"{current!r} -> {version!r}",
        )
    old_crc = gp.block_crc(bytes(raw[block.start : block.end]))
    raw[value_off : value_off + len(version)] = version.encode("iso_8859_1")
    # Restamp the page block's content stamp after the bytes changed.
    (old_stamp,) = struct.unpack_from("<I", raw, block.start)
    new_crc = gp.block_crc(bytes(raw[block.start : block.end]))
    struct.pack_into("<I", raw, block.start, old_stamp ^ old_crc ^ new_crc)
    path.write_bytes(bytes(raw))
    return True, f"{path.name}: set {TARGET_WIDGET}.{TXT_NAME} {current!r} -> {version!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--version",
        default=None,
        help="version to write (default: the integration's manifest version)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change without writing the HMI files",
    )
    parser.add_argument(
        "--hmi",
        type=Path,
        action="append",
        default=None,
        help="HMI file to edit (repeatable; default: both release HMIs)",
    )
    args = parser.parse_args(argv)

    version = args.version
    if version is None:
        try:
            version = json.loads(MANIFEST.read_text(encoding="utf-8")).get("version", "")
        except (OSError, ValueError) as exc:
            print(f"error: cannot read {MANIFEST}: {exc}", file=sys.stderr)
            return 2
    if not version:
        print("error: cannot determine the version to write", file=sys.stderr)
        return 2

    hmis = args.hmi or list(DEFAULT_HMIS)
    failed = False
    for hmi in hmis:
        if not hmi.exists():
            print(f"error: HMI not found: {hmi}", file=sys.stderr)
            failed = True
            continue
        ok, message = bump_hmi(hmi, version, check=args.check)
        print(("[OK] " if ok else "[FAIL] ") + message)
        if not ok:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

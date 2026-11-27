#!/usr/bin/env python3
"""Set the ``system.tftVersion`` text of the Nextion HMI files to a version.

The version is overwritten in place, so its length must not change; a longer or
shorter version needs the Nextion Editor. Only active page blocks are edited.

A successful run also regenerates the virtual layouts the editor's live preview
reads, because they carry the ``tftVersion`` text as a widget attribute: skipping
that leaves them stale and ``tests/test_virtual_layout.py`` fails.

Usage:
    python -m scripts.bump_tft_version [--version X.Y.Z] [--check] [--hmi PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

from scripts.hmi_layout import gen_layout as gp

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "nspanel_haui" / "manifest.json"
DEFAULT_HMIS = (
    ROOT / "nextion" / "nspanel_haui.HMI",
    ROOT / "nextion" / "nspanel_haui_portrait.HMI",
)
VIRTUAL_LAYOUT_GENERATOR = "scripts.hmi_layout.gen_virtual_layout"

TARGET_WIDGET = "tftVersion"
TARGET_PAGE = "system"
TXT_NAME = "txt"
NAME_WIDTH = 16


def _active_pages(raw: bytes) -> dict[str, gp.PageBlock]:
    """Return ``{page_name: PageBlock}`` for the active (non-deleted) pages."""
    return gp.parse_pages(raw)


def _find_txt_record(raw: bytes, block: gp.PageBlock) -> tuple[int, int] | None:
    """Return ``(length_field_offset, value_offset)`` of the ``tftVersion`` ``txt``.

    Text attributes are not in ``Widget.offsets``, so the record is located from
    the widget's ``objname`` value and walked forward to ``txt``.
    """
    needle = TARGET_WIDGET.encode("iso_8859_1")
    pos = block.start
    while pos < block.end:
        pos = raw.find(needle, pos, block.end)
        if pos < 0:
            return None
        # objname's 16-byte name field sits 16 bytes before its value.
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


def read_tft_version(path: Path) -> str:
    """Return the ``system.tftVersion`` text of the HMI at ``path``.

    Raises:
        ValueError: The ``system`` page or its ``tftVersion`` text is missing.
    """
    raw = path.read_bytes()
    block = _active_pages(raw).get(TARGET_PAGE)
    if block is None:
        raise ValueError(f"{path.name}: page {TARGET_PAGE!r} not found")
    located = _find_txt_record(raw, block)
    if located is None:
        raise ValueError(f"{path.name}: widget {TARGET_WIDGET!r} has no {TXT_NAME!r} attribute")
    length_field_off, value_off = located
    return _read_text(raw, value_off, length_field_off)


def check_tft_carries(tft: Path, version: str) -> None:
    """Raise unless the compiled TFT at ``tft`` embeds the ``tftVersion`` ``version``.

    The hub reinstalls a TFT until the display reports the required version, so a
    TFT published under a version it never reports is offered again forever.

    Raises:
        ValueError: The TFT does not carry the version.
    """
    # The compiled TFT stores the text as a NUL-terminated string.
    if b"\0" + version.encode("iso_8859_1") + b"\0" not in tft.read_bytes():
        raise ValueError(
            f"{tft.name} does not carry {TARGET_WIDGET} {version!r}; recompile it from its HMI"
        )


def shipped_tft_version(hmis: tuple[Path, ...] = DEFAULT_HMIS) -> str:
    """Return the version the HMIs and the TFTs compiled from them carry.

    Every HMI must name the same parseable version and its TFT must embed it: an
    HMI bumped without a recompile would advertise a version no display reports.

    Raises:
        ValueError: The HMIs disagree, the version does not parse, or a TFT does
            not carry the version.
    """
    versions = {hmi: read_tft_version(hmi) for hmi in hmis}
    if len(set(versions.values())) != 1:
        found = ", ".join(f"{hmi.name}={value!r}" for hmi, value in versions.items())
        raise ValueError(f"the HMIs disagree on {TARGET_WIDGET}: {found}")
    version = versions[hmis[0]]
    if re.fullmatch(r"\d+\.\d+\.\d+(?:\.dev\d+)?", version) is None:
        raise ValueError(f"{TARGET_WIDGET} {version!r} is not an X.Y.Z or X.Y.Z.devN version")
    for hmi in hmis:
        check_tft_carries(hmi.with_suffix(".tft"), version)
    return version


def bump_hmi(path: Path, version: str, check: bool = False) -> tuple[bool, str]:
    """Set ``tftVersion`` to ``version`` in ``path``.

    Returns ``(ok, message)``; ``ok`` is False when the edit cannot be made.
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
            f"{path.name}: would set {TARGET_WIDGET}.{TXT_NAME} {current!r} -> {version!r}",
        )
    old_crc = gp.block_crc(bytes(raw[block.start : block.end]))
    raw[value_off : value_off + len(version)] = version.encode("iso_8859_1")
    # Restamp the page block after the bytes changed.
    (old_stamp,) = struct.unpack_from("<I", raw, block.start)
    new_crc = gp.block_crc(bytes(raw[block.start : block.end]))
    struct.pack_into("<I", raw, block.start, old_stamp ^ old_crc ^ new_crc)
    path.write_bytes(bytes(raw))
    return True, f"{path.name}: set {TARGET_WIDGET}.{TXT_NAME} {current!r} -> {version!r}"


def regenerate_virtual_layouts() -> tuple[bool, str]:
    """Rewrite the virtual layouts that carry the HMIs' widget texts.

    Runs the generator as a subprocess, because it installs the ``homeassistant``
    stubs for itself.

    Returns:
        ``(ok, message)``; ``ok`` is False when the generator reports a problem.
    """
    result = subprocess.run(
        [sys.executable, "-m", VIRTUAL_LAYOUT_GENERATOR],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True, "regenerated the virtual layouts"
    detail = " ".join((result.stderr or result.stdout).split())
    return False, f"the virtual layouts could not be regenerated: {detail}"


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
    # A custom --hmi is not what the layouts under frontend/virtual are exported from,
    # and --check writes nothing, so only a write over both release HMIs refreshes them.
    if not failed and not args.check and args.hmi is None:
        ok, message = regenerate_virtual_layouts()
        print(("[OK] " if ok else "[FAIL] ") + message)
        failed = not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

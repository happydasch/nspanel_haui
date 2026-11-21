#!/usr/bin/env python3
"""Fail when the compiled firmware uses too much of its app partition.

The image an OTA update writes must fit an app partition with room for the next
update, so this measures the newest ``firmware.ota.bin`` (or ``firmware.bin``)
under the ESPHome build directory against the smallest app partition in the
generated ``partitions.csv``.

A warning is printed at 85% and the script fails at 92%. The percentages are
deliberately below a full partition: the next update needs space, and a build
that only just fits is a release risk.

Usage::

    python -m scripts.verify_firmware.check_size
    python -m scripts.verify_firmware.check_size --build-dir esphome/.esphome/build
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = ROOT / "esphome" / ".esphome" / "build"
WARN_PERCENT = 85.0
FAIL_PERCENT = 92.0
IMAGE_NAMES = ("firmware.ota.bin", "firmware.bin")
PARTITION_NAMES = ("partitions.csv",)


def parse_app_partitions(text: str) -> list[tuple[str, int]]:
    """Return ``(name, size)`` for every app partition in a ``partitions.csv``.

    The ESPHome/ESP-IDF layout is ``Name, Type, SubType, Offset, Size, Flags``
    with comments and blank lines around it. Sizes are hexadecimal or decimal
    and may carry a K/M suffix.
    """
    partitions: list[tuple[str, int]] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 5 or fields[1].lower() != "app":
            continue
        name, size_text = fields[0], fields[4]
        if not name or not size_text:
            continue
        try:
            size = _parse_size(size_text)
        except ValueError:
            continue
        partitions.append((name, size))
    return partitions


def _parse_size(text: str) -> int:
    """Parse ``0x1C0000``, ``1835008`` or ``1792K`` into bytes."""
    suffix = text[-1:].upper()
    if suffix in {"K", "M"}:
        return int(text[:-1], 0) * (1024 if suffix == "K" else 1024 * 1024)
    return int(text, 0)


def smallest_app_partition(partitions_csv: Path) -> int | None:
    """Return the smallest app partition size in ``partitions_csv``, or ``None``."""
    partitions = parse_app_partitions(partitions_csv.read_text(encoding="utf-8"))
    if not partitions:
        return None
    return min(size for _, size in partitions)


def newest_image(build_dir: Path) -> Path | None:
    """Return the newest compiled OTA or app image under ``build_dir``."""
    for name in IMAGE_NAMES:
        images = [path for path in build_dir.rglob(name) if path.is_file()]
        if images:
            return max(images, key=lambda path: path.stat().st_mtime)
    return None


def find_partitions_csv(image: Path, build_dir: Path | None = None) -> Path | None:
    """Return the nearest ``partitions.csv`` above ``image``, optionally inside ``build_dir``."""
    stop = build_dir.resolve() if build_dir is not None else None
    for directory in [image.parent, *image.parents]:
        for name in PARTITION_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        if stop is not None and directory.resolve() == stop:
            break
    return None


def check(
    image: Path, partition: int, warn: float = WARN_PERCENT, fail: float = FAIL_PERCENT
) -> tuple[int, str]:
    """Return ``(exit_code, message)`` for an image against its app partition.

    The exit code is 0 below the warning, 0 at or above the warning, and 1 at
    or above the failure percentage.
    """
    used = image.stat().st_size
    percent = 100 * used / partition
    message = f"flash {percent:.1f}% ({used:,} of {partition:,} bytes of the app partition)"
    if percent >= fail:
        return 1, f"{message}; at or above the {fail:.0f}% limit"
    if percent >= warn:
        return 0, f"{message}; at or above the {warn:.0f}% warning"
    return 0, message


def main(argv: list[str] | None = None) -> int:
    """Check the newest firmware image and print a GitHub Actions summary."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--name", default="firmware")
    parser.add_argument("--warn", type=float, default=WARN_PERCENT)
    parser.add_argument("--fail", type=float, default=FAIL_PERCENT)
    parser.add_argument("--summary", type=Path, help="append a Markdown line to this file")
    args = parser.parse_args(argv)

    image = newest_image(args.build_dir)
    if image is None:
        print(f"no firmware image found under {args.build_dir}", file=sys.stderr)
        return 1
    partitions_csv = find_partitions_csv(image, args.build_dir)
    if partitions_csv is None:
        print(f"no partitions.csv found above {image}", file=sys.stderr)
        return 1
    partition = smallest_app_partition(partitions_csv)
    if partition is None:
        print(f"no app partition in {partitions_csv}", file=sys.stderr)
        return 1

    code, message = check(image, partition, args.warn, args.fail)
    print(f"{args.name}: {message}")
    if args.summary is not None:
        summary = (
            f"**Firmware size**: {message}. "
            f"Warning at {args.warn:.0f}%, failure at {args.fail:.0f}%.\n"
        )
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary)
    return code


if __name__ == "__main__":
    sys.exit(main())

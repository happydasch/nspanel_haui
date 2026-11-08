#!/usr/bin/env python3
"""Bump the integration version in every place that must agree.

The firmware version and the version of its required display TFT are independent:
``yaml_version`` advances with every firmware release, while ``tft_version`` in
``esphome/nspanel_haui/version.yaml`` advances only when that release includes
a TFT update. The script always updates the integration, firmware and
``yaml_version`` sources; pass ``--tft-update`` to also update ``tft_version``
and both HMI ``system.tftVersion`` values.

A development version (``X.Y.Z.devN``, the ``.dev<run>`` shape the dev-release
CI publishes) is a firmware-only bump: it updates ``manifest.json`` and the
firmware ``yaml_version`` but leaves ``pyproject.toml``, ``tft_version`` and the
HMI binaries alone — the dev-release CI copies ``tft_version`` from the
HMIs' ``system.tftVersion`` itself.

``CHANGELOG.md`` is *not* edited: its heading carries the release date and its
content comes from the commits, so the maintainer writes it by hand.

A same-length TFT version change (``0.4.1`` -> ``0.4.2``) is written in place in
the HMI binaries. A longer or shorter version would resize the attribute record
and shift the rest of the page block, so the script refuses it — use the Nextion
Editor for a length-changing bump.

Usage:
    python -m scripts.bump_version 0.5.0                     # firmware-only release
    python -m scripts.bump_version 0.5.0 --tft-update        # release with a TFT update
    python -m scripts.bump_version 0.5.0 --check --tft-update  # dry run
    python -m scripts.bump_version 0.5.0.dev3                # dev firmware bump

Exit code 0 when every selected source carries the requested version (or was
updated), 1 when a source needs a manual edit (length-changing HMI bump, missing
widget).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "nspanel_haui" / "manifest.json"
PYPROJECT = ROOT / "pyproject.toml"
VERSION_YAML = ROOT / "esphome" / "nspanel_haui" / "version.yaml"

from scripts import bump_tft_version as hmi  # noqa: E402
from scripts.release.dev_version import version_kind as _shared_version_kind  # noqa: E402


def _version_kind(version: str) -> str | None:
    """Classify a supported release version as stable, dev, or invalid."""
    return _shared_version_kind(version)


def _display(path: Path) -> str:
    """A short path for messages; keeps temp paths readable in tests."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _replace_in_file(path: Path, pattern: str, replacement: str, check: bool) -> tuple[bool, str]:
    """Replace the first regex match in ``path``; report what changed."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"{_display(path)}: cannot read ({exc})"
    new_text, count = re.subn(pattern, replacement, text, count=1)
    if count == 0:
        return False, f"{_display(path)}: pattern not found ({pattern!r})"
    if new_text == text:
        return True, f"{_display(path)}: already up to date"
    if check:
        return False, f"{_display(path)}: would change"
    path.write_text(new_text, encoding="utf-8")
    return True, f"{_display(path)}: updated"


def bump_text_sources(version: str, check: bool, tft_update: bool = False) -> bool:
    """Update firmware version sources and, when requested, the TFT version.

    A stable ``X.Y.Z`` version updates ``manifest.json``, ``pyproject.toml``
    and the firmware ``yaml_version``. A development version (``X.Y.Z.devN``)
    is a firmware-only bump in the shape the dev-release CI writes:
    ``manifest.json`` and the firmware
    ``yaml_version`` advance, while ``pyproject.toml``, ``tft_version`` and the
    HMI binaries stay unchanged because the dev-release CI copies
    ``tft_version`` from the HMIs itself.
    """
    ok = True
    dev = _version_kind(version) == "dev"
    sources = [
        (MANIFEST, r'("version"\s*:\s*)"[^"]*"', rf'\g<1>"{version}"'),
        (VERSION_YAML, r"(?m)^(\s*yaml_version:\s*)'[^']*'", rf"\g<1>'{version}'"),
    ]
    if not dev:
        sources.insert(1, (PYPROJECT, r'(?m)^(version\s*=\s*)"[^"]*"', rf'\g<1>"{version}"'))
        if tft_update:
            sources.append(
                (VERSION_YAML, r"(?m)^(\s*tft_version:\s*)'[^']*'", rf"\g<1>'{version}'")
            )
    elif tft_update:
        print("note: development version: leaving TFT sources unchanged")
    for path, pattern, replacement in sources:
        changed, message = _replace_in_file(path, pattern, replacement, check)
        print(("[OK] " if changed else "[FAIL] ") + message)
        ok = ok and changed
    return ok


def bump_hmis(version: str, check: bool) -> bool:
    """Update the ``tftVersion`` text of both release HMI binaries."""
    ok = True
    for path in hmi.DEFAULT_HMIS:
        if not path.exists():
            print(f"[FAIL] {path.relative_to(ROOT)}: not found")
            ok = False
            continue
        changed, message = hmi.bump_hmi(path, version, check=check)
        print(("[OK] " if changed else "[FAIL] ") + message)
        ok = ok and changed
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("version", help="version to write, e.g. 0.5.0")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change without writing any file",
    )
    tft_group = parser.add_mutually_exclusive_group()
    tft_group.add_argument(
        "--tft-update",
        action="store_true",
        help="also bump the TFT version and both HMI binaries",
    )
    tft_group.add_argument(
        "--text-only",
        action="store_true",
        help="legacy alias for a firmware-only release (TFT versions stay unchanged)",
    )
    args = parser.parse_args(argv)

    version = args.version.strip()
    kind = _version_kind(version)
    if kind is None:
        print(
            f"error: version must be stable (X.Y.Z) or a dev version (X.Y.Z.devN); got {version!r}",
            file=sys.stderr,
        )
        return 2

    ok = bump_text_sources(version, args.check, tft_update=args.tft_update)
    # Only a stable bump can advance the TFT sources: a dev version must never
    # move tft_version or the HMI binaries (the dev-release CI copies tft_version
    # from the HMIs instead).
    if args.tft_update and kind == "stable":
        ok = bump_hmis(version, args.check) and ok
    if args.check:
        print("\n--check: nothing was written.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

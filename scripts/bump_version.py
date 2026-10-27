#!/usr/bin/env python3
"""Bump the integration version in every place that must agree.

The release checklist lists four version sources plus the ``CHANGELOG.md``
heading.  Editing them by hand is error-prone (the HMI ``system.tftVersion``
is a text attribute in a binary file, so a typo there only shows up when the
release gate fails after a TFT recompile).  This script does all of them in one
pass:

1. ``custom_components/nspanel_haui/manifest.json`` — source of truth.
2. ``pyproject.toml`` — packaging mirror.
3. ``esphome/nspanel_haui/version.yaml`` — firmware compatibility version.
4. ``nextion/nspanel_haui.HMI`` and ``nextion/nspanel_haui_portrait.HMI`` —
   the ``system.tftVersion`` text attribute.

``CHANGELOG.md`` is *not* edited: its heading carries the release date and its
content comes from the commits, so the maintainer writes it by hand.

A same-length version change (``0.4.1`` -> ``0.4.2``) is written in place in the
HMI binaries.  A longer or shorter version would resize the attribute record and
shift the rest of the page block, so the script refuses it — use the Nextion
Editor for a length-changing bump.

Usage:
    python scripts/bump_version.py 0.5.0            # bump every source
    python scripts/bump_version.py 0.5.0 --check    # report without writing
    python scripts/bump_version.py 0.5.0 --text-only  # skip the HMI binaries

Exit code 0 when every source carries the requested version (or was updated),
1 when a source needs a manual edit (length-changing HMI bump, missing widget).
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

sys.path.insert(0, str(ROOT / "scripts"))
import bump_tft_version as hmi  # noqa: E402


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


def bump_text_sources(version: str, check: bool) -> bool:
    """Update manifest.json, pyproject.toml and version.yaml."""
    ok = True
    for path, pattern, replacement in (
        (MANIFEST, r'("version"\s*:\s*)"[^"]*"', rf'\g<1>"{version}"'),
        (PYPROJECT, r'(?m)^(version\s*=\s*)"[^"]*"', rf'\g<1>"{version}"'),
        (VERSION_YAML, r"(?m)^(\s*yaml_version:\s*)'[^']*'", rf"\g<1>'{version}'"),
    ):
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
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="update the text sources only; skip the HMI binaries",
    )
    args = parser.parse_args(argv)

    version = args.version.strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"error: version must look like X.Y.Z, got {version!r}", file=sys.stderr)
        return 2

    ok = bump_text_sources(version, args.check)
    if not args.text_only:
        ok = bump_hmis(version, args.check) and ok
    if args.check:
        print("\n--check: nothing was written.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

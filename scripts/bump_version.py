#!/usr/bin/env python3
"""Bump the integration version in every place that must agree.

``yaml_version`` advances with every firmware release, ``tft_version`` only with a
release that carries a TFT update (``--tft-update``, which also writes both HMI
``system.tftVersion`` values). A development version (``X.Y.Z.devN``) is a
firmware-only bump: ``manifest.json`` and ``yaml_version`` change, while
``pyproject.toml``, ``tft_version`` and the HMIs stay as the dev-release CI
leaves them (it copies ``tft_version`` from the HMIs itself).

``CHANGELOG.md`` is not edited: its heading carries the release date.

Usage:
    python -m scripts.bump_version 0.5.0 [--tft-update] [--check]
    python -m scripts.bump_version --check      # verify against manifest.json
"""

from __future__ import annotations

import argparse
import json
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


def _manifest_version() -> str:
    """The version every other source must mirror: ``manifest.json`` is the source of truth."""
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]


def bump_text_sources(version: str, check: bool, tft_update: bool = False) -> bool:
    """Update firmware version sources and, when requested, the TFT version.

    A development version updates only ``manifest.json`` and ``yaml_version``.
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
    if ok and not check:
        # The virtual layouts embed this text as a widget attribute.
        ok, message = hmi.regenerate_virtual_layouts()
        print(("[OK] " if ok else "[FAIL] ") + message)
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "version",
        nargs="?",
        help="version to write, e.g. 0.5.0 (with --check: defaults to manifest.json's version)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change without writing any file",
    )
    parser.add_argument(
        "--tft-update",
        action="store_true",
        help="also bump the TFT version and both HMI binaries",
    )
    args = parser.parse_args(argv)

    if args.version is None:
        # A dry run without a version is the drift check: every other source must
        # mirror the manifest. Writing needs an explicit version, because a stale
        # --tft-update would otherwise move tft_version to the firmware version.
        if not args.check:
            print(
                "error: pass the version to write (--check alone verifies manifest.json)",
                file=sys.stderr,
            )
            return 2
        version = _manifest_version()
    else:
        version = args.version.strip()
    kind = _version_kind(version)
    if kind is None:
        print(
            f"error: version must be stable (X.Y.Z) or a dev version (X.Y.Z.devN); got {version!r}",
            file=sys.stderr,
        )
        return 2

    ok = bump_text_sources(version, args.check, tft_update=args.tft_update)
    # Only a stable bump advances the TFT sources; a dev version must never move
    # tft_version or the HMIs.
    if args.tft_update and kind == "stable":
        ok = bump_hmis(version, args.check) and ok
    if args.check:
        print("\n--check: nothing was written.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

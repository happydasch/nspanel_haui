#!/usr/bin/env python3
"""Fail when a Nextion HMI or TFT changed without advancing the display TFT version.

A screen change committed under an unchanged ``system.tftVersion`` never reaches
a panel that already reports that version: the hub only installs a display image
whose version is newer than the reported one. The release docs therefore require
a TFT version bump whenever an HMI or a compiled TFT changes.

CI compares the HMI and TFT files and the configured ``tft_version`` against the
commit the change is based on (the PR merge base or the pushed-from commit) and
fails when one of them changed while the TFT version did not advance.

Usage:
    python -m scripts.verify_nextion.check_hmi_bump --base origin/dev

Exit code 0 when no HMI or TFT changed or the TFT version advanced, 1 when the
version is missing or did not advance, 2 when git cannot resolve the base commit
or read its ``version.yaml``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_YAML = ROOT / "esphome" / "nspanel_haui" / "version.yaml"
DISPLAY_ASSETS = ("nextion/*.HMI", "nextion/*.tft")

TFT_VERSION_RE = re.compile(r"^\s*tft_version:\s*'?([^'\s]+)'?", re.MULTILINE)
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.dev(\d+))?$")


def read_tft_version(text: str) -> str:
    """Return the ``tft_version`` substitution of a ``version.yaml`` text."""
    match = TFT_VERSION_RE.search(text)
    return match.group(1) if match else ""


def version_key(version: str) -> tuple[int, int, int, int, int] | None:
    """Return a sortable key for ``X.Y.Z`` and ``X.Y.Z.devN`` versions.

    PEP 440 orders ``X.Y.Z.devN`` before the final ``X.Y.Z``: the fourth tuple
    element is 0 for a dev build and 1 for a final one.
    """
    match = VERSION_RE.fullmatch(version)
    if match is None:
        return None
    major, minor, patch, dev = match.groups()
    if dev is None:
        return (int(major), int(minor), int(patch), 1, 0)
    return (int(major), int(minor), int(patch), 0, int(dev))


def evaluate(changed: list[str], base_version: str, head_version: str) -> tuple[bool, str]:
    """Decide whether the TFT version advanced with the changed HMI and TFT files.

    Returns:
        ``(ok, message)``: ``ok`` is True when no HMI or TFT changed or the
        version advanced.
    """
    if not changed:
        return True, "no Nextion HMI or TFT changed"
    names = ", ".join(changed)
    if not base_version or not head_version:
        return (
            False,
            f"{names} changed, but the display TFT version is missing "
            f"(base {base_version!r}, now {head_version!r}); set tft_version in "
            "esphome/nspanel_haui/version.yaml",
        )
    base_key = version_key(base_version)
    head_key = version_key(head_version)
    if base_key is None or head_key is None:
        return (
            False,
            "the display TFT version must be X.Y.Z or X.Y.Z.devN; "
            f"base {base_version!r}, now {head_version!r}",
        )
    if head_key <= base_key:
        return (
            False,
            f"{names} changed, but the display TFT version did not advance "
            f"({base_version!r} -> {head_version!r}). Bump system.tftVersion in "
            "both HMIs and tft_version in esphome/nspanel_haui/version.yaml "
            "(scripts/bump_tft_version.py --version <new>), then recompile both "
            "TFTs.",
        )
    return True, f"display TFT version advanced {base_version!r} -> {head_version!r}"


def _git(*args: str, root: Path = ROOT) -> str:
    """Run git in ``root`` and return stdout, raising CalledProcessError."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def resolve_base(base: str, root: Path = ROOT) -> str:
    """Return the commit the change is compared against.

    A pull request passes its base branch tip; the merge base excludes commits
    that landed on the base branch after the PR was opened. A push passes the
    commit it was pushed from, which is normally an ancestor already.
    """
    try:
        return _git("merge-base", base, "HEAD", root=root).strip()
    except subprocess.CalledProcessError:
        return _git("rev-parse", "--verify", f"{base}^{{commit}}", root=root).strip()


def changed_display_assets(base: str, root: Path = ROOT) -> list[str]:
    """Return the Nextion HMI and TFT files that differ between ``base`` and HEAD."""
    output = _git("diff", "--name-only", base, "HEAD", "--", *DISPLAY_ASSETS, root=root)
    return output.splitlines()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base",
        required=True,
        help="commit or ref the change is compared against (PR base or pushed-from commit)",
    )
    args = parser.parse_args(argv)
    base = args.base.strip()

    if not base:
        print("error: --base is empty; cannot compare the change", file=sys.stderr)
        return 2
    if re.fullmatch(r"0+", base):
        print("[SKIP] no previous commit to compare against (new branch)")
        return 0

    try:
        base_commit = resolve_base(base, root=ROOT)
        changed = changed_display_assets(base_commit, root=ROOT)
        if not changed:
            print("[OK] no Nextion HMI or TFT changed")
            return 0
        base_version = read_tft_version(
            _git("show", f"{base_commit}:{VERSION_YAML.relative_to(ROOT)}", root=ROOT)
        )
    except subprocess.CalledProcessError as exc:
        print(f"error: git failed: {exc.stderr.strip() or exc}", file=sys.stderr)
        return 2

    head_version = read_tft_version(VERSION_YAML.read_text(encoding="utf-8"))
    ok, message = evaluate(changed, base_version, head_version)
    print(("[OK] " if ok else "[FAIL] ") + message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

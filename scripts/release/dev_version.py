#!/usr/bin/env python3
"""Derive the version of a development firmware build; change no file.

``dev-firmware.yml`` hands the printed version to ``scripts.bump_version``, which
writes it into ``manifest.json`` and ``version.yaml``; the workflow commits that bump
to ``dev`` and tags the commit, so the image, the tag and an integration installed
from ``dev`` all report the same version.

The base advances with the release: the newest ``vX.Y.Z`` tag reachable from HEAD
gives ``X.Y.(Z+1)``, so the first build after a release is that release's
successor and a patch cycle needs no bump commit. A minor or major cycle passes
its base explicitly, as that cycle's first dev version (``--base 0.6.0.dev0``),
because a dev base keeps its own ``X.Y.Z`` while a stable one is read as its next
patch.

Usage:
    python -m scripts.release.dev_version 77                     # from the newest tag
    python -m scripts.release.dev_version 77 --base 0.6.0.dev0    # a new cycle
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from scripts.bump_tft_version import shipped_tft_version

_STABLE_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_DEV_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)\.dev\d+")


def version_kind(version: str) -> str | None:
    """Classify a supported release version as stable, dev, or invalid.

    Shared with ``scripts.bump_version``: one definition of what each kind is.
    """
    if _STABLE_RE.fullmatch(version):
        return "stable"
    if _DEV_RE.fullmatch(version):
        return "dev"
    return None


def next_patch(version: str) -> str:
    """The version after a stable ``X.Y.Z``: the next patch release."""
    match = _STABLE_RE.fullmatch(version)
    if not match:
        raise ValueError(f"Expected a stable X.Y.Z release, got {version!r}")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


def derive_dev_version(base_version: str, run_number: str | int) -> str:
    """Derive the PEP 440 dev version from a base version and the run number.

    ``run_number`` is the repository-wide Actions counter and is deliberately not
    reset, so every build stays unique and monotonic even when a run is cancelled
    or its tag push is retried.
    """
    previous_dev = _DEV_RE.fullmatch(base_version)
    base = ".".join(previous_dev.groups()) if previous_dev else next_patch(base_version)

    version = f"{base}.dev{run_number}"
    if not _DEV_RE.fullmatch(version):
        raise ValueError(f"{version!r} is not a publishable PEP 440 development version")
    return version


def base_from_tags(root: Path) -> str:
    """The released version the newest ``v*`` tag names, or an error without one."""
    done = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if done.returncode:
        raise ValueError(f"no vX.Y.Z tag reachable from HEAD: {done.stderr.strip()}")
    return done.stdout.strip().removeprefix("v")


def main(argv: list[str] | None = None) -> int:
    """Print the version, and hand it to the workflow through GITHUB_OUTPUT."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_number", help="the workflow run number")
    parser.add_argument("--base", help="the base version (default: from the newest tag)")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    try:
        version = derive_dev_version(args.base or base_from_tags(root), args.run_number)
        tft_version = shipped_tft_version()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"version={version}\ntft_version={tft_version}\n")
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

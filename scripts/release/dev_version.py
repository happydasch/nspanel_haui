#!/usr/bin/env python3
"""Derive the version of a development firmware build; change no file.

``dev-firmware.yml`` hands the printed version to ``scripts.bump_version``, which
writes it into ``manifest.json`` and ``version.yaml``; the workflow commits that bump
to ``dev`` and tags the commit, so the image, the tag and an integration installed
from ``dev`` all report the same version.

The build continues the cycle the branch already reports, because that bot commit is
what puts it there: after a cycle was opened with ``--base 0.6.0.dev0``, the branch
carries ``0.6.0.dev<run>`` and every later build repeats ``0.6.0`` with its own run
number. The newest ``vX.Y.Z`` tag reachable from HEAD only supplies a floor, as its
next patch, so a hotfix released from ``master`` that ``dev`` does not carry yet cannot
be built over, and the ``X.Y.Z.devN`` tags already in the repository are a floor of
their own: a build never publishes below a dev release that exists, which Home
Assistant, the hub and the GitHub release list would each order below that older one.
The newest of those floors wins, so a development version never counts backwards.
A minor or major cycle passes its base explicitly, as that cycle's first dev version
(``--base 0.6.0.dev0``), because a dev base keeps its own ``X.Y.Z`` while a stable one
is read as its next patch.

Usage:
    python -m scripts.release.dev_version 77                      # the branch's cycle
    python -m scripts.release.dev_version 77 --base 0.6.0.dev0    # a new cycle
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from scripts.bump_tft_version import shipped_tft_version

MANIFEST = Path("custom_components") / "nspanel_haui" / "manifest.json"
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(\.dev\d+)?")
_DEV_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)\.dev\d+")


def _numbers(version: str) -> tuple[int, int, int] | None:
    """The X.Y.Z numbers of a stable or dev version, or None for an unsupported one."""
    match = _VERSION_RE.fullmatch(version)
    if not match:
        return None
    major, minor, patch = match.group(1), match.group(2), match.group(3)
    return int(major), int(minor), int(patch)


def version_kind(version: str) -> str | None:
    """Classify a supported release version as stable, dev, or invalid.

    Shared with ``scripts.bump_version``: one definition of what each kind is.
    """
    if _numbers(version) is None:
        return None
    return "dev" if _DEV_RE.fullmatch(version) else "stable"


def next_patch(version: str) -> str:
    """The version after a stable ``X.Y.Z``: the next patch release."""
    numbers = _numbers(version)
    if numbers is None or version_kind(version) != "stable":
        raise ValueError(f"Expected a stable X.Y.Z release, got {version!r}")
    major, minor, patch = numbers
    return f"{major}.{minor}.{patch + 1}"


def cycle_of(version: str) -> str:
    """The ``X.Y.Z`` a version belongs to: a dev version's own, a stable version's next patch.

    A stable version is a release that is done, so the branch works toward its
    successor; a dev version names the release its own builds lead to.
    """
    numbers = _numbers(version)
    if numbers is None:
        raise ValueError(f"Expected a stable X.Y.Z or a X.Y.Z.devN version, got {version!r}")
    if version_kind(version) == "stable":
        return next_patch(version)
    major, minor, patch = numbers
    return f"{major}.{minor}.{patch}"


def _cycle_order(cycle: str) -> tuple[int, ...]:
    """The numeric order of an ``X.Y.Z`` cycle, which as strings would sort 0.10 below 0.9."""
    return tuple(int(part) for part in cycle.split("."))


def _version_order(version: str) -> tuple[int, ...]:
    """The numeric order of a dev version: its cycle first, then its build number."""
    numbers = _numbers(version)
    if numbers is None or version_kind(version) != "dev":
        raise ValueError(f"Expected a X.Y.Z.devN version, got {version!r}")
    return (*numbers, int(version.rsplit(".dev", 1)[1]))


def resolve_cycle(
    requested: str | None,
    branch_version: str,
    released_version: str,
    published: Iterable[str] = (),
) -> str:
    """The cycle of the build: the highest the branch or a dev release already carries.

    Args:
        requested: The ``--base`` input, or None to continue what the branch reports.
        branch_version: The version ``manifest.json`` names on the branch.
        released_version: The stable version the newest ``vX.Y.Z`` tag names.
        published: The dev versions the repository has already tagged.

    Returns:
        The ``X.Y.Z`` cycle for :func:`dev_version_for_cycle`.

    Raises:
        ValueError: The base is below a cycle that is already published.
    """
    floors = [cycle_of(branch_version), next_patch(released_version)]
    floors.extend(cycle_of(version) for version in published)
    floor = max(floors, key=_cycle_order)
    if requested is None:
        # A released hotfix reaches dev late (its pull request merges back after the
        # tag), so the tag's successor stays a floor under the branch's own cycle, and
        # a dev release that is already out is a floor for the same reason.
        return floor

    cycle = cycle_of(requested)
    if _cycle_order(cycle) < _cycle_order(floor):
        raise ValueError(
            f"--base {requested} builds {cycle}, below {floor}, which the branch "
            "already reports or a dev release already carries: "
            "a development build never counts backwards"
        )
    return cycle


def dev_version_for_cycle(cycle: str, run_number: str | int) -> str:
    """The PEP 440 dev version of a cycle and a run number.

    ``run_number`` is the repository-wide Actions counter and is deliberately not
    reset, so every build stays unique and monotonic even when a run is cancelled
    or its tag push is retried.
    """
    version = f"{cycle}.dev{run_number}"
    if not _DEV_RE.fullmatch(version):
        raise ValueError(f"{version!r} is not a publishable PEP 440 development version")
    return version


def refuse_below_published(version: str, published: Iterable[str]) -> None:
    """Refuse a version that does not order above every dev version already published.

    Home Assistant, the hub's update check and the GitHub release list all order
    releases by version, so a build below an earlier one is never offered as an
    update and reads as an older release everywhere.

    Args:
        version: The derived ``X.Y.Z.devN`` version.
        published: The dev versions the repository has already tagged.

    Raises:
        ValueError: A published dev version sorts at or above ``version``.
    """
    newest = max(published, key=_version_order, default=None)
    if newest is not None and _version_order(version) <= _version_order(newest):
        raise ValueError(
            f"{version} does not order above {newest}, which is already published: "
            "every development build must be the highest version so far"
        )


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


def published_dev_versions(root: Path) -> list[str]:
    """The dev versions the repository has already tagged, in version order.

    ``dev-firmware.yml`` fetches the tags before it derives a version, so this list is
    the published dev release list as well: the prune step keeps the newest ones.

    Raises:
        ValueError: ``git tag`` failed.
    """
    done = subprocess.run(
        ["git", "tag", "--list"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if done.returncode:
        raise ValueError(f"cannot list tags: {done.stderr.strip()}")
    versions = [tag.removeprefix("v") for tag in done.stdout.split()]
    return sorted(
        (version for version in versions if version_kind(version) == "dev"),
        key=_version_order,
    )


def branch_version(root: Path) -> str:
    """The version ``manifest.json`` names on the branch: the cycle the branch works toward."""
    path = root / MANIFEST
    try:
        return json.loads(path.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: no integration version ({exc})") from exc


def main(argv: list[str] | None = None) -> int:
    """Print the version, and hand it to the workflow through GITHUB_OUTPUT."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_number", help="the workflow run number")
    parser.add_argument("--base", help="the base version (default: from the branch and the tag)")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    try:
        published = published_dev_versions(root)
        cycle = resolve_cycle(args.base, branch_version(root), base_from_tags(root), published)
        version = dev_version_for_cycle(cycle, args.run_number)
        refuse_below_published(version, published)
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

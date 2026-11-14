#!/usr/bin/env python3
"""Write the release notes of a development firmware build (dev-firmware.yml).

A dispatched build has no push range, so the notes list the commits since the
newest tag reachable from the build commit: the previous development build's
tag, or the stable release after a master merge-back.

Reads ``GITHUB_REPOSITORY``, ``GITHUB_SHA``, ``DEV_VERSION`` and ``TFT_VERSION``
and writes ``dev-release-notes.md``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

NOTES = Path("dev-release-notes.md")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def previous_tag(commit: str) -> str:
    """Return the newest tag reachable from ``commit``, or ``""`` without one."""
    try:
        return _git("describe", "--tags", "--abbrev=0", commit)
    except subprocess.CalledProcessError:
        return ""


def build_notes(
    repo: str,
    commit: str,
    version: str,
    tft_version: str,
    commits: list[tuple[str, str]],
    changes: str,
) -> str:
    """Return the notes for ``commits`` (sha, subject) and the ``git --stat`` ``changes``."""
    notes = [
        f"Development firmware `{version}`",
        "",
        f"Build commit: [`{commit[:7]}`](https://github.com/{repo}/commit/{commit})",
        "Firmware variant: `universal` (for universal test panels only).",
        f"Display TFT: `{tft_version}`.",
        "",
        "## Commits in this build",
    ]
    notes.extend(
        f"- [`{sha[:7]}`](https://github.com/{repo}/commit/{sha}) {subject}"
        for sha, subject in commits
    )
    if not commits:
        notes.append("No commits since the previous release.")
    if changes:
        notes.extend(["", "## Changed files", "```text", changes, "```"])
    return "\n".join(notes) + "\n"


def main() -> None:
    """Write the notes for the build commit of this workflow run."""
    commit = os.environ["GITHUB_SHA"]
    previous = previous_tag(commit)
    if previous:
        print(f"Notes range: {previous}..{commit}")
        commit_range = f"{previous}..{commit}"
        changes = _git("diff", "--stat", "--no-renames", previous, commit)
    else:
        print("Notes range: whole history (no reachable tag)")
        commit_range = commit
        changes = _git("show", "--format=", "--stat", "--no-renames", commit)
    commits = []
    for line in _git("log", "--reverse", "--format=%H%x09%s", commit_range).splitlines():
        sha, _, subject = line.partition("\t")
        commits.append((sha, subject))
    NOTES.write_text(
        build_notes(
            os.environ["GITHUB_REPOSITORY"],
            commit,
            os.environ["DEV_VERSION"],
            os.environ["TFT_VERSION"],
            commits,
            changes,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

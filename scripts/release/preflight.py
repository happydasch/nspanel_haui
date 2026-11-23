#!/usr/bin/env python3
"""Report what a stable release still needs, without changing anything.

Run it on a ``release/X.Y.Z`` branch before the PR into ``master``; the runbook in
``docs/develop/release.md`` stays the procedure. Each item is *passed*, *regenerate*
(the output names the command that rewrites it), *manual* (a human step, or a check
that could not run here) or *failed* (the tree contradicts itself). The exit code is
1 only for a failed item, so a release is never blocked by a step that belongs to a
person; ``--strict`` also fails on a stale item. Nothing here builds, tags or
publishes: that stays with ``release.yml`` and ``scripts/release/publish_stable.py``.

Usage::

    python -m scripts.release.preflight                 # on release/X.Y.Z
    python -m scripts.release.preflight --draft          # and print a draft body
    python -m scripts.release.preflight --strict         # stale screens also fail
    python -m scripts.release.preflight --skip-screens   # no Chrome here
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.release.publish_stable import REPO
from scripts.verify_nextion.check_hmi_bump import read_tft_version

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "custom_components" / "nspanel_haui" / "manifest.json"
VERSION_YAML = ROOT / "esphome" / "nspanel_haui" / "version.yaml"
CHANGELOG = ROOT / "CHANGELOG.md"
NOTES_DIR = ROOT / ".github" / "release-notes"

# What the screen overview draws: only such a change can make a screenshot stale.
DISPLAY_INPUTS = (
    "nextion",
    "custom_components/nspanel_haui/haui/page",
    "custom_components/nspanel_haui/haui/mapping",
    "custom_components/nspanel_haui/frontend/virtual",
    "custom_components/nspanel_haui/frontend/previews",
    "custom_components/nspanel_haui/frontend/styles",
)
# The changelog's section heading that asks for a release-notes heading.
NOTE_HEADINGS = {
    "### Breaking changes": "## Before updating",
    "### Added": "## Added",
    "### Changed": "## Changed",
    "### Fixed": "## Fixed",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

PASSED = "passed"
REGENERATE = "regenerate"
MANUAL = "manual"
FAILED = "failed"


@dataclass
class Row:
    """One line of the report."""

    item: str
    status: str
    detail: str


def git(*args: str) -> str:
    """Run git here and return its stripped stdout; RuntimeError when it fails."""
    done = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.strip()


def release_version(branch: str, given: str | None) -> str | None:
    """The stable version this branch names, or None when it names none."""
    if given:
        return given if VERSION_RE.match(given) else None
    match = re.fullmatch(r"release/(\d+\.\d+\.\d+)", branch)
    return match.group(1) if match else None


def changelog_section(text: str, version: str) -> str:
    """The changelog's section for one version, without the following sections."""
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("## ") and f"[{version}]" in line
        ),
        None,
    )
    if start is None:
        return ""
    section = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        section.append(line)
    return "\n".join(section).strip()


def required_note_headings(section: str) -> list[str]:
    """The release-notes headings the changelog's section asks for."""
    required = []
    for changelog_heading, note_heading in NOTE_HEADINGS.items():
        current = None
        for line in section.splitlines():
            if line.startswith("### "):
                current = line.strip()
            elif current == changelog_heading and line.startswith("- "):
                required.append(note_heading)
                break
    return required


def missing_headings(notes: str, required: list[str]) -> list[str]:
    """The required release-notes headings the file does not carry, in order."""
    present = {line.strip() for line in notes.splitlines() if line.startswith("## ")}
    return [heading for heading in required if heading not in present]


def display_inputs_changed(paths: list[str]) -> bool:
    """Whether any changed path can change what the screen overview shows."""
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for path in paths
        for prefix in DISPLAY_INPUTS
    )


def draft_body(version: str, previous: str | None, section: str, commits: list[str]) -> str:
    """A draft of the published release body; a person edits it before publishing."""
    # `previous` is a tag name, so it already carries the `v` the URL spells itself.
    previous_version = (previous or "").removeprefix("v")
    compare = (
        f"https://github.com/{REPO}/compare/v{previous_version}...v{version}"
        if previous_version
        else f"https://github.com/{REPO}/releases/tag/v{version}"
    )
    lines = [f"# v{version}", "", compare, ""]
    if section:
        lines += [section, ""]
    if commits:
        lines += ["## Commits", "", *(f"- {subject}" for subject in commits), ""]
    return "\n".join(lines).strip() + "\n"


def newest_tag(*patterns: str, exclude: str = "") -> str | None:
    """The newest version tag matching the patterns."""
    tags = []
    for pattern in patterns:
        tags += git("tag", "--list", pattern, "--sort=-v:refname").splitlines()
    ordered = [tag for tag in tags if tag and exclude not in tag]
    return ordered[0] if ordered else None


def run_module(module: str, *args: str) -> tuple[int, str]:
    """Run a repository script with this interpreter; return (exit code, last line)."""
    done = subprocess.run(
        [sys.executable, "-m", module, *args], cwd=ROOT, capture_output=True, text=True
    )
    output = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return done.returncode, output[-1] if output else ""


def check_version(version: str | None) -> list[Row]:
    """Compare the manifest's version with the branch and the generated mirrors."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    tft_version = read_tft_version(VERSION_YAML.read_text(encoding="utf-8"))
    if version is None:
        return [
            Row(
                "version",
                MANUAL,
                f"not on release/X.Y.Z and no --version; the manifest says {manifest}",
            )
        ]
    status = PASSED if manifest == version else FAILED
    detail = f"manifest {manifest}, release {version}, tft_version {tft_version}"
    rows = [Row("version", status, detail)]
    code, line = run_module("scripts.bump_version", manifest, "--check")
    rows.append(
        Row(
            "version mirrors",
            PASSED if code == 0 else FAILED,
            line or "bump_version --check reported nothing",
        )
    )
    return rows


def check_display_assets() -> Row:
    """Run the TFT-version gate for a change based on master."""
    try:
        code, line = run_module("scripts.verify_nextion.check_hmi_bump", "--base", "origin/master")
    except OSError as error:  # no interpreter, no git — not a release failure
        return Row("display assets", MANUAL, f"could not run: {error}")
    if code == 0:
        return Row("display assets", PASSED, line)
    if code == 1:
        return Row("display assets", FAILED, line)
    return Row("display assets", MANUAL, f"could not compare with origin/master: {line}")


def check_screens(*, skip: bool) -> Row:
    """Compare the screen overview with a fresh render when a display input changed."""
    baseline = newest_tag("v*dev*") or newest_tag("v*", exclude="dev")
    if baseline is None:
        changed = git("ls-files", *(f"{prefix}/**" for prefix in DISPLAY_INPUTS)).splitlines()
        detail = "no version tag to compare against"
    else:
        try:
            changed = git(
                "diff", "--name-only", f"{baseline}..HEAD", "--", *DISPLAY_INPUTS
            ).splitlines()
        except RuntimeError as error:
            return Row("screens", MANUAL, f"could not diff against {baseline}: {error}")
        detail = f"no display change since {baseline}"
    if not display_inputs_changed(changed):
        return Row("screens", PASSED, detail)
    if skip:
        return Row(
            "screens", MANUAL, f"skipped (--skip-screens); display inputs changed since {baseline}"
        )
    code, line = run_module("scripts.preview_gallery.gen_preview_gallery", "--check")
    if code == 0:
        return Row("screens", PASSED, line)
    return Row("screens", REGENERATE, line)


def check_release_notes(version: str | None) -> Row:
    """Check the release-notes file against the changelog's section."""
    if version is None:
        return Row("release notes", MANUAL, "no version to name the file after")
    path = NOTES_DIR / f"v{version}.md"
    if not path.is_file():
        return Row(
            "release notes",
            MANUAL,
            f"{path.relative_to(ROOT)} is missing; release.yml then links the changelog",
        )
    required = required_note_headings(
        changelog_section(CHANGELOG.read_text(encoding="utf-8"), version)
    )
    missing = missing_headings(path.read_text(encoding="utf-8"), required)
    if missing:
        return Row("release notes", MANUAL, "missing " + ", ".join(missing))
    return Row("release notes", PASSED, f"{path.relative_to(ROOT)} covers the changelog")


MANUAL_REMAINDER = (
    "always manual, this check cannot do it:",
    "  - make -j4 check, make hmi-check and make esphome-config on the candidate",
    "  - compile both TFTs in the Nextion Editor when an HMI changed (and advance tft_version)",
    "  - the published-asset and hardware passes on a real EU and US panel",
    "  - squash-merge release/X.Y.Z into master with a clean body",
    "  - python -m scripts.release.publish_stable --push vX.Y.Z",
)


def main(argv: list[str] | None = None) -> int:
    """Report every release item and return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--version", help="the version being released (default: from release/X.Y.Z)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="also fail on a stale screen overview"
    )
    parser.add_argument(
        "--skip-screens", action="store_true", help="do not run the Chrome comparison"
    )
    parser.add_argument("--draft", action="store_true", help="print a draft release body")
    args = parser.parse_args(argv)

    try:
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    version = release_version(branch, args.version)

    rows = [*check_version(version), check_display_assets(), check_screens(skip=args.skip_screens)]
    rows.append(check_release_notes(version))

    width = max(len(row.item) for row in rows)
    print(f"release preflight on {branch}")
    for row in rows:
        print(f"  {row.status:<10}  {row.item:<{width}}  {row.detail}")
    print()
    for line in MANUAL_REMAINDER:
        print(line)

    if args.draft:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
        previous = newest_tag("v*", exclude="dev")
        commits = [
            line
            for line in git(
                "log", "--pretty=- %s", "--no-merges", "origin/master..HEAD"
            ).splitlines()
            if line.startswith("- ")
        ]
        section = changelog_section(CHANGELOG.read_text(encoding="utf-8"), version or manifest)
        print()
        print("--- draft release body (stdout only, never published) ---")
        print(draft_body(version or manifest, previous, section, commits), end="")

    failures = [row for row in rows if row.status == FAILED]
    stale = [row for row in rows if row.status == REGENERATE]
    if failures or (args.strict and stale):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

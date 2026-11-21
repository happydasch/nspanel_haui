#!/usr/bin/env python3
"""Bring ``master`` and ``dev`` back in step once a stable release is published.

A release tags a commit on ``master``, so afterwards ``dev`` lacks the released
version files and ``master`` lacks the dev history. This script closes both gaps in
one pull request: a ``sync/vX.Y.Z`` branch off ``dev`` merges ``master`` into it (a
file both sides rewrote takes the release's version, everything ``dev`` changed
elsewhere survives) and opens the next changelog section; the branch is merged
through the "Protect master (release-only)" ruleset, which refuses a direct push;
``dev`` is then fast-forwarded to that merge commit, so both branches end on one tree.

Nothing here builds, tags or publishes: the stable release workflow runs ``--apply``
once it has published the release, and you run the same command by hand when that
job failed. Every git command runs in a throwaway worktree, so the checkout that
starts the script is never modified.

Usage::

    python -m scripts.release.sync_branches                  # report, change nothing
    python -m scripts.release.sync_branches --apply          # sync both branches
    python -m scripts.release.sync_branches --apply --version 0.5.3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from scripts.release.publish_stable import REPO, remote_is_canonical

MANIFEST = "custom_components/nspanel_haui/manifest.json"
WORKFLOW = "ci.yml"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
RELEASED_RE = re.compile(r"^\d+\.\d+\.\d+$")
REFERENCE_RE = re.compile(r"^\[\d")


def run(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> str:
    """Run a command and return its stripped stdout; raise RuntimeError when it fails."""
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    if check and done.returncode:
        raise RuntimeError(f"{' '.join(args)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout.strip()


def git(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> str:
    """Run one git command and return its stripped stdout."""
    return run("git", *args, cwd=cwd, env=env, check=check)


def snapshot(*args: str, cwd: Path | None = None) -> int:
    """Run a command for its exit code alone."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).returncode


def ancestor(rev: str, of: str, cwd: Path | None = None) -> bool:
    """Whether ``rev`` is reachable from ``of``."""
    return snapshot("git", "merge-base", "--is-ancestor", rev, of, cwd=cwd) == 0


def manifest_version(rev: str) -> str:
    """The integration version ``rev`` carries in its manifest."""
    version = json.loads(git("show", f"{rev}:{MANIFEST}")).get("version")
    if not isinstance(version, str):
        raise ValueError(f"{rev} carries no version in {MANIFEST}")
    return version


def released_version(master: str) -> str:
    """The stable version ``master`` carries; the sync starts from it."""
    version = manifest_version(master)
    if not RELEASED_RE.fullmatch(version):
        raise ValueError(f"origin/master carries {version}, not a stable release")
    return version


def next_version(released: str) -> str:
    """The version whose changelog section the sync opens."""
    major, minor, patch = released.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def is_dev_build(version: str, released: str) -> bool:
    """Whether ``version`` is a development build of ``released``."""
    return re.fullmatch(rf"{re.escape(released)}\.dev\d+", version) is not None


def section_open(text: str, version: str) -> bool:
    """Whether the changelog already carries the section for one version."""
    return any(line.startswith(f"## [{version}]") for line in text.splitlines())


def open_changelog_section(text: str, version: str, released: str) -> str | None:
    """Add the ``version`` section and its link reference; None when both are there."""
    heading = f"## [{version}] — unreleased"
    reference = f"[{version}]: https://github.com/{REPO}/compare/v{released}...dev"
    lines = text.split("\n")
    if not section_open(text, version):
        first = next((index for index, line in enumerate(lines) if line.startswith("## [")), None)
        if first is None:
            raise ValueError("CHANGELOG.md has no released section to open the next one above")
        lines[first:first] = [heading, ""]
    if reference not in lines:
        first = next((index for index, line in enumerate(lines) if REFERENCE_RE.match(line)), None)
        if first is None:
            raise ValueError("CHANGELOG.md has no link reference to add the next one to")
        lines[first:first] = [reference]
    opened = "\n".join(lines)
    return None if opened == text else opened


def identity(cwd: Path) -> dict[str, str]:
    """The environment a commit needs where the checkout names no user (a runner)."""
    environment = dict(os.environ)
    if not git("config", "user.email", cwd=cwd, check=False):
        environment.update(
            GIT_AUTHOR_NAME=BOT_NAME,
            GIT_AUTHOR_EMAIL=BOT_EMAIL,
            GIT_COMMITTER_NAME=BOT_NAME,
            GIT_COMMITTER_EMAIL=BOT_EMAIL,
        )
    return environment


@contextmanager
def worktree(ref: str, *, cwd: Path | None = None) -> Iterator[Path]:
    """A throwaway checkout of one commit; the caller's checkout stays untouched."""
    path = Path(tempfile.mkdtemp(prefix="haui-sync-"))
    path.rmdir()
    git("worktree", "add", "--detach", str(path), ref, cwd=cwd)
    try:
        yield path
    finally:
        git("worktree", "remove", "--force", str(path), check=False)
        shutil.rmtree(path, ignore_errors=True)


def build_branch(
    checkout: Path, *, branch: str, start: str, master: str, released: str
) -> list[str]:
    """Create ``branch`` at ``start`` (``dev``) and merge ``master`` into it.

    The merge resolves a file that both sides rewrote in master's favour, because the
    release owns the version files, the changelog and the notes, while everything
    ``dev`` changed elsewhere survives the merge untouched.

    Returns the commit subjects it added, oldest first; an empty list means the
    branch already started in the released state.
    """
    git("switch", "--create", branch, start, cwd=checkout)
    subjects: list[str] = []
    if not ancestor(master, "HEAD", checkout):
        message = f"chore(release): merge the v{released} release into dev"
        git(
            "merge",
            "--strategy-option",
            "theirs",
            "--message",
            message,
            master,
            cwd=checkout,
            env=identity(checkout),
        )
        subjects.append(message)
    changelog = checkout / "CHANGELOG.md"
    opened = open_changelog_section(
        changelog.read_text(encoding="utf-8"), next_version(released), released
    )
    if opened is not None:
        changelog.write_text(opened, encoding="utf-8")
        message = f"chore(release): open the {next_version(released)} changelog section"
        git("add", "--", "CHANGELOG.md", cwd=checkout)
        git("commit", "--message", message, cwd=checkout, env=identity(checkout))
        subjects.append(message)
    return subjects


def pull_request_title(released: str) -> str:
    """The Conventional Commits title of the sync pull request."""
    return f"chore(release): sync master and dev after {released}"


def pull_request_body(released: str, subjects: list[str], paths: list[str]) -> str:
    """The body of the sync pull request: not a release, and what it reconciles."""
    lines = [
        f"`v{released}` stays where it is: this is not a release.",
        "",
        "It merges the release into `dev` (where both sides rewrote one file, the released",
        "version wins) and opens the next changelog section, so `dev` and `master` end on",
        f"one tree with the {next_version(released)} section open.",
        "",
    ]
    if subjects:
        lines += ["Commits:", "", *(f"- {subject}" for subject in subjects), ""]
    if paths:
        lines += [
            f"The release rewrote {len(paths)} file(s), so `dev` adopts the released versions:",
            "",
            *(f"- `{path}`" for path in paths),
            "",
        ]
    lines += [f"Opened by `scripts/release/sync_branches.py` after the `v{released}` release."]
    return "\n".join(lines) + "\n"


def open_pull_request(branch: str, released: str, subjects: list[str], paths: list[str]) -> int:
    """The number of the open sync pull request, opened here when there is none."""
    found = json.loads(
        run(
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--head",
            branch,
            "--base",
            "master",
            "--state",
            "open",
            "--json",
            "number,url",
        )
    )
    if found:
        print(f"  pull       reusing {found[0]['url']}", flush=True)
        return int(found[0]["number"])
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".md", prefix="haui-sync-", delete=False, encoding="utf-8"
    )
    try:
        with handle:
            handle.write(pull_request_body(released, subjects, paths))
        url = run(
            "gh",
            "pr",
            "create",
            "--repo",
            REPO,
            "--base",
            "master",
            "--head",
            branch,
            "--title",
            pull_request_title(released),
            "--body-file",
            handle.name,
        )
    finally:
        os.unlink(handle.name)
    print(f"  pull       opened {url}", flush=True)
    return int(url.rstrip("/").rsplit("/", 1)[1])


def ensure_ci(sha: str, *, ref: str, grace: int = 40) -> str:
    """A ``ci.yml`` run for one commit; a push with ``GITHUB_TOKEN`` starts no workflow."""
    deadline = time.monotonic() + grace
    while True:
        runs = json.loads(
            run(
                "gh",
                "run",
                "list",
                "--repo",
                REPO,
                "--workflow",
                WORKFLOW,
                "--commit",
                sha,
                "--limit",
                "1",
                "--json",
                "headSha,url",
            )
        )
        if runs and runs[0]["headSha"] == sha:
            return f"running {runs[0]['url']}"
        if time.monotonic() >= deadline:
            break
        time.sleep(5)
    run("gh", "workflow", "run", WORKFLOW, "--repo", REPO, "--ref", ref)
    return f"dispatched {WORKFLOW} on {ref}"


def required_checks(number: int) -> list[dict[str, str]]:
    """The pull request's required checks as ``gh`` reports them; empty until they arrive."""
    output = run(
        "gh",
        "pr",
        "checks",
        str(number),
        "--repo",
        REPO,
        "--required",
        "--json",
        "name,bucket",
        check=False,
    )
    if not output:
        return []
    try:
        return list(json.loads(output))
    except json.JSONDecodeError:
        return []


def wait_for_checks(number: int, *, timeout: int, poll: int = 15) -> None:
    """Block until every required check on the pull request has passed."""
    deadline = time.monotonic() + timeout
    while True:
        checks = required_checks(number)
        buckets = {check.get("bucket", "") for check in checks}
        if checks and buckets <= {"pass", "skipping"}:
            return
        failed = [
            check.get("name", "?") for check in checks if check["bucket"] in {"fail", "cancel"}
        ]
        if failed:
            raise ValueError(f"pull request #{number}: {', '.join(failed)} failed")
        if time.monotonic() >= deadline:
            raise ValueError(
                f"pull request #{number} reported no green required checks within {timeout}s "
                f"(https://github.com/{REPO}/pull/{number}); merge it by hand, or push a commit "
                "to its branch so a user-token run reports the checks"
            )
        time.sleep(poll)


def released_page(released: str) -> str:
    """The release page URL once ``vX.Y.Z`` is out; refuse while it is a draft."""
    data = json.loads(
        run(
            "gh",
            "release",
            "view",
            f"v{released}",
            "--repo",
            REPO,
            "--json",
            "isDraft,isPrerelease,url",
        )
    )
    if data["isDraft"] or data["isPrerelease"]:
        raise ValueError(f"v{released} is not published yet; wait for the release workflow")
    return str(data["url"])


def sync(*, apply: bool, version: str | None, timeout: int) -> None:
    """Report what the two branches owe each other, and with ``apply`` even them out."""
    remote = git("remote", "get-url", "--push", "origin")
    if not remote_is_canonical(remote):
        raise ValueError(f"origin must push to github.com/{REPO}")
    git("fetch", "--tags", "origin")
    master = git("rev-parse", "origin/master")
    dev = git("rev-parse", "origin/dev")
    released = released_version(master)
    if version and version != released:
        raise ValueError(f"origin/master carries {released}, not {version}")
    if snapshot("git", "rev-parse", "--verify", "--quiet", f"refs/tags/v{released}") != 0:
        raise ValueError(f"v{released} is not on origin; publish the release before syncing")
    page = released_page(released)
    dev_version = manifest_version(dev)
    if dev_version != released and not is_dev_build(dev_version, released):
        raise ValueError(
            f"dev carries {dev_version}, so it has moved past the {released} release; merge "
            "origin/master into dev by hand, then rerun"
        )

    paths = git("diff", "--name-only", master, dev).splitlines()
    section = next_version(released)
    print(f"sync {released} (origin/master {master[:7]}, origin/dev {dev[:7]})")
    print(f"  release    {page}")
    print(f"  dev        carries {dev_version}, adopts the {released} release")
    if section_open(git("show", f"{dev}:CHANGELOG.md"), section):
        print(f"  changelog  the {section} section is already open")
    else:
        print(f"  changelog  opens the {section} section")
    print(f"  paths      {len(paths)} differ: {', '.join(paths) or 'none'}")
    if ancestor(dev, master) and not paths:
        print("  branches   in step; nothing to do")
        return
    if not apply:
        print(
            f"\nPreview only. Rerun with --apply to push sync/v{released}, merge it into "
            f"master and point dev at the merged tree."
        )
        return

    branch = f"sync/v{released}"
    with worktree(master) as checkout:
        existing = git(
            "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}", check=False
        )
        start = f"origin/{branch}" if existing else dev
        subjects = build_branch(
            checkout, branch=branch, start=start, master=master, released=released
        )
        for subject in subjects:
            print(f"  commit     {subject}", flush=True)
        if subjects:
            git("push", "origin", f"refs/heads/{branch}:refs/heads/{branch}", cwd=checkout)
        head = git("rev-parse", "HEAD", cwd=checkout)
        number = open_pull_request(branch, released, subjects, paths)
        print(f"  ci         {ensure_ci(head, ref=branch)}", flush=True)
        wait_for_checks(number, timeout=timeout)
        run("gh", "pr", "merge", str(number), "--repo", REPO, "--merge")
        print(f"  merged     pull request #{number}", flush=True)
        git("fetch", "origin", "master", "dev", cwd=checkout)
        git("push", "origin", "refs/remotes/origin/master:refs/heads/dev", cwd=checkout)
        git("push", "origin", "--delete", f"refs/heads/{branch}", cwd=checkout)
        git("fetch", "origin", "master", "dev", cwd=checkout)
        if git("diff", "--name-only", "origin/master", "origin/dev", cwd=checkout):
            raise ValueError("origin/master and origin/dev still differ after the sync")
        merged = git("rev-parse", "origin/master", cwd=checkout)
        print(f"  branches   master and dev on {merged[:7]}")
        print(f"  ci         {ensure_ci(merged, ref='master')}")


def main(argv: list[str] | None = None) -> int:
    """Parse the flags and sync; the exit code is 1 for a refused or failed sync."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="push the branches; without it nothing changes"
    )
    parser.add_argument(
        "--version", help="the released version (default: origin/master's manifest)"
    )
    parser.add_argument(
        "--timeout", type=int, default=1800, help="seconds to await the required checks"
    )
    args = parser.parse_args(argv)
    try:
        sync(apply=args.apply, version=args.version, timeout=args.timeout)
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Branch sync failed: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

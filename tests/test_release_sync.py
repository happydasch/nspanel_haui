"""The post-release sync records dev in master without touching the caller's checkout.

The git parts run against a temporary repository laid out like the real history: the
release commit on ``master`` is a squash, so it is no descendant of ``dev``'s tip,
which is exactly the shape the sync has to reconcile.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.release.publish_stable import REPO
from scripts.release.sync_branches import (
    build_branch,
    is_dev_build,
    next_version,
    open_changelog_section,
    pull_request_body,
    pull_request_title,
    worktree,
)

BASE_CHANGELOG = """# Changelog

Intro.

## [0.5.3] — unreleased

### Fixed

- one

[0.5.3]: https://github.com/happydasch/nspanel_haui/compare/v0.5.2...dev
[0.5.2]: https://github.com/happydasch/nspanel_haui/compare/v0.5.1...v0.5.2
"""

# The one line both sides rewrote, so the merge has to pick a side.
DEV_CHANGELOG = BASE_CHANGELOG.replace("- one", "- one (dev)")
RELEASED_CHANGELOG = (
    BASE_CHANGELOG.replace("- one", "- one (release)")
    .replace("unreleased", "2026-11-21")
    .replace("v0.5.2...dev", "v0.5.2...v0.5.3")
)

MANIFEST = "custom_components/nspanel_haui/manifest.json"


def _git(path: Path, *args: str) -> str:
    """Run git in the temporary repository and return its stripped stdout."""
    done = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _code(path: Path, *args: str) -> int:
    """Run git in the temporary repository for its exit code alone."""
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True
    ).returncode


def _version(path: Path, version: str) -> None:
    """Write a manifest carrying one version."""
    manifest = path / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")


def _repo(path: Path) -> Path:
    """A release on master and the dev cycle it was cut from."""
    path.mkdir()
    _git(path, "init", "--initial-branch=master")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "CHANGELOG.md").write_text(BASE_CHANGELOG, encoding="utf-8")
    (path / "feature.txt").write_text("one\n", encoding="utf-8")
    _version(path, "0.5.3.dev74")
    _git(path, "add", "-A")
    _git(path, "commit", "--message", "feat: one")

    _git(path, "switch", "--create", "dev")
    (path / "CHANGELOG.md").write_text(DEV_CHANGELOG, encoding="utf-8")
    (path / "feature.txt").write_text("two\n", encoding="utf-8")
    (path / "dev-only.txt").write_text("dev work\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "--message", "feat: dev work")

    # The squash merge of release/0.5.3: master's release commit squashes dev's
    # changes but carries no dev commit, so it is no descendant of dev's tip.
    _git(path, "switch", "master")
    (path / "CHANGELOG.md").write_text(RELEASED_CHANGELOG, encoding="utf-8")
    (path / "feature.txt").write_text("two\n", encoding="utf-8")
    _version(path, "0.5.3")
    _git(path, "commit", "--all", "--message", "chore(release): prepare v0.5.3")
    return path


def test_the_next_section_is_the_next_patch() -> None:
    assert next_version("0.5.3") == "0.5.4"
    assert next_version("0.5.9") == "0.5.10"


def test_only_a_dev_build_of_the_released_version_is_recognised() -> None:
    assert is_dev_build("0.5.3.dev74", "0.5.3")
    assert not is_dev_build("0.5.4.dev1", "0.5.3")
    assert not is_dev_build("0.5.3", "0.5.3")


def test_opening_a_section_puts_it_above_the_released_one() -> None:
    opened = open_changelog_section(RELEASED_CHANGELOG, "0.5.4", "0.5.3")

    assert opened is not None
    lines = opened.splitlines()
    assert lines[lines.index("## [0.5.4] — unreleased") + 1] == ""
    assert lines.index("## [0.5.4] — unreleased") < lines.index("## [0.5.3] — 2026-11-21")
    reference = f"[0.5.4]: https://github.com/{REPO}/compare/v0.5.3...dev"
    assert lines.index(reference) < lines.index(
        "[0.5.3]: https://github.com/happydasch/nspanel_haui/compare/v0.5.2...v0.5.3"
    )
    assert opened.startswith("# Changelog\n\nIntro.\n")


def test_an_open_section_is_left_alone() -> None:
    opened = open_changelog_section(RELEASED_CHANGELOG, "0.5.4", "0.5.3")

    assert opened is not None
    assert open_changelog_section(opened, "0.5.4", "0.5.3") is None


def test_the_sync_merges_the_release_into_dev_and_keeps_dev_work(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")

    with worktree("dev", cwd=repo) as checkout:
        subjects = build_branch(
            checkout, branch="sync/v0.5.3", start="dev", master="master", released="0.5.3"
        )

        assert subjects == [
            "chore(release): merge the v0.5.3 release into dev",
            "chore(release): open the 0.5.4 changelog section",
        ]
        assert _code(checkout, "merge-base", "--is-ancestor", "master", "HEAD") == 0
        assert _code(checkout, "merge-base", "--is-ancestor", "dev", "HEAD") == 0
        # What only dev changed survives; the line both sides rewrote takes the release's.
        assert (checkout / "dev-only.txt").read_text(encoding="utf-8") == "dev work\n"
        changelog = (checkout / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "- one (release)" in changelog
        assert "- one (dev)" not in changelog
        assert "## [0.5.4] — unreleased" in changelog
        assert "## [0.5.3] — 2026-11-21" in changelog
        assert json.loads((checkout / MANIFEST).read_text(encoding="utf-8"))["version"] == "0.5.3"
        assert set(_git(checkout, "diff", "--name-only", "master", "HEAD").splitlines()) == {
            "CHANGELOG.md",
            "dev-only.txt",
        }
        assert _git(checkout, "show", "--format=%s", "--no-patch", "HEAD") == (
            "chore(release): open the 0.5.4 changelog section"
        )


def test_a_second_run_adds_no_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")

    with worktree("dev", cwd=repo) as first:
        build_branch(first, branch="sync/v0.5.3", start="dev", master="master", released="0.5.3")
        head = _git(first, "rev-parse", "HEAD")

    with worktree(head, cwd=repo) as second:
        subjects = build_branch(
            second, branch="sync-again", start="HEAD", master="master", released="0.5.3"
        )

        assert subjects == []
        assert _git(second, "rev-parse", "HEAD") == head


def test_the_pull_request_says_which_files_the_release_rewrote() -> None:
    body = pull_request_body(
        "0.5.3", ["chore(release): merge the v0.5.3 release into dev"], ["CHANGELOG.md", MANIFEST]
    )

    assert "this is not a release" in body
    assert "chore(release): merge the v0.5.3 release into dev" in body
    assert "- `CHANGELOG.md`" in body
    assert "- `0.5.4`" not in body
    assert "with the 0.5.4 section open" in body


def test_the_pull_request_title_fits_the_repository_limit() -> None:
    assert len(pull_request_title("0.5.3")) <= 100

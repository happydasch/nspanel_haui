"""Tests for the development firmware release notes (scripts/release/dev_release_notes.py)."""

from __future__ import annotations

from scripts.release import dev_release_notes

REPO = "example/nspanel-haui"
COMMIT = "abcdef0123456789"


def test_notes_link_each_commit_and_list_the_changed_files():
    notes = dev_release_notes.build_notes(
        REPO,
        COMMIT,
        "0.5.0.dev63",
        "0.4.5",
        [("1111111aaaa", "fix(pages): one"), ("2222222bbbb", "feat(editor): two")],
        " docs/a.md | 2 +-",
    )

    assert notes.startswith("Development firmware `0.5.0.dev63`\n")
    assert f"[`abcdef0`](https://github.com/{REPO}/commit/{COMMIT})" in notes
    assert "Display TFT: `0.4.5`." in notes
    assert f"- [`1111111`](https://github.com/{REPO}/commit/1111111aaaa) fix(pages): one\n" in notes
    assert "```text\n docs/a.md | 2 +-\n```\n" in notes


def test_notes_say_when_no_commit_is_new():
    notes = dev_release_notes.build_notes(REPO, COMMIT, "0.5.0.dev63", "0.4.5", [], "")

    assert "No commits since the previous release." in notes
    assert "## Changed files" not in notes

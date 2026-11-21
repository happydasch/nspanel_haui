"""The release preflight reads the release branch, changelog and notes conservatively.

Only the pure decision helpers are tested here; the checks that shell out (git,
bump_version, check_hmi_bump, the Chrome screen comparison) are exercised by
running the script, which is what the runbook asks a human to do.
"""

from __future__ import annotations

from scripts.release.preflight import (
    changelog_section,
    display_inputs_changed,
    draft_body,
    missing_headings,
    release_version,
    required_note_headings,
)

CHANGELOG = """# Changelog

## [0.5.3] — unreleased

### Breaking changes

- Panel: the starter templates are gone.

### Added

- Editor: **Copy to device**.

### Fixed

- Hub: a number Home Assistant has no value for is left alone.

## [0.5.2] — 2026-11-20

### Added

- Something older.
"""


def test_a_release_branch_names_its_version() -> None:
    assert release_version("release/0.5.3", None) == "0.5.3"


def test_a_work_branch_names_no_version() -> None:
    assert release_version("cleanup/candidate", None) is None


def test_an_override_wins_over_the_branch_name() -> None:
    assert release_version("release/0.5.3", "0.6.0") == "0.6.0"


def test_an_override_that_is_not_a_stable_version_names_nothing() -> None:
    assert release_version("release/0.5.3", "0.6") is None
    assert release_version("release/0.5.3", "0.6.0.dev12") is None


def test_a_changelog_section_stops_at_the_next_version() -> None:
    section = changelog_section(CHANGELOG, "0.5.3")

    assert section.startswith("## [0.5.3]")
    assert "Something older" not in section
    assert "**Copy to device**" in section


def test_a_version_the_changelog_does_not_list_has_no_section() -> None:
    assert changelog_section(CHANGELOG, "9.9.9") == ""


def test_every_changelog_heading_with_entries_asks_for_a_notes_heading() -> None:
    section = changelog_section(CHANGELOG, "0.5.3")

    assert required_note_headings(section) == [
        "## Before updating",
        "## Added",
        "## Fixed",
    ]


def test_an_empty_changelog_section_asks_for_nothing() -> None:
    assert required_note_headings("## [0.5.3] — unreleased") == []


def test_a_notes_file_covering_every_heading_is_complete() -> None:
    notes = "## Before updating\n\nText\n\n## Added\n\n- One\n\n## Fixed\n\n- Two\n"

    assert missing_headings(notes, ["## Before updating", "## Added", "## Fixed"]) == []


def test_a_notes_file_without_a_heading_is_reported() -> None:
    notes = "## Added\n\n- One\n"

    assert missing_headings(notes, ["## Added", "## Fixed"]) == ["## Fixed"]


def test_a_change_inside_a_display_directory_counts() -> None:
    assert display_inputs_changed(["custom_components/nspanel_haui/haui/page/grid.py"])
    assert display_inputs_changed(["nextion/nspanel_haui.HMI"])
    assert display_inputs_changed(["custom_components/nspanel_haui/frontend/styles/card-styles.js"])


def test_a_change_outside_the_display_inputs_does_not_count() -> None:
    assert not display_inputs_changed(["custom_components/nspanel_haui/frontend/store/store.js"])
    assert not display_inputs_changed(["CHANGELOG.md"])
    assert not display_inputs_changed([])


def test_a_draft_links_the_previous_release() -> None:
    body = draft_body("0.5.3", "0.5.2", "## [0.5.3] — unreleased\n\n### Added\n", ["- One"])

    assert body.startswith("# v0.5.3")
    assert "compare/v0.5.2...v0.5.3" in body
    assert "compare/vv" not in body
    assert "### Added" in body
    assert "- One" in body


def test_a_draft_takes_the_previous_tag_with_its_v() -> None:
    body = draft_body("0.5.3", "v0.5.2", "", [])

    assert "compare/v0.5.2...v0.5.3" in body
    assert "compare/vv" not in body


def test_a_first_release_has_no_compare_link() -> None:
    body = draft_body("0.5.3", None, "", [])

    assert "releases/tag/v0.5.3" in body
    assert "## Commits" not in body

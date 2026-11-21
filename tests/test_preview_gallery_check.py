"""The screen overview's `--check` reports a stale, extra or missing screen.

``diff_docs` compares two docs trees by relative path, by the bytes of the
overview page, and — only on request — by the bytes of every screenshot, because
those belong to the browser that took them. The Chrome-driven render itself is
exercised by the gallery.
"""

from __future__ import annotations

from pathlib import Path

from scripts.preview_gallery.docs_overview import diff_docs, docs_files

PAGE = b"<html>overview</html>"
LANDSCAPE = b"png-landscape"
PORTRAIT = b"png-portrait"

OVERVIEW = {
    "screens.html": PAGE,
    "assets/screens/landscape/grid.png": LANDSCAPE,
    "assets/screens/portrait/grid.png": PORTRAIT,
}


def write_tree(root: Path, files: dict[str, bytes]) -> Path:
    """Write a docs tree, creating the directories its files need."""
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return root


def test_an_overview_that_matches_a_fresh_render_reports_nothing(tmp_path: Path) -> None:
    generated = write_tree(tmp_path / "generated", OVERVIEW)
    committed = write_tree(tmp_path / "committed", OVERVIEW)

    assert diff_docs(generated, committed) == []
    assert diff_docs(generated, committed, pixels=True) == []


def test_a_stale_overview_page_is_reported(tmp_path: Path) -> None:
    generated = write_tree(tmp_path / "generated", OVERVIEW)
    committed = write_tree(
        tmp_path / "committed", {**OVERVIEW, "screens.html": b"<html>old</html>"}
    )

    assert diff_docs(generated, committed) == ["changed   screens.html"]


def test_a_screen_drawn_elsewhere_is_only_reported_on_request(tmp_path: Path) -> None:
    """A screenshot's bytes are its browser's, so the default check ignores them."""
    generated = write_tree(tmp_path / "generated", OVERVIEW)
    committed = write_tree(
        tmp_path / "committed",
        {**OVERVIEW, "assets/screens/portrait/grid.png": b"png-from-another-browser"},
    )

    assert diff_docs(generated, committed) == []
    assert diff_docs(generated, committed, pixels=True) == [
        "changed   assets/screens/portrait/grid.png"
    ]


def test_a_committed_screen_the_render_no_longer_writes_is_reported_as_extra(
    tmp_path: Path,
) -> None:
    generated = write_tree(tmp_path / "generated", OVERVIEW)
    committed = write_tree(
        tmp_path / "committed",
        {**OVERVIEW, "assets/screens/landscape/removed.png": b"png-gone"},
    )

    assert diff_docs(generated, committed) == ["extra     assets/screens/landscape/removed.png"]


def test_a_screen_the_commit_misses_is_reported_as_missing(tmp_path: Path) -> None:
    generated = write_tree(
        tmp_path / "generated",
        {**OVERVIEW, "assets/screens/landscape/added.png": b"png-new"},
    )
    committed = write_tree(tmp_path / "committed", OVERVIEW)

    assert diff_docs(generated, committed) == ["missing   assets/screens/landscape/added.png"]


def test_a_docs_root_without_an_overview_holds_no_files(tmp_path: Path) -> None:
    """The repository before the first `--docs` run has nothing to compare."""
    assert docs_files(write_tree(tmp_path / "docs", {"index.md": b"# docs"})) == set()

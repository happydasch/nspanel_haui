"""Compare a fresh screen-overview render with the committed one.

Pure path and byte comparison, so it runs and is tested without Home Assistant stubs,
Chrome or a render.
"""

from __future__ import annotations

from pathlib import Path

SCREENS_PAGE_NAME = "screens.html"
SCREENS_DIR = "assets/screens"


def docs_files(root: Path) -> set[str]:
    """The overview files of a docs root: every screen PNG, plus ``screens.html``."""
    files = {path.relative_to(root).as_posix() for path in (root / SCREENS_DIR).rglob("*.png")}
    if (root / SCREENS_PAGE_NAME).is_file():
        files.add(SCREENS_PAGE_NAME)
    return files


def diff_docs(generated: Path, committed: Path, *, pixels: bool = False) -> list[str]:
    """What the committed screen overview misses, holds extra, or holds stale.

    One line per differing file, prefixed ``missing``/``extra``/``changed``; empty when
    the committed overview is what a fresh render writes. A screenshot's bytes are the
    browser's, so ``pixels`` compares them too.
    """
    fresh, stored = docs_files(generated), docs_files(committed)
    lines = [f"missing   {name}" for name in sorted(fresh - stored)]
    lines += [f"extra     {name}" for name in sorted(stored - fresh)]
    lines += [
        f"changed   {name}"
        for name in sorted(fresh & stored)
        if (name == SCREENS_PAGE_NAME or pixels)
        and (generated / name).read_bytes() != (committed / name).read_bytes()
    ]
    return lines

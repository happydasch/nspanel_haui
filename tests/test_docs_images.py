"""Every image a docs page points at exists in the repository.

``zensical build --strict`` checks the links between pages but not an ``<img src>``, so a
moved or renamed screenshot leaves a broken picture behind on a page that still builds clean.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# Both forms a page can use: ``<img src="...">`` and ``![alt](...)``.
IMG_TAG = re.compile(r'<img[^>]*?src="([^"]+)"')
MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")

# A source that is not a file in this repository.
REMOTE = ("http://", "https://", "data:")


def _sources(page: Path) -> list[str]:
    """The image sources of one page, HTML and Markdown."""
    text = page.read_text()
    return IMG_TAG.findall(text) + MD_IMAGE.findall(text)


def test_every_docs_image_resolves():
    """A page's images are found next to it, whatever theme the reader has."""
    missing = []
    for page in sorted(DOCS.rglob("*.md")):
        for source in _sources(page):
            if source.startswith(REMOTE):
                continue
            target = page.parent / source.split("#", 1)[0]
            if not target.is_file():
                missing.append(f"{page.relative_to(ROOT)}: {source}")

    assert not missing, "Docs pages point at images that do not exist:\n" + "\n".join(missing)

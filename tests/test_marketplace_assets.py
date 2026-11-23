import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "nspanel_haui"

# Where the README's images are served from: the repository and its one long-lived
# branch. A URL naming any other ref breaks as soon as that ref is deleted.
REPO = "happydasch/nspanel_haui"
README_BRANCH = "master"


def test_marketplace_readme_images_use_resolvable_absolute_urls():
    from urllib.parse import urlparse

    readme = (ROOT / "README.md").read_text()
    sources = [
        segment.split('src="', 1)[1].split('"', 1)[0]
        for segment in readme.split("<img")[1:]
        if 'src="' in segment
    ]

    assert sources
    for source in sources:
        parsed = urlparse(source)
        assert parsed.scheme in {"http", "https"}
        if parsed.netloc == "raw.githubusercontent.com":
            # The ref must be the live branch, not a branch that no longer exists:
            # a deleted ref answers 404 and every README image breaks.
            prefix = f"/{REPO}/{README_BRANCH}/"
            assert parsed.path.startswith(prefix), source
            asset = parsed.path[len(prefix) :]
            assert (ROOT / asset).is_file(), source


def test_integration_has_the_brand_icon_used_by_update_entities():
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())

    assert (INTEGRATION_DIR / "brand" / "icon.png").is_file()
    assert manifest["domain"] == "nspanel_haui"

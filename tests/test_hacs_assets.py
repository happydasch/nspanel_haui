

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "nspanel_haui"


def test_hacs_readme_images_use_resolvable_absolute_urls():
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
            asset = parsed.path.split("/dev/", 1)[1]
            assert (ROOT / asset).is_file(), source


def test_integration_has_the_brand_icon_used_by_update_entities():
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())

    assert (INTEGRATION_DIR / "brand" / "icon.png").is_file()
    assert manifest["domain"] == "nspanel_haui"

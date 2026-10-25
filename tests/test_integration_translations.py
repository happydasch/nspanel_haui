"""Home Assistant reads a custom integration's UI strings from translations/en.json."""

import json
from pathlib import Path

INTEGRATION = Path(__file__).parent.parent / "custom_components" / "nspanel_haui"


def test_english_translations_match_strings_json():
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))

    assert english == strings

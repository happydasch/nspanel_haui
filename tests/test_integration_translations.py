"""Home Assistant reads a custom integration's UI strings from translations/en.json."""

import json
import string
from pathlib import Path

import pytest

INTEGRATION = Path(__file__).parent.parent / "custom_components" / "nspanel_haui"
TRANSLATIONS = INTEGRATION / "translations"


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_english_translations_match_strings_json():
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))

    assert english == strings


def test_a_service_field_carries_a_name_and_a_description():
    """hassfest refuses a field's label and help text as one plain string.

    Since Home Assistant 2023.7 a service field's name and description live in a
    mapping, one per language, the shape the config flows' strings already use.
    """
    for path in [INTEGRATION / "strings.json", *sorted(TRANSLATIONS.glob("*.json"))]:
        services = json.loads(path.read_text(encoding="utf-8"))["services"]
        for service, config in services.items():
            for field, value in config.get("fields", {}).items():
                assert isinstance(value, dict), f"{path.name}: {service}.{field}"
                for key in ("name", "description"):
                    assert value.get(key), f"{path.name}: {service}.{field} has no {key}"


@pytest.mark.parametrize(
    "language", sorted(path.stem for path in TRANSLATIONS.glob("*.json") if path.stem != "en")
)
def test_language_translations_cover_every_english_string(language):
    english = _flatten(json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8")))
    translated = _flatten(
        json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
    )

    assert translated.keys() == english.keys()
    for key, text in translated.items():
        assert _placeholders(text) == _placeholders(english[key]), key

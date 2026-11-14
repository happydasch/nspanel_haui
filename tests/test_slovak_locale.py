"""Slovak catalogs must load without English fallback or broken placeholders."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from custom_components.nspanel_haui.haui.utils.datetime import format_datetime
from custom_components.nspanel_haui.haui.utils.locale_data import get_day_name, get_month_name
from custom_components.nspanel_haui.haui.utils.text import (
    get_state_translation,
    get_translation,
    has_glyphs,
)

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "nspanel_haui"


def _leaves(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, (*path, key))
    else:
        yield path, value


@pytest.mark.parametrize("directory", ["haui/locale", "translations"])
def test_slovak_catalog_matches_english_keys_and_placeholders(directory):
    english = dict(_leaves(json.loads((ROOT / directory / "en.json").read_text())))
    slovak = dict(_leaves(json.loads((ROOT / directory / "sk.json").read_text())))
    assert slovak.keys() == english.keys()
    for path, source in english.items():
        translated = slovak[path]
        assert isinstance(translated, str) and translated.strip(), path
        assert sorted(re.findall(r"\{[^{}]*\}", translated)) == sorted(
            re.findall(r"\{[^{}]*\}", source)
        ), path


@pytest.mark.parametrize("locale", ["sk", "sk_SK", "sk-SK", "SK-sk"])
def test_slovak_language_variants_load_the_catalog(locale):
    assert get_translation("Settings", locale) == "Nastavenia"
    assert get_state_translation("weather", "snowy-rainy", locale) == "Dážď so snehom"
    assert get_state_translation("climate", "dry", locale) == "Odvlhčovanie"


def test_slovak_dates_use_genitive_months_and_local_weekdays():
    date = datetime(2026, 11, 12)
    assert format_datetime(date, "%x", "full", "sk_SK") == "štvrtok 12. novembra 2026"
    assert format_datetime(date, "%x", "long", "sk_SK") == "12. novembra 2026"
    assert format_datetime(date, "%x", "medium", "sk_SK") == "12. nov 2026"
    assert format_datetime(date, "%x", "E", "sk_SK") == "št"
    assert get_day_name("sk_SK", 6) == "nedeľa"
    assert get_month_name("sk_SK", 1) == "januára"
    assert get_month_name("sk_SK", 12) == "decembra"


@pytest.mark.parametrize("font", range(5))
def test_display_text_fonts_support_slovak_alphabet(font):
    assert has_glyphs("áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ", font)

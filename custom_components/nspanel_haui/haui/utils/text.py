import json
import logging
import os
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Cache translation files per language so we read each one only once.
# Keyed by language code; value is the parsed dict or ``{}`` if the file
# was missing (cached so we do not retry the disk read on every call).
_TRANSLATION_CACHE: dict[str, dict] = {}


def get_translation(text: str, locale: str) -> str:
    translations = get_translations(locale)
    translation = text
    if "text" in translations and text in translations["text"]:
        translation = translations["text"][text]
    return translation


def get_state_translation(item_type: str, state: str, locale: str, attr: str = "state") -> str:
    translations = get_translations(locale)
    lookup = f"component.{item_type}.{attr}._.{state}"
    res: Any = translations
    for k in lookup.split("."):
        if k in res:
            res = res[k]
        else:
            res = None
            break
    if res is not None:
        return str(res)
    return state


def _translations_root() -> str:
    """Resolve the absolute path to the translations/ directory.

    ``text.py`` lives at ``custom_components/nspanel_haui/haui/utils/`` and
    the JSON files live at ``custom_components/nspanel_haui/translations/``.
    ``os.path.realpath`` collapses the ``..`` segments so the path that
    reaches ``open()`` is canonical — some HA installs (notably under
    s6/Supervisor) reject the un-normalized form.
    """
    here = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(here, "..", "..", "translations"))


def get_translations(locale: str) -> dict:
    lang = (locale or "en").split("_")[0] or "en"
    if lang in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[lang]

    root = _translations_root()
    path_file = os.path.join(root, f"{lang}.json")
    if not os.path.isfile(path_file):
        path_file = os.path.join(root, "en.json")

    if not os.path.isfile(path_file):
        _LOGGER.warning(
            "Translations directory missing or unreadable at %s; returning empty translation table",
            root,
        )
        _TRANSLATION_CACHE[lang] = {}
        return {}

    try:
        with open(path_file, encoding="utf-8") as translation_file:
            translations = json.load(translation_file)
    except OSError as exc:
        _LOGGER.warning("Could not read translation file %s: %s", path_file, exc)
        _TRANSLATION_CACHE[lang] = {}
        return {}

    _TRANSLATION_CACHE[lang] = translations
    return translations


def trim_text(text: str, num_chr: int, suffix: str = "..") -> str:
    """Trim text to a certain number of characters

    Args:
        text (str): Text to trim
        num_chr (int): Number of characters to trim to
        suffix (str): Suffix to add to the end of the trimmed text

    Returns:
        str: The trimmed text
    """
    if not suffix:
        suffix = ""
    if not text:
        return text
    if len(text) > num_chr:
        return text[: num_chr - len(suffix)] + suffix
    else:
        return text

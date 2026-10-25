import json
import logging
import os
import re
from typing import Any

from ..utils.icon import get_icon

_LOGGER = logging.getLogger(__name__)

# Cache translation files per language so we read each one only once.
# Keyed by language code; value is the parsed dict or ``{}`` if the file
# was missing (cached so we do not retry the disk read on every call).
_TRANSLATION_CACHE: dict[str, dict] = {}


def get_translation(text: str, locale: str) -> str:
    translations = get_translations(locale)
    translation = text
    # Empty values are keys added by extract_translations.py that are not yet translated.
    if "text" in translations and translations["text"].get(text):
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
    """Resolve the absolute path to the haui/locale/ directory.

    ``text.py`` lives at ``custom_components/nspanel_haui/haui/utils/`` and
    the JSON files live at ``custom_components/nspanel_haui/haui/locale/``.
    ``os.path.realpath`` collapses the ``..`` segments so the path that
    reaches ``open()`` is canonical — some HA installs (notably under
    s6/Supervisor) reject the un-normalized form.
    """
    here = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(here, "..", "locale"))


def get_translations(locale: str) -> dict:
    # The language becomes part of a file path, and the REST API passes it
    # straight from the URL.
    match = re.match(r"([a-z]+)(?:[_-]|$)", (locale or "en").lower())
    if match is None:
        raise ValueError(f"Invalid language code: {locale!r}")
    lang = match[1]
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


def parse_notification_text(text: str) -> str:
    """Parse notification text for display.

    Only extracts icon characters from mdi: prefixed strings.
    Leaves all other text unchanged.

    Args:
        text (str): Text to parse

    Returns:
        str: Parsed text with icon characters substituted when applicable
    """
    if text.startswith("mdi:"):
        return get_icon(text)
    return text


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


def chunk_text(text: str, chars_per_line: int, lines: int) -> list[str]:
    """Split *text* into pages fitting a Nextion text widget.

    Respects embedded ``\\r\\n`` line breaks; wraps longer lines at
    ``chars_per_line``; each returned page holds at most ``chars_per_line*lines``
    characters.
    """
    if not text:
        return []

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    logical_lines = text.split('\n')

    wrapped_lines = []
    for line in logical_lines:
        line = line.rstrip()
        while len(line) > chars_per_line:
            break_at = line.rfind(' ', 0, chars_per_line)
            if break_at == -1:
                break_at = chars_per_line
            wrapped_lines.append(line[:break_at].rstrip())
            line = line[break_at:].lstrip()
        wrapped_lines.append(line)

    pages: list[str] = []
    current_page: list[str] = []
    max_len = chars_per_line * lines

    for line in wrapped_lines:
        candidate = '\n'.join(current_page + [line])
        if len(candidate) > max_len and current_page:
            pages.append('\n'.join(current_page).strip())
            current_page = [line]
        else:
            current_page.append(line)

    if current_page:
        pages.append('\n'.join(current_page).strip())

    while pages and not pages[-1]:
        pages.pop()

    return pages

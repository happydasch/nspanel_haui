import functools
import json
import logging
import os
import re
from typing import Any, NamedTuple

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


class TextBox(NamedTuple):
    """Drawing area of a Nextion text widget, from its HMI attributes."""

    width: int  # w, px
    height: int  # h, px
    border: int  # borderw, px
    max_len: int  # txt_maxl: bytes the widget stores


_FONT_METRICS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "mapping", "font_metrics.json"
)


@functools.cache
def _font_metrics() -> dict[int, tuple[int, tuple[int, ...]]]:
    """Line height and glyph widths per display font.

    ``font_metrics.json`` is exported from the HMI fonts by
    ``scripts/gen_virtual_layout/gen_virtual_layout.py``; read on first use.
    """
    with open(_FONT_METRICS_FILE, encoding="utf-8") as metrics_file:
        fonts = json.load(metrics_file)["fonts"]
    return {font["id"]: (font["height"], tuple(font["widths"])) for font in fonts}


def text_width(text: str, font: int) -> int:
    """Width in px of *text* drawn in display font *font*.

    A character without a text glyph (an icon, or one the font lacks) counts as
    wide as the line is high: icons are square, and no text glyph is wider.
    """
    height, widths = _font_metrics()[font]
    return sum(widths[cp] if (cp := ord(char)) < len(widths) else height for char in text)


def _wrap_line(line: str, font: int, width: int) -> list[str]:
    """Word-wrap one line to *width* px; a word wider than a line breaks where it overflows."""
    space = text_width(" ", font)
    lines: list[str] = []
    current: str | None = None
    current_width = 0
    for word in line.split(" "):
        word_width = text_width(word, font)
        if current is not None and current_width + space + word_width <= width:
            current += " " + word
            current_width += space + word_width
            continue
        if current is not None:
            lines.append(current)
        while word_width > width:
            used = cut = 0
            while cut < len(word) and used + (char_width := text_width(word[cut], font)) <= width:
                used += char_width
                cut += 1
            cut = max(cut, 1)
            lines.append(word[:cut])
            word = word[cut:]
            word_width = text_width(word, font)
        current, current_width = word, word_width
    lines.append(current or "")
    return lines


def _stored_len(lines: list[str]) -> int:
    """Bytes a widget stores for *lines*: UTF-8 text, each line break as CR LF."""
    return len("\n".join(lines).encode("utf-8")) + len(lines) - 1


def fit_text(text: str, font: int, box: TextBox) -> list[str]:
    """Wrap *text* as the display draws it in *box* and split it into pages.

    Lines are wrapped by the font's glyph widths, so the display never wraps
    them again and a page shows exactly its lines.  A page holds as many lines
    as the box is tall and no more bytes than the widget stores.  The display's
    inset inside a text widget is not documented: the border width is kept
    clear on every side.  Embedded line breaks (``\\n``, ``\\r\\n``) are kept.
    """
    if not text.strip():
        return []
    height, _widths = _font_metrics()[font]
    width = box.width - 2 * box.border
    max_lines = max(1, (box.height - 2 * box.border) // height)

    lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        lines += _wrap_line(line.rstrip(), font, width)

    pages: list[list[str]] = []
    page: list[str] = []
    for line in lines:
        if page and (len(page) == max_lines or _stored_len([*page, line]) > box.max_len):
            pages.append(page)
            page = []
        # A blank line at the top of a page would only waste one of its lines.
        if page or line:
            page.append(line)
    if page:
        pages.append(page)
    return ["\n".join(page).rstrip() for page in pages]

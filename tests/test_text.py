"""Tests for display text translation lookup."""

from custom_components.nspanel_haui.haui.utils import text
from custom_components.nspanel_haui.haui.utils.text import get_translation


def test_untranslated_text_falls_back_to_english(monkeypatch):
    monkeypatch.setitem(
        text._TRANSLATION_CACHE, "xx", {"text": {"Keypad font size": "", "Close": "Zu"}}
    )

    assert get_translation("Keypad font size", "xx") == "Keypad font size"
    assert get_translation("Close", "xx") == "Zu"


def test_parse_notification_text_preserves_manual_line_breaks():
    """Notification bodies are free text (issue #49).

    parse_icon() used to be applied to the message and collapsed every
    \\n into a single line; the 0.4 replacement must leave plain text,
    including embedded line breaks, untouched.
    """
    message = "First line\nSecond line"
    assert text.parse_notification_text(message) == message
    assert text.parse_notification_text("plain text") == "plain text"
    assert text.parse_notification_text("\n") == "\n"
    assert text.parse_notification_text("") == ""


BOX = text.TextBox(284, 170, 2, 150)  # the notify page's tText in landscape


def _lines(page):
    return page.split("\n")


def test_font_metrics_come_from_the_display_fonts():
    assert text.text_width("i", 1) < text.text_width("W", 1)
    assert text.text_width("Wi", 1) == text.text_width("W", 1) + text.text_width("i", 1)
    assert text.text_width("Ż", 3) > text.text_width("Ż", 1)
    # Polish and German letters have glyphs of their own, narrower than the fallback.
    assert all(0 < text.text_width(char, 1) < 24 for char in "łżśäöüß")


def test_glyphless_characters_count_as_wide_as_the_line_is_high():
    # Icons (U+E000+) are square; a character the font lacks must not overflow.
    assert text.text_width("\ue334", 1) == 24
    assert text.text_width("€", 2) == 32


def test_fit_text_empty():
    assert text.fit_text("", 1, BOX) == []
    assert text.fit_text("   ", 1, BOX) == []


def test_fit_text_short_message_is_one_line():
    assert text.fit_text("short message", 1, BOX) == ["short message"]


def test_fit_text_keeps_line_breaks():
    assert text.fit_text("line1\r\nline2", 1, BOX) == ["line1\nline2"]


def test_fit_text_wraps_by_pixel_width_at_word_boundaries():
    message = "The washing machine has finished. Please empty it before the clothes get wrinkled."
    (page,) = text.fit_text(message, 1, BOX)
    lines = _lines(page)
    assert len(lines) > 1
    assert all(text.text_width(line, 1) <= BOX.width - 2 * BOX.border for line in lines)
    # Words are never split, and nothing is lost.
    assert " ".join(lines) == message


def test_fit_text_page_holds_the_lines_the_box_is_tall():
    message = "\n".join(f"line {i}" for i in range(20))
    pages = text.fit_text(message, 2, BOX)
    # 32 px lines in 170 - 2 * 2 px: five per page.
    assert [len(_lines(page)) for page in pages] == [5, 5, 5, 5]


def test_fit_text_page_respects_the_widget_text_length():
    box = text.TextBox(426, 300, 2, 60)
    pages = text.fit_text("word " * 60, 1, box)
    for page in pages:
        assert len(page.encode("utf-8")) + page.count("\n") <= box.max_len


def test_fit_text_breaks_a_word_wider_than_the_line():
    pages = text.fit_text("A" * 60, 3, BOX)
    lines = [line for page in pages for line in _lines(page)]
    assert "".join(lines) == "A" * 60
    assert all(text.text_width(line, 3) <= BOX.width - 2 * BOX.border for line in lines)


def test_fit_text_drops_a_blank_line_at_the_top_of_a_page():
    message = "\n".join(["one", "two", "three", "four", "five", "", "six"])
    assert text.fit_text(message, 2, BOX) == ["one\ntwo\nthree\nfour\nfive", "six"]

"""Tests for display text translation lookup."""

from nspanel_haui.haui.utils import text
from nspanel_haui.haui.utils.text import get_translation


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


def test_chunk_text_empty():
    assert text.chunk_text("", 10, 2) == []
    assert text.chunk_text("   ", 10, 2) == []


def test_chunk_text_fits_single_page():
    result = text.chunk_text("short message", 20, 2)
    assert len(result) == 1
    assert result[0] == "short message"


def test_chunk_text_respects_line_breaks():
    result = text.chunk_text("line1\nline2", 20, 2)
    assert len(result) == 1
    assert result[0] == "line1\nline2"


def test_chunk_text_wraps_long_lines():
    result = text.chunk_text("hello world this is a test", 10, 2)
    assert len(result) == 2
    combined = "".join(result)
    assert "hello" in combined
    assert "world" in combined
    assert "this" in combined
    assert "is" in combined
    assert "test" in combined


def test_chunk_text_respects_max_length():
    text_input = "A" * 50
    result = text.chunk_text(text_input, 10, 2)
    assert len(result) > 1
    for page in result:
        assert len(page) <= 20

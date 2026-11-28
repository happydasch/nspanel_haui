"""Media cover art: which address is fetched, and the program a cover becomes.

The download is the only part that touches the network, so a test replaces it and
checks what the page gets: fills that stay inside the icon's rectangle.
"""

import io

import pytest

from custom_components.nspanel_haui.haui.utils.image_program import Rect
from custom_components.nspanel_haui.hub import media_cover
from custom_components.nspanel_haui.hub.media_cover import (
    MediaCoverError,
    absolute_url,
    cover_runs,
)

_RECT = Rect(12, 68, 50, 50)


def _png(size=(16, 16), colour=(200, 30, 30)):
    """A PNG of one colour, as the hub's picture decoder expects it."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _fills(rect, *args, **kwargs):
    """The ``(x, y, w, h)`` each run of a program paints."""
    boxes = []
    for run in cover_runs(*args, **kwargs):
        assert run.startswith("fill "), run
        x, y, w, h, _colour = run.removeprefix("fill ").split(",")
        boxes.append((int(x), int(y), int(w), int(h)))
    return boxes


def test_a_full_url_is_fetched_as_it_is():
    assert absolute_url("http://radio.example/cover.png", "http://ha.local:8123") == (
        "http://radio.example/cover.png"
    )


def test_a_path_on_home_assistant_is_resolved_against_its_address():
    assert absolute_url("/api/media_player_proxy/x?token=1", "http://ha.local:8123/") == (
        "http://ha.local:8123/api/media_player_proxy/x?token=1"
    )


def test_a_path_without_an_address_is_refused():
    """Home Assistant reports no internal URL: say so instead of guessing one."""
    with pytest.raises(MediaCoverError):
        absolute_url("/api/media_player_proxy/x", "")


def test_a_cover_is_painted_inside_the_icon_rectangle(monkeypatch):
    monkeypatch.setattr(media_cover, "_download", lambda url: _png())

    boxes = _fills(_RECT, "http://radio.example/cover.png", _RECT)

    assert boxes
    for x, y, w, h in boxes:
        assert _RECT.x <= x and x + w <= _RECT.right
        assert _RECT.y <= y and y + h <= _RECT.bottom


def test_a_cover_costs_at_most_its_run_budget(monkeypatch):
    monkeypatch.setattr(media_cover, "_download", lambda url: _png((160, 160), (12, 120, 200)))

    runs = cover_runs("http://radio.example/cover.png", _RECT, budget=60)

    assert len(runs) <= 60


def test_a_url_that_is_not_a_picture_is_refused(monkeypatch):
    monkeypatch.setattr(media_cover, "_download", lambda url: b"not a picture")

    with pytest.raises(MediaCoverError):
        cover_runs("http://radio.example/cover.png", _RECT)

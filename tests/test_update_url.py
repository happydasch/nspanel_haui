"""Tests for the TFT URL pre-flight (``update_url``)."""

from __future__ import annotations

import pytest

from custom_components.nspanel_haui import update_url


class _Response:
    """One probe answer: status, headers, and whether it was released."""

    def __init__(self, status: int, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {}
        self.released = 0

    def release(self) -> None:
        self.released += 1


class _Session:
    """A fake Home Assistant session: HEAD and the ranged GET answer as given."""

    def __init__(self, head=None, probe=None) -> None:
        self._answers = {"head": head, "get": probe}
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def _answer(self, kind: str, headers: dict[str, str]):
        self.calls.append((kind, headers))
        answer = self._answers[kind]
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def head(self, url, **kwargs):
        return await self._answer("head", kwargs.get("headers") or {})

    async def get(self, url, **kwargs):
        return await self._answer("get", kwargs.get("headers") or {})


def _use(monkeypatch, session) -> None:
    monkeypatch.setattr(update_url, "_session", lambda hass: session)


@pytest.mark.asyncio
async def test_a_usable_url_passes_and_is_probed_in_ranges(monkeypatch):
    session = _Session(
        head=_Response(200, {"Content-Length": "1048576"}),
        probe=_Response(206, {"Content-Length": "1"}),
    )
    _use(monkeypatch, session)

    assert await update_url.tft_url_problem(None, "http://ha.local/display.tft") is None
    assert session.calls == [("head", {}), ("get", {"Range": "bytes=0-0"})]


@pytest.mark.asyncio
async def test_a_missing_file_is_refused(monkeypatch):
    _use(monkeypatch, _Session(head=_Response(404)))

    problem = await update_url.tft_url_problem(None, "http://ha.local/missing.tft")

    assert problem == "The TFT URL answered HTTP 404"


@pytest.mark.asyncio
async def test_a_server_without_range_support_is_refused(monkeypatch):
    """The panel downloads a TFT in ranges; a 200 for a ranged GET cannot work."""
    _use(
        monkeypatch,
        _Session(
            head=_Response(200, {"Content-Length": "1048576"}),
            probe=_Response(200, {"Content-Length": "1048576"}),
        ),
    )

    problem = await update_url.tft_url_problem(None, "http://ha.local/display.tft")

    assert "range requests" in problem


@pytest.mark.asyncio
async def test_a_file_over_the_display_partition_is_refused(monkeypatch):
    _use(monkeypatch, _Session(head=_Response(200, {"Content-Length": str(32 * 1024 * 1024)})))

    problem = await update_url.tft_url_problem(None, "http://ha.local/huge.tft")

    assert "33554432" in problem
    assert str(update_url.TFT_MAX_BYTES) in problem


@pytest.mark.asyncio
async def test_the_size_falls_back_to_the_content_range(monkeypatch):
    """A server that refuses HEAD still names the file size in its range answer."""
    _use(
        monkeypatch,
        _Session(
            head=_Response(405),
            probe=_Response(206, {"Content-Length": "1", "Content-Range": "bytes 0-0/20971520"}),
        ),
    )

    problem = await update_url.tft_url_problem(None, "http://ha.local/display.tft")

    assert "20971520" in problem


@pytest.mark.asyncio
async def test_a_transport_error_from_home_assistant_does_not_block_the_install(monkeypatch):
    """HA's egress and the panel's differ: a LAN URL it cannot read still installs."""
    _use(monkeypatch, _Session(head=OSError("no route to host")))

    assert await update_url.tft_url_problem(None, "http://192.168.1.20/x.tft") is None


@pytest.mark.asyncio
async def test_a_non_http_url_is_refused():
    assert await update_url.tft_url_problem(None, "ftp://ha.local/x.tft")

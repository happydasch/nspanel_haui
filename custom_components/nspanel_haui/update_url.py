"""Pre-flight of a TFT URL before a panel is sent off to download it.

The panel's uploader reports its own failures, but only after a long transfer,
and older firmware reports nothing at all: a 404, a server that ignores ``Range``,
or a file the display's partition cannot hold all look the same from the hub.
Home Assistant can check the URL first. Only a rejected answer stops the
install — a transport error is a warning, because HA's egress and the panel's
can differ (a LAN host, a name only the device resolves).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

# The display's TFT partition: a bigger file cannot be flashed, and the panel
# downloads all of it before the upload starts.
TFT_MAX_BYTES = 16 * 1024 * 1024
# Long enough for a slow host, short enough that a service call does not hang.
PROBE_TIMEOUT_SECONDS = 15


def _session(hass: Any) -> Any:
    """Home Assistant's shared HTTP session.

    Imported lazily so this helper (and the services module and API views that
    use it) loads without Home Assistant's HTTP client, as the tests do.
    """
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    return async_get_clientsession(hass)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """One header of a response, case-insensitively."""
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def _content_length(headers: Mapping[str, str]) -> int | None:
    """The response's declared byte length, or None when it names none."""
    raw = _header(headers, "Content-Length")
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def _range_total(headers: Mapping[str, str]) -> int | None:
    """The file's total size from a ``Content-Range: bytes 0-0/123`` header."""
    raw = _header(headers, "Content-Range") or ""
    _, _, total = raw.rpartition("/")
    try:
        return int(total)
    except ValueError:
        return None


async def _probe(session: Any, url: str, *, range_request: bool) -> Any | None:
    """One request to ``url``; None when Home Assistant could not reach it."""
    headers = {"Range": "bytes=0-0"} if range_request else {}
    request = session.get if range_request else session.head
    try:
        return await request(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=ClientTimeout(total=PROBE_TIMEOUT_SECONDS),
        )
    except (TimeoutError, ClientError, OSError) as err:
        _LOGGER.warning(
            "Could not check the TFT URL %s from Home Assistant (%s); the panel may still "
            "reach it, so the install continues",
            url,
            err,
        )
        return None


def _release(response: Any) -> None:
    """Free the connection of a probe the checks no longer read."""
    release = getattr(response, "release", None)
    if callable(release):
        release()


async def tft_url_problem(hass: Any, url: str) -> str | None:
    """Why the panel could not install the TFT at ``url``, or None when it can.

    Returns:
        str | None: The reason to show the user, or None when the URL is usable
        (also when Home Assistant could not reach it — that is only a warning)
    """
    if not url.startswith(("http://", "https://")):
        return "The TFT URL must start with http:// or https://"

    session = _session(hass)
    size: int | None = None

    head = await _probe(session, url, range_request=False)
    if head is not None:
        head_status = int(head.status)
        size = _content_length(head.headers)
        _release(head)
        # A server that does not implement HEAD still serves the ranged GET,
        # which carries the same answers.
        if head_status not in (405, 501):
            if head_status >= 400:
                return f"The TFT URL answered HTTP {head_status}"
            if size is not None and size > TFT_MAX_BYTES:
                return f"The TFT file is {size} bytes; the display can take at most {TFT_MAX_BYTES}"

    probe = await _probe(session, url, range_request=True)
    if probe is None:
        return None
    status = int(probe.status)
    ranged_size = _content_length(probe.headers)
    total = _range_total(probe.headers)
    _release(probe)
    if status == 200:
        return (
            "The server ignores range requests and answers the whole file; the panel "
            "downloads a TFT in ranges, so it cannot install this one"
        )
    if status >= 400:
        return f"The TFT URL answered HTTP {status}"
    size = size if size is not None else total or ranged_size
    if size is not None and size > TFT_MAX_BYTES:
        return f"The TFT file is {size} bytes; the display can take at most {TFT_MAX_BYTES}"
    return None

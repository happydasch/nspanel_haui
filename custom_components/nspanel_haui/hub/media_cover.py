"""Draw a media player's cover art into the panel's icon rectangle.

A Nextion has no image buffer, so a cover is the same kind of picture
``show_image`` sends: one ``fill`` per block of the picture, a few hundred of them
for a 50x50 icon (``haui/utils/image_program.py``). At icon size that is a mosaic
rather than artwork, and it is drawn once per picture instead of every frame.

Two rules shape this module:

* **Nothing here blocks the worker.** The worker runs the display pipeline in
  order, so a download on it would stall every command queued behind it - and the
  page the cover belongs to is rendering at that moment. The download and the
  rasterising run off the worker (``submit_off_worker``) and the program comes
  back on it through ``on_done``, in order with the page's own work.
* **The URL is the player's.** Home Assistant hands a media player's
  ``entity_picture`` as a path on its own API (``/api/media_player_proxy/...``,
  with the player's token in the query), which needs Home Assistant's internal
  address; an internet station publishes a full URL, which is used as it is.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit

import requests

from ..haui.utils.image_program import RUN_BUDGET, ImageProgramError, Rect, image_plan

if TYPE_CHECKING:
    from collections.abc import Callable

    from .app import NSPanelHAUI

#: The ceilings ``show_image`` puts on a picture: a cover is a cover, and a
#: download that carries more than this is not one.
COVER_MAX_BYTES: Final = 4 * 1024 * 1024
#: Seconds a cover may take to arrive. Long enough for a slow station logo, short
#: enough that the off-worker pool is not held by a server that will not answer.
COVER_FETCH_TIMEOUT: Final = 10
_COVER_CHUNK_BYTES: Final = 64 * 1024
#: The only schemes a cover is fetched over. The URL is an integration's
#: ``entity_picture``, not something this hub chose, so it may address nothing else.
_PICTURE_SCHEMES: Final = ("http", "https")


class MediaCoverError(RuntimeError):
    """A cover could not be fetched or turned into a draw program."""


def absolute_url(url: str, base: str) -> str:
    """``url`` as a full address, resolving a path against ``base``.

    Args:
        url: The player's ``entity_picture``: a full URL, or a path on Home
            Assistant's own API.
        base: Home Assistant's internal address, empty when it reports none.

    Returns:
        The address to fetch.

    Raises:
        MediaCoverError: When ``url`` is a path and there is no address to
            resolve it against.
    """
    parts = urlsplit(url)
    if parts.scheme in ("http", "https") and parts.netloc:
        return url
    if not base:
        raise MediaCoverError(
            f"{url!r} is a path on Home Assistant and no internal URL is configured "
            "to fetch it from"
        )
    return f"{base.rstrip('/')}/{url.lstrip('/')}"


def base_url(hass: Any) -> str:
    """Home Assistant's internal address, where it serves a player's picture path."""
    from homeassistant.helpers.network import NoURLAvailableError, get_url

    try:
        return get_url(hass, allow_external=False, allow_cloud=False)
    except NoURLAvailableError:
        return ""


def cover_runs(url: str, rect: Rect, *, budget: int = RUN_BUDGET) -> list[str]:
    """The run program that paints the cover at ``url`` into ``rect`` (blocking).

    Args:
        url: The full address of the picture.
        rect: The widget rectangle the picture goes in, in display pixels.
        budget: Runs the program may cost; the default is the latency
            ``show_image`` draws an image at.

    Returns:
        The ``fill`` instructions, in the order they are painted.

    Raises:
        MediaCoverError: When the picture cannot be downloaded, is too large, or
            is not an image the display can be sent.
    """
    data = _download(url)
    try:
        programs, _cell = image_plan(data, rect, budget=budget)
    except ImageProgramError as exc:
        raise MediaCoverError(f"{url} is not a picture the panel can draw: {exc}") from exc
    return [run for program in programs for run in program]


def request_cover(
    app: NSPanelHAUI,
    url: str,
    rect: Rect,
    on_done: Callable[[list[str], BaseException | None], None],
) -> None:
    """Fetch a cover and plan it, delivering ``on_done(runs, error)`` on the worker.

    The address is resolved here, so a path Home Assistant serves without an
    address to resolve it against fails as one log line instead of a callback the
    page has to unwrap. Everything after that is off the worker.
    """
    if app.stopped:
        return
    try:
        target = absolute_url(url, base_url(app.hass))
    except MediaCoverError as exc:
        app.log(f"media cover: {exc}", level="WARNING")
        return
    app.submit_off_worker(partial(cover_runs, target, rect), on_done=on_done)


def _download(url: str) -> bytes:
    """Download a picture, bounded in size and in time (blocking).

    Only ``http`` and ``https`` are fetched, and a redirect is followed only while
    it stays on those schemes: the URL comes from an integration's
    ``entity_picture``, which is a third party's string, and it must not be able to
    make the hub read anything but a picture off the network. Home Assistant's own
    proxy path (``/api/media_player_proxy/...``) is the common case and never
    redirects.

    Raises:
        MediaCoverError: When the request fails, redirects somewhere that is not
            http(s), or answers with too much.
    """
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _PICTURE_SCHEMES:
        raise MediaCoverError(
            f"{url} is a {scheme or 'relative'} address; a cover is fetched over http(s)"
        )
    try:
        with requests.get(url, timeout=COVER_FETCH_TIMEOUT, stream=True) as response:
            response.raise_for_status()
            if urlsplit(response.url).scheme.lower() not in _PICTURE_SCHEMES:
                raise MediaCoverError(f"{url} redirected to {response.url}, which is not http(s)")
            data = bytearray()
            for chunk in response.iter_content(_COVER_CHUNK_BYTES):
                data.extend(chunk)
                if len(data) > COVER_MAX_BYTES:
                    raise MediaCoverError(
                        f"{url} is larger than the {COVER_MAX_BYTES // (1024 * 1024)} MiB "
                        "a cover may be"
                    )
            return bytes(data)
    except requests.RequestException as exc:
        raise MediaCoverError(f"{url} could not be fetched: {exc}") from exc

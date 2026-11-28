"""Services for the NSPanel HAUI integration.

Provides HA service calls that go through the navigation controller so the
full render pipeline runs (goto_page, page ack, settle, set_panel).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import probatio as vol
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .haui.mapping.const import DEFAULT_NOTIFICATION_SOUND, SOUND_NAMES
from .haui.utils.image_program import (
    MAX_RECOMMENDED_CELL_PX,
    MAX_RUN_BUDGET,
    MIN_RUN_BUDGET,
    RUN_BUDGET,
    ImageProgramError,
    Rect,
    clear_run,
    display_size,
    image_plan,
)
from .haui.utils.image_stream import (
    DEAD_BAND,
    DEFAULT_CELL_PX,
    DEFAULT_FRAME_RUNS,
    MAX_CELL_PX,
    MAX_FPS,
    MAX_FRAME_RUNS,
    MIN_CELL_PX,
    MIN_FPS,
    MIN_FRAME_RUNS,
    ImageStreamError,
)
from .haui.version import DRAW_RUNS_FIRMWARE_VERSION, firmware_supports_draw_runs

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .hub.app import NSPanelHAUI

#: Frames per second a camera stream asks for unless the caller picks one. Two is
#: what a full-page rectangle on this display sustains while a subject moves; a
#: smaller rectangle or a stiller scene does better, and the stream drops frames
#: rather than queueing them, so a higher value is safe to try.
DEFAULT_STREAM_FPS = 2.0

_LOGGER = logging.getLogger(__name__)

# How long a service waits for the controller's answer before it reports the
# request as started: a URL pre-flight or a busy worker can take longer, and the
# dispatch is queued either way, so waiting forever would fail a call that runs.
ANSWER_TIMEOUT_SECONDS = 5.0

# An image is downloaded once, on the event loop, and rasterised per panel. The
# caps keep a mistyped URL from filling memory: a 4 MiB PNG is 4000x4000, far
# past anything the display can show.
IMAGE_MAX_BYTES = 4 * 1024 * 1024
IMAGE_FETCH_TIMEOUT_SECONDS = 15
# A local image is read from the folder Home Assistant already serves at
# ``/local``, so a file dropped in ``<config>/www`` needs no web server — and
# nothing outside that folder is reachable, so a path cannot read the rest of
# the configuration directory.
IMAGE_LOCAL_ROOT = "www"

# ── Service names ────────────────────────────────────────────
SERVICE_OPEN_PANEL = "open_panel"
SERVICE_CLOSE_PANEL = "close_panel"
SERVICE_WAKEUP = "wakeup"
SERVICE_IDLE = "idle"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_RESET_LAST_INTERACTION = "reset_last_interaction"
SERVICE_UPDATE_TFT = "update_tft"
SERVICE_UPDATE_FIRMWARE = "update_firmware"
SERVICE_SHOW_IMAGE = "show_image"
SERVICE_CLEAR_IMAGE = "clear_image"
SERVICE_START_CAMERA_STREAM = "start_camera_stream"
SERVICE_STOP_CAMERA_STREAM = "stop_camera_stream"

# ── Service schemas ─────────────────────────────────────────
SERVICE_OPEN_PANEL_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Required("panel"): cv.string,
        vol.Optional("wakeup", default=False): cv.boolean,
    }
)
SERVICE_DEVICE_ONLY_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
    }
)
SERVICE_UPDATE_TFT_SCHEMA = vol.Schema(
    {
        vol.Required("device"): cv.string,
        vol.Exclusive("version", "tft_source"): cv.string,
        vol.Exclusive("url", "tft_source"): cv.url,
    }
)
SERVICE_UPDATE_FIRMWARE_SCHEMA = vol.Schema(
    {
        vol.Required("device"): cv.string,
        vol.Exclusive("version", "firmware_source"): cv.string,
        vol.Exclusive("url", "firmware_source"): cv.url,
    }
)
# A colour in one of ``parse_color_value``'s formats: "#rrggbb", an RGB565
# int, [r, g, b], or "" for the popup's theme text colour.
_ICON_COLOR_SCHEMA = vol.Any(
    "",
    vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
    vol.Match(r"^#([0-9a-fA-F]{6})$"),
    vol.All(
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))],
        vol.Length(min=3, max=3),
    ),
)
SERVICE_SEND_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Required("title"): cv.string,
        vol.Optional("message", default=""): cv.string,
        vol.Optional("icon", default=""): cv.string,
        vol.Optional("persistent", default=False): cv.boolean,
        vol.Optional("icon_color", default=""): _ICON_COLOR_SCHEMA,
        vol.Optional("sound", default=DEFAULT_NOTIFICATION_SOUND): vol.In([*SOUND_NAMES, "none"]),
        vol.Optional("force_show", default=False): cv.boolean,
        vol.Optional("text_size", default="auto"): vol.Any(
            "auto", vol.All(vol.Coerce(int), vol.Range(min=1, max=3))
        ),
        vol.Optional("timeout", default=None): vol.Any(
            None, vol.All(vol.Coerce(int), vol.Range(min=0, max=3600))
        ),
    }
)
SERVICE_RESET_LAST_INTERACTION_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


# An image has no default source or place: the rectangle must be given, and the
# image comes from a URL or from a file in ``<config>/www`` — exactly one of the
# two, so a call can never guess.
def _one_image_source(value: dict[str, Any]) -> dict[str, Any]:
    """Refuse a draw call that names no image, or names an empty one.

    ``vol.Exclusive`` already refuses both sources; this refuses neither, which
    would otherwise get as far as fetching nothing. An empty string passes the
    field schema (``cv.string``), so it is refused here too instead of being
    read as a URL or resolved to the ``www`` folder itself.

    Args:
        value: The validated service call data.

    Returns:
        The same data, for the next validator.

    Raises:
        vol.Invalid: When neither ``url`` nor ``path`` is given, or the one
            that is has no content.
    """
    if "url" not in value and "path" not in value:
        raise vol.Invalid("give url or path: the image to draw")
    if "url" in value and not str(value["url"]).strip():
        raise vol.Invalid("url is empty: name the image to fetch")
    if "path" in value and not str(value["path"]).strip():
        raise vol.Invalid("path is empty: name a file in www/")
    return value


SERVICE_SHOW_IMAGE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("device", default=None): vol.Any(str, None),
            vol.Exclusive("url", "image_source"): cv.url,
            vol.Exclusive("path", "image_source"): cv.string,
            vol.Required("x"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required("y"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required("w"): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required("h"): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("progressive", default=True): cv.boolean,
            vol.Optional("quality", default=RUN_BUDGET): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_RUN_BUDGET, max=MAX_RUN_BUDGET)
            ),
        }
    ),
    _one_image_source,
)
SERVICE_CLEAR_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Required("x"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required("y"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required("w"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("h"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)
SERVICE_START_CAMERA_STREAM_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Required("camera"): cv.entity_id,
        vol.Optional("x", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("y", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required("w"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("h"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("fps", default=DEFAULT_STREAM_FPS): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_FPS, max=MAX_FPS)
        ),
        vol.Optional("cell", default=DEFAULT_CELL_PX): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_CELL_PX, max=MAX_CELL_PX)
        ),
        vol.Optional("band", default=DEAD_BAND): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional("max_runs", default=DEFAULT_FRAME_RUNS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_FRAME_RUNS, max=MAX_FRAME_RUNS)
        ),
    }
)
SERVICE_STOP_CAMERA_STREAM_SCHEMA = vol.Schema(
    {vol.Optional("device", default=None): vol.Any(str, None)}
)


def _resolve_target_apps(
    hass: HomeAssistant, device_id: str | None
) -> list[tuple[str, NSPanelHAUI]]:
    """Resolve HAUI apps matching an optional HA device registry ID.

    A panel has two devices and either selects it: its ESPHome device (the
    app's ``_ha_device_id``) and the integration's own device, the one its
    update and notify entities sit on, identified by ``(DOMAIN, dev_name)``.
    The services' device selector offers only the latter.

    Returns list of (device_name, app) tuples.  If device_id is None,
    returns ALL apps across all hub entries.
    """
    from homeassistant.helpers import device_registry as dr

    identifiers: set[tuple[str, str]] = set()
    if device_id is not None:
        device = dr.async_get(hass).async_get(device_id)
        if device is not None:
            identifiers = device.identifiers

    targets: list[tuple[str, NSPanelHAUI]] = []
    for _entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if not isinstance(entry_data, dict):
            continue
        if device_id is None:
            # device_id omitted → all apps
            for dev_name, app in entry_data.items():
                targets.append((str(dev_name), app))
            continue
        for dev_name, app in entry_data.items():
            if app._ha_device_id == device_id or (DOMAIN, str(dev_name)) in identifiers:
                targets.append((str(dev_name), app))

    return targets


def _wake_display(app: NSPanelHAUI) -> None:
    """Reset the firmware's inactivity timer before a wake action."""
    _publish_action(app, "reset_last_interaction", "0")


def _publish_action(
    app: NSPanelHAUI,
    action: str,
    value: str | dict[str, Any] | list[Any],
) -> None:
    """Publish an ESPAction to a device via its ESPHome controller."""
    esp_ctrl = app.controller.get("esphome")
    if esp_ctrl and hasattr(esp_ctrl, "esphome"):
        esp_ctrl.esphome.publish(action, value)
    else:
        _LOGGER.warning(
            "ESPHome controller missing on '%s' — cannot publish %s",
            getattr(app, "name", "?"),
            action,
        )


# ── Shared dispatch helper ──────────────────────────────────


def _resolve_required_targets(
    hass: HomeAssistant, call: ServiceCall
) -> list[tuple[str, NSPanelHAUI]]:
    """Resolve the call's targets, refusing a call that matches no panel.

    Returns:
        list: (device_name, app) for every matching panel

    Raises:
        ServiceValidationError: When no panel matches ``device``; the call
            then fails visibly instead of doing nothing.
    """
    from homeassistant.exceptions import ServiceValidationError

    device_id: str | None = call.data.get("device")
    targets = _resolve_target_apps(hass, device_id)

    if not targets:
        raise ServiceValidationError(
            f"{call.service}: no NSPanel HAUI panel matches device {device_id}; select a "
            "panel's NSPanel HAUI device or its ESPHome device"
        )
    return targets


async def _device_action(
    hass: HomeAssistant,
    call: ServiceCall,
    *,
    action: Callable[[Any, str], None],
    wake_first: bool = False,
) -> None:
    """Resolve device targets and run *action(app, dev_name)* on each.

    Resolves the ``device`` from the service call, looks up each target
    app, and dispatches *action* via the executor so HA's async loop is
    not blocked.  The action receives the full ``NSPanelHAUI`` instance so
    it can access both navigation and ESPHome controllers.

    Raises:
        ServiceValidationError: When no panel matches ``device``; the call
            then fails visibly instead of doing nothing.
    """
    for dev_name, app in _resolve_required_targets(hass, call):

        def _do(app: Any = app, dev_name: str = dev_name) -> None:
            if wake_first:
                _wake_display(app)
            try:
                action(app, dev_name)
            except Exception:
                _LOGGER.exception("%s: failed for '%s'", call.service, dev_name)

        # Queued on the app's worker without waiting: app code may itself be
        # blocked on this service call (e.g. an item action), and waiting for
        # the worker from here would deadlock it.
        app.dispatch(_do)


class _InstallAnswer:
    """A one-shot answer the app worker hands back to an awaiting service call."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._future: asyncio.Future[tuple[str, dict[str, Any]]] = loop.create_future()

    def complete(self, device_name: str, result: dict[str, Any]) -> None:
        """Hand the controller's answer to the event loop; the worker calls this."""

        def _set() -> None:
            if not self._future.done():
                self._future.set_result((device_name, result))

        self._loop.call_soon_threadsafe(_set)

    async def wait(self, timeout: float) -> tuple[str, dict[str, Any]] | None:
        """The answer, or None when the worker did not produce one in time."""
        try:
            return await asyncio.wait_for(asyncio.shield(self._future), timeout)
        except TimeoutError:
            return None


async def _install_on_targets(
    hass: HomeAssistant,
    call: ServiceCall,
    start: Callable[[Any, Callable[[dict[str, Any]], None]], None],
    error_of: Callable[[dict[str, Any]], str | None],
) -> dict[str, Any]:
    """Run an install on each target and answer with the controller's own state.

    The worker's answer is awaited (bounded by ``ANSWER_TIMEOUT_SECONDS``) so a
    refusal reaches Developer Tools and automations instead of only the log.

    Raises:
        HomeAssistantError: When a target's install did not start
        ServiceValidationError: When no panel matches ``device``
    """
    from homeassistant.exceptions import HomeAssistantError

    loop = asyncio.get_running_loop()
    answers: list[_InstallAnswer] = []
    for dev_name, app in _resolve_required_targets(hass, call):
        answer = _InstallAnswer(loop)
        answers.append(answer)

        def _do(app: Any = app, dev_name: str = dev_name, answer: _InstallAnswer = answer) -> None:
            def _on_complete(result: dict[str, Any]) -> None:
                answer.complete(dev_name, result)

            try:
                start(app, _on_complete)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("%s: failed for '%s'", call.service, dev_name)
                answer.complete(dev_name, {"state": "error", "last_error": str(exc)})

        app.dispatch(_do)

    answered = [
        resolved
        for resolved in await asyncio.gather(
            *(answer.wait(ANSWER_TIMEOUT_SECONDS) for answer in answers)
        )
        if resolved is not None
    ]
    for dev_name, result in answered:
        message = error_of(result)
        if message:
            raise HomeAssistantError(f"{call.service} failed for '{dev_name}': {message}")
    if not answered:
        # A worker busy with a panel action, or a pre-flight: the dispatch is
        # queued and runs after this call, so this is a start, not a failure.
        return {"state": "started"}
    return answered[0][1]


# ── Service call handlers ───────────────────────────────────


async def _handle_open_panel(hass: HomeAssistant, call: ServiceCall) -> None:
    panel_key: str = call.data["panel"]
    wakeup: bool = call.data.get("wakeup", False)

    def _open_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is None:
            _LOGGER.warning("open_panel: navigation missing on '%s'", dev_name)
            return
        if wakeup:
            nav.mark_awake()
        nav.reset_activity()
        nav.open_panel(panel_key)

    await _device_action(hass, call, action=_open_action, wake_first=wakeup)


async def _handle_close_panel(hass: HomeAssistant, call: ServiceCall) -> None:
    def _close_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is not None:
            nav.close_panel()

    await _device_action(hass, call, action=_close_action)


async def _handle_wakeup(hass: HomeAssistant, call: ServiceCall) -> None:
    def _wakeup_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is not None:
            # Wake is a device operation: reset the firmware interaction timer
            # (wake_first) always runs; the idle page is exited only when one
            # is actually shown. The hub's inactivity clock is a wake too.
            nav.reset_activity()
            nav.exit_idle_to_prev_or_home(app.device.config)

    await _device_action(hass, call, action=_wakeup_action, wake_first=True)


async def _handle_idle(hass: HomeAssistant, call: ServiceCall) -> None:
    def _idle_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is not None:
            nav.open_idle_panel(True)

    await _device_action(hass, call, action=_idle_action)


async def _handle_send_notification(hass: HomeAssistant, call: ServiceCall) -> None:
    # Goes straight to the controller: the ESPHome send_notification action
    # cannot carry force_show or timeout.
    def _notify_action(app: Any, dev_name: str) -> None:
        app.controller["notification"].add_notification(
            title=call.data["title"],
            message=call.data.get("message", ""),
            icon=call.data.get("icon", ""),
            persistent=call.data.get("persistent", False),
            force_show=call.data.get("force_show", False),
            icon_color=call.data.get("icon_color"),
            sound=call.data.get("sound", DEFAULT_NOTIFICATION_SOUND),
            text_size=call.data.get("text_size", "auto"),
            timeout=call.data.get("timeout"),
        )

    await _device_action(hass, call, action=_notify_action)


async def _handle_reset_last_interaction(hass: HomeAssistant, call: ServiceCall) -> None:
    offset: int = call.data.get("offset", 0)

    def _reset_action(app: Any, dev_name: str) -> None:
        _publish_action(app, "reset_last_interaction", str(offset))

    await _device_action(hass, call, action=_reset_action)


async def _check_tft_url(hass: HomeAssistant, url: str) -> None:
    """Refuse a TFT URL Home Assistant cannot serve; a transport error only warns.

    The panel's silent failures are mostly the URL itself (a 404, a server
    without range support, a file the display's partition cannot hold), and
    Home Assistant can see those before the panel is sent off to download.

    Raises:
        HomeAssistantError: When the URL is unreachable or unusable
    """
    from homeassistant.exceptions import HomeAssistantError

    from .update_url import tft_url_problem

    problem = await tft_url_problem(hass, url)
    if problem:
        raise HomeAssistantError(problem)


async def _handle_update_tft(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Install the TFT the device's firmware needs, another release, or the one at ``url``.

    Returns the update state the controller reported, so an automation can
    branch on ``started``/``installing``.

    Raises:
        HomeAssistantError: When the install did not start (see ``_install_on_targets``)
    """
    version: str | None = call.data.get("version")
    url: str | None = call.data.get("url")
    if url is not None:
        # A rejected URL raises before anything is dispatched.
        await _check_tft_url(hass, url)

    def _start(app: Any, on_complete: Callable[[dict[str, Any]], None]) -> None:
        app.start_async_tft_install(version, url, on_complete)

    def _error_of(result: dict[str, Any]) -> str | None:
        if result.get("state") == "error":
            return result.get("last_error") or "TFT update failed"
        return None

    return await _install_on_targets(hass, call, _start, _error_of)


async def _handle_update_firmware(hass: HomeAssistant, call: ServiceCall) -> None:
    """Install the offered firmware update, another release, or the image at ``url``."""
    version: str | None = call.data.get("version")
    url: str | None = call.data.get("url")

    def _update_action(app: Any, dev_name: str) -> None:
        def _on_complete(result: dict[str, Any]) -> None:
            if result.get("firmware_install_error"):
                _LOGGER.error(
                    "update_firmware failed for '%s': %s",
                    dev_name,
                    result["firmware_install_error"],
                )

        app.start_async_firmware_install(version, url, _on_complete)

    await _device_action(hass, call, action=_update_action)


# ── Images on the panel ─────────────────────────────────────


def _image_rect(app: NSPanelHAUI, call: ServiceCall) -> Rect:
    """The rectangle to draw into, refused when this panel cannot draw it.

    Read on the event loop, like ``_resolve_target_apps``: the display model, the
    firmware version the panel reported and the update controller's install flag
    are plain reads of state the worker owns, not calls into it.

    Raises:
        ServiceValidationError: When the rectangle is off the display, the
            firmware has no ``draw_runs`` action, or a TFT install owns the display.
    """
    from homeassistant.exceptions import ServiceValidationError

    try:
        rect = Rect(
            int(call.data["x"]),
            int(call.data["y"]),
            int(call.data["w"]),
            int(call.data["h"]),
        )
    except ImageProgramError as exc:
        raise ServiceValidationError(f"{call.service}: {exc}") from exc

    width, height = display_size(app.device.is_portrait)
    if rect.right > width or rect.bottom > height:
        raise ServiceValidationError(
            f"{call.service}: a {rect.w}x{rect.h} rectangle at ({rect.x}, {rect.y}) does not fit "
            f"the {width}x{height} display of '{app.name}'"
        )

    version = (app.device.device_info or {}).get("yaml_version")
    if not firmware_supports_draw_runs(version):
        raise ServiceValidationError(
            f"{call.service}: '{app.name}' runs firmware {version or 'unknown'}, which cannot "
            f"draw an image; update it to {DRAW_RUNS_FIRMWARE_VERSION} or newer"
        )

    update = app.controller.get("update")
    if update is not None and update.tft_install_active:
        raise ServiceValidationError(
            f"{call.service}: '{app.name}' is installing a TFT — try again when it has finished"
        )
    return rect


def _page_background(app: NSPanelHAUI) -> int:
    """The RGB565 colour the panel's current page shows behind its widgets.

    ``clear_image`` paints this back, so a cleared rectangle matches the page it
    sits on rather than leaving a block of its own colour.
    """
    nav = app.controller.get("navigation")
    page = getattr(nav, "page", None) if nav is not None else None
    if page is not None:
        return int(page.get_color("background"))
    # No page drawn yet: the device theme is what the next repaint paints anyway.
    return int(app.theme.get("background"))


async def _fetch_image(hass: HomeAssistant, url: str) -> bytes:
    """Download an image for drawing, bounded in size and in time.

    Raises:
        HomeAssistantError: When the URL fails, times out or serves too much.
    """
    from aiohttp import ClientError, ClientTimeout
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    try:
        async with session.get(
            url, timeout=ClientTimeout(total=IMAGE_FETCH_TIMEOUT_SECONDS)
        ) as response:
            if response.status >= 400:
                raise HomeAssistantError(f"{url} answered HTTP {response.status}")
            # One byte over the cap is enough to know it is too large without
            # holding the whole file in memory first.
            data = await response.content.read(IMAGE_MAX_BYTES + 1)
    except TimeoutError as exc:
        raise HomeAssistantError(
            f"{url} did not answer within {IMAGE_FETCH_TIMEOUT_SECONDS} s"
        ) from exc
    except (ClientError, OSError) as exc:
        raise HomeAssistantError(f"{url} could not be fetched: {exc}") from exc

    if len(data) > IMAGE_MAX_BYTES:
        raise HomeAssistantError(
            f"{url} is larger than the {IMAGE_MAX_BYTES // (1024 * 1024)} MiB an image may be"
        )
    return data


def _image_file(hass: HomeAssistant, path: str, *, service: str) -> Path:
    """The file a ``path`` names, resolved inside ``<config>/www``.

    The folder Home Assistant serves at ``/local``, so a file dropped there needs
    no URL. ``path`` is relative to it and a leading ``www/`` is accepted, because
    both spellings appear in the documentation. Anything that resolves outside it
    — ``..``, a symlink to elsewhere — is refused: a service call must not be able
    to read the rest of the configuration directory.

    Args:
        hass: Home Assistant, for the configuration directory.
        path: The value of the call's ``path`` field.
        service: The service name, for the error message.

    Returns:
        The resolved path, which need not exist.

    Raises:
        ServiceValidationError: When the path is absolute or leaves the folder.
    """
    from homeassistant.exceptions import ServiceValidationError

    root = Path(hass.config.path(IMAGE_LOCAL_ROOT))
    raw = Path(path)
    if raw.is_absolute():
        raise ServiceValidationError(
            f"{service}: '{path}' is absolute; give a path inside {IMAGE_LOCAL_ROOT}/, "
            "for example 'logo.png'"
        )
    parts = raw.parts[1:] if raw.parts and raw.parts[0] == IMAGE_LOCAL_ROOT else raw.parts
    resolved = (root / Path(*parts)).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ServiceValidationError(
            f"{service}: '{path}' points outside {IMAGE_LOCAL_ROOT}/, which is the only "
            "folder an image may be read from"
        )
    return resolved


async def _read_image_file(hass: HomeAssistant, path: str, *, service: str) -> bytes:
    """Read a local image for drawing, bounded like a download.

    Args:
        hass: Home Assistant, for the configuration directory and the executor.
        path: The value of the call's ``path`` field.
        service: The service name, for the error messages.

    Returns:
        The image file's bytes.

    Raises:
        ServiceValidationError: When the path is refused or names no file.
        HomeAssistantError: When the file is larger than an image may be.
    """
    from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

    target = _image_file(hass, path, service=service)
    if not target.is_file():
        raise ServiceValidationError(
            f"{service}: '{path}' does not exist in {hass.config.path(IMAGE_LOCAL_ROOT)}"
        )
    size = target.stat().st_size
    if size > IMAGE_MAX_BYTES:
        raise HomeAssistantError(
            f"{path} is {size // 1024} KiB, larger than the "
            f"{IMAGE_MAX_BYTES // (1024 * 1024)} MiB an image may be"
        )
    return await hass.async_add_executor_job(target.read_bytes)


async def _read_image(hass: HomeAssistant, call: ServiceCall) -> bytes:
    """The image a draw call asks for: the file it names or the URL it fetches.

    The field's presence picks the source, not truthiness: the schema already
    refused an empty value, and a present-but-falsy one must not silently turn a
    file request into a URL lookup.

    Raises:
        ServiceValidationError: When the path is refused or names no file.
        HomeAssistantError: When the URL or the file cannot be read.
    """
    if "path" in call.data:
        return await _read_image_file(hass, str(call.data["path"]), service=call.service)
    return await _fetch_image(hass, str(call.data["url"]))


def _draw_programs(app: NSPanelHAUI, dev_name: str, programs: list[list[str]]) -> None:
    """Send an image to the panel as one queue of runs, coarse pass first.

    The passes are flattened rather than sent one after the other: the panel
    restarts its draw on every call, so a second call would cut the coarse pass
    short instead of letting it finish, and the full pass already paints over it.
    The hub slices the queue itself (``draw_wire.program_slices``).

    Runs on the app's worker: the display path records the program for the page
    replay, which is worker-owned state.
    """
    esp_ctrl = app.controller.get("esphome")
    if esp_ctrl is None or not hasattr(esp_ctrl, "draw_runs"):
        _LOGGER.warning("%s: no ESPHome controller — the image was not drawn", dev_name)
        return
    runs = [run for program in programs for run in program]
    if runs:
        esp_ctrl.draw_runs(runs)


def _clear_rect(app: NSPanelHAUI, dev_name: str, rect: Rect) -> None:
    """Paint the rectangle in the page's background colour: a single ``fill``."""
    esp_ctrl = app.controller.get("esphome")
    if esp_ctrl is None or not hasattr(esp_ctrl, "draw_runs"):
        _LOGGER.warning("%s: no ESPHome controller — the image was not cleared", dev_name)
        return
    esp_ctrl.draw_runs([clear_run(rect, _page_background(app))])


async def _handle_show_image(hass: HomeAssistant, call: ServiceCall) -> None:
    """Paint an image into a rectangle on whatever page the panel is showing.

    The image is read once for all targets — downloaded, or read from
    ``<config>/www`` — the rasterising runs in the executor (a pure function over
    the image bytes — ``app.run_off_worker`` waits for the worker and would block
    this loop), and only the send is dispatched to the panel's worker.

    Raises:
        ServiceValidationError: When no panel matches, the rectangle is off the
            display, the image cannot be decoded, the path is refused or names no
            file, or a panel cannot draw yet.
        HomeAssistantError: When the image URL cannot be fetched or the file is
            too large.
    """
    from homeassistant.exceptions import ServiceValidationError

    targets = _resolve_required_targets(hass, call)
    # Every target's rectangle is checked before anything is read.
    rects = {dev_name: _image_rect(app, call) for dev_name, app in targets}
    data = await _read_image(hass, call)
    budget: int = call.data.get("quality", RUN_BUDGET)
    progressive: bool = call.data.get("progressive", True)

    for dev_name, app in targets:
        rect = rects[dev_name]
        try:
            programs, cell = await hass.async_add_executor_job(
                partial(
                    image_plan,
                    data,
                    rect,
                    budget=budget,
                    progressive=progressive,
                )
            )
        except ImageProgramError as exc:
            raise ServiceValidationError(f"{call.service} for '{dev_name}': {exc}") from exc

        if cell > MAX_RECOMMENDED_CELL_PX:
            _LOGGER.warning(
                "%s: a %sx%s rectangle at %d runs draws in %d px blocks, a mosaic; draw it "
                "smaller, or use a picture background for a full-page image",
                dev_name,
                rect.w,
                rect.h,
                budget,
                cell,
            )
        app.dispatch(partial(_draw_programs, app, dev_name, programs))


async def _handle_clear_image(hass: HomeAssistant, call: ServiceCall) -> None:
    """Paint a rectangle back to the page background colour.

    Only the flat colour the theme defines: on a page whose background is a
    picture the fill leaves a block, so navigating away is the way to restore it.

    Raises:
        ServiceValidationError: When no panel matches or the rectangle is off the
            display, or the firmware cannot draw.
    """
    for dev_name, app in _resolve_required_targets(hass, call):
        rect = _image_rect(app, call)
        app.dispatch(partial(_clear_rect, app, dev_name, rect))


async def _handle_start_camera_stream(hass: HomeAssistant, call: ServiceCall) -> None:
    """Draw a camera's snapshots continuously into a rectangle of a panel.

    The rectangle is checked before anything else, so a call that cannot fit the
    display fails without touching a camera - the same order ``show_image`` uses.
    The stream itself owns the frames from then on: it stops on a page change, a
    sleeping display, a panel installing a TFT, a camera that stops answering, or
    ``stop_camera_stream``.

    Raises:
        ServiceValidationError: When the rectangle is off the display, the panel
            cannot draw yet, or an argument is outside its range.
    """
    from homeassistant.exceptions import ServiceValidationError

    from .hub.camera_stream import CameraStream, stop_stream

    targets = _resolve_required_targets(hass, call)
    rects = {dev_name: _image_rect(app, call) for dev_name, app in targets}
    camera = str(call.data["camera"])
    if hass.states.get(camera) is None:
        raise ServiceValidationError(
            f"{call.service}: camera '{camera}' does not exist; pick a camera entity"
        )
    try:
        for dev_name, app in targets:
            await stop_stream(app)
            stream = CameraStream(
                hass,
                app,
                entity_id=camera,
                rect=rects[dev_name],
                fps=float(call.data["fps"]),
                cell=int(call.data["cell"]),
                band=int(call.data["band"]),
                max_runs=int(call.data["max_runs"]),
            )
            await stream.async_start()
            _LOGGER.info(
                "%s: camera stream from %s into %sx%s at (%s, %s), %.1f fps",
                dev_name,
                camera,
                rects[dev_name].w,
                rects[dev_name].h,
                rects[dev_name].x,
                rects[dev_name].y,
                stream.fps,
            )
    except ImageStreamError as exc:
        raise ServiceValidationError(f"{call.service}: {exc}") from exc


async def _handle_stop_camera_stream(hass: HomeAssistant, call: ServiceCall) -> None:
    """Stop the camera stream on one panel, leaving its last frame on the screen."""
    from .hub.camera_stream import stop_stream

    for dev_name, app in _resolve_required_targets(hass, call):
        if await stop_stream(app):
            _LOGGER.info("%s: camera stream stopped by service", dev_name)
        else:
            _LOGGER.debug("%s: stop_camera_stream with no stream running", dev_name)


# ── Registration ─────────────────────────────────────────────


def async_register_services(hass: HomeAssistant) -> None:
    """Register all nspanel_haui services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_OPEN_PANEL):
        return  # all registered as one block

    from homeassistant.core import SupportsResponse

    # Only ``update_tft`` answers: it returns the controller's update state, so
    # an automation can branch on ``started``/``installing``.
    responses = {SERVICE_UPDATE_TFT: SupportsResponse.OPTIONAL}

    for name, schema, handler in (
        (SERVICE_OPEN_PANEL, SERVICE_OPEN_PANEL_SCHEMA, _handle_open_panel),
        (SERVICE_CLOSE_PANEL, SERVICE_DEVICE_ONLY_SCHEMA, _handle_close_panel),
        (SERVICE_WAKEUP, SERVICE_DEVICE_ONLY_SCHEMA, _handle_wakeup),
        (SERVICE_IDLE, SERVICE_DEVICE_ONLY_SCHEMA, _handle_idle),
        (SERVICE_SEND_NOTIFICATION, SERVICE_SEND_NOTIFICATION_SCHEMA, _handle_send_notification),
        (
            SERVICE_RESET_LAST_INTERACTION,
            SERVICE_RESET_LAST_INTERACTION_SCHEMA,
            _handle_reset_last_interaction,
        ),
        (SERVICE_UPDATE_TFT, SERVICE_UPDATE_TFT_SCHEMA, _handle_update_tft),
        (SERVICE_UPDATE_FIRMWARE, SERVICE_UPDATE_FIRMWARE_SCHEMA, _handle_update_firmware),
        (SERVICE_SHOW_IMAGE, SERVICE_SHOW_IMAGE_SCHEMA, _handle_show_image),
        (SERVICE_CLEAR_IMAGE, SERVICE_CLEAR_IMAGE_SCHEMA, _handle_clear_image),
        (
            SERVICE_START_CAMERA_STREAM,
            SERVICE_START_CAMERA_STREAM_SCHEMA,
            _handle_start_camera_stream,
        ),
        (
            SERVICE_STOP_CAMERA_STREAM,
            SERVICE_STOP_CAMERA_STREAM_SCHEMA,
            _handle_stop_camera_stream,
        ),
    ):
        hass.services.async_register(
            DOMAIN,
            name,
            partial(handler, hass),
            schema=schema,
            supports_response=responses.get(name, SupportsResponse.NONE),
        )

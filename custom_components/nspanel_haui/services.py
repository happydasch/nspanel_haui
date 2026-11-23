"""Services for the NSPanel HAUI integration.

Provides HA service calls that go through the navigation controller so the
full render pipeline runs (goto_page, page ack, settle, set_panel).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any

import probatio as vol
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .haui.mapping.const import DEFAULT_NOTIFICATION_SOUND, SOUND_NAMES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .hub.app import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

# How long a service waits for the controller's answer before it reports the
# request as started: a URL pre-flight or a busy worker can take longer, and the
# dispatch is queued either way, so waiting forever would fail a call that runs.
ANSWER_TIMEOUT_SECONDS = 5.0

# ── Service names ────────────────────────────────────────────
SERVICE_OPEN_PANEL = "open_panel"
SERVICE_CLOSE_PANEL = "close_panel"
SERVICE_WAKEUP = "wakeup"
SERVICE_IDLE = "idle"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_RESET_LAST_INTERACTION = "reset_last_interaction"
SERVICE_UPDATE_TFT = "update_tft"
SERVICE_UPDATE_FIRMWARE = "update_firmware"

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
    ):
        hass.services.async_register(
            DOMAIN,
            name,
            partial(handler, hass),
            schema=schema,
            supports_response=responses.get(name, SupportsResponse.NONE),
        )

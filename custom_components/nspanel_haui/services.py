"""Services for the NSPanel HAUI integration.

Provides HA service calls that go through the navigation controller so the
full render pipeline runs (goto_page, page ack, settle, set_panel).

Also exposes direct ESPAction publish calls for brightness, raw commands,
and other device-level operations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .haui.mapping.const import ESPAction, NotificationAction

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

# ── Service names ────────────────────────────────────────────
SERVICE_OPEN_PANEL = "open_panel"
SERVICE_CLOSE_PANEL = "close_panel"
SERVICE_WAKEUP = "wakeup"
SERVICE_SLEEP = "sleep"
SERVICE_SET_BRIGHTNESS = "set_brightness"
SERVICE_SEND_COMMAND = "send_command"
SERVICE_GOTO_PAGE = "goto_page"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_PLAY_RTTTL = "play_rtttl"
SERVICE_PLAY_SOUND = "play_sound"
SERVICE_RESET_LAST_INTERACTION = "reset_last_interaction"

# DOMAIN is defined in __init__.py; we keep a local copy to avoid
# circular imports when services.py is imported there.
DOMAIN = "nspanel_haui"

# ── Service schemas ─────────────────────────────────────────
SERVICE_OPEN_PANEL_SCHEMA = vol.Schema(
    {
        vol.Required("panel"): cv.string,
        vol.Optional("wakeup", default=False): cv.boolean,
    }
)
SERVICE_CLOSE_PANEL_SCHEMA = vol.Schema({})
SERVICE_WAKEUP_SCHEMA = vol.Schema({})
SERVICE_SLEEP_SCHEMA = vol.Schema({})
SERVICE_SET_BRIGHTNESS_SCHEMA = vol.Schema(
    {
        vol.Required("intensity"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)
SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("cmd"): cv.string,
    }
)
SERVICE_GOTO_PAGE_SCHEMA = vol.Schema(
    {
        vol.Required("page"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
SERVICE_SEND_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required("title"): cv.string,
        vol.Optional("message", default=""): cv.string,
        vol.Optional("icon", default=""): cv.string,
        vol.Optional("timeout", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("persistent", default=False): cv.boolean,
    }
)
SERVICE_PLAY_RTTTL_SCHEMA = vol.Schema(
    {
        vol.Required("song_str"): cv.string,
    }
)
SERVICE_PLAY_SOUND_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
    }
)
SERVICE_RESET_LAST_INTERACTION_SCHEMA = vol.Schema(
    {
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


def _resolve_target_apps(
    hass: HomeAssistant, device_id: str | None
) -> list[tuple[str, NSPanelHAUI]]:
    """Resolve HAUI apps matching an optional HA device registry ID.

    Returns list of (device_name, app) tuples.  If device_id is None,
    returns ALL apps across all hub entries.
    """
    targets: list[tuple[str, NSPanelHAUI]] = []
    for _entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if not isinstance(entry_data, dict):
            continue  # skip _device_id_listeners and other non-app keys
        if device_id is None:
            # device_id omitted → all apps
            for dev_name, app in entry_data.items():
                targets.append((str(dev_name), app))
            continue
        for dev_name, app in entry_data.items():
            if getattr(app, "_ha_device_id", None) == device_id:
                targets.append((str(dev_name), app))

    return targets


def _wake_display(app: NSPanelHAUI) -> None:
    """Publish reset_last_interaction to wake the display."""
    try:
        esp_ctrl = app.controller.get("esphome")
        if esp_ctrl and hasattr(esp_ctrl, "esphome"):
            esp_ctrl.esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")
    except Exception:
        _LOGGER.debug(
            "reset_last_interaction failed for '%s'",
            getattr(app, "name", "?"),
            exc_info=True,
        )


def _publish_action(
    app: NSPanelHAUI,
    action: ESPAction | NotificationAction,
    value: str | dict | list,
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


async def _device_action(
    hass: HomeAssistant,
    call: ServiceCall,
    *,
    action: Callable[[Any, str], None],
    wake_first: bool = False,
) -> None:
    """Resolve device targets and run *action(app, dev_name)* on each.

    Resolves the ``device_id`` from the service call, looks up each target
    app, and dispatches *action* via the executor so HA's async loop is
    not blocked.  The action receives the full ``NSPanelHAUI`` instance so
    it can access both navigation and ESPHome controllers.
    """
    device_id: str | None = call.data.get("device_id")
    targets = _resolve_target_apps(hass, device_id)

    if not targets:
        _LOGGER.warning(
            "%s: no matching HAUI device (device_id=%s)",
            call.service,
            device_id,
        )
        return

    for dev_name, app in targets:
        if app is None:
            continue

        def _do(app=app, dev_name=dev_name) -> None:
            if wake_first:
                _wake_display(app)
            try:
                action(app, dev_name)
            except Exception:
                _LOGGER.exception("%s: failed for '%s'", call.service, dev_name)

        await hass.async_add_executor_job(_do)


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
            nav.open_wakeup_panel()

    await _device_action(hass, call, action=_wakeup_action, wake_first=True)


async def _handle_sleep(hass: HomeAssistant, call: ServiceCall) -> None:
    def _sleep_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is not None:
            nav.open_sleep_panel(True)

    await _device_action(hass, call, action=_sleep_action)


async def _handle_set_brightness(hass: HomeAssistant, call: ServiceCall) -> None:
    intensity: int = call.data["intensity"]

    def _brightness_action(app: Any, dev_name: str) -> None:
        _publish_action(app, ESPAction.SET_BRIGHTNESS, str(intensity))

    await _device_action(hass, call, action=_brightness_action)


async def _handle_send_command(hass: HomeAssistant, call: ServiceCall) -> None:
    cmd: str = call.data["cmd"]

    def _command_action(app: Any, dev_name: str) -> None:
        _publish_action(app, ESPAction.SEND_COMMAND, cmd)

    await _device_action(hass, call, action=_command_action)


async def _handle_goto_page(hass: HomeAssistant, call: ServiceCall) -> None:
    page_id: int = call.data["page"]

    def _goto_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is None:
            _LOGGER.warning("goto_page: navigation missing on '%s'", dev_name)
            return
        nav.goto_page(page_id)

    await _device_action(hass, call, action=_goto_action)


async def _handle_send_notification(hass: HomeAssistant, call: ServiceCall) -> None:
    timeout: int = call.data.get("timeout", 0)
    persistent: bool = call.data.get("persistent", False)

    data: dict[str, Any] = {
        "title": call.data["title"],
        "message": call.data.get("message", ""),
        "icon": call.data.get("icon", ""),
    }
    if timeout > 0:
        data["timeout"] = timeout
        action = (
            NotificationAction.SEND_NOTIFICATION_PERSISTENT_WITH_TIMEOUT
            if persistent
            else NotificationAction.SEND_NOTIFICATION_WITH_TIMEOUT
        )
    else:
        action = (
            NotificationAction.SEND_NOTIFICATION_PERSISTENT
            if persistent
            else NotificationAction.SEND_NOTIFICATION
        )

    def _notify_action(app: Any, dev_name: str) -> None:
        _publish_action(app, action, data)

    await _device_action(hass, call, action=_notify_action)


async def _handle_play_rtttl(hass: HomeAssistant, call: ServiceCall) -> None:
    song_str: str = call.data["song_str"]

    def _rtttl_action(app: Any, dev_name: str) -> None:
        _publish_action(app, ESPAction.PLAY_RTTTL, song_str)

    await _device_action(hass, call, action=_rtttl_action)


async def _handle_play_sound(hass: HomeAssistant, call: ServiceCall) -> None:
    sound_name: str = call.data["name"]

    def _sound_action(app: Any, dev_name: str) -> None:
        _publish_action(app, ESPAction.PLAY_SOUND, sound_name)

    await _device_action(hass, call, action=_sound_action)


async def _handle_reset_last_interaction(hass: HomeAssistant, call: ServiceCall) -> None:
    offset: int = call.data.get("offset", 0)

    def _reset_action(app: Any, dev_name: str) -> None:
        _publish_action(app, ESPAction.RESET_LAST_INTERACTION, str(offset))

    await _device_action(hass, call, action=_reset_action)


# ── Registration ─────────────────────────────────────────────


def async_register_services(hass: HomeAssistant) -> None:
    """Register all nspanel_haui services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_OPEN_PANEL):
        return  # all registered as one block

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_PANEL,
        partial(_handle_open_panel, hass),
        schema=SERVICE_OPEN_PANEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLOSE_PANEL,
        partial(_handle_close_panel, hass),
        schema=SERVICE_CLOSE_PANEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_WAKEUP,
        partial(_handle_wakeup, hass),
        schema=SERVICE_WAKEUP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SLEEP,
        partial(_handle_sleep, hass),
        schema=SERVICE_SLEEP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BRIGHTNESS,
        partial(_handle_set_brightness, hass),
        schema=SERVICE_SET_BRIGHTNESS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        partial(_handle_send_command, hass),
        schema=SERVICE_SEND_COMMAND_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GOTO_PAGE,
        partial(_handle_goto_page, hass),
        schema=SERVICE_GOTO_PAGE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_NOTIFICATION,
        partial(_handle_send_notification, hass),
        schema=SERVICE_SEND_NOTIFICATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_RTTTL,
        partial(_handle_play_rtttl, hass),
        schema=SERVICE_PLAY_RTTTL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_SOUND,
        partial(_handle_play_sound, hass),
        schema=SERVICE_PLAY_SOUND_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_LAST_INTERACTION,
        partial(_handle_reset_last_interaction, hass),
        schema=SERVICE_RESET_LAST_INTERACTION_SCHEMA,
    )

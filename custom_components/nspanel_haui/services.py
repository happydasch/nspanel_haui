"""Services for the NSPanel HAUI integration.

Provides HA service calls that go through the navigation controller so the
full render pipeline runs (goto_page, page ack, settle, set_panel).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

# ── Service names ────────────────────────────────────────────
SERVICE_OPEN_PANEL = "open_panel"
SERVICE_CLOSE_PANEL = "close_panel"
SERVICE_WAKEUP = "wakeup"
SERVICE_IDLE = "idle"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_RESET_LAST_INTERACTION = "reset_last_interaction"

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
SERVICE_SEND_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Optional("device", default=None): vol.Any(str, None),
        vol.Required("title"): cv.string,
        vol.Optional("message", default=""): cv.string,
        vol.Optional("icon", default=""): cv.string,
        vol.Optional("persistent", default=False): cv.boolean,
        vol.Optional("type", default="info"): vol.In(["info", "warning", "critical"]),
        vol.Optional("force_show", default=False): cv.boolean,
        vol.Optional("text_size", default="auto"): vol.Any(
            "auto", vol.All(vol.Coerce(int), vol.Range(min=1, max=3))
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

    Returns list of (device_name, app) tuples.  If device_id is None,
    returns ALL apps across all hub entries.
    """
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
            if getattr(app, "_ha_device_id", None) == device_id:
                targets.append((str(dev_name), app))

    return targets


def _wake_display(app: NSPanelHAUI) -> None:
    """Publish reset_last_interaction to wake the display."""
    try:
        esp_ctrl = app.controller.get("esphome")
        if esp_ctrl and hasattr(esp_ctrl, "esphome"):
            esp_ctrl.esphome.publish("reset_last_interaction", "0")
    except Exception:
        _LOGGER.debug(
            "reset_last_interaction failed for '%s'",
            getattr(app, "name", "?"),
            exc_info=True,
        )


def _publish_action(
    app: NSPanelHAUI,
    action: str,
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

    Resolves the ``device`` from the service call, looks up each target
    app, and dispatches *action* via the executor so HA's async loop is
    not blocked.  The action receives the full ``NSPanelHAUI`` instance so
    it can access both navigation and ESPHome controllers.
    """
    device_id: str | None = call.data.get("device")
    targets = _resolve_target_apps(hass, device_id)

    if not targets:
        _LOGGER.warning(
            "%s: no matching HAUI app (device=%s) — "
            "selected ESPHome device may not be running HAUI firmware",
            call.service,
            device_id,
        )
        return

    for dev_name, app in targets:
        def _do(app=app, dev_name=dev_name) -> None:
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
            # Wake is a device operation: reset the firmware interaction timer
            # (wake_first) always runs; the idle page is exited only when one
            # is actually shown.
            nav.exit_idle_to_prev_or_home(app.device.config)

    await _device_action(hass, call, action=_wakeup_action, wake_first=True)


async def _handle_idle(hass: HomeAssistant, call: ServiceCall) -> None:
    def _idle_action(app: Any, dev_name: str) -> None:
        nav = app.controller.get("navigation")
        if nav is not None:
            nav.open_idle_panel(True)

    await _device_action(hass, call, action=_idle_action)


async def _handle_send_notification(hass: HomeAssistant, call: ServiceCall) -> None:
    # Goes straight to the controller: the ESPHome send_notification actions
    # only carry title/message/icon/persistent/text_size, so type and
    # force_show would be lost.
    def _notify_action(app: Any, dev_name: str) -> None:
        persistent = call.data.get("persistent", False)
        force_show = call.data.get("force_show", False)
        # A persistent notification must be visible immediately, otherwise it
        # only sits in the queue and users never see it appear on the panel.
        if persistent and not force_show:
            force_show = True
        app.controller["notification"].send_notification(
            title=call.data["title"],
            message=call.data.get("message", ""),
            icon=call.data.get("icon", ""),
            persistent=persistent,
            notif_type=call.data.get("type", "info"),
            force_show=force_show,
            text_size=call.data.get("text_size", "auto"),
        )

    await _device_action(hass, call, action=_notify_action)


async def _handle_reset_last_interaction(hass: HomeAssistant, call: ServiceCall) -> None:
    offset: int = call.data.get("offset", 0)

    def _reset_action(app: Any, dev_name: str) -> None:
        _publish_action(app, "reset_last_interaction", str(offset))

    await _device_action(hass, call, action=_reset_action)


# ── Registration ─────────────────────────────────────────────


def async_register_services(hass: HomeAssistant) -> None:
    """Register all nspanel_haui services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_OPEN_PANEL):
        return  # all registered as one block

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
    ):
        hass.services.async_register(DOMAIN, name, partial(handler, hass), schema=schema)

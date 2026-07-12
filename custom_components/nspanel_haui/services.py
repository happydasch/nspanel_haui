"""Services for the NSPanel HAUI integration.

Provides HA service calls that go through the navigation controller so the
full render pipeline runs (goto_page, page ack, settle, set_panel).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .haui.mapping.const import ESPAction

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .nspanel_haui import NSPanelHAUI

_LOGGER = logging.getLogger(__name__)

# ── Service names ────────────────────────────────────────────
SERVICE_OPEN_PANEL = "open_panel"
SERVICE_CLOSE_PANEL = "close_panel"
SERVICE_WAKEUP = "wakeup"
SERVICE_SLEEP = "sleep"

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


# ── Service call handlers ───────────────────────────────────


async def _handle_open_panel(hass: HomeAssistant, call: ServiceCall) -> None:
    panel_key: str = call.data["panel"]
    wakeup: bool = call.data.get("wakeup", False)
    device_id: str | None = call.data.get("device_id")

    targets = _resolve_target_apps(hass, device_id)
    if not targets:
        _LOGGER.warning("open_panel: no matching HAUI device (device_id=%s)", device_id)
        return

    for dev_name, app in targets:
        nav = app.controller.get("navigation")
        if nav is None:
            _LOGGER.warning("open_panel: navigation missing on '%s'", dev_name)
            continue

        def _do_open(
            _app: NSPanelHAUI = app,
            _nav: Any = nav,
            _wakeup: bool = wakeup,
            _panel_key: str = panel_key,
            _dev_name: str = dev_name,
        ) -> None:
            if _wakeup:
                _wake_display(_app)
            try:
                _nav.open_panel(_panel_key)
            except Exception:
                _LOGGER.exception("open_panel: failed for '%s' panel=%s", _dev_name, _panel_key)

        await hass.async_add_executor_job(_do_open)


async def _handle_close_panel(hass: HomeAssistant, call: ServiceCall) -> None:
    device_id: str | None = call.data.get("device_id")
    targets = _resolve_target_apps(hass, device_id)
    for dev_name, app in targets:
        nav = app.controller.get("navigation")
        if nav is None:
            continue

        def _do_close(_nav: Any = nav, _dev_name: str = dev_name) -> None:
            try:
                _nav.close_panel()
            except Exception:
                _LOGGER.exception("close_panel: failed for '%s'", _dev_name)

        await hass.async_add_executor_job(_do_close)


async def _handle_wakeup(hass: HomeAssistant, call: ServiceCall) -> None:
    device_id: str | None = call.data.get("device_id")
    targets = _resolve_target_apps(hass, device_id)
    for dev_name, app in targets:
        nav = app.controller.get("navigation")
        if nav is None:
            continue

        def _do_wakeup(_app: NSPanelHAUI = app, _nav: Any = nav, _dev_name: str = dev_name) -> None:
            _wake_display(_app)
            try:
                _nav.open_wakeup_panel()
            except Exception:
                _LOGGER.exception("wakeup: failed for '%s'", _dev_name)

        await hass.async_add_executor_job(_do_wakeup)


async def _handle_sleep(hass: HomeAssistant, call: ServiceCall) -> None:
    device_id: str | None = call.data.get("device_id")
    targets = _resolve_target_apps(hass, device_id)
    for dev_name, app in targets:
        nav = app.controller.get("navigation")
        if nav is None:
            continue

        def _do_sleep(_nav: Any = nav, _dev_name: str = dev_name) -> None:
            try:
                _nav.open_sleep_panel(True)
            except Exception:
                _LOGGER.exception("sleep: failed for '%s'", _dev_name)

        await hass.async_add_executor_job(_do_sleep)


# ── Registration ─────────────────────────────────────────────


def async_register_services(hass: HomeAssistant) -> None:
    """Register all nspanel_haui services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_OPEN_PANEL):
        return  # all registered as one block

    async def _async_handle_open_panel(call: ServiceCall) -> None:
        await _handle_open_panel(hass, call)

    async def _async_handle_close_panel(call: ServiceCall) -> None:
        await _handle_close_panel(hass, call)

    async def _async_handle_wakeup(call: ServiceCall) -> None:
        await _handle_wakeup(hass, call)

    async def _async_handle_sleep(call: ServiceCall) -> None:
        await _handle_sleep(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_PANEL,
        _async_handle_open_panel,
        schema=SERVICE_OPEN_PANEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLOSE_PANEL,
        _async_handle_close_panel,
        schema=SERVICE_CLOSE_PANEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_WAKEUP,
        _async_handle_wakeup,
        schema=SERVICE_WAKEUP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SLEEP,
        _async_handle_sleep,
        schema=SERVICE_SLEEP_SCHEMA,
    )

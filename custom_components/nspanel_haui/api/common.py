"""Helpers shared by the REST views: error responses, request parsing, device lookup."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from ..const import DOMAIN
from ..haui.mapping.color import BUILTIN_THEMES

_LOGGER = logging.getLogger(__name__)

# The ``device`` value that addresses every running device of an entry.
ALL_DEVICES = "*"


class ApiError(Exception):
    """A refused request that ``api_errors`` answers with an error response."""

    def __init__(
        self, message: str, status_code: int, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error(
    view: HomeAssistantView,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> web.Response:
    """Build the ``{"status": "error", "message": ...}`` response of every view.

    ``details`` adds fields, e.g. the ``errors`` of a refused panel save.
    """
    return view.json(
        {"status": "error", "message": message, **(details or {})}, status_code=status_code
    )


def api_errors(
    handler: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Answer an ``ApiError`` raised by a view handler with the error response."""

    @wraps(handler)
    async def wrapper(view: HomeAssistantView, request: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await handler(view, request, *args, **kwargs)
        except ApiError as exc:
            return error(view, exc.message, exc.status_code, exc.details)

    return wrapper


def get_apps(hass: Any, entry_id: str) -> dict[str, Any] | None:
    """Return the running apps of a config entry by device name, or None when unset."""
    apps = hass.data.get(DOMAIN, {}).get(entry_id)
    return apps if isinstance(apps, dict) else None


def running_apps(hass: Any, entry_id: str) -> dict[str, Any]:
    """Return the entry's running apps by device name.

    Raises:
        ApiError: When the entry is not set up
    """
    apps = get_apps(hass, entry_id)
    if apps is None:
        raise ApiError("No running devices", 400)
    return apps


def device_app(apps: dict[str, Any], device_name: str) -> Any:
    """Return the running app of ``device_name``.

    Raises:
        ApiError: When the device runs no app
    """
    app = apps.get(device_name)
    if app is None:
        raise ApiError(f'Device "{device_name}" not found', 404)
    return app


def running_device_app(hass: Any, entry_id: str, device_name: str) -> Any:
    """Return one device's running app.

    Raises:
        ApiError: When the entry is not set up or the device runs no app
    """
    return device_app(running_apps(hass, entry_id), device_name)


def text_field(value: Any, name: str) -> str:
    """Return a request field as stripped text; a missing field is ''.

    Raises:
        ApiError: When the field is present but not a string
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ApiError(f"The {name} field must be a string", 400)
    return value.strip()


def query_device(request: web.Request) -> str:
    """Return the stripped ``device`` query param ('' when absent)."""
    return text_field(request.query.get("device"), "device")


def body_device(body: dict[str, Any]) -> str:
    """Return the body's ``device`` field; blank or missing addresses every device."""
    return text_field(body.get("device"), "device") or ALL_DEVICES


async def json_object(request: web.Request) -> dict[str, Any]:
    """Return the request's JSON object body; an empty body is ``{}``.

    Raises:
        ApiError: When the body is not JSON or not an object
    """
    try:
        body = await request.json()
    except ValueError as exc:
        raise ApiError("Invalid JSON request body", 400) from exc
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ApiError("The request body must be a JSON object", 400)
    return body


async def for_each_app(
    apps: dict[str, Any],
    action: str,
    run: Callable[[str, Any], Awaitable[str | None]],
) -> tuple[list[str], list[dict[str, str]]]:
    """Run ``run(name, app)`` for every app in turn.

    ``run`` returns why the device refused, or None on success. An exception
    counts as a refusal too, so one device cannot stop the rest.

    Returns:
        The names that succeeded, and ``{"name", "error"}`` for every failure
    """
    done: list[str] = []
    failed: list[dict[str, str]] = []
    for name, app in apps.items():
        try:
            message = await run(name, app)
        except Exception as exc:
            _LOGGER.exception("Failed to %s on device '%s'", action, name)
            failed.append({"name": name, "error": str(exc) or f"{action} failed"})
            continue
        if message:
            failed.append({"name": name, "error": message})
        else:
            done.append(name)
    return done, failed


def used_theme_ids(store: dict[str, Any]) -> set[str]:
    """Return the theme IDs the store's device settings and panels select."""
    used: set[str] = set()
    for device in store.get("devices", {}).values():
        if not isinstance(device, dict):
            continue
        config = device.get("config", {})
        if isinstance(config, dict):
            theme_id = config.get("theme_id", "dark")
            if isinstance(theme_id, str) and theme_id:
                used.add(theme_id)
        for panel in device.get("panels", []):
            if isinstance(panel, dict):
                theme_id = panel.get("theme_id", "")
                if isinstance(theme_id, str) and theme_id:
                    used.add(theme_id)
    return used


def ensure_known_theme_ids(store: dict[str, Any], themes: dict[str, Any]) -> None:
    """Reject a device or panel reference to a theme that is not available."""
    unknown = used_theme_ids(store) - set(BUILTIN_THEMES) - set(themes)
    if unknown:
        raise ApiError(f"Unknown color theme {sorted(unknown)[0]!r}", 400)


def now_iso() -> str:
    """Return the current time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()

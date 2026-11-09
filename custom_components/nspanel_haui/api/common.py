"""Helpers shared by the REST views: error responses, request parsing, device lookup."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from homeassistant.helpers.http import HomeAssistantView

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# The ``device`` value that addresses every running device of an entry.
ALL_DEVICES = "*"


class ApiError(Exception):
    """A refused request; ``api_errors`` answers it with the error response."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def error(view: HomeAssistantView, message: str, status_code: int):
    """Build the ``{"status": "error", "message": ...}`` response used by all views."""
    return view.json({"status": "error", "message": message}, status_code=status_code)


def api_errors(
    handler: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Answer an ``ApiError`` raised by a view handler with the error response."""

    @wraps(handler)
    async def wrapper(view: HomeAssistantView, request: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await handler(view, request, *args, **kwargs)
        except ApiError as exc:
            return error(view, exc.message, exc.status_code)

    return wrapper


def get_apps(hass: Any, entry_id: str) -> Any:
    """Return what hass.data holds for a config entry: the apps dict, or None if not set up."""
    return hass.data.get(DOMAIN, {}).get(entry_id)


def running_apps(hass: Any, entry_id: str) -> dict[str, Any]:
    """Return the entry's running apps by device name.

    Raises:
        ApiError: When the entry holds no apps dict (not set up)
    """
    apps = get_apps(hass, entry_id)
    if not isinstance(apps, dict):
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


def query_device(request: Any) -> str:
    """Return the stripped ``device`` query param ('' when absent)."""
    return (request.query.get("device") or "").strip()


def body_device(body: dict[str, Any]) -> str:
    """Return the body's ``device`` field; blank or missing addresses every device."""
    return (body.get("device") or "").strip() or ALL_DEVICES


async def json_object(request: Any) -> dict[str, Any]:
    """Return the request's JSON object body; an empty body is ``{}``.

    Raises:
        ApiError: When the body is not a JSON object
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
    """Run ``run(name, app)`` for every app, one after the other.

    ``run`` returns why the device refused, or None on success; an exception
    is logged and counts as a refusal too, so one device cannot stop the rest.

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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017

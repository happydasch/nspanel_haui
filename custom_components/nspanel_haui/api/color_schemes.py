"""Saved semantic color scheme library API."""

from __future__ import annotations

from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..haui.mapping.color import (
    BUILTIN_COLOR_SCHEMES,
    COLOR_SCHEME_VERSION,
    validate_color_schemes,
)
from ..hub.storage import empty_store, panel_store
from .common import ApiError, api_errors


class ColorSchemesView(HomeAssistantView):
    """Manage custom color definitions shared by devices in one entry."""

    url = "/api/nspanel_haui/color_schemes/{entry_id}"
    name = "api:nspanel_haui:color_schemes"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return built-in and saved custom color schemes."""
        store = panel_store(request.app["hass"], entry_id)
        data = await store.async_load() or empty_store()
        return self.json(
            {
                "version": COLOR_SCHEME_VERSION,
                "builtins": BUILTIN_COLOR_SCHEMES,
                "schemes": data.get("color_schemes", {}),
            }
        )

    @require_admin
    @api_errors
    async def post(self, request, entry_id: str):
        """Replace the custom scheme collection without pushing panel config."""
        hass = request.app["hass"]
        body = await request.json()
        if not isinstance(body, dict) or body.get("version") != COLOR_SCHEME_VERSION:
            raise ApiError("Unsupported color scheme file version", 400)
        try:
            schemes = await hass.async_add_executor_job(validate_color_schemes, body.get("schemes"))
        except Exception as exc:
            raise ApiError(str(exc), 400) from exc

        builtin_names = {scheme["name"].casefold() for scheme in BUILTIN_COLOR_SCHEMES.values()}
        if builtin_names.intersection(scheme["name"].casefold() for scheme in schemes.values()):
            raise ApiError("Custom scheme names must not duplicate built-in schemes", 400)

        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
        old_schemes = data.get("color_schemes", {})
        active_ids = {
            device.get("config", {}).get("color_scheme_id", "dark")
            for device in data.get("devices", {}).values()
            if isinstance(device, dict)
        }
        removed_in_use = (set(old_schemes) - set(schemes)) & active_ids
        if removed_in_use:
            raise ApiError(
                "Cannot remove a color scheme that is selected by a device: "
                + ", ".join(sorted(removed_in_use)),
                409,
            )
        changed_active = any(
            old_schemes.get(scheme_id) != schemes.get(scheme_id)
            for scheme_id in active_ids
            if scheme_id not in BUILTIN_COLOR_SCHEMES
        )

        data["color_schemes"] = schemes
        await store.async_save(data)
        if changed_active:
            from .config import push_panels

            await push_panels(hass, entry_id, data)
        return self.json({"version": COLOR_SCHEME_VERSION, "schemes": schemes})

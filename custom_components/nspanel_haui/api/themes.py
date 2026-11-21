"""Saved custom color theme library API."""

from __future__ import annotations

from aiohttp import web
from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..haui.mapping.color import (
    BUILTIN_THEMES,
    THEME_VERSION,
    validate_themes,
)
from ..hub.storage import empty_store, panel_store
from .common import ApiError, api_errors, ensure_known_theme_ids, json_object, used_theme_ids
from .panel_edits import edit_panels


class ThemesView(HomeAssistantView):
    """Manage the custom themes the devices of one entry share."""

    url = "/api/nspanel_haui/themes/{entry_id}"
    name = "api:nspanel_haui:themes"
    requires_auth = True

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the built-in themes and the saved custom themes."""
        store = panel_store(request.app["hass"], entry_id)
        data = await store.async_load() or empty_store()
        return self.json(
            {
                "version": THEME_VERSION,
                "builtins": BUILTIN_THEMES,
                "themes": data.get("themes", {}),
            }
        )

    @require_admin
    @api_errors
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Replace the custom theme collection; panels are pushed only if one changes."""
        hass = request.app["hass"]
        body = await json_object(request)
        if body.get("version") != THEME_VERSION:
            raise ApiError("Unsupported color theme file version", 400)
        try:
            themes = await hass.async_add_executor_job(validate_themes, body.get("themes"))
        except ValueError as exc:
            raise ApiError(str(exc), 400) from exc

        async with edit_panels(hass, entry_id) as edit:
            data = await edit.load()
            old_themes = data.get("themes", {})
            active_ids = used_theme_ids(data)
            removed_in_use = (set(old_themes) - set(themes)) & active_ids
            if removed_in_use:
                raise ApiError(
                    "Cannot remove a color theme that is selected by a device or panel: "
                    + ", ".join(sorted(removed_in_use)),
                    409,
                )
            ensure_known_theme_ids(data, themes)
            changed_active = any(
                old_themes.get(theme_id) != themes.get(theme_id)
                for theme_id in active_ids
                if theme_id not in BUILTIN_THEMES
            )

            data["themes"] = themes
            await edit.save(data, apply=changed_active)
        return self.json({"version": THEME_VERSION, "themes": themes})

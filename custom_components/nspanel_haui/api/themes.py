"""Saved semantic color theme library API."""

from __future__ import annotations

from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView

from ..haui.mapping.color import (
    BUILTIN_THEMES,
    THEME_VERSION,
    validate_themes,
)
from ..hub.storage import empty_store, panel_store
from .common import ApiError, api_errors, ensure_known_theme_ids, used_theme_ids


class ThemesView(HomeAssistantView):
    """Manage custom theme definitions shared by devices in one entry."""

    url = "/api/nspanel_haui/themes/{entry_id}"
    name = "api:nspanel_haui:themes"
    requires_auth = True

    @require_admin
    async def get(self, request, entry_id: str):
        """Return built-in and saved custom color themes."""
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
    async def post(self, request, entry_id: str):
        """Replace the custom theme collection without pushing panel config."""
        hass = request.app["hass"]
        body = await request.json()
        if not isinstance(body, dict) or body.get("version") != THEME_VERSION:
            raise ApiError("Unsupported color theme file version", 400)
        try:
            themes = await hass.async_add_executor_job(validate_themes, body.get("themes"))
        except Exception as exc:
            raise ApiError(str(exc), 400) from exc

        store = panel_store(hass, entry_id)
        data = await store.async_load() or empty_store()
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
        await store.async_save(data)
        if changed_active:
            from .config import push_panels

            await push_panels(hass, entry_id, data)
        return self.json({"version": THEME_VERSION, "themes": themes})

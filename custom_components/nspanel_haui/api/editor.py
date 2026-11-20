"""Static data the editor loads: translations, panel types, colours and icons."""

from __future__ import annotations

from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from .common import error


class TranslationsView(HomeAssistantView):
    """Return the display text translations for one language."""

    url = "/api/nspanel_haui/translations/{language}"
    name = "api:nspanel_haui:translations"
    requires_auth = True

    async def get(self, request: web.Request, language: str) -> web.Response:
        """Return the translations of a language code, falling back to English.

        Query param ``flat=1`` (the default) answers the flat
        ``{text_key: translation}`` mapping; ``flat=0`` the whole structure.
        ``section=component`` answers only the component section: the state
        names per domain, which the editor offers as an item's states.
        """
        from ..haui.utils.text import get_translations

        hass = request.app["hass"]
        try:
            translations = await hass.async_add_executor_job(get_translations, language)
        except ValueError as exc:
            return error(self, str(exc), 400)

        if request.query.get("section") == "component":
            return self.json(translations.get("component", {}))
        if request.query.get("flat", "1") == "1":
            return self.json(translations.get("text", {}))
        return self.json(translations)


class PanelTypesView(HomeAssistantView):
    """Return the panel type descriptors for the editor."""

    url = "/api/nspanel_haui/panel_types"
    name = "api:nspanel_haui:panel_types"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the descriptors of every user-visible panel type.

        Query param ``language`` (optional, defaults to ``"en"``) selects the
        locale of the translated fields.
        """
        from ..haui.mapping.panel import get_user_panel_type_descriptors

        lang = request.query.get("language", "en")
        hass = request.app["hass"]
        descriptors = await hass.async_add_executor_job(get_user_panel_type_descriptors, lang)
        return self.json(descriptors)


class ColorDefaultsView(HomeAssistantView):
    """Return the built-in colors of the panel types."""

    url = "/api/nspanel_haui/color_defaults"
    name = "api:nspanel_haui:color_defaults"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the ``COLORS`` registry as JSON."""
        from ..haui.mapping.color import COLORS

        return self.json(COLORS)


class IconSearchView(HomeAssistantView):
    """Return MDI icon names for the editor's icon picker."""

    url = "/api/nspanel_haui/icons"
    name = "api:nspanel_haui:icons"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the MDI icon names, or those containing the ``q`` query param.

        Without ``q`` the picker fetches every name once and searches it
        client-side.
        """
        from ..haui.mapping.icon_names import ICON_NAMES

        query = (request.query.get("q") or "").strip().lower()
        if not query:
            return self.json(ICON_NAMES)
        return self.json([name for name in ICON_NAMES if query in name])

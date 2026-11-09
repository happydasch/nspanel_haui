"""Static data the editor loads: translations, panel types, colours and icons."""

from __future__ import annotations

from homeassistant.helpers.http import HomeAssistantView

from .common import error


class TranslationsView(HomeAssistantView):
    """REST API view returning translation data for the frontend editor."""

    url = "/api/nspanel_haui/translations/{language}"
    name = "api:nspanel_haui:translations"
    requires_auth = True

    async def get(self, request, language: str):
        """Return translation data for a language code.

        Query param ``flat`` (optional, defaults to ``1``) controls whether the
        response is a flat ``{text_key: translation}`` mapping.  When ``0`` the
        full JSON structure (including ``component`` section) is returned.

        Falls back to English when the requested language is not available.
        """
        from ..haui.utils.text import get_translations

        hass = request.app["hass"]
        flat = request.query.get("flat", "1")
        try:
            translations = await hass.async_add_executor_job(get_translations, language)
        except ValueError as exc:
            return error(self, str(exc), 400)

        if flat == "1" or flat is True:
            return self.json(translations.get("text", {}))
        return self.json(translations)


class PanelTypesView(HomeAssistantView):
    """REST API view returning panel type descriptors for the frontend editor."""

    url = "/api/nspanel_haui/panel_types"
    name = "api:nspanel_haui:panel_types"
    requires_auth = True

    async def get(self, request):
        """Return JSON descriptors for all user-visible panel types.

        Query param ``language`` (optional, defaults to ``"en"``) controls the
        locale for pre-translating string fields.
        """
        from ..haui.mapping.panel import get_user_panel_type_descriptors

        lang = request.query.get("language", "en")
        hass = request.app["hass"]
        descriptors = await hass.async_add_executor_job(get_user_panel_type_descriptors, lang)
        return self.json(descriptors)


class ColorDefaultsView(HomeAssistantView):
    """REST API view returning built-in color defaults for the frontend editor."""

    url = "/api/nspanel_haui/color_defaults"
    name = "api:nspanel_haui:color_defaults"
    requires_auth = True

    async def get(self, request):
        """Return the COLORS dict as JSON (single source of truth from color.py)."""
        from ..haui.mapping.color import COLORS

        return self.json(COLORS)


class IconSearchView(HomeAssistantView):
    """REST API view providing MDI icon names for the frontend icon picker."""

    url = "/api/nspanel_haui/icons"
    name = "api:nspanel_haui:icons"
    requires_auth = True

    # Cache the icon list after first load
    _icons: list[str] | None = None

    async def get(self, request):
        """Return filtered list of MDI icon names.

        Query param ``q`` (optional) filters by substring match on the icon
        name (case-insensitive).  When omitted returns all icon names, which
        the icon picker fetches once and searches client-side.
        """
        if IconSearchView._icons is None:
            from ..haui.mapping.icon_names import ICON_NAMES

            IconSearchView._icons = ICON_NAMES

        query = (request.query.get("q") or "").strip().lower()
        if query:
            results = [name for name in IconSearchView._icons if query in name]
        else:
            results = IconSearchView._icons

        return self.json(results)

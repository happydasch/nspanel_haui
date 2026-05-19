"""Frontend resources for NSPanel HAUI - Editor."""

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

_LOGGER = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent
STATIC_URL_PATH = "/nspanel_haui_frontend"
PANEL_URL_PATH = "nspanel-haui"
PANEL_MODULE_URL = f"{STATIC_URL_PATH}/haui-editor.js"
ICONSET_URL = f"{STATIC_URL_PATH}/iconset.js"


async def async_register_frontend(hass) -> None:
    """Register the HAUI Editor frontend and sidebar panel."""
    if hass.data.get("nspanel_haui_frontend_registered"):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                STATIC_URL_PATH,
                str(FRONTEND_DIR),
                False,
            )
        ]
    )

    # Register the custom icon set as a global frontend module so the sidebar
    # icon (haui:home-assistant) is available before the editor panel loads.
    add_extra_js_url(hass, ICONSET_URL)

    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name="nspanel-haui-editor",
        module_url=PANEL_MODULE_URL,
        sidebar_title="NSPanel HAUI",
        sidebar_icon="haui:home-assistant",
        require_admin=True,
        embed_iframe=False,
    )

    hass.data["nspanel_haui_frontend_registered"] = True
    _LOGGER.info("NSPanel HAUI frontend panel registered at /%s", PANEL_URL_PATH)

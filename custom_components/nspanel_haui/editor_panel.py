"""Frontend resources for NSPanel HAUI.

Lives outside ``frontend/`` because that whole directory is served as
static files without authentication; it should hold only browser assets.
"""

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .haui.version import get_version

_LOGGER = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent / "frontend"
STATIC_URL_PREFIX = "/nspanel_haui_frontend"
PANEL_URL_PATH = "nspanel-haui"


async def async_register_frontend(hass) -> None:
    """Register the HAUI Editor frontend and sidebar panel."""
    if hass.data.get("nspanel_haui_frontend_registered"):
        return

    # The version is part of the path so an upgrade changes every module URL,
    # including the editor's relative imports, and browsers cannot mix a cached
    # old module with new ones.
    version = await hass.async_add_executor_job(get_version)
    static_url_path = f"{STATIC_URL_PREFIX}/{version}"

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                static_url_path,
                str(FRONTEND_DIR),
                False,
            )
        ]
    )

    # Register the custom icon set as a global frontend module so the sidebar
    # icon (haui:home-assistant) is available before the editor panel loads.
    add_extra_js_url(hass, f"{static_url_path}/iconset.js")

    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name="nspanel-haui-editor",
        module_url=f"{static_url_path}/haui-editor.js",
        sidebar_title="NSPanel HAUI",
        sidebar_icon="haui:home-assistant",
        require_admin=True,
        embed_iframe=False,
    )

    hass.data["nspanel_haui_frontend_registered"] = True
    _LOGGER.info("NSPanel HAUI frontend panel registered at /%s", PANEL_URL_PATH)

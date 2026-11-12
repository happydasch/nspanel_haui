"""REST API of the NSPanel HAUI editor.

One module per area: ``editor`` (static editor data), ``config`` (panel store,
devices, YAML), ``status`` (live device state) and ``updates`` (TFT and
firmware); ``common`` holds what they share.
"""

from __future__ import annotations

from typing import Any

from .config import DeviceConfigView, DeviceYamlView, PanelConfigView
from .editor import (
    ColorDefaultsView,
    IconSearchView,
    PanelTypesView,
    TranslationsView,
)
from .status import (
    DeviceRefreshDisplayView,
    DeviceStatusView,
    NotificationsView,
)
from .themes import ThemesView
from .updates import (
    DeviceFirmwareReleasesView,
    DeviceTftReleasesView,
    DeviceUpdateArtifactView,
    DeviceUpdateCheckView,
    DeviceUpdateFirmwareView,
    DeviceUpdateTftView,
    DeviceUpdateUploadView,
)

VIEWS = (
    TranslationsView,
    PanelConfigView,
    PanelTypesView,
    ColorDefaultsView,
    ThemesView,
    DeviceConfigView,
    DeviceStatusView,
    NotificationsView,
    DeviceRefreshDisplayView,
    DeviceUpdateUploadView,
    DeviceUpdateArtifactView,
    DeviceUpdateTftView,
    DeviceTftReleasesView,
    DeviceUpdateFirmwareView,
    DeviceFirmwareReleasesView,
    DeviceUpdateCheckView,
    DeviceYamlView,
    IconSearchView,
)


def register_views(hass: Any) -> None:
    """Register every REST view with Home Assistant's HTTP server."""
    for view in VIEWS:
        hass.http.register_view(view())

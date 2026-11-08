"""REST API of the NSPanel HAUI editor.

One module per area: ``editor`` (static editor data), ``config`` (panel store,
devices, YAML), ``status`` (live device state) and ``updates`` (TFT and
firmware); ``common`` holds what they share.
"""

from __future__ import annotations

from typing import Any

from .color_schemes import ColorSchemesView
from .config import DeviceConfigView, DeviceYamlView, PanelConfigView
from .editor import (
    ColorDefaultsView,
    IconCharsView,
    IconSearchView,
    PanelTypesView,
    TranslationsView,
)
from .status import (
    DeviceRefreshDisplayView,
    DeviceResetInteractionView,
    DeviceStatusView,
    NotificationsView,
)
from .updates import (
    DeviceFirmwareReleasesView,
    DeviceTftReleasesView,
    DeviceUpdateArtifactView,
    DeviceUpdateCheckView,
    DeviceUpdateFirmwareView,
    DeviceUpdateTftView,
    DeviceUpdateUploadView,
    FirmwareDownloadView,
)

VIEWS = (
    TranslationsView,
    PanelConfigView,
    PanelTypesView,
    ColorDefaultsView,
    ColorSchemesView,
    DeviceConfigView,
    DeviceStatusView,
    NotificationsView,
    DeviceRefreshDisplayView,
    DeviceResetInteractionView,
    DeviceUpdateUploadView,
    DeviceUpdateArtifactView,
    DeviceUpdateTftView,
    DeviceTftReleasesView,
    DeviceUpdateFirmwareView,
    DeviceFirmwareReleasesView,
    DeviceUpdateCheckView,
    FirmwareDownloadView,
    DeviceYamlView,
    IconSearchView,
    IconCharsView,
)


def register_views(hass: Any) -> None:
    """Register every REST view with Home Assistant's HTTP server."""
    for view in VIEWS:
        hass.http.register_view(view())

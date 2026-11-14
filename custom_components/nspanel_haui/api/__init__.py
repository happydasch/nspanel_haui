"""REST API of the NSPanel HAUI editor.

One module per area: ``editor`` (static editor data), ``config`` (panel store,
devices, YAML), ``status`` (live device state) and ``updates`` (TFT and
firmware); ``common`` holds what they share.
"""

from __future__ import annotations

from typing import Any

from .config import (
    DeviceConfigView,
    DeviceOrderView,
    DevicePanelsView,
    DeviceSettingsView,
    DeviceYamlView,
    PanelConfigView,
)
from .editor import (
    ColorDefaultsView,
    IconSearchView,
    PanelTemplatesView,
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
    RolloutDeviceView,
    RolloutView,
    UpdateControlView,
)

VIEWS = (
    TranslationsView,
    PanelConfigView,
    DeviceOrderView,
    PanelTypesView,
    PanelTemplatesView,
    ColorDefaultsView,
    ThemesView,
    DeviceConfigView,
    DeviceSettingsView,
    DevicePanelsView,
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
    UpdateControlView,
    RolloutView,
    RolloutDeviceView,
    DeviceYamlView,
    IconSearchView,
)


def register_views(hass: Any) -> None:
    """Register every REST view with Home Assistant's HTTP server."""
    for view in VIEWS:
        hass.http.register_view(view())

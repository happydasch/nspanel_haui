"""REST API of the NSPanel HAUI editor.

One module per area: ``editor`` (static editor data), ``config`` (panel store,
devices, themes, YAML), ``status`` (live device state) and ``updates`` (TFT and
firmware); ``panel_edits`` serializes the store writes and ``common`` holds the
helpers they share.
"""

from __future__ import annotations

from typing import Any

from .config import (
    DeviceConfigView,
    DeviceCopyView,
    DeviceOrderView,
    DevicePanelMoveView,
    DevicePanelsView,
    DeviceSettingsView,
    DeviceYamlView,
    PanelConfigView,
)
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
    DeviceRepairDisplayView,
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
    ColorDefaultsView,
    ThemesView,
    DeviceConfigView,
    DeviceSettingsView,
    DevicePanelsView,
    DevicePanelMoveView,
    DeviceStatusView,
    NotificationsView,
    DeviceRefreshDisplayView,
    DeviceUpdateUploadView,
    DeviceUpdateArtifactView,
    DeviceUpdateTftView,
    DeviceTftReleasesView,
    DeviceUpdateFirmwareView,
    DeviceRepairDisplayView,
    DeviceFirmwareReleasesView,
    DeviceUpdateCheckView,
    UpdateControlView,
    RolloutView,
    RolloutDeviceView,
    DeviceYamlView,
    DeviceCopyView,
    IconSearchView,
)


def register_views(hass: Any) -> None:
    """Register every REST view with Home Assistant's HTTP server."""
    for view in VIEWS:
        hass.http.register_view(view())

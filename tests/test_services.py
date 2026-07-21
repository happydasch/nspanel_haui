"""Tests for NSPanel HAUI services."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Stub out homeassistant before importing services so tests run without HA.
# (voluptuous is installed as a dev dependency, so it doesn't need stubbing.)
# ---------------------------------------------------------------------------


def _install_ha_stubs() -> None:
    """Insert minimal homeassistant stubs for services tests."""

    class _ServiceCall:
        def __init__(self, data: dict[str, Any]) -> None:
            self.data = data

    core = MagicMock()
    core.ServiceCall = _ServiceCall  # type: ignore[attr-defined]

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = ["homeassistant.helpers"]
    helpers.config_validation = MagicMock()

    stubs = {
        "homeassistant": MagicMock(),
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": helpers.config_validation,
        "homeassistant.const": MagicMock(),
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_install_ha_stubs()

import pytest  # noqa: E402
from nspanel_haui.haui.mapping.const import (  # noqa: E402
    NotificationAction,
)
from nspanel_haui.services import (  # noqa: E402
    DOMAIN,
    SERVICE_CLOSE_PANEL,
    SERVICE_OPEN_PANEL,
    SERVICE_RESET_LAST_INTERACTION,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_SLEEP,
    SERVICE_WAKEUP,
    _resolve_target_apps,
    async_register_services,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant with the HAUI apps dict."""
    hass = MagicMock(spec_set=["data", "services", "async_create_task", "async_add_executor_job"])
    hass.data = {}
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro_or_future: MagicMock())
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    return hass


@pytest.fixture
def mock_nav():
    """Create a mock navigation controller."""
    nav = MagicMock()
    nav.open_panel = MagicMock()
    nav.close_panel = MagicMock()
    nav.open_wakeup_panel = MagicMock()
    nav.open_sleep_panel = MagicMock()
    nav.goto_page = MagicMock()
    return nav


@pytest.fixture
def mock_esphome_ctrl():
    """Create a mock ESPHome controller with esphome proxy."""
    ctrl = MagicMock()
    ctrl.esphome = MagicMock()
    ctrl.esphome.publish = MagicMock()
    return ctrl


def _make_app(
    mock_nav, mock_esphome_ctrl, *, ha_device_id: str = "dev_1", name: str = "test_device"
):
    """Create a minimal NSPanelHAUI-like mock."""
    app = MagicMock()
    app._ha_device_id = ha_device_id
    app.controller = {"navigation": mock_nav, "esphome": mock_esphome_ctrl}
    app.name = name
    return app


# ── _resolve_target_apps ────────────────────────────────────────────────


class TestResolveTargetApps:
    """Tests for _resolve_target_apps."""

    def test_no_device_id_returns_all(self, mock_hass, mock_nav, mock_esphome_ctrl):
        """Without device_id, returns all apps across all entry_ids."""
        app1 = _make_app(mock_nav, mock_esphome_ctrl)
        app2 = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_2", name="other")
        mock_hass.data[DOMAIN] = {
            "entry_1": {"first": app1},
            "entry_2": {"second": app2},
        }
        targets = _resolve_target_apps(mock_hass, device_id=None)
        assert len(targets) == 2

    def test_device_id_filter(self, mock_hass, mock_nav, mock_esphome_ctrl):
        """With device_id, only matching apps are returned."""
        app1 = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
        app2 = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_other", name="other")
        mock_hass.data[DOMAIN] = {
            "entry_1": {"first": app1, "second": app2},
        }
        targets = _resolve_target_apps(mock_hass, device_id="dev_target")
        assert len(targets) == 1
        assert targets[0][1]._ha_device_id == "dev_target"

    def test_unknown_device_id(self, mock_hass, mock_nav, mock_esphome_ctrl):
        """Unknown device_id returns empty list."""
        app = _make_app(mock_nav, mock_esphome_ctrl)
        mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}
        targets = _resolve_target_apps(mock_hass, device_id="nonexistent")
        assert len(targets) == 0

    def test_skips_non_dict_entries(self, mock_hass, mock_nav, mock_esphome_ctrl):
        """Skips non-dict entries like _device_id_listeners."""
        app = _make_app(mock_nav, mock_esphome_ctrl)
        mock_hass.data[DOMAIN] = {
            "entry_1": {"dev": app},
            "_device_id_listeners": "skipped",
        }
        targets = _resolve_target_apps(mock_hass, device_id="dev_1")
        assert len(targets) == 1

    def test_empty_data(self, mock_hass):
        """Empty data returns empty list."""
        mock_hass.data[DOMAIN] = {}
        targets = _resolve_target_apps(mock_hass, device_id=None)
        assert len(targets) == 0


# ── async_register_services ─────────────────────────────────────────────


class TestRegisterServices:
    """Tests for async_register_services."""

    def test_registers_all_services(self, mock_hass):
        """All services are registered."""
        async_register_services(mock_hass)
        assert mock_hass.services.async_register.call_count == 6

    def test_idempotent(self, mock_hass):
        """Second call skips registration (has_service returns True)."""
        mock_hass.services.has_service = MagicMock(return_value=True)
        async_register_services(mock_hass)
        async_register_services(mock_hass)
        # async_register should not be called since has_service returns True
        assert mock_hass.services.async_register.call_count == 0

    def test_registers_correct_names(self, mock_hass):
        """Services are registered with correct names."""
        async_register_services(mock_hass)
        registered = [call.args[1] for call in mock_hass.services.async_register.call_args_list]
        assert SERVICE_OPEN_PANEL in registered
        assert SERVICE_CLOSE_PANEL in registered
        assert SERVICE_WAKEUP in registered
        assert SERVICE_SLEEP in registered
        assert SERVICE_SEND_NOTIFICATION in registered
        assert SERVICE_RESET_LAST_INTERACTION in registered


# ── Service handler integration tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_open_panel(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel delegates to nav.open_panel."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": False, "device_id": "dev_1"}

    await _handle_open_panel(mock_hass, call)

    mock_nav.open_panel.assert_called_once_with("alarm")


@pytest.mark.asyncio
async def test_open_panel_with_wakeup(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel with wakeup=True also calls reset_last_interaction."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": True, "device_id": "dev_1"}

    await _handle_open_panel(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "0")
    mock_nav.open_panel.assert_called_once_with("alarm")


@pytest.mark.asyncio
async def test_open_panel_no_matching_device(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel with unknown device_id logs warning, no crash."""
    mock_hass.data[DOMAIN] = {}
    from nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": False, "device_id": "unknown"}

    # Should not raise
    await _handle_open_panel(mock_hass, call)


@pytest.mark.asyncio
async def test_close_panel(mock_hass, mock_nav, mock_esphome_ctrl):
    """close_panel delegates to nav.close_panel."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_close_panel

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_close_panel(mock_hass, call)

    mock_nav.close_panel.assert_called_once()


@pytest.mark.asyncio
async def test_wakeup(mock_hass, mock_nav, mock_esphome_ctrl):
    """wakeup delegates to nav.open_wakeup_panel and resets interaction."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_wakeup

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_wakeup(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "0")
    mock_nav.open_wakeup_panel.assert_called_once()


@pytest.mark.asyncio
async def test_sleep(mock_hass, mock_nav, mock_esphome_ctrl):
    """sleep delegates to nav.open_sleep_panel(True)."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_sleep

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_sleep(mock_hass, call)

    mock_nav.open_sleep_panel.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_set_brightness(mock_hass, mock_nav, mock_esphome_ctrl):
    """set_brightness publishes ESPAction.SET_BRIGHTNESS with intensity."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_send_notification

    call = MagicMock()
    call.data = {
        "title": "Doorbell",
        "message": "At the door",
        "icon": "mdi:bell",
        "timeout": 0,
        "persistent": False,
        "device_id": "dev_1",
    }

    await _handle_send_notification(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with(
        NotificationAction.SEND_NOTIFICATION,
        {
            "title": "Doorbell",
            "message": "At the door",
            "icon": "mdi:bell",
            "notif_type": "info",
            "force_show": False,
        },
    )


@pytest.mark.asyncio
async def test_send_notification_persistent_with_timeout(mock_hass, mock_nav, mock_esphome_ctrl):
    """persistent + timeout selects the persistent-with-timeout action."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_send_notification

    call = MagicMock()
    call.data = {
        "title": "Alarm",
        "message": "",
        "icon": "",
        "timeout": 30,
        "persistent": True,
        "device_id": "dev_1",
    }

    await _handle_send_notification(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with(
        NotificationAction.SEND_NOTIFICATION_PERSISTENT_WITH_TIMEOUT,
        {
            "title": "Alarm",
            "message": "",
            "icon": "",
            "timeout": 30,
            "notif_type": "info",
            "force_show": False,
        },
    )


@pytest.mark.asyncio
async def test_reset_last_interaction(mock_hass, mock_nav, mock_esphome_ctrl):
    """reset_last_interaction publishes the offset as a string."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from nspanel_haui.services import _handle_reset_last_interaction

    call = MagicMock()
    call.data = {"offset": 5, "device_id": "dev_1"}

    await _handle_reset_last_interaction(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "5")

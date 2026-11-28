"""Tests for NSPanel HAUI services."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Stub out homeassistant before importing services so tests run without HA.
# (probatio ships with Home Assistant, so it doesn't need stubbing.)
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

import probatio as vol  # noqa: E402
import pytest  # noqa: E402

from custom_components.nspanel_haui.haui.mapping.const import SOUND_NAMES  # noqa: E402
from custom_components.nspanel_haui.haui.utils.image_program import (  # noqa: E402
    MAX_RUN_BUDGET,
    MIN_RUN_BUDGET,
)
from custom_components.nspanel_haui.services import (  # noqa: E402
    DOMAIN,
    SERVICE_CLOSE_PANEL,
    SERVICE_IDLE,
    SERVICE_OPEN_PANEL,
    SERVICE_RESET_LAST_INTERACTION,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_SEND_NOTIFICATION_SCHEMA,
    SERVICE_UPDATE_FIRMWARE,
    SERVICE_UPDATE_FIRMWARE_SCHEMA,
    SERVICE_UPDATE_TFT,
    SERVICE_UPDATE_TFT_SCHEMA,
    SERVICE_WAKEUP,
    _resolve_target_apps,
    async_register_services,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant with the HAUI apps dict."""
    hass = MagicMock(
        spec_set=["data", "services", "async_create_task", "async_add_executor_job", "config"]
    )
    hass.data = {}
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro_or_future: MagicMock())
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    hass.config = MagicMock()
    return hass


@pytest.fixture
def mock_nav():
    """Create a mock navigation controller."""
    nav = MagicMock()
    nav.open_panel = MagicMock()
    nav.close_panel = MagicMock()
    nav.open_idle_panel = MagicMock()
    nav.exit_idle_to_prev_or_home = MagicMock()
    nav.goto_page = MagicMock()
    return nav


@pytest.fixture
def mock_esphome_ctrl():
    """Create a mock ESPHome controller with esphome proxy."""
    ctrl = MagicMock()
    ctrl.esphome = MagicMock()
    ctrl.esphome.publish = MagicMock()
    return ctrl


@pytest.fixture(autouse=True)
def device_registry(monkeypatch):
    """Stub HA's device registry; tests add ``device id → identifiers`` to the returned dict."""
    devices: dict[str, set[tuple[str, str]]] = {}

    def _get_device(device_id: str) -> Any:
        if device_id not in devices:
            return None
        return types.SimpleNamespace(id=device_id, identifiers=devices[device_id])

    registry = types.ModuleType("homeassistant.helpers.device_registry")
    registry.async_get = lambda hass: types.SimpleNamespace(async_get=_get_device)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.device_registry", registry)
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers"], "device_registry", registry, raising=False
    )
    return devices


class _ServiceValidationError(Exception):
    pass


class _HomeAssistantError(Exception):
    pass


@pytest.fixture(autouse=True)
def ha_exceptions(monkeypatch):
    """Stub ``homeassistant.exceptions`` with the errors a service raises."""
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.ServiceValidationError = _ServiceValidationError
    exceptions.HomeAssistantError = _HomeAssistantError
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions)
    return exceptions


@pytest.fixture(autouse=True)
def unreachable_preflight(monkeypatch):
    """Home Assistant cannot reach the test URLs: the pre-flight only warns.

    ``update_url`` asks Home Assistant's shared session; a transport error
    is the "the panel may still reach it" path, so URL installs proceed.
    """
    from custom_components.nspanel_haui import update_url

    class _Unreachable:
        async def head(self, *args, **kwargs):
            raise OSError("no route to host")

        async def get(self, *args, **kwargs):
            raise OSError("no route to host")

    monkeypatch.setattr(update_url, "_session", lambda hass: _Unreachable())


def _make_app(
    mock_nav, mock_esphome_ctrl, *, ha_device_id: str = "dev_1", name: str = "test_device"
):
    """Create a minimal NSPanelHAUI-like mock."""
    app = MagicMock()
    # Real apps queue the action on their worker thread; run it straight away here.
    app.dispatch = MagicMock(side_effect=lambda fn, *args: fn(*args))
    app._ha_device_id = ha_device_id
    app.controller = {"navigation": mock_nav, "esphome": mock_esphome_ctrl}
    app.name = name
    # The controller answers on its worker; the service waits for that answer,
    # so a bare MagicMock would leave every install waiting out the timeout.
    app.start_async_tft_install = MagicMock(
        side_effect=lambda version, url, on_complete: on_complete({"state": "installing"})
    )
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

    @pytest.mark.parametrize(
        "device_id",
        [
            pytest.param("esphome_kitchen", id="esphome-device"),
            pytest.param("haui_kitchen", id="haui-device"),
        ],
    )
    def test_both_devices_of_a_panel_select_it(
        self, mock_hass, mock_nav, mock_esphome_ctrl, device_registry, device_id
    ):
        """The ESPHome device and the HAUI device (the one the selector offers) both match."""
        kitchen = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="esphome_kitchen")
        office = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="esphome_office")
        mock_hass.data[DOMAIN] = {"entry_1": {"kitchen": kitchen, "office": office}}
        device_registry["esphome_kitchen"] = {("esphome", "aa:bb:cc:dd:ee:ff")}
        device_registry["haui_kitchen"] = {(DOMAIN, "kitchen")}
        device_registry["haui_office"] = {(DOMAIN, "office")}

        assert _resolve_target_apps(mock_hass, device_id=device_id) == [("kitchen", kitchen)]

    def test_device_of_another_integration_does_not_match(
        self, mock_hass, mock_nav, mock_esphome_ctrl, device_registry
    ):
        """A registered device only matches through an nspanel_haui identifier."""
        app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="esphome_kitchen")
        mock_hass.data[DOMAIN] = {"entry_1": {"kitchen": app}}
        device_registry["hue_kitchen"] = {("hue", "kitchen")}

        assert _resolve_target_apps(mock_hass, device_id="hue_kitchen") == []

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
        assert mock_hass.services.async_register.call_count == 10

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
        assert SERVICE_IDLE in registered
        assert SERVICE_SEND_NOTIFICATION in registered
        assert SERVICE_RESET_LAST_INTERACTION in registered
        assert SERVICE_UPDATE_TFT in registered
        assert SERVICE_UPDATE_FIRMWARE in registered


def test_update_tft_requires_a_device():
    """The TFT update service must never default to every registered device."""
    with pytest.raises(vol.Invalid):
        SERVICE_UPDATE_TFT_SCHEMA({})


# ── Service handler integration tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_open_panel(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel delegates to nav.open_panel."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": False, "device_id": "dev_1"}

    await _handle_open_panel(mock_hass, call)

    mock_nav.open_panel.assert_called_once_with("alarm")
    mock_nav.reset_activity.assert_called_once_with()


@pytest.mark.asyncio
async def test_open_panel_with_wakeup(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel with wakeup=True also calls reset_last_interaction."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": True, "device_id": "dev_1"}

    await _handle_open_panel(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "0")
    mock_nav.reset_activity.assert_called_once_with()
    mock_nav.open_panel.assert_called_once_with("alarm")


@pytest.mark.asyncio
async def test_open_panel_no_matching_device(mock_hass, mock_nav, mock_esphome_ctrl):
    """open_panel with an unknown device fails the call."""
    mock_hass.data[DOMAIN] = {}
    from custom_components.nspanel_haui.services import _handle_open_panel

    call = MagicMock()
    call.data = {"panel": "alarm", "wakeup": False, "device": "unknown"}
    call.service = SERVICE_OPEN_PANEL

    with pytest.raises(_ServiceValidationError, match="device unknown"):
        await _handle_open_panel(mock_hass, call)


@pytest.mark.asyncio
async def test_close_panel(mock_hass, mock_nav, mock_esphome_ctrl):
    """close_panel delegates to nav.close_panel."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_close_panel

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_close_panel(mock_hass, call)

    mock_nav.close_panel.assert_called_once()


@pytest.mark.asyncio
async def test_update_tft_targets_selected_device(mock_hass, mock_nav, mock_esphome_ctrl):
    """update_tft installs the firmware-matched TFT only on the selected device."""
    target = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    other = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_other", name="other")
    mock_hass.data[DOMAIN] = {"entry_1": {"target": target, "other": other}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target"}
    call.service = SERVICE_UPDATE_TFT

    await _handle_update_tft(mock_hass, call)

    target.start_async_tft_install.assert_called_once()
    assert target.start_async_tft_install.call_args.args[:2] == (None, None)
    assert callable(target.start_async_tft_install.call_args.args[2])
    other.start_async_tft_install.assert_not_called()


@pytest.mark.asyncio
async def test_update_tft_accepts_the_haui_device(
    mock_hass, mock_nav, mock_esphome_ctrl, device_registry
):
    """The device the service's selector offers (the HAUI device) starts the install."""
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="esphome_kitchen")
    mock_hass.data[DOMAIN] = {"entry_1": {"kitchen": app}}
    device_registry["haui_kitchen"] = {(DOMAIN, "kitchen")}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "haui_kitchen"}
    call.service = SERVICE_UPDATE_TFT

    await _handle_update_tft(mock_hass, call)

    app.start_async_tft_install.assert_called_once()
    assert app.start_async_tft_install.call_args.args[:2] == (None, None)


@pytest.mark.asyncio
async def test_update_tft_rejects_an_unknown_device(mock_hass, mock_nav, mock_esphome_ctrl):
    """An id that is neither device of a panel fails the call and installs nothing."""
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="esphome_kitchen")
    mock_hass.data[DOMAIN] = {"entry_1": {"kitchen": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "unknown", "url": "http://homeassistant.local:8123/local/x.tft"}
    call.service = SERVICE_UPDATE_TFT

    with pytest.raises(_ServiceValidationError, match=r"update_tft: .*device unknown"):
        await _handle_update_tft(mock_hass, call)

    app.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_update_tft_with_url_installs_that_file(mock_hass, mock_nav, mock_esphome_ctrl):
    """The url field replaces the public ESPHome upload_tft_url action."""
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target", "url": "http://ha.local/nspanel_haui.tft"}
    call.service = SERVICE_UPDATE_TFT

    await _handle_update_tft(mock_hass, call)

    app.start_async_tft_install.assert_called_once()
    assert app.start_async_tft_install.call_args.args[:2] == (
        None,
        "http://ha.local/nspanel_haui.tft",
    )


@pytest.mark.asyncio
async def test_update_tft_with_version_installs_that_release(
    mock_hass, mock_nav, mock_esphome_ctrl
):
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target", "version": "0.4.1"}
    call.service = SERVICE_UPDATE_TFT

    await _handle_update_tft(mock_hass, call)

    app.start_async_tft_install.assert_called_once()
    assert app.start_async_tft_install.call_args.args[:2] == ("0.4.1", None)


@pytest.mark.asyncio
async def test_update_tft_answers_with_the_controllers_state(
    mock_hass, mock_nav, mock_esphome_ctrl
):
    """The call returns the state, so an automation can branch on it."""
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    app.start_async_tft_install = MagicMock(
        side_effect=lambda version, url, on_complete: on_complete(
            {"state": "installing", "tft_url": url}
        )
    )
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target", "url": "http://ha.local/display.tft"}
    call.service = SERVICE_UPDATE_TFT

    answer = await _handle_update_tft(mock_hass, call)

    assert answer["state"] == "installing"
    assert answer["tft_url"] == "http://ha.local/display.tft"


@pytest.mark.asyncio
async def test_update_tft_raises_the_controllers_reason(mock_hass, mock_nav, mock_esphome_ctrl):
    """A refusal reaches the caller instead of only the log."""
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target", name="kitchen")
    app.start_async_tft_install = MagicMock(
        side_effect=lambda version, url, on_complete: on_complete(
            {"state": "error", "last_error": "A TFT install started earlier is still running"}
        )
    )
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target"}
    call.service = SERVICE_UPDATE_TFT

    with pytest.raises(_HomeAssistantError, match="still running"):
        await _handle_update_tft(mock_hass, call)


@pytest.mark.asyncio
async def test_update_tft_reports_started_when_the_worker_does_not_answer(
    mock_hass, mock_nav, mock_esphome_ctrl, monkeypatch
):
    """A busy worker delays the answer; the dispatch is queued, not lost."""
    from custom_components.nspanel_haui import services

    monkeypatch.setattr(services, "ANSWER_TIMEOUT_SECONDS", 0.01)
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    app.start_async_tft_install = MagicMock()  # never answers
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    call = MagicMock()
    call.data = {"device": "dev_target"}
    call.service = SERVICE_UPDATE_TFT

    assert await services._handle_update_tft(mock_hass, call) == {"state": "started"}
    app.start_async_tft_install.assert_called_once()


@pytest.mark.asyncio
async def test_update_tft_refuses_a_url_the_panel_cannot_install(
    mock_hass, mock_nav, mock_esphome_ctrl, monkeypatch
):
    """The pre-flight runs before anything is dispatched."""
    from custom_components.nspanel_haui import update_url

    async def _problem(hass, url):
        return "The TFT URL answered HTTP 404"

    monkeypatch.setattr(update_url, "tft_url_problem", _problem)
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_tft

    call = MagicMock()
    call.data = {"device": "dev_target", "url": "http://ha.local/missing.tft"}
    call.service = SERVICE_UPDATE_TFT

    with pytest.raises(_HomeAssistantError, match="HTTP 404"):
        await _handle_update_tft(mock_hass, call)

    app.start_async_tft_install.assert_not_called()


def test_the_tft_service_registers_as_answering(mock_hass):
    """``update_tft`` reports a state; the other services stay fire-and-forget."""
    from custom_components.nspanel_haui import services as svc

    svc.async_register_services(mock_hass)

    responses = {
        call.args[1]: call.kwargs.get("supports_response")
        for call in mock_hass.services.async_register.call_args_list
    }
    # homeassistant.core is a stub here: playbook of distinct enum members.
    assert responses[SERVICE_UPDATE_TFT] != responses[SERVICE_OPEN_PANEL]
    assert responses[SERVICE_UPDATE_FIRMWARE] == responses[SERVICE_OPEN_PANEL]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "args"),
    [
        pytest.param({}, (None, None), id="offered-update"),
        pytest.param({"version": "v0.4.2"}, ("v0.4.2", None), id="release"),
        pytest.param({"url": "http://ha.local/fw.bin"}, (None, "http://ha.local/fw.bin"), id="url"),
    ],
)
async def test_update_firmware_installs_the_chosen_firmware(
    mock_hass, mock_nav, mock_esphome_ctrl, data, args
):
    app = _make_app(mock_nav, mock_esphome_ctrl, ha_device_id="dev_target")
    mock_hass.data[DOMAIN] = {"entry_1": {"target": app}}

    from custom_components.nspanel_haui.services import _handle_update_firmware

    call = MagicMock()
    call.data = {"device": "dev_target", **data}
    call.service = SERVICE_UPDATE_FIRMWARE

    await _handle_update_firmware(mock_hass, call)

    app.start_async_firmware_install.assert_called_once()
    assert app.start_async_firmware_install.call_args.args[:2] == args


def test_update_firmware_takes_a_version_or_a_url_not_both():
    with pytest.raises(vol.Invalid):
        SERVICE_UPDATE_FIRMWARE_SCHEMA(
            {"device": "dev_target", "version": "v0.4.2", "url": "http://ha.local/fw.bin"}
        )


def test_update_tft_takes_a_version_or_a_url_not_both():
    with pytest.raises(vol.Invalid):
        SERVICE_UPDATE_TFT_SCHEMA(
            {"device": "dev_target", "version": "0.4.1", "url": "http://ha.local/x.tft"}
        )


@pytest.mark.asyncio
async def test_wakeup(mock_hass, mock_nav, mock_esphome_ctrl):
    """wakeup resets the interaction timer and exits the idle page if shown."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_wakeup

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_wakeup(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "0")
    mock_nav.reset_activity.assert_called_once_with()
    mock_nav.exit_idle_to_prev_or_home.assert_called_once()


@pytest.mark.asyncio
async def test_idle(mock_hass, mock_nav, mock_esphome_ctrl):
    """idle delegates to nav.open_idle_panel(True)."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_idle

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_idle(mock_hass, call)

    mock_nav.open_idle_panel.assert_called_once_with(True)
    mock_nav.reset_activity.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_passes_all_fields_to_controller(
    mock_hass, mock_nav, mock_esphome_ctrl
):
    """The service hands every generic field to the controller."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    notif_ctrl = MagicMock()
    app.controller["notification"] = notif_ctrl
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_send_notification

    call = MagicMock()
    call.data = {
        "title": "Alarm",
        "message": "Smoke detected",
        "icon": "mdi:fire",
        "persistent": True,
        "icon_color": "#4aa5ee",
        "sound": "alert",
        "force_show": True,
    }

    await _handle_send_notification(mock_hass, call)

    notif_ctrl.add_notification.assert_called_once_with(
        title="Alarm",
        message="Smoke detected",
        icon="mdi:fire",
        persistent=True,
        force_show=True,
        icon_color="#4aa5ee",
        sound="alert",
        text_size="auto",
        timeout=None,
    )
    mock_esphome_ctrl.esphome.publish.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_text_size_passthrough(mock_hass, mock_nav, mock_esphome_ctrl):
    """The service forwards an explicit text_size to the controller (issue #48)."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    notif_ctrl = MagicMock()
    app.controller["notification"] = notif_ctrl
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_send_notification

    call = MagicMock()
    call.data = {"title": "Door", "message": "open", "text_size": 2}

    await _handle_send_notification(mock_hass, call)

    notif_ctrl.add_notification.assert_called_once_with(
        title="Door",
        message="open",
        icon="",
        persistent=False,
        force_show=False,
        icon_color=None,
        sound="notification",
        text_size=2,
        timeout=None,
    )


@pytest.mark.asyncio
async def test_send_notification_timeout_passthrough(mock_hass, mock_nav, mock_esphome_ctrl):
    """The service forwards an explicit timeout; the controller auto-dismisses."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    notif_ctrl = MagicMock()
    app.controller["notification"] = notif_ctrl
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_send_notification

    call = MagicMock()
    call.data = {"title": "Door", "message": "open", "timeout": 10}

    await _handle_send_notification(mock_hass, call)

    notif_ctrl.add_notification.assert_called_once_with(
        title="Door",
        message="open",
        icon="",
        persistent=False,
        force_show=False,
        icon_color=None,
        sound="notification",
        text_size="auto",
        timeout=10,
    )


def test_send_notification_schema_accepts_a_timeout():
    """services.yaml documents the timeout field; the schema must accept it."""
    data = SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "timeout": 10})
    assert data["timeout"] == 10


@pytest.mark.parametrize("bad", [-1, 3601, "soon"])
def test_send_notification_schema_rejects_invalid_timeouts(bad):
    with pytest.raises(vol.Invalid):
        SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "timeout": bad})


def test_send_notification_schema_accepts_the_maximum_timeout():
    data = SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "timeout": 3600})
    assert data["timeout"] == 3600


@pytest.mark.parametrize(
    ("icon_color", "expected"),
    [
        ("", ""),
        ("#4aa5ee", "#4aa5ee"),
        ("65535", 65535),
        (65535, 65535),
        ([74, 165, 238], [74, 165, 238]),
    ],
)
def test_send_notification_schema_accepts_icon_colors(icon_color, expected):
    data = SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "icon_color": icon_color})
    assert data["icon_color"] == expected


@pytest.mark.parametrize("bad", [-1, 65536, "#12345", [1, 2], "red-ish"])
def test_send_notification_schema_rejects_invalid_icon_colors(bad):
    with pytest.raises(vol.Invalid):
        SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "icon_color": bad})


@pytest.mark.parametrize("sound", [*SOUND_NAMES, "none"])
def test_send_notification_schema_accepts_every_sound(sound):
    data = SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "sound": sound})
    assert data["sound"] == sound


def test_send_notification_schema_rejects_an_unknown_sound():
    with pytest.raises(vol.Invalid):
        SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "sound": "airhorn"})


def test_send_notification_schema_no_longer_takes_a_type():
    with pytest.raises(vol.Invalid):
        SERVICE_SEND_NOTIFICATION_SCHEMA({"title": "t", "type": "critical"})


def test_send_notification_service_metadata_and_schema_agree():
    """services.yaml and SERVICE_SEND_NOTIFICATION_SCHEMA must not drift.

    Every field the service documents must be accepted by the schema and vice
    versa, so the UI the user sees always maps to a valid service call.
    """
    from pathlib import Path

    import yaml

    services = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "nspanel_haui"
        / "services.yaml"
    )
    metadata = yaml.safe_load(services.read_text())["send_notification"]
    yaml_fields = set(metadata["fields"])
    schema_fields = {marker.schema for marker in SERVICE_SEND_NOTIFICATION_SCHEMA.schema}
    assert yaml_fields == schema_fields
    assert set(metadata["fields"]["sound"]["selector"]["select"]["options"]) == {
        *SOUND_NAMES,
        "none",
    }


@pytest.mark.asyncio
async def test_reset_last_interaction(mock_hass, mock_nav, mock_esphome_ctrl):
    """reset_last_interaction publishes the offset as a string."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_reset_last_interaction

    call = MagicMock()
    call.data = {"offset": 5, "device_id": "dev_1"}

    await _handle_reset_last_interaction(mock_hass, call)

    mock_esphome_ctrl.esphome.publish.assert_called_once_with("reset_last_interaction", "5")


@pytest.mark.asyncio
async def test_service_action_is_queued_on_the_app_worker(mock_hass, mock_nav, mock_esphome_ctrl):
    """Actions run on the app's worker, queued without waiting for it."""
    app = _make_app(mock_nav, mock_esphome_ctrl)
    queued = []
    app.dispatch = MagicMock(side_effect=lambda fn, *args: queued.append(fn))
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    from custom_components.nspanel_haui.services import _handle_close_panel

    call = MagicMock()
    call.data = {"device_id": "dev_1"}

    await _handle_close_panel(mock_hass, call)

    mock_hass.async_add_executor_job.assert_not_called()
    mock_nav.close_panel.assert_not_called()
    (action,) = queued
    action()
    mock_nav.close_panel.assert_called_once()


# show_image / clear_image


def _png_bytes() -> bytes:
    """A tiny real PNG, so the rasteriser runs for real in these tests."""
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (8, 8), (255, 255, 255))
    ImageDraw.Draw(image).rectangle((0, 0, 3, 7), fill=(200, 30, 30))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _make_drawable_app(mock_nav, mock_esphome_ctrl, **kwargs):
    """An app whose panel can draw: known display, new firmware, no install running."""
    from custom_components.nspanel_haui.haui.version import DRAW_RUNS_FIRMWARE_VERSION

    app = _make_app(mock_nav, mock_esphome_ctrl, **kwargs)
    app.device = MagicMock()
    app.device.is_portrait = False
    app.device.device_info = {"yaml_version": DRAW_RUNS_FIRMWARE_VERSION}
    app.theme = MagicMock()
    app.theme.get = MagicMock(return_value=0x0000)
    mock_nav.page = MagicMock()
    mock_nav.page.get_color = MagicMock(return_value=0x1234)
    return app


def _image_call(**overrides) -> Any:
    """A show_image call with the schema's defaults filled in."""
    call = MagicMock()
    call.service = "show_image"
    call.data = {
        "device": None,
        "url": "https://example.test/logo.png",
        "x": 10,
        "y": 10,
        "w": 40,
        "h": 40,
        "progressive": False,
        "quality": 300,
    }
    call.data.update(overrides)
    return call


@pytest.fixture
def png_fetch(monkeypatch):
    """Serve the test PNG instead of downloading it."""
    from custom_components.nspanel_haui import services

    async def _fetch(_hass, _url):
        return _png_bytes()

    monkeypatch.setattr(services, "_fetch_image", _fetch)
    return _fetch


def test_both_image_services_are_registered(mock_hass):
    async_register_services(mock_hass)

    names = {call.args[1] for call in mock_hass.services.async_register.call_args_list}
    assert {"show_image", "clear_image"} <= names


def test_the_image_schema_takes_its_documented_defaults():
    from custom_components.nspanel_haui.services import SERVICE_SHOW_IMAGE_SCHEMA

    result = SERVICE_SHOW_IMAGE_SCHEMA(
        {"url": "https://example.test/a.png", "x": 0, "y": 0, "w": 10, "h": 10}
    )

    # ``cv`` is a stub here, so only the probatio-validated entries are asserted.
    assert result["quality"] == 300
    assert result["device"] is None


@pytest.mark.parametrize("quality", [MIN_RUN_BUDGET - 1, MAX_RUN_BUDGET + 1])
def test_the_image_schema_refuses_a_quality_outside_its_range(quality):
    from custom_components.nspanel_haui.services import SERVICE_SHOW_IMAGE_SCHEMA

    with pytest.raises(vol.Invalid):
        SERVICE_SHOW_IMAGE_SCHEMA(
            {
                "url": "https://example.test/a.png",
                "x": 0,
                "y": 0,
                "w": 10,
                "h": 10,
                "quality": quality,
            }
        )


@pytest.mark.asyncio
async def test_show_image_refuses_a_rect_off_the_display(
    mock_hass, mock_nav, mock_esphome_ctrl, monkeypatch
):
    """A rectangle the display cannot show fails before anything is downloaded."""
    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}
    from custom_components.nspanel_haui import services

    fetched: list[str] = []

    async def _fetch(_hass, url):
        fetched.append(url)
        return _png_bytes()

    monkeypatch.setattr(services, "_fetch_image", _fetch)

    with pytest.raises(_ServiceValidationError, match="does not fit"):
        await services._handle_show_image(mock_hass, _image_call(x=470, w=40))

    assert fetched == []
    mock_esphome_ctrl.draw_runs.assert_not_called()


@pytest.mark.asyncio
async def test_show_image_refuses_old_firmware_and_names_the_upgrade(
    mock_hass, mock_nav, mock_esphome_ctrl, png_fetch
):
    """An unknown action only logs a warning, so the service must refuse first."""
    from custom_components.nspanel_haui.haui.version import DRAW_RUNS_FIRMWARE_VERSION
    from custom_components.nspanel_haui.services import _handle_show_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    app.device.device_info = {"yaml_version": "0.5.8"}
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    with pytest.raises(_ServiceValidationError, match=DRAW_RUNS_FIRMWARE_VERSION):
        await _handle_show_image(mock_hass, _image_call())

    mock_esphome_ctrl.draw_runs.assert_not_called()


@pytest.mark.asyncio
async def test_show_image_refuses_while_a_tft_install_runs(
    mock_hass, mock_nav, mock_esphome_ctrl, png_fetch
):
    from custom_components.nspanel_haui.services import _handle_show_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    update = MagicMock()
    update.tft_install_active = True
    app.controller = {**app.controller, "update": update}
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    with pytest.raises(_ServiceValidationError, match="installing a TFT"):
        await _handle_show_image(mock_hass, _image_call())

    mock_esphome_ctrl.draw_runs.assert_not_called()


@pytest.mark.asyncio
async def test_show_image_surfaces_a_fetch_failure(
    mock_hass, mock_nav, mock_esphome_ctrl, monkeypatch
):
    from custom_components.nspanel_haui import services

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    async def _fetch(_hass, url):
        raise _HomeAssistantError(f"{url} answered HTTP 404")

    monkeypatch.setattr(services, "_fetch_image", _fetch)

    with pytest.raises(_HomeAssistantError, match="404"):
        await services._handle_show_image(mock_hass, _image_call())

    mock_esphome_ctrl.draw_runs.assert_not_called()


@pytest.mark.asyncio
async def test_show_image_surfaces_an_undecodable_image(
    mock_hass, mock_nav, mock_esphome_ctrl, monkeypatch
):
    from custom_components.nspanel_haui import services

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    async def _fetch(_hass, _url):
        return b"not an image"

    monkeypatch.setattr(services, "_fetch_image", _fetch)

    with pytest.raises(_ServiceValidationError, match="could not be decoded"):
        await services._handle_show_image(mock_hass, _image_call())

    mock_esphome_ctrl.draw_runs.assert_not_called()


@pytest.mark.asyncio
async def test_show_image_paints_the_rectangle_black_before_the_image(
    mock_hass, mock_nav, mock_esphome_ctrl, png_fetch
):
    """The area is cleared first, so nothing that was on the page shows through.

    A pass skips the cells that already match the colour it draws on, so without
    this first fill an older image - or a widget the page put there - would stay
    visible wherever the new picture has that colour.
    """
    from custom_components.nspanel_haui.services import _handle_show_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    await _handle_show_image(mock_hass, _image_call())

    (runs,), _kwargs = mock_esphome_ctrl.draw_runs.call_args
    assert runs[0] == "fill 10,10,40,40,0", "a black rectangle over the whole area"


@pytest.mark.asyncio
async def test_show_image_draws_the_program_on_the_panel(
    mock_hass, mock_nav, mock_esphome_ctrl, png_fetch
):
    """The pixels reach the display as one program of fill instructions."""
    from custom_components.nspanel_haui.services import _handle_show_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    await _handle_show_image(mock_hass, _image_call())

    (runs,), _kwargs = mock_esphome_ctrl.draw_runs.call_args
    assert runs and all(run.startswith("fill ") for run in runs)
    assert len(runs) <= 300
    mock_hass.async_add_executor_job.assert_awaited()


@pytest.mark.asyncio
async def test_show_image_queues_the_coarse_pass_before_the_full_one(
    mock_hass, mock_nav, mock_esphome_ctrl, png_fetch
):
    """Progressive painting in one queue, so the coarse pass is not cut short."""
    from custom_components.nspanel_haui.haui.utils.image_program import PROGRESSIVE_RUNS
    from custom_components.nspanel_haui.services import _handle_show_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    await _handle_show_image(mock_hass, _image_call(progressive=True))

    # One draw, the coarse runs first: a second call would restart the panel's
    # program and cut the coarse pass short instead of letting it finish.
    from custom_components.nspanel_haui.haui.utils.image_program import (
        BACKDROP,
        Rect,
        image_plan,
    )

    (coarse, full), _cell = image_plan(
        _png_bytes(),
        Rect(10, 10, 40, 40),
        background=BACKDROP,
        budget=300,
        progressive=True,
    )
    (sent,), _kwargs = mock_esphome_ctrl.draw_runs.call_args
    assert 0 < len(coarse) <= PROGRESSIVE_RUNS
    assert sent == [*coarse, *full]


# A file from ``<config>/www`` instead of a URL (the ``path`` field).


def _file_call(path: str = "logo.png", **overrides) -> Any:
    """A show_image call that names a file with the schema's defaults."""
    call = MagicMock()
    call.service = "show_image"
    call.data = {
        "device": None,
        "path": path,
        "x": 10,
        "y": 10,
        "w": 40,
        "h": 40,
        "progressive": False,
        "quality": 300,
        **overrides,
    }
    return call


@pytest.fixture
def config_www(mock_hass, tmp_path):
    """A configuration directory whose ``www`` holds the test PNG as logo.png."""
    www = tmp_path / "www"
    www.mkdir()
    (www / "logo.png").write_bytes(_png_bytes())
    mock_hass.config.path = MagicMock(return_value=str(www))
    return www


@pytest.mark.asyncio
async def test_show_image_draws_a_file_without_fetching_anything(
    mock_hass, mock_nav, mock_esphome_ctrl, config_www, monkeypatch
):
    """``path`` reads the file: a panel needs no web server to draw an image."""
    from custom_components.nspanel_haui import services

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}

    async def _unreachable(_hass, url):
        raise AssertionError(f"a path must not download {url}")

    monkeypatch.setattr(services, "_fetch_image", _unreachable)

    await services._handle_show_image(mock_hass, _file_call())

    (runs,), _kwargs = mock_esphome_ctrl.draw_runs.call_args
    assert runs and all(run.startswith("fill ") for run in runs)


@pytest.mark.parametrize("path", ["logo.png", "www/logo.png"])
@pytest.mark.asyncio
async def test_a_path_reads_from_the_www_folder_with_or_without_its_name(
    mock_hass, config_www, path
):
    """Both spellings the documentation uses name the same file."""
    from custom_components.nspanel_haui.services import _read_image

    assert await _read_image(mock_hass, _file_call(path)) == _png_bytes()


@pytest.mark.parametrize(
    ("path", "reason"),
    [("../secrets.yaml", "outside"), ("/config/www/logo.png", "absolute")],
)
@pytest.mark.asyncio
async def test_a_path_outside_the_www_folder_is_refused(mock_hass, config_www, path, reason):
    """The configuration directory is not a readable image store."""
    from custom_components.nspanel_haui.services import _read_image

    with pytest.raises(_ServiceValidationError, match=reason):
        await _read_image(mock_hass, _file_call(path))


@pytest.mark.asyncio
async def test_a_missing_file_names_the_folder_it_looked_in(mock_hass, config_www):
    from custom_components.nspanel_haui.services import _read_image

    with pytest.raises(_ServiceValidationError, match=f"{config_www}"):
        await _read_image(mock_hass, _file_call("missing.png"))


@pytest.mark.asyncio
async def test_a_file_over_the_image_cap_is_refused(mock_hass, config_www):
    from custom_components.nspanel_haui.services import IMAGE_MAX_BYTES, _read_image

    (config_www / "big.png").write_bytes(b"\0" * (IMAGE_MAX_BYTES + 1))

    with pytest.raises(_HomeAssistantError, match="larger than"):
        await _read_image(mock_hass, _file_call("big.png"))


def test_the_image_schema_refuses_both_sources_at_once():
    from custom_components.nspanel_haui.services import SERVICE_SHOW_IMAGE_SCHEMA

    with pytest.raises(vol.Invalid):
        SERVICE_SHOW_IMAGE_SCHEMA(
            {
                "url": "https://example.test/a.png",
                "path": "logo.png",
                "x": 0,
                "y": 0,
                "w": 10,
                "h": 10,
            }
        )


def test_the_image_schema_refuses_a_call_that_names_no_image():
    from custom_components.nspanel_haui.services import SERVICE_SHOW_IMAGE_SCHEMA

    with pytest.raises(vol.Invalid, match="url or path"):
        SERVICE_SHOW_IMAGE_SCHEMA({"x": 0, "y": 0, "w": 10, "h": 10})


def test_show_image_service_metadata_and_schema_agree():
    """services.yaml and SERVICE_SHOW_IMAGE_SCHEMA must not drift.

    Both sources are documented, so the action's form offers the file a user has
    without a URL to serve it from.
    """
    from pathlib import Path

    import yaml

    from custom_components.nspanel_haui.services import SERVICE_SHOW_IMAGE_SCHEMA

    services = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "nspanel_haui"
        / "services.yaml"
    )
    metadata = yaml.safe_load(services.read_text())["show_image"]
    schema = SERVICE_SHOW_IMAGE_SCHEMA.validators[0]
    assert set(metadata["fields"]) == {marker.schema for marker in schema.schema}
    # The range the form offers is the range the schema enforces.
    selector = metadata["fields"]["quality"]["selector"]["number"]
    assert (selector["min"], selector["max"]) == (MIN_RUN_BUDGET, MAX_RUN_BUDGET)


@pytest.mark.asyncio
async def test_clear_image_paints_the_page_background(mock_hass, mock_nav, mock_esphome_ctrl):
    """One fill in the page's own colour: no image, no program."""
    from custom_components.nspanel_haui.services import _handle_clear_image

    app = _make_drawable_app(mock_nav, mock_esphome_ctrl)
    mock_hass.data[DOMAIN] = {"entry_1": {"dev": app}}
    call = MagicMock()
    call.service = "clear_image"
    call.data = {"device": None, "x": 10, "y": 20, "w": 30, "h": 40}

    await _handle_clear_image(mock_hass, call)

    mock_esphome_ctrl.draw_runs.assert_called_once_with(["fill 10,20,30,40,4660"])

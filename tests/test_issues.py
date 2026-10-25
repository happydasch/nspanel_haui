"""Tests for the issue-registry (Repairs) integration.

Covers issue creation/deletion wired into ``async_setup_entry`` and the
fix flow provided by ``repairs.py``.  Runs without Home Assistant using the
same sys.modules stubbing pattern as the other test files.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Install stubs before importing the modules under test.
# ---------------------------------------------------------------------------


class _IssueSeverity:
    """Minimal stand-in for issue_registry.IssueSeverity."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"


def _make_stubs() -> None:
    issue_registry_mod = types.ModuleType("homeassistant.helpers.issue_registry")
    issue_registry_mod.IssueSeverity = _IssueSeverity
    issue_registry_mod.async_create_issue = MagicMock()
    issue_registry_mod.async_delete_issue = MagicMock()

    storage_helpers = types.ModuleType("homeassistant.helpers.storage")

    class _Store:
        """Minimal stand-in for homeassistant.helpers.storage.Store."""

        def __init__(self, hass: Any, version: int, key: str) -> None:
            self._hass = hass
            self._version = version
            self._key = key

        async def async_load(self) -> Any:
            return None

        async def async_save(self, data: Any) -> None:
            pass

    storage_helpers.Store = _Store

    repairs_comp = types.ModuleType("homeassistant.components.repairs")

    class StubRepairsFlow:
        """Minimal stand-in for homeassistant.components.repairs.RepairsFlow."""

        def __init__(self) -> None:
            self.hass: Any = None
            self.data: dict[str, str | int | float | None] | None = None
            self.context: dict[str, Any] = {}

        def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "create_entry", **kwargs}

    repairs_comp.RepairsFlow = StubRepairsFlow
    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict

    stubs = {
        "homeassistant.helpers.issue_registry": issue_registry_mod,
        "homeassistant.helpers.storage": storage_helpers,
        "homeassistant.components.repairs": repairs_comp,
        "homeassistant.data_entry_flow": data_entry_flow,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_make_stubs()

import nspanel_haui.storage as storage_mod  # noqa: E402
from nspanel_haui import (  # noqa: E402
    _create_device_start_failed_issue,
    _create_hub_idle_issue,
    _delete_device_start_failed_issue,
    _device_issue_id,
    async_setup_entry,
)
from nspanel_haui.const import DOMAIN  # noqa: E402
from nspanel_haui.repairs import (  # noqa: E402
    DEVICE_START_FAILED,
    DeviceStartFailedFixFlow,
    async_create_fix_flow,
)


def _hass_stub() -> MagicMock:
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    def _discard_task(coro: Any) -> None:
        coro.close()

    hass.async_create_task = _discard_task
    return hass


def _entry_stub(entry_id: str = "hub1") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.title = "NSPanel HAUI Hub"
    entry.data = {"name": "NSPanel HAUI Hub", "devices": []}
    return entry


def _storage_patches(enabled: list[str]) -> list[Any]:
    """Return context-managers for the storage imports used in async_setup_entry."""
    storage_cls = MagicMock()
    storage_cls.return_value.load = AsyncMock(return_value={"version": 1, "devices": {}})
    return [
        patch.object(storage_mod, "PanelStorage", storage_cls),
        patch.object(
            storage_mod,
            "enabled_device_names",
            MagicMock(return_value=enabled),
        ),
    ]


def _run_setup_with_storage(hass: Any, entry: Any, enabled: list[str]) -> None:
    with contextlib.ExitStack() as stack:
        for cm in _storage_patches(enabled):
            stack.enter_context(cm)
        asyncio.run(async_setup_entry(hass, entry))


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


def test_device_issue_id_is_slugified() -> None:
    assert _device_issue_id("Kitchen Panel") == f"{DEVICE_START_FAILED}_kitchen_panel"


def test_create_device_failed_issue_kwargs() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass, _entry = _hass_stub(), _entry_stub()
    ir.async_create_issue.reset_mock()

    _create_device_start_failed_issue(hass, "Kitchen", RuntimeError("boom"))

    kwargs = ir.async_create_issue.call_args.kwargs
    assert ir.async_create_issue.call_args.args == (hass, DOMAIN, "device_start_failed_kitchen")
    assert kwargs["translation_key"] == "device_start_failed"
    assert kwargs["severity"] == "error"
    assert kwargs["is_fixable"] is True
    assert kwargs["is_persistent"] is False
    assert "config_entry_id" not in kwargs
    assert kwargs["translation_placeholders"] == {
        "device": "Kitchen",
        "error": "boom",
    }


def test_delete_device_failed_issue() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass = _hass_stub()
    ir.async_delete_issue.reset_mock()

    _delete_device_start_failed_issue(hass, "Kitchen")

    assert ir.async_delete_issue.call_args.args == (hass, DOMAIN, "device_start_failed_kitchen")


def test_hub_idle_issue_kwargs() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass, entry = _hass_stub(), _entry_stub()
    ir.async_create_issue.reset_mock()

    _create_hub_idle_issue(hass, entry)

    kwargs = ir.async_create_issue.call_args.kwargs
    assert ir.async_create_issue.call_args.args == (hass, DOMAIN, "hub_idle")
    assert kwargs["translation_key"] == "hub_idle"
    assert kwargs["severity"] == "warning"
    assert kwargs["is_fixable"] is False
    assert kwargs["translation_placeholders"] == {"hub": "NSPanel HAUI Hub"}


# ---------------------------------------------------------------------------
# async_setup_entry wiring tests
# ---------------------------------------------------------------------------


def test_setup_failure_creates_issue() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass, entry = _hass_stub(), _entry_stub()
    ir.async_create_issue.reset_mock()
    ir.async_delete_issue.reset_mock()

    async def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("startup exploded")

    with patch("nspanel_haui._create_app", new=_boom):
        _run_setup_with_storage(hass, entry, ["Kitchen"])

    created = [
        c
            for c in ir.async_create_issue.call_args_list
            if c.args[2] == "device_start_failed_kitchen"
    ]
    assert len(created) == 1
    assert created[0].kwargs["translation_placeholders"]["error"] == "startup exploded"
    assert not ir.async_delete_issue.called


def test_setup_success_deletes_issue() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass, entry = _hass_stub(), _entry_stub()
    ir.async_delete_issue.reset_mock()

    async def _ok(*_args: Any, **_kwargs: Any) -> Any:
        app = MagicMock()
        app._runtime_device_name = "Kitchen"
        return app

    with patch("nspanel_haui._create_app", new=_ok):
        _run_setup_with_storage(hass, entry, ["Kitchen"])

    deleted = [
        c
            for c in ir.async_delete_issue.call_args_list
            if c.args[2] == "device_start_failed_kitchen"
    ]
    assert len(deleted) == 1


def test_setup_without_devices_creates_hub_idle_issue() -> None:
    from homeassistant.helpers import issue_registry as ir

    hass, entry = _hass_stub(), _entry_stub()
    ir.async_create_issue.reset_mock()
    ir.async_delete_issue.reset_mock()

    with patch("nspanel_haui._create_app", new=AsyncMock()):
        _run_setup_with_storage(hass, entry, [])

    created = [c for c in ir.async_create_issue.call_args_list if c.args[2] == "hub_idle"]
    assert len(created) == 1


# ---------------------------------------------------------------------------
# Repairs fix flow tests
# ---------------------------------------------------------------------------


def test_fix_flow_routing() -> None:
    hass = _hass_stub()
    flow = asyncio.run(async_create_fix_flow(hass, "device_start_failed_kitchen", None))
    assert isinstance(flow, DeviceStartFailedFixFlow)
    assert asyncio.run(async_create_fix_flow(hass, "other_issue", None)) is None


def test_fix_flow_reloads_hub_on_confirm() -> None:
    hass = _hass_stub()
    hub_entry = _entry_stub("hub1")
    hass.config_entries.async_entries.return_value = [hub_entry]

    flow = DeviceStartFailedFixFlow()
    flow.hass = hass
    flow.data = {"device": "Kitchen"}

    init_result = asyncio.run(flow.async_step_init(None))
    assert init_result["type"] == "form"

    confirm_result = asyncio.run(flow.async_step_reload({"confirm": True}))
    assert confirm_result["type"] == "create_entry"
    assert hass.config_entries.async_schedule_reload.call_args.args == ("hub1",)


def test_fix_flow_handles_missing_hub_silently() -> None:
    hass = _hass_stub()
    hass.config_entries.async_entries.return_value = []

    flow = DeviceStartFailedFixFlow()
    flow.hass = hass
    flow.data = {"device": "Kitchen"}

    result = asyncio.run(flow.async_step_reload({"confirm": True}))
    assert result["type"] == "create_entry"
    assert not hass.config_entries.async_schedule_reload.called

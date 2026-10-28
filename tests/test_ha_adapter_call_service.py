"""Tests for strict service dispatch used by firmware auto-install."""

from __future__ import annotations

import asyncio
import types

import nspanel_haui.ha_adapter as adapter_module
import pytest
from nspanel_haui.ha_adapter import HAAdapter


class _Services:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def async_call(self, domain, service, **kwargs):
        self.calls.append((domain, service, kwargs))
        if self.error:
            raise self.error


def _adapter(monkeypatch, services):
    adapter = HAAdapter.__new__(HAAdapter)
    adapter.hass = types.SimpleNamespace(services=services)
    adapter._loop = object()
    monkeypatch.setattr(
        adapter_module,
        "_run_on_loop",
        lambda loop, coro, timeout=10: asyncio.run(coro),
    )
    return adapter


def test_strict_service_dispatch_confirms_call_and_promotes_entity_target(monkeypatch):
    services = _Services()
    adapter = _adapter(monkeypatch, services)

    assert adapter.call_service(
        "update.install", entity_id="update.haui_firmware", raise_on_error=True
    ) is True
    assert services.calls == [
        (
            "update",
            "install",
            {
                "service_data": {},
                "target": {"entity_id": "update.haui_firmware"},
                "blocking": True,
                "return_response": False,
            },
        )
    ]


def test_strict_service_dispatch_propagates_errors(monkeypatch):
    adapter = _adapter(monkeypatch, _Services(RuntimeError("service unavailable")))

    with pytest.raises(RuntimeError, match="service unavailable"):
        adapter.call_service(
            "update.install", entity_id="update.haui_firmware", raise_on_error=True
        )


def test_normal_service_dispatch_keeps_best_effort_behavior(monkeypatch):
    adapter = _adapter(monkeypatch, _Services(RuntimeError("service unavailable")))

    assert adapter.call_service("light.turn_on", entity_id="light.kitchen") is None


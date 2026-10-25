"""ItemProxy.set_state must change an entity's value through its service.

Writing to the state machine (``hass.states.async_set``) only overwrites what
HA displays: the entity's real value is untouched and its attributes (min,
max, step, ...) are dropped.  ``number`` and ``input_number`` both expose a
``set_value`` service for this.
"""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest
from nspanel_haui.ha_adapter import ItemProxy


@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    loop.close()


def _hass():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


def _drain(loop):
    for _ in range(3):
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop).result(timeout=5)


@pytest.mark.parametrize("domain", ["number", "input_number"])
def test_set_state_calls_set_value_service(loop, domain):
    hass = _hass()
    proxy = ItemProxy(hass, loop, f"{domain}.target_temp", proxy=None)

    proxy.set_state(state=21.5)
    _drain(loop)

    hass.services.async_call.assert_awaited_once_with(
        domain,
        "set_value",
        service_data={"value": 21.5},
        target={"entity_id": f"{domain}.target_temp"},
        blocking=True,
    )
    hass.states.async_set.assert_not_called()


def test_set_state_rejects_domains_without_set_value(loop):
    hass = _hass()
    proxy = ItemProxy(hass, loop, "sensor.outside_temp", proxy=None)

    with pytest.raises(ValueError, match="sensor.outside_temp"):
        proxy.set_state(state=3)
    _drain(loop)

    hass.states.async_set.assert_not_called()
    hass.services.async_call.assert_not_called()


def test_call_service_without_a_target_still_calls_ha(loop):
    """Services like script.<name> or notify.<name> take no entity target."""
    from nspanel_haui.ha_adapter import HAAdapter

    adapter = HAAdapter.__new__(HAAdapter)
    adapter.hass = _hass()
    adapter._loop = loop

    adapter.call_service("script/morning", service_data={"brightness": 50})

    adapter.hass.services.async_call.assert_awaited_once_with(
        "script",
        "morning",
        service_data={"brightness": 50},
        target=None,
        blocking=True,
        return_response=False,
    )

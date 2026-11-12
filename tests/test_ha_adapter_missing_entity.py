"""A missing entity is reported once, not on every render that reads it.

Pages read their entities on every render. The warning used to be written each
time, so one missing entity filled the 100-line status log (and Home
Assistant's log) and pushed every other message out of the editor's Logs.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_entity import HAUIEntity
from custom_components.nspanel_haui.hub.adapter import HAAdapter


@pytest.fixture
def world():
    states: dict[str, object] = {}
    hass = MagicMock()
    hass.states.get = states.get
    adapter = HAAdapter(hass, "hub")
    yield adapter, states
    adapter._worker.shutdown(wait=False)
    adapter._io.shutdown(wait=False)


def _warnings(adapter):
    return [line for line in adapter.get_status_logs() if "not available" in line]


def test_a_missing_entity_is_warned_about_once(world):
    adapter, _states = world
    cover = HAUIEntity(adapter, "cover.hall")

    for _ in range(3):
        assert cover.get_entity_state() is None
    cover.get_entity_attr("current_position")
    cover.call_entity_service("open_cover")
    # A second item for the same entity (the next panel, a card render) stays quiet too.
    HAUIEntity(adapter, "cover.hall").get_entity_state()

    assert len(_warnings(adapter)) == 1
    assert "Entity 'cover.hall' not available for state" in _warnings(adapter)[0]


def test_each_missing_entity_gets_its_own_warning(world):
    adapter, _states = world
    HAUIEntity(adapter, "cover.hall").get_entity_state()
    HAUIEntity(adapter, "light.desk").get_entity_attr("brightness")

    assert len(_warnings(adapter)) == 2
    assert "Entity 'light.desk' not available for attr 'brightness'" in _warnings(adapter)[1]


def test_an_entity_that_returns_and_goes_again_is_warned_about_again(world):
    adapter, states = world
    cover = HAUIEntity(adapter, "cover.hall")
    cover.get_entity_state()

    states["cover.hall"] = object()
    assert cover.has_entity()
    del states["cover.hall"]
    cover.get_entity_state()

    assert len(_warnings(adapter)) == 2

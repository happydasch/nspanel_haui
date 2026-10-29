"""Tests for HAAdapter.find_entity_id (entity-registry based id resolution).

The registry lookup is what keeps the ESPHome config sync working when Home
Assistant uses area/device-prefixed entity ids or the device was renamed, so
``number.{node}_{entity}``-style guesses no longer match new entities.
"""

from __future__ import annotations

from nspanel_haui.ha_adapter import HAAdapter


class _Entry:
    def __init__(self, domain, platform, original_name, device_id, disabled_by=None):
        self.domain = domain
        self.platform = platform
        self.original_name = original_name
        self.device_id = device_id
        self.disabled_by = disabled_by


class _Registry:
    def __init__(self, entities):
        self.entities = entities


class _Hass:
    def __init__(self, entities):
        self.helpers = type(
            "H",
            (),
            {
                "entity_registry": type(
                    "ER",
                    (),
                    {"async_get": staticmethod(lambda hass: _Registry(entities))},
                )()
            },
        )()


def _adapter(entities, device_id="dev-1"):
    adapter = HAAdapter.__new__(HAAdapter)
    adapter.hass = _Hass(entities)
    adapter._ha_device_id = device_id
    return adapter


def test_finds_the_entity_on_the_linked_device_by_original_name():
    entities = {
        "number.goscinny_nspanel_goscinny_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-2"
        ),
        "number.nspanel_guestroom_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-1"
        ),
    }
    assert _adapter(entities).find_entity_id("number", "Display Model") == (
        "number.nspanel_guestroom_display_model"
    )


def test_prefers_the_linked_device_over_other_panels():
    """Area-prefixed id on this device wins over others with the same name."""
    entities = {
        "number.salon_nspanel_salon_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-8"
        ),
        "number.goscinny_nspanel_goscinny_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-1"
        ),
    }
    assert _adapter(entities).find_entity_id("number", "Display Model") == (
        "number.goscinny_nspanel_goscinny_display_model"
    )


def test_returns_none_when_the_entity_is_missing():
    assert _adapter({}).find_entity_id("number", "Display Model") is None


def test_ignores_non_matching_names_and_domains():
    entities = {
        "switch.nspanel_guestroom_use_auto_dimming": _Entry(
            "switch", "esphome", "Use Auto-Dimming", "dev-1"
        ),
        "number.nspanel_guestroom_timeout_display_off": _Entry(
            "number", "esphome", "Timeout Display-Off", "dev-1"
        ),
    }
    assert _adapter(entities).find_entity_id("number", "Display Model") is None


def test_falls_back_to_a_sole_candidate_without_a_device_link():
    entities = {
        "number.salon_nspanel_salon_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-8"
        )
    }
    adapter = _adapter(entities, device_id=None)
    assert adapter.find_entity_id("number", "Display Model") == (
        "number.salon_nspanel_salon_display_model"
    )


def test_returns_none_with_multiple_candidates_and_no_device_link():
    """Without a device link, several panels' numbers are indistinguishable."""
    entities = {
        "number.salon_nspanel_salon_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-8"
        ),
        "number.kasia_nspanel_kasia_display_model": _Entry(
            "number", "esphome", "Display Model", "dev-9"
        ),
    }
    adapter = _adapter(entities, device_id=None)
    assert adapter.find_entity_id("number", "Display Model") is None


def test_prefers_enabled_candidate_over_disabled_copy():
    """A renamed entity leaves a disabled copy; the live candidate wins."""
    entities = {
        "sensor.salon_nspanel_temperature": _Entry(
            "sensor", "esphome", "Temperature", "dev-1", disabled_by="integration"
        ),
        "sensor.nspanel_bedroom_temperature": _Entry(
            "sensor", "esphome", "Temperature", "dev-1"
        ),
    }
    assert _adapter(entities).find_entity_id("sensor", "Temperature") == (
        "sensor.nspanel_bedroom_temperature"
    )


def test_falls_back_to_a_sole_disabled_candidate():
    entities = {
        "sensor.nspanel_bedroom_temperature": _Entry(
            "sensor", "esphome", "Temperature", "dev-1", disabled_by="integration"
        )
    }
    assert _adapter(entities).find_entity_id("sensor", "Temperature") == (
        "sensor.nspanel_bedroom_temperature"
    )


def test_production_registry_path_without_hass_helpers(monkeypatch):
    """The HomeAssistant object has no ``.helpers`` attribute.

    Production goes through ``homeassistant.helpers.entity_registry`` directly;
    the helper-module path above exists only for tests.
    """
    import sys
    import types

    entities = {
        "sensor.area_nspanel_temperature": _Entry(
            "sensor", "esphome", "Temperature", "dev-1"
        )
    }
    er_module = types.ModuleType("homeassistant.helpers.entity_registry")
    er_module.async_get = lambda hass: _Registry(entities)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", er_module)

    class _HassWithoutHelpers:
        pass

    adapter = HAAdapter.__new__(HAAdapter)
    adapter.hass = _HassWithoutHelpers()
    adapter._ha_device_id = "dev-1"

    assert adapter.find_entity_id("sensor", "Temperature") == "sensor.area_nspanel_temperature"

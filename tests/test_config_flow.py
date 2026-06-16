"""Tests for NSPanel HAUI config flow helpers and options-to-config conversion."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out homeassistant before importing config_flow so tests run without HA.
# ---------------------------------------------------------------------------


def _make_ha_stubs() -> None:
    """Insert minimal homeassistant stubs into sys.modules."""

    class _ConfigFlow:
        """Stub for config_entries.ConfigFlow - accepts domain= keyword."""

        def __init_subclass__(cls, domain: str = "", **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)

        def __init__(self) -> None:
            self.context: dict[str, Any] = {}

        def async_show_form(self, **kwargs: Any) -> dict:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict:
            return {"type": "create_entry", **kwargs}

        def async_show_menu(self, **kwargs: Any) -> dict:
            return {"type": "menu", **kwargs}

        def async_abort(self, reason: str = "", **kwargs: Any) -> dict:
            return {"type": "abort", "reason": reason}

        async def async_set_unique_id(self, unique_id: str) -> None:
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self) -> None:
            pass

        def _async_current_entries(self) -> list:
            return []

        def _set_confirm_only(self) -> None:
            self._confirm_only = True

    ha = MagicMock()
    ha.config_entries.ConfigFlow = _ConfigFlow
    ha.config_entries.ConfigFlowResult = dict

    selector_mod = MagicMock()

    class _SelectOptionDict(dict):
        def __new__(cls, *, value: str, label: str):
            obj = super().__new__(cls)
            obj.update({"value": value, "label": label})
            return obj

    selector_mod.SelectOptionDict = _SelectOptionDict
    selector_mod.SelectSelectorMode = MagicMock()
    selector_mod.SelectSelectorMode.DROPDOWN = "dropdown"
    selector_mod.SelectSelectorMode.LIST = "list"
    selector_mod.SelectSelector = MagicMock(return_value=MagicMock())
    selector_mod.EntitySelector = MagicMock(return_value=MagicMock())
    selector_mod.EntitySelectorConfig = MagicMock(return_value=MagicMock())

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = ["homeassistant.helpers"]  # marks as package for sub-imports
    helpers.selector = selector_mod

    entity_registry_mod = MagicMock()
    entity_registry_mod.async_get = MagicMock()

    helpers.entity_registry = entity_registry_mod

    # Storage stub so that storage.py can import Store
    storage_mod = types.ModuleType("homeassistant.helpers.storage")

    class _Store:
        """Minimal Store stub for tests."""

        def __init__(self, hass: Any, version: int, key: str) -> None:
            self._hass = hass
            self._version = version
            self._key = key

        async def async_load(self) -> Any:
            return None

        async def async_save(self, data: Any) -> None:
            pass

    storage_mod.Store = _Store

    mqtt_mod = MagicMock()
    mqtt_mod.is_connected = MagicMock(return_value=True)
    mqtt_mod.async_subscribe = MagicMock()

    components_mod = MagicMock()
    components_mod.mqtt = mqtt_mod

    stubs = {
        "homeassistant": ha,
        "homeassistant.config_entries": ha.config_entries,
        "homeassistant.core": MagicMock(),
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.selector": selector_mod,
        "homeassistant.helpers.entity_registry": entity_registry_mod,
        "homeassistant.helpers.storage": storage_mod,
        "homeassistant.helpers.config_validation": MagicMock(),
        "homeassistant.const": MagicMock(),
        "homeassistant.components": components_mod,
        "homeassistant.components.mqtt": mqtt_mod,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_make_ha_stubs()

# Now safe to import
from nspanel_haui import _build_config_dict  # noqa: E402, I001
from nspanel_haui.config_flow import NSPanelHAUIConfigFlow  # noqa: E402
from nspanel_haui.esphome_helpers import (  # noqa: E402
    find_esphome_device as _find_esphome_device,
    normalize_device_name as _normalize_device_name,
)


@contextlib.contextmanager
def _patch_device_registry(entries: list):
    """Patch ``homeassistant.helpers.device_registry`` for ``is_haui_device``.

    The product code resolves the registry via
    ``from homeassistant.helpers import device_registry`` — a binding on the
    ``homeassistant.helpers`` package object. Replacing only the ``sys.modules``
    entry (the old approach) is silently shadowed once real Home Assistant has
    bound that attribute (which happens whenever another test imports the
    package, since ``_make_ha_stubs`` only stubs via ``setdefault`` when HA is
    absent). Patching the attribute itself works in both the stubbed and the
    real-HA world. ``entity_registry`` (strategy 5) is neutralised so it can
    never produce a false match.
    """
    import homeassistant.helpers as ha_helpers

    fake_dr = types.ModuleType("homeassistant.helpers.device_registry")
    fake_dr.async_get = MagicMock(return_value=MagicMock())
    fake_dr.async_entries_for_config_entry = MagicMock(return_value=list(entries))

    empty_ent_reg = MagicMock()
    empty_ent_reg.entities = {}
    fake_er = MagicMock()
    fake_er.async_get = MagicMock(return_value=empty_ent_reg)

    with (
        patch.object(ha_helpers, "device_registry", fake_dr, create=True),
        patch.object(ha_helpers, "entity_registry", fake_er, create=True),
        patch.dict(
            sys.modules,
            {
                "homeassistant.helpers.device_registry": fake_dr,
                "homeassistant.helpers.entity_registry": fake_er,
            },
        ),
    ):
        yield

# ---------------------------------------------------------------------------
# _build_config_dict  -  three-layer model (data, options, panels)
# ---------------------------------------------------------------------------


class TestOptionsToConfigDict:
    """Tests for _build_config_dict with the simplified three-layer model.

    Panels come from the third ``panels`` argument (PanelStorage), not options.
    """

    def test_name_always_set_from_argument(self):
        """Device name always comes from the ``data`` argument."""
        result = _build_config_dict({"name": "living_room"}, {})
        assert result["device"]["name"] == "living_room"

    def test_panels_from_third_argument(self):
        """Panels come from the ``panels`` (3rd) argument, not options."""
        panels = {
            "devices": {
                "test": {
                    "panels": [{"type": "grid", "key": "grid_0"}],
                }
            }
        }
        result = _build_config_dict(
            {"name": "test", "devices": [{"name": "test", "panels": []}]},
            {},
            panels,
        )
        assert result["panels"] == [{"type": "grid", "key": "grid_0"}]

    def test_does_not_mutate_default_config(self):
        """_build_config_dict uses copy.deepcopy, never mutates DEFAULT_CONFIG."""
        from nspanel_haui.haui.mapping.const import DEFAULT_CONFIG

        original = copy.deepcopy(DEFAULT_CONFIG)
        _build_config_dict({"name": "test", "devices": [{"name": "test"}]}, {})
        assert DEFAULT_CONFIG == original

    def test_devices_from_data(self):
        """Devices list is deep-copied from ``data`` with DEVICE_CONFIG defaults."""
        devices = [
            {"name": "dev1", "panels": [{"type": "clock"}]},
            {"name": "dev2", "panels": []},
        ]
        result = _build_config_dict({"name": "test", "devices": devices}, {})
        # Devices get filled with DEVICE_CONFIG defaults
        assert result["devices"][0]["name"] == "dev1"
        assert result["devices"][0]["panels"] == [{"type": "clock"}]
        assert result["devices"][1]["name"] == "dev2"
        assert result["devices"][1]["panels"] == []
        # Verify deep copy
        assert result["devices"] is not devices

    def test_panels_merged_into_devices(self):
        """Panel storage data merges into cfg['devices'] entries correctly."""
        panels = {
            "devices": {
                "dev1": {
                    "panels": [{"type": "grid", "key": "grid_0"}],
                }
            }
        }
        result = _build_config_dict(
            {"name": "test", "devices": [{"name": "dev1", "panels": []}]},
            {},
            panels,
        )
        assert result["devices"][0]["panels"] == [{"type": "grid", "key": "grid_0"}]
        assert result["panels"] == [{"type": "grid", "key": "grid_0"}]

    def test_panels_store_config_flows_to_device(self):
        """When panels arg carries per-device config, cfg["device"] reflects it."""
        panels = {
            "version": 1,
            "devices": {
                "living_room": {
                    "config": {
                        "locale": "de_DE",
                        "show_home_button": True,
                        "sleep_exit_behavior": "one_touch",
                        "snapshot_max_age_seconds": 30,
                    },
                    "panels": [{"type": "clock"}],
                },
            },
        }
        data = {
            "name": "nspanel_haui",
            "devices": [{"name": "living_room"}],
        }
        result = _build_config_dict(data, {}, panels)

        # cfg["device"] picks up store config
        assert result["device"]["locale"] == "de_DE"
        assert result["device"]["show_home_button"] is True
        assert result["device"]["snapshot_max_age_seconds"] == 30

        # fields NOT in store config keep DEFAULT_CONFIG values
        assert result["device"]["button_left_entity"] == ""
        assert result["device"]["sound_on_startup"] is True

        # name still comes from data, not store
        assert result["device"]["name"] == "nspanel_haui"

    def test_device_config_home_sleep_wakeup_keys(self):
        """Device config carries home/sleep/wakeup panel key references."""
        panels = {
            "version": 1,
            "devices": {
                "living_room": {
                    "config": {
                        "home_panel": "my_clock",
                        "sleep_panel": "screensaver",
                        "wakeup_panel": "welcome",
                    },
                    "panels": [{"type": "clock"}],
                },
            },
        }
        data = {
            "name": "nspanel_haui",
            "devices": [{"name": "living_room"}],
        }
        result = _build_config_dict(data, {}, panels)

        assert result["device"]["home_panel"] == "my_clock"
        assert result["device"]["sleep_panel"] == "screensaver"
        assert result["device"]["wakeup_panel"] == "welcome"

    def test_panels_without_config_leaves_device_defaults(self):
        """Without a panels arg, cfg["device"] stays at DEFAULT_CONFIG values."""
        result = _build_config_dict({"name": "test"}, {})

        # Device fields hold DEFAULT_CONFIG defaults
        assert result["device"]["locale"] == "en_US"
        assert result["device"]["show_home_button"] is False
        assert result["device"]["show_notifications_button"] is True

    def test_panels_store_no_config_block_leaves_device_defaults(self):
        """With panels arg but no config block, cfg["device"] stays at defaults."""
        panels = {
            "version": 1,
            "devices": {
                "living_room": {"panels": []},
            },
        }
        data = {
            "name": "nspanel_haui",
            "devices": [{"name": "living_room"}],
        }
        result = _build_config_dict(data, {}, panels)

        # No config block → device stays at DEFAULT_CONFIG
        assert result["device"]["locale"] == "en_US"

    def test_panels_store_name_mismatch_leaves_device_defaults(self):
        """When store device name doesn't match any device, cfg["device"] unchanged."""
        panels = {
            "version": 1,
            "devices": {
                "other_room": {
                    "config": {"locale": "fr_FR"},
                    "panels": [],
                },
            },
        }
        data = {
            "name": "nspanel_haui",
            "devices": [{"name": "living_room"}],
        }
        result = _build_config_dict(data, {}, panels)

        # other_room doesn't match living_room → device stays default
        assert result["device"]["locale"] == "en_US"

    def test_build_config_dict_per_device_filtering(self):
        """_build_config_dict with device_name= filters to only that device."""
        data = {
            "name": "hub",
            "devices": [
                {"name": "dev1", "panels": [{"type": "grid", "key": "grid_1"}]},
                {"name": "dev2", "panels": [{"type": "clock", "key": "clock_1"}]},
            ],
        }
        result = _build_config_dict(data, {}, device_name="dev1")
        assert len(result["devices"]) == 1
        assert result["devices"][0]["name"] == "dev1"
        assert result["panels"] == [{"type": "grid", "key": "grid_1"}]

    def test_build_config_dict_per_device_with_store(self):
        """With device_name=, store data is scoped to the matching device only."""
        panels = {
            "devices": {
                "dev1": {"panels": [{"type": "grid", "key": "store_grid"}]},
                "dev2": {"panels": [{"type": "clock", "key": "store_clock"}]},
            }
        }
        data = {
            "name": "hub",
            "devices": [
                {"name": "dev1", "panels": []},
                {"name": "dev2", "panels": []},
            ],
        }
        result = _build_config_dict(data, {}, panels, device_name="dev2")
        assert len(result["devices"]) == 1
        assert result["devices"][0]["name"] == "dev2"
        assert result["panels"] == [{"type": "clock", "key": "store_clock"}]

    def test_build_config_dict_per_device_unknown_creates_minimal(self):
        """When device_name isn't in devices list, a minimal entry is created."""
        data = {
            "name": "hub",
            "devices": [{"name": "dev1", "panels": []}],
        }
        result = _build_config_dict(data, {}, device_name="unknown_dev")
        assert len(result["devices"]) == 1
        assert result["devices"][0]["name"] == "unknown_dev"

    def test_build_config_dict_without_device_name_includes_all(self):
        """Without device_name= (default), all devices are included."""
        data = {
            "name": "hub",
            "devices": [
                {"name": "dev1", "panels": [{"type": "grid"}]},
                {"name": "dev2", "panels": [{"type": "clock"}]},
            ],
        }
        result = _build_config_dict(data, {})
        assert len(result["devices"]) == 2


# ---------------------------------------------------------------------------
# resolve_ha_device_id
# ---------------------------------------------------------------------------


class TestResolveHaDeviceId:
    """Tests for resolve_ha_device_id helper."""

    def test_returns_device_id_when_found(self):
        """Returns the HA device registry id when a matching ESPHome entry exists."""
        from nspanel_haui.esphome_helpers import resolve_ha_device_id

        # Ensure homeassistant.helpers.device_registry exists so the
        # import inside resolve_ha_device_id does not trigger the
        # ImportError fallback (which returns None).
        if "homeassistant.helpers.device_registry" not in sys.modules:
            mock_dev_reg_module = types.ModuleType("homeassistant.helpers.device_registry")
            sys.modules["homeassistant.helpers.device_registry"] = mock_dev_reg_module
        if "homeassistant.helpers" not in sys.modules:
            sys.modules["homeassistant.helpers"] = types.ModuleType("homeassistant.helpers")

        device_entry = MagicMock()
        device_entry.id = "abc123-def456"
        dev_reg = MagicMock()
        dev_reg.async_entries_for_config_entry = MagicMock(return_value=[device_entry])

        with (
            patch.object(
                sys.modules["homeassistant.helpers.device_registry"],
                "async_get",
                return_value=dev_reg,
                create=True,
            ),
            patch.object(
                sys.modules["homeassistant.helpers.device_registry"],
                "async_entries_for_config_entry",
                return_value=[device_entry],
                create=True,
            ),
        ):
            hass = MagicMock()
            esphome_entry = MagicMock()
            esphome_entry.data = {"device_name": "nspanel-living"}
            esphome_entry.entry_id = "esphome_entry_id"
            hass.config_entries.async_entries = MagicMock(return_value=[esphome_entry])

            result = resolve_ha_device_id(hass, "nspanel-living")
            assert result == "abc123-def456"

    def test_returns_none_when_no_match(self):
        """Returns None when no ESPHome entry matches."""
        from nspanel_haui.esphome_helpers import resolve_ha_device_id

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"device_name": "other-device"}
        entry.entry_id = "other_id"
        hass.config_entries.async_entries = MagicMock(return_value=[entry])

        result = resolve_ha_device_id(hass, "nspanel-living")
        assert result is None

    def test_returns_none_when_empty_name(self):
        """Returns None when given an empty node_name."""
        from nspanel_haui.esphome_helpers import resolve_ha_device_id

        hass = MagicMock()
        result = resolve_ha_device_id(hass, "")
        assert result is None


# ---------------------------------------------------------------------------
# async_migrate_entry - no-op (current version)
# ---------------------------------------------------------------------------


class TestMigrateEntry:
    """Test the no-op config entry migration (VERSION=1)."""

    def _make_entry(self, version=1, data=None, options=None):
        """Build a MagicMock config entry."""
        entry = MagicMock()
        entry.version = version
        entry.data = data or {"name": "test_device"}
        entry.options = options or {}
        return entry

    def _run_migration(self, entry):
        """Run the migration synchronously via asyncio. Returns (hass, result)."""
        from nspanel_haui.config_flow import NSPanelHAUIConfigFlow

        hass = MagicMock()

        async def _migrate():
            return await NSPanelHAUIConfigFlow.async_migrate_entry(hass, entry)

        return hass, asyncio.run(_migrate())

    def test_migration_returns_true(self):
        """Migration returns True without modifying the entry."""
        entry = self._make_entry(data={"name": "test"})
        _hass, result = self._run_migration(entry)
        assert result is True

    def test_migration_does_not_update_entry(self):
        """Migration does not call async_update_entry."""
        entry = self._make_entry(
            data={"name": "test", "devices": [{"name": "dev1"}]},
            options={"update_interval": 30, "debug": False},
        )
        hass, result = self._run_migration(entry)
        assert result is True
        assert not hass.config_entries.async_update_entry.called

    def test_migration_preserves_v1_entry_data(self):
        """Migration leaves entry data and version untouched."""
        entry = self._make_entry(
            data={"name": "test", "devices": [{"name": "dev1"}]},
            options={"update_interval": 30, "debug": False},
        )
        hass, result = self._run_migration(entry)
        assert result is True
        assert entry.version == 1
        assert entry.data["name"] == "test"
        assert entry.data["devices"] == [{"name": "dev1"}]
        assert entry.options["update_interval"] == 30


# ---------------------------------------------------------------------------
# Tests for MQTT discovery & ESPHome matching (config flow v3)
# ---------------------------------------------------------------------------


class TestNormalizeDeviceName:
    """Tests for _normalize_device_name."""

    def test_lowercases(self):
        assert _normalize_device_name("Panel-Living") == "panel living"

    def test_replaces_underscores(self):
        assert _normalize_device_name("panel_living_room") == "panel living room"

    def test_replaces_hyphens(self):
        assert _normalize_device_name("panel-living-room") == "panel living room"

    def test_strips_whitespace(self):
        assert _normalize_device_name("  panel living  ") == "panel living"

    def test_mixed_chars(self):
        assert _normalize_device_name("Panel_Living-Room") == "panel living room"


class TestFindESPHomeDevice:
    """Tests for _find_esphome_device(hass, device_name)."""

    def test_matches_by_device_info_name(self):
        """Returns entry_id when device_info.name matches."""
        hass = MagicMock()
        hass.data = {"esphome": {"entry1": {"device_info": {"name": "panel-living"}}}}
        result = _find_esphome_device(hass, "panel-living")
        assert result == "entry1"

    def test_matches_by_normalized_name(self):
        """Returns entry_id when names differ in case/separators but normalize equal."""
        hass = MagicMock()
        hass.data = {"esphome": {"entry1": {"device_info": {"name": "Panel Living"}}}}
        result = _find_esphome_device(hass, "panel_living")
        assert result == "entry1"

    def test_no_match_returns_none(self):
        """Returns None when no device_info.name matches."""
        hass = MagicMock()
        hass.data = {"esphome": {"entry1": {"device_info": {"name": "panel-living"}}}}
        result = _find_esphome_device(hass, "other-panel")
        assert result is None

    def test_empty_esphome_data_returns_none(self):
        """Returns None when esphome data dict is empty."""
        hass = MagicMock()
        hass.data = {"esphome": {}}
        result = _find_esphome_device(hass, "panel-living")
        assert result is None

    def test_no_esphome_key_returns_none(self):
        """Returns None when hass.data has no 'esphome' key."""
        hass = MagicMock()
        hass.data = {}
        result = _find_esphome_device(hass, "panel-living")
        assert result is None

    def test_fallback_entity_registry_returns_none(self):
        """Fallback path matches via entity registry but cannot determine entry_id."""
        from homeassistant.helpers import entity_registry

        hass = MagicMock()
        hass.data = {}

        fake_entity = MagicMock()
        fake_entity.platform = "esphome"
        fake_entity.name = "panel_living"

        er_mock = MagicMock()
        er_mock.entities.values.return_value = [fake_entity]
        entity_registry.async_get.return_value = er_mock

        result = _find_esphome_device(hass, "panel-living")
        # Fallback confirms match but can't determine entry_id
        assert result is None

    def test_fallback_entity_registry_no_match_returns_none(self):
        """Fallback path: no entity match returns None."""
        from homeassistant.helpers import entity_registry

        hass = MagicMock()
        hass.data = {}

        fake_entity = MagicMock()
        fake_entity.platform = "sensor"
        fake_entity.name = "temperature"

        er_mock = MagicMock()
        er_mock.entities.values.return_value = [fake_entity]
        entity_registry.async_get.return_value = er_mock

        result = _find_esphome_device(hass, "panel-living")
        assert result is None

    def test_exception_handled_gracefully(self):
        """Exceptions during lookup are caught and return None."""
        hass = MagicMock()
        hass.data = MagicMock()
        hass.data.get.side_effect = AttributeError("boom")
        result = _find_esphome_device(hass, "panel-living")
        assert result is None

    def test_non_dict_entry_skipped(self):
        """Non-dict esphome entries are gracefully skipped."""
        hass = MagicMock()
        hass.data = {
            "esphome": {
                "entry1": ["not", "a", "dict"],
                "entry2": {"device_info": {"name": "panel-living"}},
            }
        }
        result = _find_esphome_device(hass, "panel-living")
        assert result == "entry2"


class TestDiscoverEspHomeDevices:
    """Tests for _discover_esphome_devices(hass)."""

    def test_returns_list_of_dicts(self):
        """Each result has 'name' and 'esphome_device_id' keys."""
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        # Mock a HAUI service so is_haui_device() returns True
        svc = MagicMock()
        svc.name = "send_command"

        entry1 = MagicMock()
        entry1.entry_id = "entry1"
        entry1.title = "Panel Kitchen"
        # Use device_name so the name is resolved from it
        entry1.data = {"device_name": "kitchen-panel"}
        entry1.runtime_data = MagicMock()
        entry1.runtime_data.services = {"svc1": svc}

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry1])

        result = asyncio.run(discover_esphome_devices(hass))
        assert len(result) == 1
        assert result[0]["name"] == "kitchen-panel"
        assert result[0]["esphome_device_id"] == "entry1"

    def test_returns_empty_list_when_no_esphome_entries(self):
        """Returns [] when there are no ESPHome config entries."""
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[])

        result = asyncio.run(discover_esphome_devices(hass))
        assert result == []

    def test_name_falls_back_to_title(self):
        """Uses entry.title when device_name is not in data."""
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        # Mock a HAUI service so is_haui_device() returns True
        svc = MagicMock()
        svc.name = "send_command"

        entry1 = MagicMock()
        entry1.entry_id = "entry1"
        entry1.title = "My Panel"
        entry1.data = {}
        entry1.runtime_data = MagicMock()
        entry1.runtime_data.services = {"svc1": svc}

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry1])

        result = asyncio.run(discover_esphome_devices(hass))
        assert len(result) == 1
        assert result[0]["name"] == "My Panel"

    def test_esphome_device_id_populated(self):
        """ESPHome discovery result includes entry_id as esphome_device_id."""
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        # Mock a HAUI service so is_haui_device() returns True
        svc = MagicMock()
        svc.name = "send_command"

        entry1 = MagicMock()
        entry1.entry_id = "abc123"
        entry1.title = "Living Room Panel"
        entry1.data = {}
        entry1.runtime_data = MagicMock()
        entry1.runtime_data.services = {"svc1": svc}

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry1])

        result = asyncio.run(discover_esphome_devices(hass))
        assert len(result) == 1
        assert result[0]["esphome_device_id"] == "abc123"

    def test_matches_via_device_registry_offline(self):
        """Offline device with no runtime_data still matches via device registry.

        The ESPHome integration writes manufacturer/model on the HA device
        entry. These persist across restarts and let us detect HAUI
        devices that are not currently online.
        """
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        dev_entry = MagicMock()
        dev_entry.manufacturer = "happydasch"
        dev_entry.model = "nspanel_haui"

        # Offline ESPHome entry: no runtime_data services, no project_name.
        entry1 = MagicMock()
        entry1.entry_id = "offline-entry"
        entry1.title = "Bedroom Panel"
        entry1.data = {"device_name": "nspanel-bedroom"}
        # Force runtime_data to look "empty": no device_info, no services.
        entry1.runtime_data = MagicMock(spec=[])

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry1])
        hass.services.async_services = MagicMock(return_value={"esphome": {}})

        with _patch_device_registry(entries=[dev_entry]):
            result = asyncio.run(discover_esphome_devices(hass))
        assert len(result) == 1
        assert result[0]["name"] == "nspanel-bedroom"
        assert result[0]["esphome_device_id"] == "offline-entry"

    def test_skips_non_haui_via_device_registry(self):
        """Non-HAUI ESPHome entry (different manufacturer/model) is skipped."""
        from nspanel_haui.esphome_helpers import discover_esphome_devices

        dev_entry = MagicMock()
        dev_entry.manufacturer = "espressif"
        dev_entry.model = "esp32dev"

        entry1 = MagicMock()
        entry1.entry_id = "non-haui"
        entry1.title = "Some other ESPHome device"
        entry1.data = {"device_name": "some-other-device"}
        entry1.runtime_data = MagicMock(spec=[])

        hass = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry1])
        hass.services.async_services = MagicMock(return_value={"esphome": {}})

        with _patch_device_registry(entries=[dev_entry]):
            result = asyncio.run(discover_esphome_devices(hass))
        assert result == []


class TestConfigFlowUserStep:
    """Tests for NSPanelHAUIConfigFlow.async_step_user."""

    def _make_flow(self):
        """Create a flow instance with a mocked hass."""
        flow = NSPanelHAUIConfigFlow()
        flow.hass = MagicMock()
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_single_instance_aborts(self):
        """When an entry already exists, flow aborts."""
        flow = self._make_flow()
        flow._async_current_entries = MagicMock(return_value=[MagicMock()])
        result = self._run(flow.async_step_user())
        assert result["type"] == "abort"
        assert result["reason"] == "single_instance_allowed"

    def test_auto_creates_entry_without_esphome_devices(self):
        """When no ESPHome devices found, creates entry with empty devices list."""

        flow = self._make_flow()

        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=[]),
        ):
            result = self._run(flow.async_step_user())
            assert result["type"] == "create_entry"
            assert result["title"] == "NSPanel HAUI Hub"
            assert result["data"]["name"] == "NSPanel HAUI Hub"
            assert result["data"]["devices"] == []

    def test_auto_discovery_creates_entry_with_devices(self):
        """ESPHome discovery runs automatically and adds devices to entry."""

        flow = self._make_flow()

        discovered = [
            {"name": "panel-living", "esphome_device_id": "entry1", "friendly_name": ""},
            {"name": "panel-kitchen", "esphome_device_id": None, "friendly_name": ""},
        ]

        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=discovered),
        ):
            result = self._run(flow.async_step_user())
            assert result["type"] == "create_entry"
            assert result["title"] == "NSPanel HAUI Hub"
            assert result["data"]["name"] == "NSPanel HAUI Hub"
            assert len(result["data"]["devices"]) == 2
            assert result["data"]["devices"][0]["name"] == "panel-living"
            assert result["data"]["devices"][0]["esphome_device_id"] == "entry1"
            assert result["data"]["devices"][1]["name"] == "panel-kitchen"
            assert result["data"]["devices"][1]["esphome_device_id"] == ""

    def test_auto_discovery_empty_result_creates_entry(self):
        """When discovery finds no devices, creates entry with empty devices."""

        flow = self._make_flow()

        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=[]),
        ):
            result = self._run(flow.async_step_user())
            assert result["type"] == "create_entry"
            assert result["title"] == "NSPanel HAUI Hub"
            assert result["data"]["name"] == "NSPanel HAUI Hub"
            assert result["data"]["devices"] == []

    def test_esphome_discovery_unavailable_creates_entry(self):
        """ESPHome discovery always runs; empty result still creates entry."""

        flow = self._make_flow()

        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=[]),
        ):
            result = self._run(flow.async_step_user())
            assert result["type"] == "create_entry"
            assert result["title"] == "NSPanel HAUI Hub"
            assert result["data"]["name"] == "NSPanel HAUI Hub"
            assert result["data"]["devices"] == []


class TestDiscoveryCard:
    """Tests for the integration_discovery confirm card flow."""

    def _make_flow(self):
        flow = NSPanelHAUIConfigFlow()
        flow.hass = MagicMock()
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_integration_discovery_shows_form_when_devices_found(self):
        """integration_discovery → confirm form, not auto-create."""
        flow = self._make_flow()
        discovered = [
            {"name": "panel-living", "esphome_device_id": "e1"},
            {"name": "panel-kitchen", "esphome_device_id": "e2"},
        ]
        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=discovered),
        ):
            result = self._run(flow.async_step_integration_discovery({}))
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"
        assert result["description_placeholders"]["count"] == "2"
        assert "panel-living" in result["description_placeholders"]["names"]

    def test_integration_discovery_aborts_when_no_devices(self):
        """integration_discovery aborts with no_devices_found if scan empty."""
        flow = self._make_flow()
        with patch(
            "nspanel_haui.config_flow._discover_esphome_devices",
            new=AsyncMock(return_value=[]),
        ):
            result = self._run(flow.async_step_integration_discovery({}))
        assert result["type"] == "abort"
        assert result["reason"] == "no_devices_found"

    def test_integration_discovery_aborts_when_entry_exists(self):
        """integration_discovery aborts if a hub entry is already present."""
        flow = self._make_flow()
        flow._async_current_entries = MagicMock(return_value=[MagicMock()])
        result = self._run(flow.async_step_integration_discovery({}))
        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"

    def test_confirm_creates_entry_on_submit(self):
        """Submitting the confirm form creates the hub entry with devices."""
        flow = self._make_flow()
        flow._discovered_devices = [
            {"name": "panel-living", "esphome_device_id": "e1"},
        ]
        with patch(
            "nspanel_haui.config_flow._register_discovery",
            new=AsyncMock(return_value=None),
            create=True,
        ):
            # _register_discovery is imported inside the method via
            # ``from . import _register_discovery``; patch the package attr.
            import nspanel_haui as pkg

            pkg._register_discovery = AsyncMock(return_value=None)
            result = self._run(flow.async_step_confirm({}))
        assert result["type"] == "create_entry"
        assert result["title"] == "NSPanel HAUI Hub"
        assert len(result["data"]["devices"]) == 1
        assert result["data"]["devices"][0]["name"] == "panel-living"
        assert result["data"]["devices"][0]["esphome_device_id"] == "e1"

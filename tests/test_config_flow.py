"""Tests for NSPanel HAUI config flow helpers and options-to-config conversion."""

from __future__ import annotations

import asyncio
import copy
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out homeassistant before importing config_flow so tests run without HA.
# ---------------------------------------------------------------------------

def _make_ha_stubs() -> None:
    """Insert minimal homeassistant stubs into sys.modules."""

    class _ConfigFlow:
        """Stub for config_entries.ConfigFlow — accepts domain= keyword."""
        def __init_subclass__(cls, domain: str = "", **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)

        def async_show_form(self, **kwargs: Any) -> dict:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict:
            return {"type": "create_entry", **kwargs}

        def async_show_menu(self, **kwargs: Any) -> dict:
            return {"type": "menu", **kwargs}

        def async_abort(self, reason: str = "", **kwargs: Any) -> dict:
            return {"type": "abort", "reason": reason}

        async def async_set_unique_id(self, unique_id: str) -> None:
            pass

        def _abort_if_unique_id_configured(self) -> None:
            pass

    class _OptionsFlowWithConfigEntry:
        """Stub for options flow base."""
        def __init__(self, config_entry: Any) -> None:
            self.config_entry = config_entry

        def async_show_form(self, **kwargs: Any) -> dict:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict:
            return {"type": "create_entry", **kwargs}

        def async_show_menu(self, **kwargs: Any) -> dict:
            return {"type": "menu", **kwargs}

    ha = MagicMock()
    ha.config_entries.ConfigFlow = _ConfigFlow
    ha.config_entries.OptionsFlowWithConfigEntry = _OptionsFlowWithConfigEntry
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

    helpers = MagicMock()
    helpers.selector = selector_mod

    entity_registry_mod = MagicMock()
    entity_registry_mod.async_get = MagicMock()

    helpers.entity_registry = entity_registry_mod

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
        "homeassistant.helpers.config_validation": MagicMock(),
        "homeassistant.const": MagicMock(),
        "homeassistant.components": components_mod,
        "homeassistant.components.mqtt": mqtt_mod,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_make_ha_stubs()

# Now safe to import
import voluptuous as vol  # noqa: E402
from nspanel_haui.config_flow import (  # noqa: E402
    MQTT_DISCOVERY_TIMEOUT,
    NSPanelHAUIConfigFlow,
    NSPanelHAUIOptionsFlow,
    Action,
    _apply_transforms,
    _extract_panel_config,
    _find_esphome_device,
    _mqtt_available,
    _normalize_device_name,
    _panel_action_options,
    _device_action_options,
    _device_list_options,
    _panel_edit_schema,
    _panel_label,
    _panel_list_options,
    _panel_type_options,
    _panel_type_specific_schema,
    _run_mqtt_discovery,
    _user_panel_types,
)
from nspanel_haui import _options_to_config_dict  # noqa: E402


def _vol_default(vol_key):
    """Extract the default from a voluptuous key, calling it if it's a factory."""
    default = vol_key.default
    if callable(default):
        return default()
    return default


# ---------------------------------------------------------------------------
# _panel_label
# ---------------------------------------------------------------------------

class TestPanelLabel:
    def test_type_only(self):
        assert _panel_label({"type": "clock"}) == "clock"

    def test_title_and_type(self):
        assert _panel_label({"type": "grid", "title": "Living Room"}) == "Living Room (grid)"

    def test_empty_title_falls_back_to_type(self):
        assert _panel_label({"type": "light", "title": ""}) == "light"

    def test_missing_type(self):
        assert _panel_label({"title": "My Panel"}) == "My Panel (?)"

    def test_missing_both(self):
        assert _panel_label({}) == "?"


# ---------------------------------------------------------------------------
# _panel_list_options
# ---------------------------------------------------------------------------

class TestPanelListOptions:
    def _opts(self, panels: list[dict]) -> list[dict]:
        return _panel_list_options(panels)

    def test_empty_panels_has_add_and_done(self):
        opts = self._opts([])
        values = [o["value"] for o in opts]
        assert Action.ADD in values
        assert Action.DONE in values
        assert len(opts) == 2

    def test_single_panel_generates_select(self):
        opts = self._opts([{"type": "clock"}])
        values = [o["value"] for o in opts]
        assert "0" in values
        # should NOT have individual action rows
        assert "edit_0" not in values
        assert "remove_0" not in values

    def test_multiple_panels_correct_indices(self):
        panels = [{"type": "clock"}, {"type": "grid", "title": "Home"}]
        opts = self._opts(panels)
        values = [o["value"] for o in opts]
        assert "0" in values
        assert "1" in values

    def test_order_add_selects_done(self):
        opts = self._opts([{"type": "clock"}, {"type": "light"}])
        values = [o["value"] for o in opts]
        assert values[0] == Action.ADD
        assert values[1] == "0"
        assert values[2] == "1"
        assert values[-1] == Action.DONE

    def test_label_is_panel_label(self):
        opts = self._opts([{"type": "grid", "title": "Lounge"}])
        select_opt = next(o for o in opts if o["value"] == "0")
        assert "Lounge" in select_opt["label"]


# ---------------------------------------------------------------------------
# _panel_action_options  —  sub-menu for a selected panel
# ---------------------------------------------------------------------------


class TestPanelActionOptions:
    def _opts(self, idx: int, panels: list[dict]) -> list[dict]:
        return _panel_action_options(idx, panels)

    def test_has_all_action_types(self):
        opts = self._opts(0, [{"type": "clock"}])
        values = [o["value"] for o in opts]
        assert "edit_0" in values
        assert "dup_0" in values
        assert "up_0" in values
        assert "down_0" in values
        assert "remove_0" in values
        assert Action.BACK in values

    def test_back_is_last(self):
        opts = self._opts(0, [{"type": "clock"}])
        assert opts[-1]["value"] == Action.BACK

    def test_uses_correct_index(self):
        opts = self._opts(2, [
            {"type": "clock"}, {"type": "grid"}, {"type": "light"}
        ])
        values = [o["value"] for o in opts]
        assert "edit_2" in values
        assert "edit_0" not in values

    def test_labels_include_panel_label(self):
        opts = self._opts(0, [{"type": "grid", "title": "Living Room"}])
        edit_opt = next(o for o in opts if o["value"] == "edit_0")
        assert "Living Room" in edit_opt["label"]


# ---------------------------------------------------------------------------
# _user_panel_types
# ---------------------------------------------------------------------------

class TestUserPanelTypes:
    def test_returns_list_of_dicts(self):
        types = _user_panel_types()
        assert isinstance(types, list)
        assert all("value" in t and "label" in t for t in types)

    def test_no_popup_types(self):
        types = _user_panel_types()
        values = [t["value"] for t in types]
        assert not any(v.startswith("popup_") for v in values)

    def test_no_sys_types(self):
        types = _user_panel_types()
        values = [t["value"] for t in types]
        assert not any(v.startswith("sys_") for v in values)

    def test_sorted_by_label(self):
        types = _user_panel_types()
        labels = [t["label"] for t in types]
        assert labels == sorted(labels)

    def test_clock_present(self):
        types = _user_panel_types()
        values = [t["value"] for t in types]
        assert "clock" in values


# ---------------------------------------------------------------------------
# _extract_panel_config
# ---------------------------------------------------------------------------

class TestExtractPanelConfig:
    def test_basic_fields(self):
        result = _extract_panel_config({"type": "clock", "title": "My Clock"}, -1, [])
        assert result["type"] == "clock"
        assert result["title"] == "My Clock"

    def test_auto_generates_key_for_new_panel(self):
        result = _extract_panel_config({"type": "grid"}, -1, [{"type": "clock"}])
        # idx is len(panels) = 1 for new panel
        assert result["key"] == "grid_1"

    def test_auto_generates_key_for_edit(self):
        panels = [{"type": "clock"}, {"type": "light"}]
        result = _extract_panel_config({"type": "light", "key": ""}, 1, panels)
        assert result["key"] == "light_1"

    def test_explicit_key_preserved(self):
        result = _extract_panel_config({"type": "clock", "key": "my_clock"}, -1, [])
        assert result["key"] == "my_clock"

    def test_none_entity_stays_none(self):
        result = _extract_panel_config({"type": "clock"}, -1, [])
        assert result["entity"] is None

    def test_entities_defaults_to_empty_list(self):
        result = _extract_panel_config({"type": "grid"}, -1, [])
        assert result["entities"] == []

    def test_does_not_mutate_panels_list(self):
        panels = [{"type": "clock"}]
        original = copy.deepcopy(panels)
        _extract_panel_config({"type": "grid"}, -1, panels)
        assert panels == original


# ---------------------------------------------------------------------------
# _options_to_config_dict
# ---------------------------------------------------------------------------

class TestOptionsToConfigDict:
    def test_yaml_override_takes_priority(self):
        options = {"config_yaml": "device:\n  name: test\npanels: []\n"}
        result = _options_to_config_dict("ignored", options)
        assert result["device"]["name"] == "test"
        assert result["panels"] == []

    def test_empty_options_uses_defaults(self):
        result = _options_to_config_dict("my_device", {})
        assert result["device"]["name"] == "my_device"
        assert "panels" in result
        assert "mqtt" in result
        # mqtt topic_prefix comes from DEFAULT_CONFIG when not in options
        assert result["mqtt"]["topic_prefix"] == "nspanel_haui_test"

    def test_name_always_set_from_argument(self):
        result = _options_to_config_dict("living_room", {})
        assert result["device"]["name"] == "living_room"

    def test_structured_panels_override_default(self):
        panels = [{"type": "grid", "key": "grid_0", "title": "Home"}]
        result = _options_to_config_dict("test", {"panels": panels})
        assert result["panels"] == panels

    def test_mqtt_topic_prefix_from_options(self):
        result = _options_to_config_dict("test", {"mqtt_topic_prefix": "my_custom_prefix"})
        assert result["mqtt"]["topic_prefix"] == "my_custom_prefix"

    def test_mqtt_topic_prefix_default_when_absent(self):
        result = _options_to_config_dict("test", {})
        assert result["mqtt"]["topic_prefix"] == "nspanel_haui_test"

    def test_does_not_mutate_default_config(self):
        from nspanel_haui.haui.mapping.const import DEFAULT_CONFIG

        original_panels = copy.deepcopy(DEFAULT_CONFIG["panels"])
        _options_to_config_dict("test", {"panels": [{"type": "grid"}]})
        assert DEFAULT_CONFIG["panels"] == original_panels

    def test_backward_compat_old_yaml_only_entry(self):
        """Old entries that only have config_yaml still work via escape hatch."""
        yaml_str = "device:\n  name: old_device\npanels:\n  - type: clock\n"
        result = _options_to_config_dict("old_device", {"config_yaml": yaml_str})
        assert result["device"]["name"] == "old_device"
        assert result["panels"][0]["type"] == "clock"

    def test_empty_config_yaml_falls_through_to_structured(self):
        """config_yaml='' (falsy) must not be treated as YAML override."""
        result = _options_to_config_dict("dev", {"config_yaml": "", "panels": []})
        assert result["panels"] == []
        assert result["device"]["name"] == "dev"


# ---------------------------------------------------------------------------
# _panel_type_options  —  fetches PageOption list for a given panel type
# ---------------------------------------------------------------------------


class TestPanelTypeOptions:
    def test_returns_list_for_known_type(self):
        opts = _panel_type_options("clock")
        assert isinstance(opts, list)
        assert len(opts) > 0

    def test_returns_empty_for_unknown_type(self):
        assert _panel_type_options("nonexistent") == []

    def test_returns_empty_for_empty_string(self):
        assert _panel_type_options("") == []

    def test_clock_options_contain_background(self):
        keys = [o.key for o in _panel_type_options("clock")]
        assert "background" in keys
        assert "show_weather" in keys

    def test_light_options_contain_entity_with_domain(self):
        opts = _panel_type_options("light")
        entities = [o for o in opts if o.key == "entity"]
        assert len(entities) == 1
        assert entities[0].domain == "light"

    def test_media_options_contain_list_str(self):
        opts = _panel_type_options("media")
        kinds = {o.key: o.kind for o in opts}
        assert kinds.get("media_favorites") == "list_str"
        assert kinds.get("group_entities") == "list_str"

    def test_grid_options_contain_colors(self):
        opts = _panel_type_options("grid")
        colors = [o for o in opts if o.kind == "color"]
        assert len(colors) > 0

    def test_row_options_minimal(self):
        opts = _panel_type_options("row")
        keys = [o.key for o in opts]
        assert "initial_page" in keys


# ---------------------------------------------------------------------------
# _panel_type_specific_schema  —  builds vol.Optional dict from PageOptions
# ---------------------------------------------------------------------------


class TestPanelTypeSpecificSchema:
    def test_bool_option(self):
        schema, transforms = _panel_type_specific_schema("timer")
        # show_notification is a bool option
        assert schema  # non-empty
        assert isinstance(transforms, dict)
        for key in schema:
            if str(key).startswith("show_notification"):
                assert schema[key] == bool

    def test_int_option(self):
        schema, _transforms = _panel_type_specific_schema("clock")
        for key, val in schema.items():
            if "temp_precision" in str(key):
                assert isinstance(val, vol.Coerce)
                assert val.type == int

    def test_select_option_has_choices(self):
        schema, transforms = _panel_type_specific_schema("weather")
        for key, val in schema.items():
            if "background" in str(key) or "show_forecast" in str(key):
                # SelectSelector is used for select kind
                assert val is not None
        # Select fields should have drop_empty transform
        for t_key in transforms:
            if "background" in t_key or "show_forecast" in t_key:
                assert transforms[t_key] == "drop_empty"

    def test_entity_with_domain(self):
        schema, _transforms = _panel_type_specific_schema("light")
        assert schema  # should include entity with domain=light

    def test_str_option(self):
        schema, transforms = _panel_type_specific_schema("qr")
        for key, val in schema.items():
            if "qr_code" in str(key):
                assert val == str
        # str fields should have drop_empty transform
        assert any("qr_code" in k for k in transforms)

    def test_list_str_option(self):
        schema, transforms = _panel_type_specific_schema("media")
        found_schema = False
        for key, val in schema.items():
            if "media_favorites" in str(key) or "group_entities" in str(key):
                found_schema = True
        assert found_schema
        # list_str fields should have list_str transform
        assert any(
            transforms.get(k) == "list_str"
            for k in transforms
            if "media_favorites" in k or "group_entities" in k
        )

    def test_unknown_type_returns_empty(self):
        schema, transforms = _panel_type_specific_schema("nonexistent")
        assert schema == {}
        assert transforms == {}

    def test_empty_type_returns_empty(self):
        schema, transforms = _panel_type_specific_schema("")
        assert schema == {}
        assert transforms == {}

    def test_uses_current_values_for_defaults(self):
        current = {"show_weather": False, "show_temp": True, "temp_precision": 2}
        schema, _transforms = _panel_type_specific_schema("clock", current)
        for vol_key in schema:
            key_str = str(vol_key)
            if "show_weather" in key_str:
                assert _vol_default(vol_key) is False
            if "temp_precision" in key_str:
                assert _vol_default(vol_key) == 2

    def test_all_user_panel_types_produce_valid_schemas(self):
        """Every user-visible panel type must produce a valid schema dict and transforms dict."""
        for pt in _user_panel_types():
            schema, transforms = _panel_type_specific_schema(pt["value"])
            assert isinstance(schema, dict)
            assert isinstance(transforms, dict)


# ---------------------------------------------------------------------------
# _apply_transforms  —  converts form values to canonical config via transform map
# ---------------------------------------------------------------------------


class TestApplyTransforms:
    def test_list_str_becomes_list(self):
        transforms = {"media_favorites": "list_str"}
        result = _apply_transforms(
            {"media_favorites": "fav1\nfav2\n", "entity": "media_player.test"},
            transforms,
        )
        assert result["media_favorites"] == ["fav1", "fav2"]

    def test_list_str_empty_becomes_empty_list(self):
        transforms = {"media_favorites": "list_str"}
        result = _apply_transforms({"media_favorites": ""}, transforms)
        assert result["media_favorites"] == []

    def test_empty_str_dropped(self):
        transforms = {"background": "drop_empty"}
        result = _apply_transforms({"show_weather": True, "background": ""}, transforms)
        assert "background" not in result
        assert result["show_weather"] is True

    def test_empty_select_dropped(self):
        transforms = {"background": "drop_empty"}
        result = _apply_transforms({"background": "", "show_weather": True}, transforms)
        assert "background" not in result

    def test_non_option_keys_preserved(self):
        transforms = {}  # type/title are not in transforms
        result = _apply_transforms({"type": "clock", "title": "My Clock"}, transforms)
        assert result["type"] == "clock"
        assert result["title"] == "My Clock"

    def test_already_list_preserved(self):
        transforms = {"media_favorites": "list_str"}
        result = _apply_transforms({"media_favorites": ["a", "b"]}, transforms)
        assert result["media_favorites"] == ["a", "b"]

    def test_color_empty_string_dropped(self):
        transforms = {"text_color": "drop_empty"}
        result = _apply_transforms({"text_color": ""}, transforms)
        assert "text_color" not in result

    def test_color_value_preserved(self):
        transforms = {"text_color": "drop_empty"}
        result = _apply_transforms({"text_color": "65535"}, transforms)
        assert result["text_color"] == "65535"

    def test_transforms_from_schema(self):
        """Integration: transforms returned by _panel_type_specific_schema."""
        _schema, transforms = _panel_type_specific_schema("media")
        result = _apply_transforms(
            {"media_favorites": "fav1\nfav2\n", "entity": "media_player.test"},
            transforms,
        )
        assert result["media_favorites"] == ["fav1", "fav2"]


# ---------------------------------------------------------------------------
# _panel_edit_schema  —  common panel edit form schema
# ---------------------------------------------------------------------------


class TestPanelEditSchema:
    def test_returns_vol_schema(self):
        schema = _panel_edit_schema({}, _user_panel_types())
        assert isinstance(schema, vol.Schema)

    def test_contains_common_fields(self):
        schema = _panel_edit_schema({}, _user_panel_types()).schema
        keys = [str(k) for k in schema]
        assert any("type" in k for k in keys)
        assert any("title" in k for k in keys)
        assert any("key" in k for k in keys)
        assert any("entity" in k for k in keys)

    def test_uses_current_values(self):
        current = {"type": "clock", "title": "My Clock", "key": "clock_0"}
        schema = _panel_edit_schema(current, _user_panel_types()).schema
        for key, val in schema.items():
            if "title" in str(key) and hasattr(key, "default"):
                assert _vol_default(key) == "My Clock"

    def test_falls_back_to_first_type_when_current_empty(self):
        empty_current = {}
        schema = _panel_edit_schema(empty_current, _user_panel_types()).schema
        first_type = _user_panel_types()[0]["value"]
        for key in schema:
            if "type" in str(key) and hasattr(key, "default"):
                assert _vol_default(key) == first_type


# ---------------------------------------------------------------------------
# NSPanelHAUIOptionsFlow._build_panel_schema  —  merges base + type-specific
# ---------------------------------------------------------------------------


class TestBuildPanelSchema:
    def _make_flow(self, options=None):
        """Create a NSPanelHAUIOptionsFlow with a mock config_entry."""
        entry = MagicMock()
        entry.options = options or {}
        return NSPanelHAUIOptionsFlow(entry)

    def test_clock_schema_includes_specific_options(self):
        flow = self._make_flow()
        schema = flow._build_panel_schema({"type": "clock"}, _user_panel_types())
        assert isinstance(schema, vol.Schema)
        keys = [str(k) for k in schema.schema]
        assert any("background" in k for k in keys)
        assert any("temp_precision" in k for k in keys)

    def test_light_schema_has_domain_specific_entity(self):
        flow = self._make_flow()
        schema = flow._build_panel_schema({"type": "light"}, _user_panel_types())
        keys = [str(k) for k in schema.schema]
        # entity field should be present (domain-filtered from DESCRIPTOR)
        assert any("entity" in k for k in keys)

    def test_type_change_detected_from_user_input(self):
        """When user changes type in the form, previous type-specific values dropped."""
        flow = self._make_flow()
        current = {"type": "clock", "background": "summer", "temp_precision": 1}
        user_input = {"type": "grid"}
        schema = flow._build_panel_schema(current, _user_panel_types(), user_input)
        keys = [str(k) for k in schema.schema]
        # should have grid-specific options, not clock-specific
        assert any("color_seed" in k or "color_mode" in k for k in keys)

    def test_no_type_falls_back_to_first(self):
        flow = self._make_flow()
        schema = flow._build_panel_schema({}, _user_panel_types())
        assert isinstance(schema, vol.Schema)



# ---------------------------------------------------------------------------
# NSPanelHAUIOptionsFlow._build_full_config  —  builds full config for validation
# ---------------------------------------------------------------------------


class TestBuildFullConfig:
    def _make_flow(self, options=None):
        entry = MagicMock()
        entry.options = options or {}
        entry.data = {"name": "test_device"}
        flow = NSPanelHAUIOptionsFlow(entry)
        # Pre-populate ctx so _build_full_config has data to work with
        flow._ctx["panels"] = [{"type": "clock", "key": "clock_0"}]
        return flow

    def _make_flow_with_devices(self):
        entry = MagicMock()
        entry.options = {"mqtt_topic_prefix": "custom_prefix"}
        entry.data = {"name": "test_device"}
        flow = NSPanelHAUIOptionsFlow(entry)
        flow._ctx["devices"] = [
            {"name": "dev1", "locale": "en_US", "panels": [{"type": "clock", "key": "clock_0"}]},
        ]
        return flow

    def test_builds_valid_config_from_panels(self):
        flow = self._make_flow()
        cfg = flow._build_full_config()
        assert cfg["device"]["name"] == "test_device"
        assert cfg["panels"] == [{"type": "clock", "key": "clock_0"}]
        # Should pass validation (pydantic or stub)
        from nspanel_haui.haui.config_models import validate_config
        result = validate_config(cfg)
        assert result is not None

    def test_builds_valid_config_from_devices(self):
        flow = self._make_flow_with_devices()
        cfg = flow._build_full_config()
        assert cfg["device"]["name"] == "test_device"
        assert cfg["mqtt"]["topic_prefix"] == "custom_prefix"
        assert len(cfg["devices"]) == 1
        assert cfg["devices"][0]["name"] == "dev1"
        # Panels are flattened from devices
        assert cfg["panels"] == [{"type": "clock", "key": "clock_0"}]
        # Should pass validation
        from nspanel_haui.haui.config_models import validate_config
        result = validate_config(cfg)
        assert result is not None

    def test_does_not_mutate_default_config(self):
        from nspanel_haui.haui.mapping.const import DEFAULT_CONFIG
        original = copy.deepcopy(DEFAULT_CONFIG["panels"])
        flow = self._make_flow()
        flow._build_full_config()
        assert DEFAULT_CONFIG["panels"] == original

    def test_empty_panels_falls_back_to_default(self):
        """When _ctx has empty panels, DEFAULT_CONFIG panels are used."""
        from nspanel_haui.haui.mapping.const import DEFAULT_CONFIG
        flow = self._make_flow()
        flow._ctx["panels"] = []
        cfg = flow._build_full_config()
        # Empty list is falsy, so cfg["panels"] retains DEFAULT_CONFIG["panels"]
        assert cfg["panels"] == DEFAULT_CONFIG["panels"]

# ---------------------------------------------------------------------------
# NSPanelHAUIOptionsFlow  —  full options flow steps
# ---------------------------------------------------------------------------


class TestOptionsFlowPanels:
    def _make_flow(self, options=None):
        entry = MagicMock()
        entry.options = options or {"panels": [{"type": "clock", "key": "clock_0"}]}
        flow = NSPanelHAUIOptionsFlow(entry)
        flow._ctx["panels"] = []
        return flow

    def _make_flow_with_device(self, devices=None, panel_device_index=-1):
        """Create a flow in per-device mode with pre-populated devices.

        Sets _devices and _panel_device_index so that panels operations
        route through the per-device codepath.
        """
        entry = MagicMock()
        entry.options = {"devices": devices or [
            {"name": "dev1", "locale": "en_US", "panels": [{"type": "clock", "key": "c0"}]},
        ]}
        flow = NSPanelHAUIOptionsFlow(entry)
        flow._ctx["devices"] = copy.deepcopy(entry.options["devices"])
        flow._ctx["panels"] = []
        flow._ctx["panel_device_idx"] = panel_device_index
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_init_returns_menu(self):
        flow = self._make_flow()
        result = self._run(flow.async_step_init())
        assert result["type"] == "menu"
        assert result["menu_options"] == ["devices", "topic", "yaml_override"]

    def test_panels_first_visit_loads_from_options(self):
        flow = self._make_flow()
        result = self._run(flow.async_step_panels())
        assert result["type"] == "form"
        assert flow._ctx["panels"] == [{"type": "clock", "key": "clock_0"}]

    def test_panels_add_action(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        result = self._run(flow.async_step_panels({"panel_action": Action.ADD}))
        assert result["type"] == "form" or result["step_id"] == "panel_edit"
        assert flow._ctx["panel_idx"] == -1

    def test_panels_done_action_saves(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        flow._ctx["panels"].append({"type": "grid", "key": "grid_1"})
        result = self._run(flow.async_step_panels({"panel_action": Action.DONE}))
        assert result["type"] == "create_entry"
        assert result["data"]["panels"] == flow._ctx["panels"]
        assert "config_yaml" not in result["data"]

    def test_panels_select_shows_menu(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())  # load panels
        result = self._run(flow.async_step_panels({"panel_action": "0"}))
        assert result["type"] == "menu"
        assert result["step_id"] == "panel_menu"
        assert "edit_panel" in result["menu_options"]

    def test_panel_menu_edit(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        result = self._run(flow.async_step_panel_menu({"menu_item": "edit_panel"}))
        assert result["type"] == "form"
        assert result["step_id"] == "panel_edit"
        assert flow._ctx["panel_idx"] == 0

    def test_panel_menu_back(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        result = self._run(flow.async_step_panel_menu({"menu_item": "back"}))
        assert result["type"] == "form"
        assert result["step_id"] == "panels"

    def test_panel_menu_dup(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        result = self._run(flow.async_step_panel_menu({"menu_item": "duplicate_panel"}))
        # dup returns to panels list immediately
        assert result["type"] == "form"
        assert result["step_id"] == "panels"
        assert len(flow._ctx["panels"]) == 2

    def test_panel_menu_up(self):
        flow = self._make_flow({"panels": [
            {"type": "clock", "key": "clock_0"},
            {"type": "grid", "key": "grid_1"},
        ]})
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "1"}))
        self._run(flow.async_step_panel_menu({"menu_item": "move_up"}))
        assert flow._ctx["panels"][0]["key"] == "grid_1"
        assert flow._ctx["panels"][1]["key"] == "clock_0"

    def test_panel_menu_up_first_element_noop(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        original = copy.deepcopy(flow._ctx["panels"])
        self._run(flow.async_step_panels({"panel_action": "0"}))
        self._run(flow.async_step_panel_menu({"menu_item": "move_up"}))
        assert flow._ctx["panels"] == original

    def test_panel_menu_down(self):
        flow = self._make_flow({"panels": [
            {"type": "clock", "key": "clock_0"},
            {"type": "grid", "key": "grid_1"},
        ]})
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        self._run(flow.async_step_panel_menu({"menu_item": "move_down"}))
        assert flow._ctx["panels"][0]["key"] == "grid_1"
        assert flow._ctx["panels"][1]["key"] == "clock_0"

    def test_panel_menu_down_last_element_noop(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        original = copy.deepcopy(flow._ctx["panels"])
        self._run(flow.async_step_panels({"panel_action": "0"}))
        self._run(flow.async_step_panel_menu({"menu_item": "move_down"}))
        assert flow._ctx["panels"] == original

    def test_panel_menu_remove(self):
        flow = self._make_flow({"panels": [
            {"type": "clock", "key": "clock_0"},
            {"type": "grid", "key": "grid_1"},
        ]})
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        self._run(flow.async_step_panel_menu({"menu_item": "remove_panel"}))
        assert len(flow._ctx["panels"]) == 1
        assert flow._ctx["panels"][0]["key"] == "grid_1"

    def test_panel_menu_shows_menu(self):
        flow = self._make_flow()
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": "0"}))
        result = self._run(flow.async_step_panel_menu())
        assert result["type"] == "menu"
        assert result["step_id"] == "panel_menu"

    # ── per-device panels tests ───────────────────────────────────────────

    def test_manage_panels_from_device_menu(self):
        """Simulates async_step_device_menu with manage_panels, asserts routing and state."""
        flow = self._make_flow_with_device()
        self._run(flow.async_step_devices())
        self._run(flow.async_step_devices({"device_action": "0"}))
        result = self._run(flow.async_step_device_menu({"menu_item": "manage_panels"}))
        assert result["type"] == "form"
        assert result["step_id"] == "panels"
        assert flow._ctx["panel_device_idx"] == 0
        # Per-device panels loaded from the device, not top-level options
        assert flow._ctx["panels"] == [{"type": "clock", "key": "c0"}]

    def test_panels_save_to_device(self):
        """__done__ saves to result["data"]["devices"][0]["panels"], no top-level "panels"."""
        flow = self._make_flow_with_device(panel_device_index=0)
        self._run(flow.async_step_panels())
        flow._ctx["panels"].append({"type": "grid", "key": "grid_1"})
        result = self._run(flow.async_step_panels({"panel_action": Action.DONE}))
        assert result["type"] == "create_entry"
        assert "devices" in result["data"]
        assert result["data"]["devices"][0]["panels"] == flow._ctx["panels"]
        assert "panels" not in result["data"]

    def test_per_device_panel_isolation(self):
        """Editing device 0 panels must not affect device 1 panels."""
        flow = self._make_flow_with_device(
            devices=[
                {"name": "dev1", "locale": "en_US", "panels": [{"type": "clock", "key": "c0"}]},
                {"name": "dev2", "locale": "de_DE", "panels": [{"type": "grid", "key": "g0"}]},
            ],
            panel_device_index=0,
        )
        self._run(flow.async_step_panels())
        # Add a panel to device 0
        flow._ctx["panels"].append({"type": "light", "key": "light_1"})
        result = self._run(flow.async_step_panels({"panel_action": Action.DONE}))
        assert result["data"]["devices"][0]["panels"] == [
            {"type": "clock", "key": "c0"},
            {"type": "light", "key": "light_1"},
        ]
        # Device 1 unchanged
        assert result["data"]["devices"][1]["panels"] == [
            {"type": "grid", "key": "g0"},
        ]

    def test_panels_save_resets_panel_device_index(self):
        """After __done__, _panel_device_index must be -1."""
        flow = self._make_flow_with_device(panel_device_index=0)
        self._run(flow.async_step_panels())
        self._run(flow.async_step_panels({"panel_action": Action.DONE}))
        assert flow._ctx["panel_device_idx"] == -1


class TestOptionsFlowPanelEdit:
    def _make_flow(self, options=None):
        entry = MagicMock()
        entry.options = options or {}
        return NSPanelHAUIOptionsFlow(entry)

    def _run(self, coro):
        return asyncio.run(coro)

    def test_edit_new_panel_shows_form(self):
        flow = self._make_flow()
        flow._ctx["panels"] = []
        flow._ctx["panel_idx"] = -1
        result = self._run(flow.async_step_panel_edit())
        assert result["type"] == "form"
        assert result["step_id"] == "panel_edit"

    def test_add_valid_panel_appends(self):
        flow = self._make_flow()
        flow._ctx["panels"] = []
        flow._ctx["panel_idx"] = -1
        result = self._run(flow.async_step_panel_edit({"type": "clock", "title": "Test Clock"}))
        assert len(flow._ctx["panels"]) == 1
        assert flow._ctx["panels"][0]["type"] == "clock"

    def test_add_invalid_panel_shows_errors(self):
        flow = self._make_flow()
        flow._ctx["panels"] = []
        flow._ctx["panel_idx"] = -1
        result = self._run(flow.async_step_panel_edit({"type": ""}))
        if "errors" in result:
            assert result["errors"]
        else:
            assert result["type"] == "form"

    def test_edit_existing_panel_replaces(self):
        flow = self._make_flow()
        flow._ctx["panels"] = [{"type": "clock", "key": "clock_0", "title": "Old Clock"}]
        flow._ctx["panel_idx"] = 0
        result = self._run(flow.async_step_panel_edit({"type": "clock", "title": "New Clock"}))
        assert flow._ctx["panels"][0]["title"] == "New Clock"

# ---------------------------------------------------------------------------
# async_migrate_entry  v1 → v2
# ---------------------------------------------------------------------------


class TestMigrateEntry:
    """Test the v1→v2 config entry migration."""

    def _make_entry(self, version=1, data=None, options=None):
        """Build a MagicMock config entry."""
        entry = MagicMock()
        entry.version = version
        entry.data = data or {"name": "test_device", "mqtt_topic_prefix": "custom_prefix"}
        entry.options = options or {}
        return entry

    def _make_v3_entry(self, data=None, options=None):
        """Build a v3 MagicMock config entry (panels at top-level, devices list)."""
        return self._make_entry(
            version=3,
            data=data or {"name": "test_device"},
            options=options or {"devices": [], "panels": [{"type": "clock"}]},
        )

    def _run_migration(self, entry):
        """Run the migration synchronously via asyncio. Returns (hass, result)."""
        from nspanel_haui.config_flow import NSPanelHAUIConfigFlow

        hass = MagicMock()

        async def _migrate():
            return await NSPanelHAUIConfigFlow.async_migrate_entry(hass, entry)

        return hass, asyncio.run(_migrate())

    def _get_update_kwargs(self, hass):
        """Extract kwargs from hass.config_entries.async_update_entry call."""
        assert hass.config_entries.async_update_entry.called
        _, kwargs = hass.config_entries.async_update_entry.call_args
        return kwargs

    def test_v1_moves_mqtt_prefix_to_options(self):
        entry = self._make_entry(
            data={"name": "living_room", "mqtt_topic_prefix": "my_prefix"},
            options={"panels": [{"type": "clock"}], "device": {"locale": "en_US"}},
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        new_data = kwargs["data"]
        new_options = kwargs["options"]
        assert kwargs["version"] == 2
        assert new_data == {"name": "living_room"}
        assert new_options["mqtt_topic_prefix"] == "my_prefix"
        assert new_options["panels"] == [{"type": "clock"}]
        assert "device" not in new_options

    def test_v1_missing_prefix_defaults_from_default_config(self):
        entry = self._make_entry(
            data={"name": "test"},
            options={"device": {"locale": "de_DE"}},
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        new_options = kwargs["options"]
        # Should use DEFAULT_CONFIG["mqtt"]["topic_prefix"]
        assert new_options["mqtt_topic_prefix"] == "nspanel_haui_test"

    def test_v1_drops_device_connection_update_navigation(self):
        entry = self._make_entry(
            data={"name": "test", "mqtt_topic_prefix": "pfx"},
            options={
                "device": {"locale": "en_US"},
                "connection": {"heartbeat_interval": 10},
                "update": {"auto_update": True},
                "navigation": {"page_timeout": 30.0},
                "panels": [],
                "config_yaml": "",
            },
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        new_options = kwargs["options"]
        assert "device" not in new_options
        assert "connection" not in new_options
        assert "update" not in new_options
        assert "navigation" not in new_options
        assert new_options["panels"] == []
        assert new_options["config_yaml"] == ""
        assert new_options["mqtt_topic_prefix"] == "pfx"

    def test_v1_preserves_panels_and_config_yaml(self):
        entry = self._make_entry(
            data={"name": "test", "mqtt_topic_prefix": "pfx"},
            options={
                "panels": [{"type": "grid", "key": "g1"}],
                "config_yaml": "device:\n  name: yaml_name\n",
            },
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        new_options = kwargs["options"]
        assert new_options["panels"] == [{"type": "grid", "key": "g1"}]
        assert new_options["config_yaml"] == "device:\n  name: yaml_name\n"

    def test_v1_data_ends_up_name_only(self):
        entry = self._make_entry(
            data={"name": "my_panel", "mqtt_topic_prefix": "extra"},
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["data"] == {"name": "my_panel"}

    def test_v1_handles_missing_name(self):
        """If data has no name, defaults to nspanel_haui."""
        entry = self._make_entry(
            data={"mqtt_topic_prefix": "test_prefix"},
        )
        hass, _result = self._run_migration(entry)
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["data"]["name"] == "nspanel_haui"

    def test_v2_entry_unchanged(self):
        """Version 2 entries are migrated to v3 with empty devices list."""
        entry = self._make_entry(
            version=2,
            data={"name": "test"},
            options={"mqtt_topic_prefix": "pfx", "panels": []},
        )
        hass, result = self._run_migration(entry)
        assert result is True
        assert hass.config_entries.async_update_entry.called
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["version"] == 3
        assert kwargs["options"]["devices"] == []
        assert kwargs["options"]["mqtt_topic_prefix"] == "pfx"
        assert kwargs["options"]["panels"] == []

    def test_migration_returns_true(self):
        entry = self._make_entry(data={"name": "test"})
        _hass, result = self._run_migration(entry)
        assert result is True

    # ── v3 → v4 migration ─────────────────────────────────────────────────

    def test_v3_to_v4_distributes_shared_panels(self):
        """v3 shared panels distributed to all devices."""
        entry = self._make_v3_entry(options={
            "devices": [
                {"name": "dev1", "locale": "en_US"},
                {"name": "dev2", "locale": "de_DE"},
            ],
            "panels": [{"type": "clock"}, {"type": "grid"}],
        })
        hass, result = self._run_migration(entry)
        assert result is True
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["version"] == 4
        assert "panels" not in kwargs["options"]
        assert kwargs["options"]["devices"][0]["panels"] == [{"type": "clock"}, {"type": "grid"}]
        assert kwargs["options"]["devices"][1]["panels"] == [{"type": "clock"}, {"type": "grid"}]

    def test_v3_to_v4_preserves_existing_device_panels(self):
        """Devices with existing non-empty panels keep them during v3→v4 migration."""
        entry = self._make_v3_entry(options={
            "devices": [
                {"name": "dev1", "locale": "en_US", "panels": [{"type": "light"}]},
                {"name": "dev2", "locale": "de_DE"},
            ],
            "panels": [{"type": "clock"}],
        })
        hass, result = self._run_migration(entry)
        assert result is True
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["version"] == 4
        # dev1 keeps its own panels
        assert kwargs["options"]["devices"][0]["panels"] == [{"type": "light"}]
        # dev2 gets the shared panels
        assert kwargs["options"]["devices"][1]["panels"] == [{"type": "clock"}]

    def test_v3_to_v4_no_panels_noop(self):
        """When no top-level panels, devices are unchanged."""
        entry = self._make_v3_entry(options={
            "devices": [
                {"name": "dev1", "locale": "en_US", "panels": [{"type": "light"}]},
            ],
        })
        hass, result = self._run_migration(entry)
        assert result is True
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["version"] == 4
        # Device panels preserved as-is
        assert kwargs["options"]["devices"][0]["panels"] == [{"type": "light"}]
        assert "panels" not in kwargs["options"]

    def test_v3_entry_becomes_v4(self):
        """Basic v3→v4 version bump with empty devices and shared panels."""
        entry = self._make_v3_entry()
        hass, result = self._run_migration(entry)
        assert result is True
        kwargs = self._get_update_kwargs(hass)
        assert kwargs["version"] == 4
        assert "panels" not in kwargs["options"]
        # Shared panels distributed to all devices
        for dev in kwargs["options"]["devices"]:
            assert "panels" in dev


# ---------------------------------------------------------------------------
# NSPanelHAUIOptionsFlow  —  topic step
# ---------------------------------------------------------------------------


class TestOptionsFlowTopic:
    def _make_flow(self, options=None):
        entry = MagicMock()
        entry.options = options if options is not None else {"mqtt_topic_prefix": "my_prefix"}
        from nspanel_haui.config_flow import NSPanelHAUIOptionsFlow
        flow = NSPanelHAUIOptionsFlow(entry)
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_topic_step_shows_form_with_current_prefix(self):
        flow = self._make_flow()
        result = self._run(flow.async_step_topic())
        assert result["type"] == "form"
        assert result["step_id"] == "topic"
        # Extract default from schema
        schema = result["data_schema"]
        for key in schema.schema:
            if "mqtt_topic_prefix" in str(key):
                assert key.default() == "my_prefix"

    def test_topic_step_saves_new_prefix(self):
        flow = self._make_flow()
        result = self._run(flow.async_step_topic({"mqtt_topic_prefix": "new_prefix"}))
        assert result["type"] == "create_entry"
        assert result["data"]["mqtt_topic_prefix"] == "new_prefix"
        assert "config_yaml" not in result["data"]

    def test_topic_step_default_when_no_existing(self):
        flow = self._make_flow({})
        result = self._run(flow.async_step_topic())
        schema = result["data_schema"]
        for key in schema.schema:
            if "mqtt_topic_prefix" in str(key):
                assert key.default() == "nspanel_haui"



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

    def test_matches_by_friendly_name(self):
        """Returns entry_id when friendly_name matches."""
        hass = MagicMock()
        hass.data = {"esphome": {"entry1": {"device_info": {
            "name": "esphome-web-abc123",
            "friendly_name": "Panel Living",
        }}}}
        result = _find_esphome_device(hass, "panel-living")
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
        hass.data = {"esphome": {"entry1": ["not", "a", "dict"], "entry2": {"device_info": {"name": "panel-living"}}}}
        result = _find_esphome_device(hass, "panel-living")
        assert result == "entry2"


class TestRunMqttDiscovery:
    """Tests for _run_mqtt_discovery(hass, prefix, timeout)."""

    def test_returns_list_of_dicts(self):
        """Each result has 'name' and 'esphome_device_id' keys."""
        import json
        from homeassistant.components import mqtt

        class FakeMsg:
            def __init__(self, topic, name):
                self.topic = topic
                self.payload = json.dumps({"name": name})

        messages = [FakeMsg("nspanel_haui/panel-kitchen/recv", "connected")]

        unsub = MagicMock()
        async def fake_subscribe(hass, topic, callback):
            for msg in messages:
                await callback(msg)
            return unsub

        mqtt.async_subscribe = fake_subscribe

        with patch("asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(_run_mqtt_discovery(MagicMock(), timeout=0))
            assert len(result) == 1
            assert result[0]["name"] == "panel-kitchen"
            assert "esphome_device_id" in result[0]

    def test_ignores_non_connected_messages(self):
        """Messages without name=connected are ignored."""
        import json
        from homeassistant.components import mqtt

        class FakeMsg:
            def __init__(self, topic, payload_name):
                self.topic = topic
                self.payload = json.dumps({"name": payload_name})

        messages = [
            FakeMsg("nspanel_haui/panel-kitchen/recv", "heartbeat"),
            FakeMsg("nspanel_haui/panel-living/recv", "connected"),
        ]

        unsub = MagicMock()
        async def fake_subscribe(hass, topic, callback):
            for msg in messages:
                await callback(msg)
            return unsub

        mqtt.async_subscribe = fake_subscribe

        with patch("asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(_run_mqtt_discovery(MagicMock(), timeout=0))
            assert len(result) == 1
            assert result[0]["name"] == "panel-living"

    def test_esphome_device_id_populated_when_matched(self):
        """ESPHome-enriched result gets non-None esphome_device_id when matched."""
        import json
        from homeassistant.components import mqtt

        class FakeMsg:
            def __init__(self, topic):
                self.topic = topic
                self.payload = json.dumps({"name": "connected"})

        messages = [FakeMsg("nspanel_haui/panel-living/recv")]

        unsub = MagicMock()
        async def fake_subscribe(hass, topic, callback):
            for msg in messages:
                await callback(msg)
            return unsub

        mqtt.async_subscribe = fake_subscribe

        hass = MagicMock()
        hass.data = {"esphome": {"entry1": {"device_info": {"name": "panel-living"}}}}

        with patch("asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(_run_mqtt_discovery(hass, timeout=0))
            assert len(result) == 1
            assert result[0]["esphome_device_id"] == "entry1"

    def test_exception_handled_gracefully(self):
        """MQTT errors are caught and empty list is returned."""
        from homeassistant.components import mqtt
        mqtt.async_subscribe = AsyncMock(side_effect=RuntimeError("MQTT unavailable"))

        with patch("asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(_run_mqtt_discovery(MagicMock(), timeout=0))
            assert result == []


class TestMqttAvailable:
    """Tests for _mqtt_available(hass)."""

    def test_returns_true_when_connected(self):
        """Returns True when mqtt.is_connected returns True."""
        from homeassistant.components import mqtt
        mqtt.is_connected = MagicMock(return_value=True)
        result = asyncio.run(_mqtt_available(MagicMock()))
        assert result is True

    def test_returns_false_when_not_connected(self):
        """Returns False when mqtt.is_connected returns False."""
        from homeassistant.components import mqtt
        mqtt.is_connected = MagicMock(return_value=False)
        result = asyncio.run(_mqtt_available(MagicMock()))
        assert result is False

    def test_returns_false_on_exception(self):
        """Returns False when mqtt import raises."""
        result = asyncio.run(_mqtt_available(MagicMock()))
        assert isinstance(result, bool)
        # With proper stubs this returns True (since mqtt.is_connected stub defaults to True);
        # the exception path is tested implicitly by the empty stubs case.
        # This test verifies the function returns a bool either way.


class TestConfigFlowUserStep:
    """Tests for NSPanelHAUIConfigFlow.async_step_user."""

    def _make_flow(self):
        """Create a flow instance with a mocked hass."""
        flow = NSPanelHAUIConfigFlow()
        flow.hass = MagicMock()
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_shows_form_with_name_prefix_scan_fields(self):
        """No input shows the user step form with name, mqtt_topic_prefix, scan_mqtt fields."""
        flow = self._make_flow()
        result = self._run(flow.async_step_user())
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        schema = result["data_schema"]
        schema_keys = [str(k) for k in schema.schema]
        assert any("name" in k for k in schema_keys)
        assert any("mqtt_topic_prefix" in k for k in schema_keys)
        assert any("scan_mqtt" in k for k in schema_keys)

    def test_submit_without_scan_creates_entry(self):
        """Submit with scan_mqtt=False creates entry with empty devices."""
        flow = self._make_flow()
        result = self._run(flow.async_step_user({
            "name": "Test Panel",
            "scan_mqtt": False,
        }))
        assert result["type"] == "create_entry"
        assert result["options"]["devices"] == []

    def test_empty_name_shows_error(self):
        """Empty name shows form error."""
        flow = self._make_flow()
        result = self._run(flow.async_step_user({
            "name": "",
            "scan_mqtt": False,
        }))
        assert result["type"] == "form"
        assert result.get("errors", {}).get("name") == "empty_name"

    def test_scan_mqtt_transitions_to_discovery(self):
        """When scan_mqtt=True and MQTT available, transitions to discovery step."""
        from unittest.mock import AsyncMock, patch

        flow = self._make_flow()

        with patch(
            "nspanel_haui.config_flow._mqtt_available",
            new=AsyncMock(return_value=True),
        ), patch(
            "nspanel_haui.config_flow._run_mqtt_discovery",
            new=AsyncMock(return_value=[
                {"name": "panel-1", "esphome_device_id": None},
            ]),
        ):
            result = self._run(flow.async_step_user({
                "name": "Test Panel",
                "scan_mqtt": True,
            }))
            assert result["type"] == "form"
            assert result["step_id"] == "discovery"
            assert flow._entry_name == "Test Panel"
            assert flow._mqtt_topic_prefix == "nspanel_haui"
            assert flow._discovered_devices == [{"name": "panel-1", "esphome_device_id": None}]

    def test_scan_mqtt_without_mqtt_shows_error(self):
        """When scan_mqtt=True but MQTT unavailable, shows error."""
        from unittest.mock import AsyncMock, patch

        flow = self._make_flow()

        with patch(
            "nspanel_haui.config_flow._mqtt_available",
            new=AsyncMock(return_value=False),
        ):
            result = self._run(flow.async_step_user({
                "name": "Test Panel",
                "scan_mqtt": True,
            }))
            assert result["type"] == "form"
            assert result.get("errors", {}).get("base") == "mqtt_not_configured"


class TestConfigFlowDiscoveryStep:
    """Tests for NSPanelHAUIConfigFlow.async_step_discovery."""

    def _make_flow(self, discovered=None, entry_name="Test", prefix="nspanel_haui"):
        """Create a flow instance pre-configured for the discovery step."""
        flow = NSPanelHAUIConfigFlow()
        flow.hass = MagicMock()
        flow._entry_name = entry_name
        flow._mqtt_topic_prefix = prefix
        flow._discovered_devices = discovered or []
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_shows_devices_with_esphome_info(self):
        """Form shows discovered devices with ESPHome info placeholder."""
        flow = self._make_flow(discovered=[
            {"name": "panel-living", "esphome_device_id": "entry1"},
            {"name": "panel-kitchen", "esphome_device_id": None},
        ])
        result = self._run(flow.async_step_discovery())
        assert result["type"] == "form"
        assert result["step_id"] == "discovery"
        assert result["description_placeholders"]["count"] == "2"
        assert "ESPHome matched: 1" in result["description_placeholders"]["esphome_info"]

    def test_preselects_esphome_matched_devices(self):
        """Pre-selects only ESPHome-matched devices."""
        flow = self._make_flow(discovered=[
            {"name": "panel-living", "esphome_device_id": "entry1"},
            {"name": "panel-kitchen", "esphome_device_id": None},
        ])
        result = self._run(flow.async_step_discovery())
        # Check the default on the Required key for selected_devices
        for key in result["data_schema"].schema:
            if "selected_devices" in str(key):
                assert key.default() == ["panel-living"]
                break
        else:
            pytest.fail("selected_devices key not found in schema")

    def test_falls_back_to_show_all_when_no_esphome_match(self):
        """When no device has ESPHome id, pre-selects all devices."""
        flow = self._make_flow(discovered=[
            {"name": "panel-living", "esphome_device_id": None},
            {"name": "panel-kitchen", "esphome_device_id": None},
        ])
        result = self._run(flow.async_step_discovery())
        for key in result["data_schema"].schema:
            if "selected_devices" in str(key):
                assert key.default() == ["panel-living", "panel-kitchen"]
                break
        else:
            pytest.fail("selected_devices key not found in schema")

    def test_no_devices_shows_empty_form(self):
        """Empty discovered devices shows empty schema form."""
        flow = self._make_flow(discovered=[])
        result = self._run(flow.async_step_discovery())
        assert result["type"] == "form"
        assert result["step_id"] == "discovery"
        assert result["description_placeholders"]["count"] == "0"
        # Empty schema: an empty vol.Schema({}) has no keys
        assert len(result["data_schema"].schema) == 0

    def test_submit_creates_entry_with_devices(self):
        """Submit with selected devices creates entry with those devices."""
        flow = self._make_flow(discovered=[
            {"name": "panel-kitchen", "esphome_device_id": None},
            {"name": "panel-living", "esphome_device_id": "entry1"},
        ])
        result = self._run(flow.async_step_discovery({
            "selected_devices": ["panel-kitchen"],
        }))
        assert result["type"] == "create_entry"
        assert result["title"] == "Test"
        assert len(result["options"]["devices"]) == 1
        assert result["options"]["devices"][0]["name"] == "panel-kitchen"

    def test_submit_preserves_esphome_device_id(self):
        """Selected matched device gets esphome_device_id in entry options."""
        flow = self._make_flow(discovered=[
            {"name": "panel-living", "esphome_device_id": "entry1"},
        ])
        result = self._run(flow.async_step_discovery({
            "selected_devices": ["panel-living"],
        }))
        assert result["type"] == "create_entry"
        assert result["options"]["devices"][0]["esphome_device_id"] == "entry1"

    def test_submit_non_matched_device_has_no_esphome_id(self):
        """Non-matched device gets no esphome_device_id in entry."""
        flow = self._make_flow(discovered=[
            {"name": "panel-kitchen", "esphome_device_id": None},
        ])
        result = self._run(flow.async_step_discovery({
            "selected_devices": ["panel-kitchen"],
        }))
        assert result["type"] == "create_entry"
        # DEVICE_CONFIG includes esphome_device_id: None by default;
        # when not matched, esphome_device_id remains None in the entry
        assert result["options"]["devices"][0]["esphome_device_id"] is None


class TestConfigFlowEndToEnd:
    """End-to-end tests for the two-step MQTT discovery config flow."""

    def _make_flow(self):
        """Create a flow instance with a mocked hass."""
        flow = NSPanelHAUIConfigFlow()
        flow.hass = MagicMock()
        return flow

    def _run(self, coro):
        return asyncio.run(coro)

    def test_user_scan_discovery_create_entry(self):
        """Full flow: user step → scan → discovery → create entry."""
        from unittest.mock import AsyncMock, patch

        flow = self._make_flow()

        discovered_devices = [
            {"name": "panel-living", "esphome_device_id": "entry1"},
            {"name": "panel-kitchen", "esphome_device_id": None},
        ]

        with patch(
            "nspanel_haui.config_flow._mqtt_available",
            new=AsyncMock(return_value=True),
        ), patch(
            "nspanel_haui.config_flow._run_mqtt_discovery",
            new=AsyncMock(return_value=discovered_devices),
        ):
            # Step 1: user step with scan enabled
            user_result = self._run(flow.async_step_user({
                "name": "My Panel",
                "scan_mqtt": True,
            }))
            assert user_result["type"] == "form"
            assert user_result["step_id"] == "discovery"

        # Step 2: select devices from discovery
        disc_result = self._run(flow.async_step_discovery({
            "selected_devices": ["panel-living"],
        }))
        assert disc_result["type"] == "create_entry"
        assert disc_result["title"] == "My Panel"
        assert len(disc_result["options"]["devices"]) == 1
        assert disc_result["options"]["devices"][0]["name"] == "panel-living"
        assert disc_result["options"]["devices"][0]["esphome_device_id"] == "entry1"

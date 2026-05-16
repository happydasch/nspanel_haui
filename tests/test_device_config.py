"""Tests for haui/device_config.py - constants, helpers, and DeviceConfig class."""

from __future__ import annotations

import copy
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# The device_config module has no HA dependencies, so we can import it
# directly.  conftest.py adds custom_components/ to sys.path so the
# package is available as ``nspanel_haui``.
# ---------------------------------------------------------------------------
from nspanel_haui.haui.device_config import (  # noqa: E402
    DEVICE_CONFIG,
    DEVICE_CONFIG_FIELDS,
    LOCALE_OPTIONS,
    DeviceConfig,
    _apply_panel_store,
    _find_store_device,
    _merge_store_fields,
    _populate_devices_from_store,
    _validate_config,
)

# ============================================================================
# DEVICE_CONFIG template integrity
# ============================================================================


def test_device_config_has_all_required_keys() -> None:
    """Every key needed at runtime is present in DEVICE_CONFIG."""
    required = {
        "name",
        "panels",
        "esphome_device_id",
        "enabled",
        "locale",
        "button_left_entity",
        "button_right_entity",
        "home_panel",
        "sleep_panel",
        "wakeup_panel",
        "show_home_button",
        "show_sleep_button",
        "show_notifications_button",
        "log_items",
        "debug_level",
        "home_on_wakeup",
        "home_on_first_touch",
        "home_only_when_on",
        "home_on_button_toggle",
        "return_to_home_after_seconds",
        "always_return_to_home",
        "hub_idle_timeout",
        "use_relay_left",
        "use_relay_right",
        "sound_on_startup",
        "sound_on_notification",
    }
    assert set(DEVICE_CONFIG.keys()) == required


def test_device_config_fields_match_template() -> None:
    """DEVICE_CONFIG_FIELDS is a subset of DEVICE_CONFIG keys."""
    dc_keys = set(DEVICE_CONFIG.keys())
    for field in DEVICE_CONFIG_FIELDS:
        assert field in dc_keys, f"{field} not in DEVICE_CONFIG"


def test_device_config_fields_excludes_identity() -> None:
    """DEVICE_CONFIG_FIELDS excludes name, esphome_device_id, and panels."""
    assert "name" not in DEVICE_CONFIG_FIELDS
    assert "esphome_device_id" not in DEVICE_CONFIG_FIELDS
    assert "panels" not in DEVICE_CONFIG_FIELDS


# ============================================================================
# LOCALE_OPTIONS
# ============================================================================


def test_locale_options_format() -> None:
    """Each entry is a (code, label) tuple."""
    assert len(LOCALE_OPTIONS) >= 4
    for code, label in LOCALE_OPTIONS:
        assert isinstance(code, str)
        assert isinstance(label, str)
        assert "_" in code  # e.g. "en_US"


# ============================================================================
# DeviceConfig accessor
# ============================================================================


def test_device_config_getters() -> None:
    data = {
        "name": "test-device",
        "debug_level": 2,
        "enabled": False,
    }
    dc = DeviceConfig(data)
    assert dc.name == "test-device"
    assert dc.debug_level == 2
    assert dc.enabled is False


def test_device_config_defaults() -> None:
    """Missing keys return sensible defaults."""
    dc = DeviceConfig({})
    assert dc.name == ""
    assert dc.locale == "en_US"
    assert dc.enabled is True
    assert dc.debug_level == 0
    assert dc.log_items is False
    assert dc.show_home_button is False
    assert dc.show_notifications_button is True
    assert dc.use_relay_left is True
    assert dc.use_relay_right is True
    assert dc.sound_on_startup is True
    assert dc.sound_on_notification is True
    assert dc.home_on_first_touch is True
    assert dc.home_on_wakeup is False
    assert dc.home_only_when_on is False
    assert dc.home_on_button_toggle is False
    assert dc.always_return_to_home is False
    assert dc.return_to_home_after_seconds == 0
    assert dc.home_panel == ""
    assert dc.sleep_panel == ""
    assert dc.wakeup_panel == ""
    assert dc.button_left_entity == ""
    assert dc.button_right_entity == ""
    assert dc.esphome_device_id == ""
    assert dc.panels == []


def test_device_config_setters() -> None:
    dc = DeviceConfig({})
    dc.name = "new-name"
    dc.debug_level = 3
    dc.enabled = False
    dc.show_home_button = True
    assert dc.name == "new-name"
    assert dc.debug_level == 3
    assert dc.enabled is False
    assert dc.show_home_button is True


def test_device_config_setters_affect_underlying_dict() -> None:
    data: dict[str, Any] = {}
    dc = DeviceConfig(data)
    dc.name = "mutated"
    dc.log_items = True
    assert data["name"] == "mutated"
    assert data["log_items"] is True


def test_device_config_as_dict() -> None:
    data = {"name": "test", "log_items": True}
    dc = DeviceConfig(data)
    result = dc.as_dict()
    assert result == data
    # Shallow copy: mutate result, data unchanged
    result["extra"] = 1
    assert "extra" not in data


def test_device_config_repr() -> None:
    dc = DeviceConfig({"name": "my-device"})
    assert "DeviceConfig" in repr(dc)
    assert "my-device" in repr(dc)

    dc2 = DeviceConfig({})
    assert "?" in repr(dc2)  # fallback name


# ============================================================================
# _validate_config
# ============================================================================


def _make_valid_config() -> dict[str, Any]:
    """Return a minimal valid config dict for _validate_config."""
    from nspanel_haui.haui.mapping.const import DEFAULT_CONFIG

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["device"]["name"] = "test"
    cfg["devices"] = [copy.deepcopy(DEVICE_CONFIG)]
    cfg["devices"][0]["name"] = "test"
    return cfg


def test_validate_passes_on_valid_config() -> None:
    cfg = _make_valid_config()
    _validate_config(cfg)  # should not raise


def test_validate_catches_missing_top_level_key() -> None:
    cfg = _make_valid_config()
    del cfg["device"]
    with pytest.raises(ValueError, match="device"):
        _validate_config(cfg)


def test_validate_catches_none_value_in_device() -> None:
    cfg = _make_valid_config()
    cfg["device"]["name"] = None
    with pytest.raises(ValueError, match="device.name.*None"):
        _validate_config(cfg)


def test_validate_catches_missing_device_key() -> None:
    cfg = _make_valid_config()
    del cfg["devices"][0]["name"]
    with pytest.raises(ValueError, match="devices\\[0\\]\\.name"):
        _validate_config(cfg)


def test_validate_catches_none_value_in_device_entry() -> None:
    cfg = _make_valid_config()
    cfg["devices"][0]["name"] = None
    with pytest.raises(ValueError, match="devices\\[0\\]\\.name.*None"):
        _validate_config(cfg)


def test_validate_catches_wrong_type_for_dict_section() -> None:
    cfg = _make_valid_config()
    cfg["connection"] = "not-a-dict"
    with pytest.raises(ValueError, match="connection.*expected dict"):
        _validate_config(cfg)


def test_validate_reports_all_missing_keys() -> None:
    cfg = _make_valid_config()
    del cfg["device"]["name"]
    del cfg["devices"][0]["name"]
    with pytest.raises(ValueError) as exc_info:
        _validate_config(cfg)
    msg = str(exc_info.value)
    assert "device.name" in msg
    assert "devices[0].name" in msg


# ============================================================================
# _find_store_device
# ============================================================================


def test_find_store_device_exact_match() -> None:
    store = {"dev-a": {"name": "dev-a"}}
    assert _find_store_device(store, "dev-a") == {"name": "dev-a"}


def test_find_store_device_case_insensitive() -> None:
    store = {"Dev-A": {"name": "Dev-A"}}
    assert _find_store_device(store, "dev-a") == {"name": "Dev-A"}


def test_find_store_device_not_found() -> None:
    store = {"dev-a": {"name": "dev-a"}}
    assert _find_store_device(store, "dev-b") is None


def test_find_store_device_empty_store() -> None:
    assert _find_store_device({}, "anything") is None


# ============================================================================
# _merge_store_fields
# ============================================================================


def test_merge_store_fields_copies_present() -> None:
    source = {"a": 1, "b": 2, "c": 3}
    target = {"a": 0}
    _merge_store_fields(source, target, ["a", "b"])
    assert target == {"a": 1, "b": 2}


def test_merge_store_fields_skips_missing() -> None:
    source = {"a": 1}
    target = {"a": 0, "b": 0}
    _merge_store_fields(source, target, ["a", "b", "c"])
    assert target == {"a": 1, "b": 0}  # b not in source, c not in source


# ============================================================================
# _populate_devices_from_store
# ============================================================================


def test_populate_when_empty() -> None:
    cfg: dict[str, Any] = {}
    store = {"dev-a": {"panels": [{"type": "grid"}], "config": {"log_items": True}}}
    _populate_devices_from_store(cfg, store, ["log_items"])
    assert cfg["devices"] == [{"name": "dev-a", "panels": [{"type": "grid"}], "log_items": True}]


def test_populate_skips_when_devices_exist() -> None:
    cfg = {"devices": [{"name": "existing"}]}
    store = {"dev-a": {"panels": [{"type": "grid"}]}}
    _populate_devices_from_store(cfg, store, [])
    assert cfg["devices"] == [{"name": "existing"}]  # unchanged


def test_populate_empty_store() -> None:
    cfg: dict[str, Any] = {}
    _populate_devices_from_store(cfg, {}, [])
    assert cfg["devices"] == []  # devices key created but empty


# ============================================================================
# _apply_panel_store
# ============================================================================


def test_apply_panel_store_merges_panels() -> None:
    cfg = {"devices": [{"name": "dev-a", "panels": [{"type": "old"}]}]}
    store = {"dev-a": {"panels": [{"type": "grid"}, {"type": "clock"}]}}
    _apply_panel_store(cfg, store, [])
    assert cfg["devices"][0]["panels"] == [{"type": "grid"}, {"type": "clock"}]


def test_apply_panel_store_applies_config_fields() -> None:
    cfg = {"device": {}, "devices": [{"name": "dev-a"}]}
    store = {"dev-a": {"panels": [], "config": {"log_items": True, "debug_level": 3}}}
    _apply_panel_store(cfg, store, ["log_items", "debug_level"])
    # Device entry gets the fields
    assert cfg["devices"][0]["log_items"] is True
    assert cfg["devices"][0]["debug_level"] == 3
    # cfg["device"] also gets the fields (last-write-wins)
    assert cfg["device"]["log_items"] is True
    assert cfg["device"]["debug_level"] == 3


def test_apply_panel_store_skips_unknown_device() -> None:
    cfg = {"devices": [{"name": "dev-a"}]}
    store = {"dev-b": {"panels": [{"type": "grid"}]}}
    _apply_panel_store(cfg, store, [])
    panels = cfg["devices"][0].get("panels")
    assert "panels" not in cfg["devices"][0] or panels != [{"type": "grid"}]

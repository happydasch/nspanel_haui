"""The hub-wide automatic update policy and how a device follows or overrides it."""

from __future__ import annotations

import pytest

import custom_components.nspanel_haui as nspanel_haui
from custom_components.nspanel_haui.haui.config_models import validate_update_policy
from custom_components.nspanel_haui.haui.mapping.const import (
    DEFAULT_CONFIG,
    UPDATE_POLICY_DEFAULTS,
    UPDATE_POLICY_FIELDS,
)
from custom_components.nspanel_haui.hub.storage import empty_store, migrate_device_config_keys


def _config(store: dict, device: str = "kitchen") -> dict:
    return nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}, {"name": "office"}]},
        store,
        device_name=device,
    )


def test_policy_defaults():
    assert UPDATE_POLICY_DEFAULTS == {
        "firmware_auto_update": False,
        "auto_install": True,
        "install_delay": 600,
        "max_attempts": 3,
        "retry_interval": 3600,
    }
    assert set(UPDATE_POLICY_FIELDS) == set(UPDATE_POLICY_DEFAULTS)


def test_device_update_defaults_follow_the_hub():
    update = DEFAULT_CONFIG["update"]

    assert update["policy_override"] is False
    assert update["skipped_firmware_version"] == ""
    for field, value in UPDATE_POLICY_DEFAULTS.items():
        assert update[field] == value


def test_empty_store_has_no_policy_of_its_own():
    assert empty_store()["update_policy"] == {}


def test_a_device_with_its_own_auto_update_keeps_it_as_an_override():
    config = {"update": {"firmware_auto_update": True}}

    assert migrate_device_config_keys(config) is True
    assert config["update"]["policy_override"] is True


def test_a_device_with_only_a_channel_follows_the_hub():
    config = {"update": {"firmware_update_channel": "dev"}}

    assert migrate_device_config_keys(config) is False
    assert "policy_override" not in config["update"]


def test_the_migration_runs_once():
    config = {"update": {"firmware_auto_update": False, "policy_override": False}}

    assert migrate_device_config_keys(config) is False
    assert config["update"]["policy_override"] is False


def test_a_following_device_takes_the_hub_policy():
    store = {
        "update_policy": {"max_attempts": 5, "firmware_auto_update": True},
        "devices": {"kitchen": {"config": {"update": {"firmware_update_channel": "dev"}}}},
    }

    update = _config(store)["update"]

    assert update["max_attempts"] == 5
    assert update["firmware_auto_update"] is True
    assert update["install_delay"] == 600
    assert update["firmware_update_channel"] == "dev"


def test_an_overriding_device_keeps_its_own_policy():
    store = {
        "update_policy": {"max_attempts": 5, "firmware_auto_update": True},
        "devices": {
            "kitchen": {
                "config": {
                    "update": {
                        "policy_override": True,
                        "max_attempts": 2,
                        "firmware_auto_update": False,
                    }
                }
            }
        },
    }

    update = _config(store)["update"]

    assert update["max_attempts"] == 2
    assert update["firmware_auto_update"] is False


def test_a_following_device_ignores_its_stale_policy_values():
    store = {
        "update_policy": {"max_attempts": 5},
        "devices": {
            "kitchen": {"config": {"update": {"policy_override": False, "max_attempts": 2}}}
        },
    }

    assert _config(store)["update"]["max_attempts"] == 5


def test_validate_update_policy_fills_the_defaults():
    assert validate_update_policy({"max_attempts": 4}) == {
        **UPDATE_POLICY_DEFAULTS,
        "max_attempts": 4,
    }


@pytest.mark.parametrize(
    "policy",
    [
        {"max_attempts": 0},
        {"max_attempts": 11},
        {"install_delay": -1},
        {"install_delay": 86401},
        {"retry_interval": 299},
        {"retry_interval": 604801},
        {"unknown": True},
    ],
)
def test_validate_update_policy_refuses_out_of_range_values(policy):
    with pytest.raises(ValueError):
        validate_update_policy(policy)

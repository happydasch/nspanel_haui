"""Update settings belong to each device; the hub-wide policy of the 0.5.0 dev builds is migrated."""

from __future__ import annotations

import pytest

import custom_components.nspanel_haui as nspanel_haui
from custom_components.nspanel_haui.haui.config_models import validate_device_config
from custom_components.nspanel_haui.hub.storage import empty_store, migrate_hub_update_policy

HUB_POLICY = {
    "firmware_auto_update": True,
    "auto_install": True,
    "install_delay": 300,
    "max_attempts": 5,
    "retry_interval": 3600,
}


def _store(update: dict | None, policy: dict | None = HUB_POLICY) -> dict:
    config = {} if update is None else {"update": update}
    store = {"version": 1, "devices": {"kitchen": {"config": config, "panels": []}}}
    if policy is not None:
        store["update_policy"] = dict(policy)
    return store


def _update(store: dict) -> dict:
    return store["devices"]["kitchen"]["config"].get("update", {})


def test_a_new_store_has_no_hub_policy():
    assert "update_policy" not in empty_store()


def test_a_device_that_followed_the_hub_takes_its_values():
    store = _store({"firmware_update_channel": "dev"})

    assert migrate_hub_update_policy(store) is True

    assert "update_policy" not in store
    assert _update(store) == {"firmware_update_channel": "dev", **HUB_POLICY}


def test_a_device_without_update_settings_takes_the_hub_values():
    store = _store(None)

    assert migrate_hub_update_policy(store) is True

    assert _update(store) == HUB_POLICY


def test_a_device_that_overrode_the_hub_keeps_its_own_values():
    store = _store({"policy_override": True, "max_attempts": 2, "firmware_auto_update": False})

    assert migrate_hub_update_policy(store) is True

    assert _update(store) == {"max_attempts": 2, "firmware_auto_update": False}


def test_a_following_device_drops_its_stale_values():
    store = _store({"policy_override": False, "max_attempts": 2}, policy={})

    assert migrate_hub_update_policy(store) is True

    assert _update(store) == {}


def test_a_store_from_before_the_hub_policy_is_left_alone():
    store = _store({"firmware_auto_update": True, "max_attempts": 2}, policy=None)

    assert migrate_hub_update_policy(store) is False

    assert _update(store) == {"firmware_auto_update": True, "max_attempts": 2}


def test_the_migration_runs_once():
    store = _store({"firmware_update_channel": "dev"})
    migrate_hub_update_policy(store)

    assert migrate_hub_update_policy(store) is False


def test_a_device_runs_with_its_own_stored_settings():
    store = _store({"firmware_update_channel": "dev"})
    migrate_hub_update_policy(store)

    update = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]}, store, device_name="kitchen"
    )["update"]

    assert update["max_attempts"] == 5
    assert update["firmware_auto_update"] is True
    assert update["firmware_update_channel"] == "dev"
    assert "policy_override" not in update


@pytest.mark.parametrize(
    "update",
    [
        {"max_attempts": 0},
        {"max_attempts": 11},
        {"install_delay": -1},
        {"install_delay": 86401},
        {"retry_interval": 299},
        {"retry_interval": 604801},
    ],
)
def test_out_of_range_automatic_install_settings_are_refused(update):
    with pytest.raises(ValueError):
        validate_device_config({"update": update})

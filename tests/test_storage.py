"""Panel store: pre-stable device-config key migration.

The stable release renamed several device-config keys (``sleep_panel`` →
``idle_panel``, ``show_sleep_button`` → ``show_idle_button``,
``use_auto_sleeping`` → ``use_auto_display_off``, ``timeout_sleep`` →
``timeout_display_off``).  The runtime reads only the new names, so a store
that still holds the legacy keys silently fell back to defaults — most
visibly an unset ``idle_panel`` that disabled the idle page and hid the
idle button.  ``PanelStorage.load`` migrates those keys in place.
"""

import sys
import types
from copy import deepcopy

storage_mod = types.ModuleType("homeassistant.helpers.storage")
storage_mod.Store = object
sys.modules.setdefault("homeassistant.helpers.storage", storage_mod)

from nspanel_haui.storage import (  # noqa: E402
    DEVICE_CONFIG_KEY_RENAMES,
    PanelStorage,
    migrate_device_config_keys,
)


def test_rename_mapping_covers_all_v1_renames() -> None:
    """The mapping matches the key renames documented in docs/upgrading.md."""
    assert DEVICE_CONFIG_KEY_RENAMES == {
        "sleep_panel": "idle_panel",
        "sleep_panel_extra": "idle_panel_extra",
        "show_sleep_button": "show_idle_button",
        "use_auto_sleeping": "use_auto_display_off",
        "timeout_sleep": "timeout_display_off",
    }


def test_migrate_moves_legacy_keys_and_drops_them() -> None:
    cfg = {
        "sleep_panel": "blank",
        "show_sleep_button": True,
        "use_auto_sleeping": False,
        "timeout_sleep": 120,
    }
    assert migrate_device_config_keys(cfg) is True
    assert cfg == {
        "idle_panel": "blank",
        "show_idle_button": True,
        "use_auto_display_off": False,
        "timeout_display_off": 120,
    }
    # Idempotent on the second pass.
    assert migrate_device_config_keys(cfg) is False
    assert cfg == {
        "idle_panel": "blank",
        "show_idle_button": True,
        "use_auto_display_off": False,
        "timeout_display_off": 120,
    }


def test_migrate_never_overwrites_new_key_values() -> None:
    cfg = {"sleep_panel": "blank", "idle_panel": "clock", "timeout_sleep": 30}
    assert migrate_device_config_keys(cfg) is True
    # The explicit new-key value wins; the legacy entries are still dropped
    # (and legacy keys without a new-key twin still move across).
    assert cfg == {"idle_panel": "clock", "timeout_display_off": 30}


def test_migrate_is_a_noop_without_legacy_keys() -> None:
    cfg = {"idle_panel": "blank", "show_idle_button": True}
    assert migrate_device_config_keys(cfg) is False
    assert cfg == {"idle_panel": "blank", "show_idle_button": True}


class _FakeStore:
    """Minimal Store stand-in recording async_load/async_save round trips."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.saved: list[dict] = []

    async def async_load(self) -> dict:
        return deepcopy(self.payload)

    async def async_save(self, data: dict) -> None:
        self.saved.append(deepcopy(data))


def _make_storage(store: _FakeStore) -> PanelStorage:
    """Build a PanelStorage without touching the stubbed ``Store`` constructor."""
    ps = PanelStorage.__new__(PanelStorage)
    ps._store = store  # type: ignore[assignment]
    ps._config_entry = None
    return ps


def _load(ps: PanelStorage) -> dict:
    """Drive the async ``PanelStorage.load`` from a sync test."""
    import asyncio

    return asyncio.run(ps.load())


def test_load_migrates_legacy_keys_and_persists() -> None:
    payload = {
        "version": 1,
        "devices": {
            "Salon": {
                "config": {
                    "sleep_panel": "blank",
                    "show_sleep_button": True,
                    "use_auto_sleeping": False,
                },
                "panels": [],
            },
            "Kasia": {"config": {"idle_panel": "clock"}, "panels": []},
            "broken": {"config": None, "panels": []},
        },
    }
    store = _FakeStore(payload)
    ps = _make_storage(store)

    result = _load(ps)

    assert result["devices"]["Salon"]["config"] == {
        "idle_panel": "blank",
        "show_idle_button": True,
        "use_auto_display_off": False,
    }
    # Devices already on the new keys (or with unusable configs) are untouched.
    assert result["devices"]["Kasia"]["config"] == {"idle_panel": "clock"}
    assert result["devices"]["broken"]["config"] is None
    # The migrated payload was saved back to the store.
    assert store.saved and store.saved[-1]["devices"]["Salon"]["config"]["idle_panel"] == "blank"


def test_load_does_not_save_when_nothing_to_migrate() -> None:
    payload = {
        "version": 1,
        "devices": {"Salon": {"config": {"idle_panel": "blank"}, "panels": []}},
    }
    store = _FakeStore(payload)
    ps = _make_storage(store)

    assert _load(ps) == payload
    assert store.saved == []

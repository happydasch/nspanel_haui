"""Panel store: renamed device-config keys and persisted panel data.

The stable release renamed several idle/display settings and 0.5 merged the
gesture settings into ``gestures``. ``PanelStorage.load`` migrates both in place;
theme configuration is not migrated.
"""

import sys
import types
from copy import deepcopy

storage_mod = types.ModuleType("homeassistant.helpers.storage")
storage_mod.Store = object
sys.modules.setdefault("homeassistant.helpers.storage", storage_mod)

from custom_components.nspanel_haui.haui.device_config import DEVICE_CONFIG  # noqa: E402
from custom_components.nspanel_haui.hub.storage import (  # noqa: E402
    PanelStorage,
    empty_store,
    migrate_device_config_keys,
    normalize_device_order,
)


def test_empty_store_has_an_empty_device_order() -> None:
    assert empty_store() == {
        "version": 1,
        "device_order": [],
        "devices": {},
        "themes": {},
    }


def test_normalize_device_order_preserves_valid_order_and_appends_new_devices() -> None:
    data = {
        "device_order": ["Office", "Office", "Removed", "Kitchen"],
        "devices": {"Kitchen": {}, "Office": {}, "Bedroom": {}},
    }

    assert normalize_device_order(data) is True
    assert data["device_order"] == ["Office", "Kitchen", "Bedroom"]
    assert normalize_device_order(data) is False


def test_load_normalizes_and_persists_device_order() -> None:
    payload = {
        "version": 1,
        "devices": {
            "Kitchen": {"config": {}, "panels": []},
            "Office": {"config": {}, "panels": []},
        },
    }
    store = _FakeStore(payload)

    result = _load(_make_storage(store))

    assert result["device_order"] == ["Kitchen", "Office"]
    assert store.saved == [{**payload, "device_order": ["Kitchen", "Office"]}]


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


def test_migrate_turns_0_4_7_sequences_into_gestures_after_the_fixed_swipes() -> None:
    """0.4.7 had fixed single swipes (the defaults) and ``gesture_sequences``."""
    cfg = {
        "gesture_sequences": [
            {"sequence": ["swipe_left", "swipe_right"], "timeframe": 5, "open": "lights"}
        ]
    }
    assert migrate_device_config_keys(cfg) is True
    assert cfg == {
        "gestures": [
            *DEVICE_CONFIG["gestures"],
            {"swipes": ["swipe_left", "swipe_right"], "action": "lights", "timeframe": 5},
        ]
    }
    assert migrate_device_config_keys(cfg) is False


def test_migrate_turns_swipe_actions_into_one_swipe_gestures() -> None:
    """A swipe without an action gets no gesture, so it still does nothing."""
    cfg = {
        "swipe_actions": {
            "swipe_left": "prev_panel",
            "swipe_right": "next_panel",
            "swipe_up": "",
            "swipe_down": "lights",
        },
        "gesture_sequences": [],
    }
    assert migrate_device_config_keys(cfg) is True
    assert cfg == {
        "gestures": [
            {"swipes": ["swipe_left"], "action": "prev_panel", "timeframe": 3},
            {"swipes": ["swipe_right"], "action": "next_panel", "timeframe": 3},
            {"swipes": ["swipe_down"], "action": "lights", "timeframe": 3},
        ]
    }


def test_migrate_keeps_existing_gestures_and_drops_the_old_keys() -> None:
    gestures = [{"swipes": ["swipe_up"], "action": "lights", "timeframe": 3}]
    cfg = {
        "gestures": gestures,
        "swipe_actions": {"swipe_left": "next_panel"},
        "gesture_sequences": [],
    }
    assert migrate_device_config_keys(cfg) is True
    assert cfg == {"gestures": gestures}


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
        "device_order": ["Salon"],
        "devices": {"Salon": {"config": {"idle_panel": "blank"}, "panels": []}},
    }
    store = _FakeStore(payload)
    ps = _make_storage(store)

    assert _load(ps) == payload
    assert store.saved == []


def test_load_drops_edits_of_fixed_system_panels() -> None:
    """Only popups can be edited: a stored edit of Settings (or another fixed
    system panel) is removed on load, popup edits and user panels stay."""
    cover = {"type": "cover", "key": "popup_cover", "title": "Blinds"}
    grid = {"type": "grid", "key": "grid_0", "items": []}
    payload = {
        "version": 1,
        "devices": {
            "Salon": {
                "config": {},
                "panels": [{"type": "system_settings", "key": "sys_settings"}, cover, grid],
            },
        },
    }
    store = _FakeStore(payload)

    result = _load(_make_storage(store))

    assert result["devices"]["Salon"]["panels"] == [cover, grid]
    assert store.saved[-1]["devices"]["Salon"]["panels"] == [cover, grid]

"""Home Assistant import stubs for the code-generation scripts.

The haui package imports Home Assistant types at module import time. These
scripts run outside Home Assistant, so importing this module installs stubs.
"""

from __future__ import annotations

import sys
from importlib.machinery import ModuleSpec


def _install_ha_stubs() -> None:
    """Install a meta-path finder that stubs any homeassistant.* import on demand."""
    import types

    ha_const = types.ModuleType("homeassistant.const")
    ha_const.__path__ = []
    ha_const.__dict__.update(
        {
            "__name__": "homeassistant.const",
            "STATE_ON": "on",
            "STATE_OFF": "off",
            "STATE_HOME": "home",
            "STATE_NOT_HOME": "not_home",
            "STATE_OPEN": "open",
            "STATE_CLOSED": "closed",
            "STATE_LOCKED": "locked",
            "STATE_UNLOCKED": "unlocked",
            "STATE_UNKNOWN": "unknown",
            "STATE_UNAVAILABLE": "unavailable",
            "SERVICE_TURN_ON": "turn_on",
            "SERVICE_TURN_OFF": "turn_off",
            "SERVICE_TOGGLE": "toggle",
            "EVENT_HOMEASSISTANT_START": "homeassistant_start",
            "EVENT_STATE_CHANGED": "state_changed",
            "ATTR_ENTITY_ID": "entity_id",
            "ATTR_NAME": "name",
            "ATTR_ICON": "icon",
            "ATTR_STATE": "state",
            "CONF_NAME": "name",
            "CONF_ENTITY_ID": "entity_id",
            "CONF_DEVICE_ID": "device_id",
            "CONF_DEVICES": "devices",
            "CONF_DOMAIN": "domain",
            "PLATFORM_SCHEMA": {},
            "CONFIG_SCHEMA": {},
        }
    )

    ha = types.ModuleType("homeassistant")
    ha.const = ha_const
    ha.__path__ = []
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.const"] = ha_const

    _STUB_ATTRS: dict[str, dict[str, object]] = {
        "homeassistant.helpers.config_validation": {
            "boolean": lambda x: x,
            "string": lambda x: str(x),
            "entity_id": lambda x: str(x),
            "entity_ids": lambda xs: [str(x) for x in xs],
            "entity_domain": lambda *a: lambda x: str(x),
            "ensure_list": lambda x: x if isinstance(x, list) else [x],
            "multi_select": lambda *a: lambda x: x,
            "has_at_least_one": lambda *a: lambda x: str(x),
            "empty_config_schema": lambda d: {},
            "PLATFORM_SCHEMA": {},
            "CONFIG_SCHEMA": {},
        },
        "homeassistant.helpers.storage": {
            "Store": type("Store", (), {}),
        },
        "homeassistant.core": {
            "HomeAssistant": type("HomeAssistant", (), {}),
            "State": type("State", (), {}),
            "Event": type("Event", (), {}),
            "ServiceCall": type("ServiceCall", (), {}),
            "DOMAIN": "homeassistant",
        },
        "homeassistant.config_entries": {
            "ConfigEntry": type("ConfigEntry", (), {}),
            "ConfigFlow": type("ConfigFlow", (), {}),
            "OptionsFlow": type("OptionsFlow", (), {}),
            "CONN_CLASS_LOCAL_PUSH": "local_push",
        },
        "homeassistant.exceptions": {
            "HomeAssistantError": type("HomeAssistantError", (Exception,), {}),
        },
        "homeassistant.util.unit_system": {
            "UnitSystem": type("UnitSystem", (), {}),
        },
    }

    for mod_name, attrs in _STUB_ATTRS.items():
        parts = mod_name.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent not in sys.modules:
                parent_mod = types.ModuleType(parent)
                parent_mod.__path__ = []
                sys.modules[parent] = parent_mod
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            mod.__path__ = []
            sys.modules[mod_name] = mod
        sys.modules[mod_name].__dict__.update(attrs)

    class _HAStubFinder:
        _PREFIX = "homeassistant."

        @classmethod
        def find_spec(cls, fullname, path=None, target=None):
            if not fullname.startswith(cls._PREFIX) and fullname != "homeassistant":
                return None
            if fullname in sys.modules:
                return None
            mod = types.ModuleType(fullname)
            mod.__package__ = fullname.rpartition(".")[0]
            mod.__path__ = []
            mod.__spec__ = ModuleSpec(fullname, loader=None, origin="stub", is_package=True)
            sys.modules[fullname] = mod
            return mod.__spec__

    sys.meta_path.insert(0, _HAStubFinder)


install = _install_ha_stubs
install()

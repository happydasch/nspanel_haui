"""pytest configuration and shared fixtures."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out homeassistant before any test imports trigger __init__.py.
# ---------------------------------------------------------------------------


def _install_ha_stubs() -> None:
    """Insert minimal homeassistant stubs into sys.modules so tests run without HA."""

    # Minimal config_validation with empty_config_schema
    config_validation = MagicMock()
    config_validation.empty_config_schema = MagicMock(
        return_value=MagicMock(spec_set=dict)
    )

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = ["homeassistant.helpers"]  # marks as package for sub-imports
    helpers.config_validation = config_validation

    ha = MagicMock()
    ha.helpers = helpers

    loader_mod = types.ModuleType("homeassistant.loader")
    loader_mod.Integration = MagicMock()
    loader_mod.async_get_integration = MagicMock()

    stubs: dict[str, object] = {
        "homeassistant": ha,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.entity_registry": MagicMock(),
        "homeassistant.helpers.storage": MagicMock(),
        "homeassistant.helpers.selector": MagicMock(),
        "homeassistant.helpers.device_registry": MagicMock(),
        "homeassistant.config_entries": MagicMock(),
        "homeassistant.const": MagicMock(),
        "homeassistant.core": MagicMock(),
        "homeassistant.components": MagicMock(),
        "homeassistant.components.http": MagicMock(),
        "homeassistant.components.frontend": MagicMock(),
        "homeassistant.components.panel_custom": MagicMock(),
        "homeassistant.loader": loader_mod,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


# ---------------------------------------------------------------------------
# Stub out dateutil so weather.py (transitively loaded via PANEL_MAPPING)
# does not fail.
# ---------------------------------------------------------------------------


def _install_dateutil_stubs() -> None:
    """Insert dateutil stub so tests don't need the real package."""
    from datetime import datetime, timezone

    dt_mod = types.ModuleType("dateutil")
    dt_mod.__path__ = ["dateutil"]

    def _dummy_parse(timestr: str, **kwargs: object) -> datetime:
        return datetime.now(timezone.utc)

    parser_mod = types.ModuleType("dateutil.parser")
    parser_mod.parse = _dummy_parse

    stubs: dict[str, object] = {
        "dateutil": dt_mod,
        "dateutil.parser": parser_mod,
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)


_install_ha_stubs()
_install_dateutil_stubs()

ROOT = Path(__file__).parent.parent
CC = ROOT / "custom_components"
if str(CC) not in sys.path:
    sys.path.insert(0, str(CC))

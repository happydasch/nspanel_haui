"""pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out ONLY what __init__.py needs (from homeassistant.helpers import
# config_validation as cv) so that other tests can import nspanel_haui
# without HA installed.  Keep it minimal — individual test files that need
# more detailed stubs (e.g. test_config_flow.py) install their own on top
# via setdefault.
# ---------------------------------------------------------------------------


def _install_ha_stubs() -> None:
    """Minimal homeassistant stubs so __init__.py can import."""

    config_validation = MagicMock()
    config_validation.empty_config_schema = MagicMock(
        return_value=MagicMock(spec_set=dict)
    )

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = ["homeassistant.helpers"]
    helpers.config_validation = config_validation

    ha = types.ModuleType("homeassistant")
    ha.helpers = helpers

    stubs: dict[str, object] = {
        "homeassistant": ha,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.const": MagicMock(),
        "homeassistant.core": MagicMock(),
        "homeassistant.components": MagicMock(),
        "homeassistant.loader": MagicMock(),
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

"""pytest configuration and shared fixtures."""

from __future__ import annotations

import re
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out ONLY what __init__.py needs (from homeassistant.helpers import
# config_validation as cv) so that other tests can import nspanel_haui
# without HA installed.  Keep it minimal — individual test files that need
# more detailed stubs (e.g. test_config_flow.py) install their own on top
# via setdefault.
# ---------------------------------------------------------------------------


def _slugify(text: str | None, *, separator: str = "_") -> str:
    """Mirror of homeassistant.util.slugify for ASCII names (lowercase, runs of
    non-alphanumerics collapsed to one separator, ends stripped, empty -> "unknown")."""
    if not text:
        return ""
    slug = re.sub(r"[^a-z0-9]+", separator, text.lower()).strip(separator)
    return slug or "unknown"


def _install_ha_stubs() -> None:
    """Minimal homeassistant stubs so __init__.py can import."""

    config_validation = MagicMock()
    config_validation.empty_config_schema = MagicMock(return_value=MagicMock(spec_set=dict))

    util = types.ModuleType("homeassistant.util")
    util.slugify = _slugify

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = ["homeassistant.helpers"]
    helpers.config_validation = config_validation

    # __init__.py lazily imports issue_registry for the Repairs integration
    # (device startup failures / idle hub).  A plain MagicMock lets those
    # calls succeed in tests without a running HA instance.
    issue_registry = MagicMock()
    issue_registry.IssueSeverity = type(
        "IssueSeverity", (), {"ERROR": "error", "WARNING": "warning", "CRITICAL": "critical"}
    )
    helpers.issue_registry = issue_registry

    ha = types.ModuleType("homeassistant")
    ha.helpers = helpers
    ha.util = util

    # __init__.py lazily imports the Repairs platform (device startup
    # failures), which imports homeassistant.data_entry_flow at module scope.
    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict

    stubs: dict[str, object] = {
        "homeassistant": ha,
        "homeassistant.helpers": helpers,
        "homeassistant.util": util,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.issue_registry": issue_registry,
        "homeassistant.data_entry_flow": data_entry_flow,
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

    dt_mod = types.ModuleType("dateutil")
    dt_mod.__path__ = ["dateutil"]

    def _dummy_parse(timestr: str, **kwargs: object) -> datetime:
        return datetime.now(UTC)

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

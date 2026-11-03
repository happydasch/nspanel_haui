"""Every panel preview must resolve to a physical Nextion page in both layouts.

The editor's panel-card previews are all drawn by one shared Nextion simulator,
so ``check_preview_coverage.py`` validates that user types, system panels and
popup aliases always resolve to a page present in both generated layouts.  A
new panel type whose ``page_id`` does not reach both HMIs fails here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_preview_coverage.py"


def test_preview_coverage_passes():
    # A subprocess: the checker installs homeassistant stubs for itself.
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

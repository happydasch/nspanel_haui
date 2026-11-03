"""The editor previews replay the hub's display output; that snapshot must
match what the hub renders today."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_preview_state" / "gen_preview_state.py"
STATE = ROOT / "custom_components" / "nspanel_haui" / "frontend" / "virtual" / "preview_state.json"


def test_snapshot_is_committed():
    assert STATE.exists(), "run scripts/gen_preview_state/gen_preview_state.py"


def test_snapshot_is_up_to_date():
    # A subprocess: the generator installs homeassistant stubs for itself and
    # boots the hub on its own event loop.
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

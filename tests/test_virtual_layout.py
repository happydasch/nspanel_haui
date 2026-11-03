"""The virtual panel's layout files must match the HMI files they are exported from."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_virtual_layout" / "gen_virtual_layout.py"


def test_layouts_are_up_to_date():
    # A subprocess: the generator installs homeassistant stubs for itself.
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

"""Command-line defaults for the HMI layout tool."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_default_spec_is_landscape():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.hmi_layout.gen_layout", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "spec landscape_layout consistent" in result.stdout

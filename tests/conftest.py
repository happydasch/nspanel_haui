"""pytest configuration and shared fixtures."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CC = ROOT / "custom_components"
if str(CC) not in sys.path:
    sys.path.insert(0, str(CC))

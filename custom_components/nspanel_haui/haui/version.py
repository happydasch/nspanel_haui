from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the integration version from manifest.json.

    Lazy-loaded so the file read happens at first call rather than
    at module import time, avoiding Home Assistant's blocking I/O
    detector inside the event loop.
    """
    _manifest_path = Path(__file__).parent.parent / "manifest.json"
    return json.loads(_manifest_path.read_text())["version"]

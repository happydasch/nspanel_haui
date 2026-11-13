from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_integration_version() -> str:
    """Return the integration version from manifest.json.

    Lazy-loaded so the file read happens at first call rather than
    at module import time, avoiding Home Assistant's blocking I/O
    detector inside the event loop.
    """
    _manifest_path = Path(__file__).parent.parent / "manifest.json"
    return json.loads(_manifest_path.read_text())["version"]


def integration_version_mismatch(
    integration_version: str | None, firmware_version: str | None
) -> bool | None:
    """Return whether reported ESPHome firmware differs from this integration.

    ``None`` means one of the versions has not been reported yet.
    """
    if not integration_version or not firmware_version:
        return None
    return integration_version != firmware_version

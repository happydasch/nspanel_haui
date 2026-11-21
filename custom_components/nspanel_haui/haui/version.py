from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Contract version between the firmware and the hub. The firmware reports its
# own copy in the handshake and the device state. Bump the major version only
# for an incompatible change to the handshake or the event payloads.
HUB_API_VERSION = "1.0"


@lru_cache(maxsize=1)
def get_integration_version() -> str:
    """Return the integration version from manifest.json.

    Lazy-loaded so the file read happens at first call rather than
    at module import time, avoiding Home Assistant's blocking I/O
    detector inside the event loop.
    """
    _manifest_path = Path(__file__).parent.parent / "manifest.json"
    return json.loads(_manifest_path.read_text())["version"]


def _major(version: str) -> int | None:
    """Return the major part of a dotted version, or ``None`` when it is not one."""
    head = version.split(".", 1)[0].strip()
    return int(head) if head.isdigit() else None


def hub_api_compatible(reported: str | None) -> bool | None:
    """Return whether a firmware's hub API is compatible with this integration.

    ``None`` means the firmware did not report the field (firmware older than
    the contract). A malformed value is incompatible, not unknown.
    """
    if not reported:
        return None
    reported_major = _major(reported)
    if reported_major is None:
        return False
    return reported_major == _major(HUB_API_VERSION)


def integration_version_mismatch(
    integration_version: str | None, firmware_version: str | None
) -> bool | None:
    """Return whether reported ESPHome firmware differs from this integration.

    ``None`` means one of the versions has not been reported yet.
    """
    if not integration_version or not firmware_version:
        return None
    return integration_version != firmware_version

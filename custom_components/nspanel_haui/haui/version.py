from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from packaging.version import InvalidVersion, Version

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


# The first firmware whose yaml config carries the ``draw_runs`` action
# (``esphome/nspanel_haui/image.yaml``), i.e. the first one that can paint an
# image. A version below it names no service on the device, and ``publish()``
# only logs a warning for an unknown action — the image would silently not
# appear, so the service refuses instead.
DRAW_RUNS_FIRMWARE_VERSION = "0.5.9.dev99"


def firmware_supports_draw_runs(version: str | None) -> bool:
    """Whether a panel's firmware can stream a draw program.

    Empty or unparseable means unknown, which is refused: an older build cannot
    paint, and the user needs the firmware upgrade message instead of a no-op.
    """
    if not isinstance(version, str) or not version:
        return False
    try:
        return Version(version) >= Version(DRAW_RUNS_FIRMWARE_VERSION)
    except InvalidVersion:
        return False

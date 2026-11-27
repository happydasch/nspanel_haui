#!/usr/bin/env python3
"""Check the repair TFTs against the version their manifest block advertises.

The repair TFTs are hand-built minimal projects, not the release HMIs: a display
whose own file is broken takes one of them so the hub can install the real TFT
afterwards. Nothing else verifies them — they are not compiled from a committed
HMI, and a release only publishes them when they are committed here.

A repair TFT qualifies when it embeds its ``system.tftVersion`` text
(``REPAIR_VERSION`` in ``scripts/release/generate_firmware_manifest.py``) and is
small enough for the display: the point of the file is that it always installs.

Usage:
    python -m scripts.verify_nextion.check_repair_tft
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.bump_tft_version import check_tft_carries
from scripts.release.generate_firmware_manifest import REPAIR_TFTS, REPAIR_VERSION

# The display's own flash size; a repair file that does not fit it cannot install.
REPAIR_MAX_BYTES = 16 * 1024 * 1024


def check_repair_tft(path: Path, version: str = REPAIR_VERSION) -> str | None:
    """Return why ``path`` is no usable repair TFT, or None when it is one.

    Args:
        path: The compiled ``.tft`` to inspect
        version: The ``system.tftVersion`` text the file must carry

    Returns:
        str | None: The reason it cannot be used, or None
    """
    if not path.exists():
        return f"{path} is missing; compile it from its HMI in the Nextion Editor"
    size = path.stat().st_size
    if size == 0:
        return f"{path} is empty"
    if size > REPAIR_MAX_BYTES:
        return f"{path} is {size} bytes, over the display's {REPAIR_MAX_BYTES} byte limit"
    try:
        check_tft_carries(path, version)
    except ValueError as exc:
        return str(exc)
    return None


def main(argv: list[str] | None = None) -> int:
    """Report each repair TFT of the manifest's ``repair`` block."""
    paths = list(argv) if argv else [str(path) for path in REPAIR_TFTS.values()]
    failed = False
    for path in paths:
        problem = check_repair_tft(Path(path))
        print(
            ("[FAIL] " if problem else "[OK] ")
            + (problem or f"{path}: repair TFT {REPAIR_VERSION}")
        )
        failed = failed or problem is not None
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

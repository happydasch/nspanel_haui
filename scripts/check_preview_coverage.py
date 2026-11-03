#!/usr/bin/env python3
"""Check that every panel preview resolves to a physical Nextion page.

The editor's panel-card previews are all drawn by one shared Nextion simulator
(frontend/previews/simulator-frame.js + simulator.js): it loads the generated
virtual-panel layout, jumps to a panel type's physical HMI page and renders it.
There are no per-type preview renderers, so this script validates that the
preview can resolve every panel - user types, system panels and popup aliases -
to a page that exists in the generated layouts of both orientations.

Usage:
    python scripts/check_preview_coverage.py

Exit code is non-zero when any panel has no physical page, or a page is missing
from a layout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "custom_components"))
sys.path.insert(0, str(ROOT / "scripts"))

import _ha_stubs  # noqa: E402,F401  (installs the Home Assistant stubs)

VIRTUAL_DIR = ROOT / "custom_components" / "nspanel_haui" / "frontend" / "virtual"
LAYOUTS = {
    "landscape": VIRTUAL_DIR / "layout_landscape.json",
    "portrait": VIRTUAL_DIR / "layout_portrait.json",
}


def _load_layouts() -> tuple[dict[str, set[int]], list[str]]:
    """Return ({orientation: {physical page ids}}, problems)."""
    layouts: dict[str, set[int]] = {}
    problems: list[str] = []
    for orientation, path in LAYOUTS.items():
        if not path.exists():
            problems.append(f"missing layout {path.relative_to(ROOT)}")
            continue
        with path.open(encoding="utf-8") as handle:
            layouts[orientation] = {int(pid) for pid in json.load(handle)["pages"]}
    return layouts, problems


def check_coverage() -> int:
    """Validate page-id coverage for user types, system panels and aliases."""
    from custom_components.nspanel_haui.haui.mapping.panel import (
        PAGE_MAPPING,
        PANEL_MAPPING,
        SYS_PANEL_MAPPING,
        get_system_panel_entries,
        get_user_panel_type_descriptors,
    )

    layouts, problems = _load_layouts()

    # 1. Every physical page id known to the hub exists in both layouts.
    for orientation, page_ids in layouts.items():
        for pid in sorted(PAGE_MAPPING):
            if pid not in page_ids:
                problems.append(
                    f"{orientation}: page id {pid} '{PAGE_MAPPING[pid]}' missing from layout"
                )

    # 2. User panel type descriptors expose a physical page id.
    for descriptor in get_user_panel_type_descriptors():
        pid = descriptor.get("page_id")
        if pid is None:
            problems.append(f"user type '{descriptor['type_key']}' has no page_id")
        elif "landscape" in layouts and pid not in layouts["landscape"]:
            problems.append(f"user type '{descriptor['type_key']}' page_id {pid} not in layout")

    # 3. System panel entries (incl. popup aliases) expose a physical page id.
    for entry in get_system_panel_entries():
        pid = entry.get("page_id")
        if pid is None:
            problems.append(f"system panel '{entry['key']}' has no page_id")
        elif "portrait" in layouts and pid not in layouts["portrait"]:
            problems.append(f"system panel '{entry['key']}' page_id {pid} not in portrait layout")

    # 4. Every registered type key (PANEL_MAPPING, incl. popup aliases) resolves.
    for type_key, (_, cls) in PANEL_MAPPING.items():
        descriptor = getattr(cls, "DESCRIPTOR", None)
        pid = getattr(descriptor, "page_id", None)
        if pid is None or pid not in PAGE_MAPPING:
            problems.append(f"PANEL_MAPPING['{type_key}'] has no physical page (page_id={pid})")

    # 5. Every system panel key resolves to a registered type.
    for sys_key, type_key in SYS_PANEL_MAPPING.items():
        if type_key not in PANEL_MAPPING:
            problems.append(f"SYS_PANEL_MAPPING['{sys_key}'] -> unknown type '{type_key}'")

    for problem in sorted(set(problems)):
        print(problem, file=sys.stderr)
    if problems:
        print(f"✗ {len(set(problems))} preview-coverage problem(s) found", file=sys.stderr)
        return 1
    print(
        f"✓ {len(PAGE_MAPPING)} physical pages, {len(PANEL_MAPPING)} type keys "
        f"and {len(SYS_PANEL_MAPPING)} system keys resolve to a page in both layouts."
    )
    return 0


if __name__ == "__main__":
    sys.exit(check_coverage())

"""The virtual panel's layout files must match the HMI files they are exported from."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from custom_components.nspanel_haui.haui.mapping.panel import _page_classes

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("orientation", ["landscape", "portrait"])
def test_page_component_ids_match_layout(orientation):
    layout_path = (
        ROOT / "custom_components/nspanel_haui/frontend/virtual" / f"layout_{orientation}.json"
    )
    layout = json.loads(layout_path.read_text())

    for page_class in _page_classes:
        descriptor = getattr(page_class, "DESCRIPTOR", None)
        components = getattr(page_class, "COMPONENTS", None)
        if descriptor is None or components is None:
            continue

        page = layout["pages"].get(str(descriptor.page_id))
        assert page is not None, f"{page_class.__name__} has no layout page {descriptor.page_id}"
        layout_components = {component["name"]: component["id"] for component in page["components"]}

        for component in components.values():
            assert layout_components.get(component.name) == component.id, (
                f"{page_class.__name__}.{component.name} has ID {component.id}, "
                f"but {orientation} layout has ID {layout_components.get(component.name)}"
            )


def test_layouts_are_up_to_date():
    # A subprocess: the generator installs homeassistant stubs for itself.
    result = subprocess.run(
        [sys.executable, "-m", "scripts.hmi_layout.gen_virtual_layout", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

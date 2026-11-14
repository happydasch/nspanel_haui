"""Tests for the Nextion2Text HMI dump tool."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.nextion2text.Nextion2Text import _load_custom_dictionary

ROOT = Path(__file__).resolve().parent.parent


def test_custom_dictionary_can_import_neighbor_and_restores_sys_path(tmp_path):
    helper_name = "_nspanel_haui_custom_dict_helper"
    module_name = "_nspanel_haui_custom_dict_test"
    (tmp_path / f"{helper_name}.py").write_text("VALUE = 42\n", encoding="utf-8")
    custom_path = tmp_path / f"{module_name}.py"
    custom_path.write_text(
        f"from {helper_name} import VALUE\nattributes = {{'answer': VALUE}}\n",
        encoding="utf-8",
    )
    original_sys_path = sys.path.copy()
    try:
        custom = _load_custom_dictionary(custom_path)
        assert custom.attributes == {"answer": 42}
        assert sys.path == original_sys_path
    finally:
        sys.modules.pop(module_name, None)
        sys.modules.pop(helper_name, None)


def test_dump_creates_a_missing_output_tree(tmp_path):
    """The documented dump target lives under the git-ignored ``ref_src/``, which a
    fresh clone does not have, so the output folder is created with its parents."""
    out_dir = tmp_path / "ref_src" / "nextion-out-visual"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.nextion2text.Nextion2Text",
            "-i",
            str(ROOT / "nextion" / "nspanel_haui.HMI"),
            "-o",
            str(out_dir),
            "-d",
            "-s",
            "-p",
            "visual",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert (out_dir / "clock.txt").exists()

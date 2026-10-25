"""Tests for the translation maintenance scripts.

The scripts locate files relative to their own path, so each test runs copies
of them inside a temporary repo layout and never touches the real locale files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts" / "translations"


def _repo(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts" / "translations"
    scripts.mkdir(parents=True)
    for name in ("extract_translations.py", "merge_translations.py"):
        shutil.copy(SCRIPTS / name, scripts / name)
    locale = tmp_path / "custom_components" / "nspanel_haui" / "haui" / "locale"
    locale.mkdir(parents=True)
    (tmp_path / "custom_components" / "nspanel_haui" / "frontend").mkdir()
    (locale / "en.json").write_text(json.dumps({"component": {}, "text": {"Close": "Close"}}))
    (locale / "de.json").write_text(
        json.dumps({"component": {}, "text": {"Close": "Schließen"}}, ensure_ascii=False)
    )
    (scripts / "translate.json").write_text(json.dumps({"text": {"Close": ""}}))
    return tmp_path


def _run(repo: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(repo / "scripts" / "translations" / script), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _mtimes(repo: Path) -> dict[str, int]:
    files = list(repo.rglob("*.json"))
    return {str(f): f.stat().st_mtime_ns for f in files}


def test_extract_help_prints_usage_and_writes_nothing(tmp_path):
    repo = _repo(tmp_path)
    before = _mtimes(repo)

    result = _run(repo, "extract_translations.py", "--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert _mtimes(repo) == before


def test_merge_help_prints_usage_and_writes_nothing(tmp_path):
    repo = _repo(tmp_path)
    before = _mtimes(repo)

    result = _run(repo, "merge_translations.py", "--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert _mtimes(repo) == before


def test_merge_keeps_non_ascii_text_readable(tmp_path):
    repo = _repo(tmp_path)

    result = _run(repo, "merge_translations.py")

    assert result.returncode == 0, result.stderr
    de = (repo / "custom_components" / "nspanel_haui" / "haui" / "locale" / "de.json").read_text(
        encoding="utf-8"
    )
    assert '"Close": "Schließen"' in de
    assert de.endswith("\n")

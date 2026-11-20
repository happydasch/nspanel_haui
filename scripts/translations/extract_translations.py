"""Extract translatable strings from Python and frontend JS sources.

Scans Python ``.translate("...")`` calls in the haui core and ``_("...")`` calls in
descriptors, plus ``t("...")`` calls in the editor JS. Writes
``scripts/translations/translate.json`` (the merge pipeline's template) and the
``custom_components/nspanel_haui/haui/locale/*.json`` files, adding the missing keys to
every language and an empty placeholder in the non-en ones.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PYTHON_DIR = os.path.join(REPO_ROOT, "custom_components", "nspanel_haui")
FRONTEND_DIR = os.path.join(PYTHON_DIR, "frontend")
TRANSLATIONS_DIR = os.path.join(PYTHON_DIR, "haui", "locale")
OUTPUT_TRANSLATE = os.path.join(SCRIPT_DIR, "translate.json")

# Match self.translate("...") in Python; ruff may wrap a long string onto its own line,
# with its line-length waiver comment after it.
PY_PATTERN = re.compile(r"\.translate\(\s*(['\"])(.*?)\1\s*(?:#[^\n]*\s*)?\)")

# Match _("...") or _('...') — descriptor string marker
PY_DESCRIPTOR_PATTERN = re.compile(r"(?<![.\w])_\((['\"])(.*?)\1\)")

# Match bare t("...") calls in JS
JS_PATTERN = re.compile(r"(?<![.\w])t\((['\"])(.*?)\1\)")


def extract_python_strings() -> set[str]:
    strings: set[str] = set()
    for root, _dirs, files in os.walk(PYTHON_DIR):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path) as f:
                    contents = f.read()
            except OSError:
                continue
            for match in PY_PATTERN.finditer(contents):
                strings.add(match.group(2))
            for match in PY_DESCRIPTOR_PATTERN.finditer(contents):
                strings.add(match.group(2))
    return strings


def extract_frontend_strings() -> set[str]:
    strings: set[str] = set()
    if not os.path.isdir(FRONTEND_DIR):
        return strings
    for root, _dirs, files in os.walk(FRONTEND_DIR):
        for file in files:
            if not file.endswith(".js"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path) as f:
                    contents = f.read()
            except OSError:
                continue
            for match in JS_PATTERN.finditer(contents):
                s = match.group(2).encode("raw_unicode_escape").decode("unicode_escape")
                strings.add(s)
    return strings


def read_json_or_empty(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except OSError, json.JSONDecodeError:
        return {}


def sync_json(path: str, data: dict, *, check: bool) -> bool:
    """Check or write the canonical JSON without touching a fresh file."""
    output = Path(path)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if output.exists() and output.read_text(encoding="utf-8") == text:
        return True
    if check:
        print(f"{output.relative_to(REPO_ROOT)} is out of date; run the extractor without --check")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"Updated {output.relative_to(REPO_ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="check files without writing them")
    args = parser.parse_args()
    text_keys = sorted((extract_python_strings() | extract_frontend_strings()) - {""})

    current = [
        sync_json(OUTPUT_TRANSLATE, {"text": dict.fromkeys(text_keys, "")}, check=args.check)
    ]
    paths = set(Path(TRANSLATIONS_DIR).glob("*.json")) | {Path(TRANSLATIONS_DIR) / "en.json"}
    for path in sorted(paths):
        existing = read_json_or_empty(str(path))
        translations = existing.get("text", {})
        english = path.name == "en.json"
        data = {
            "component": existing.get("component", {}),
            "text": {
                key: (translations.get(key) or key) if english else translations.get(key, "")
                for key in text_keys
            },
        }
        current.append(sync_json(str(path), data, check=args.check))
    return 0 if all(current) else 1


if __name__ == "__main__":
    raise SystemExit(main())

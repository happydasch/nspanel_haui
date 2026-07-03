"""Extract translatable strings from Python and frontend JS sources.

Scans:
  - Python `.translate("...")` calls in the haui core package
  - Python `_("...")` calls in descriptor definitions (page label/description/section/choice)
  - Frontend `host._t("...")` / `t("...")` calls in the editor JS
Outputs:
  - ``scripts/translations/translate.json`` — flat text template for merge pipeline
  - ``custom_components/nspanel_haui/haui/locale/*.json`` — HA
    custom_components translation format (component + text sections only)
    All language files are updated with missing keys; non-en files use an
    empty placeholder for new keys.
"""

from __future__ import annotations

import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PYTHON_DIR = os.path.join(REPO_ROOT, "custom_components", "nspanel_haui")
FRONTEND_DIR = os.path.join(PYTHON_DIR, "frontend")
TRANSLATIONS_DIR = os.path.join(PYTHON_DIR, "haui", "locale")
EN_JSON = os.path.join(TRANSLATIONS_DIR, "en.json")
OUTPUT_TRANSLATE = os.path.join(SCRIPT_DIR, "translate.json")

# Match self.translate("...") or self.translate('...') in Python
PY_PATTERN = re.compile(r"\.translate\((['\"])(.*?)\1\)")

# Match _("...") or _('...') — descriptor string marker
PY_DESCRIPTOR_PATTERN = re.compile(r"(?<![.\w])_\((['\"])(.*?)\1\)")

# Match bare t("...") calls in JS (host._t / this._t have been removed)
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
    except (OSError, json.JSONDecodeError):
        return {}


def update_lang_file(path: str, text_keys: list[str]) -> tuple[int, int]:
    """Sync text keys in a language file: add missing, remove unused.

    Returns (added, removed).
    """
    existing = read_json_or_empty(path)
    existing_text = existing.get("text", {})
    key_set = set(text_keys)
    added = 0
    removed = len([k for k in existing_text if k not in key_set])
    new_text: dict[str, str] = {}
    for key in text_keys:
        if key in existing_text:
            new_text[key] = existing_text[key]
        else:
            new_text[key] = ""
            added += 1
    output = {
        "component": existing.get("component", {}),
        "text": new_text,
    }
    with open(path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return added, removed


def main() -> None:
    text_keys = extract_python_strings() | extract_frontend_strings()
    text_keys.discard("")
    text_keys = sorted(text_keys)

    existing_en = read_json_or_empty(EN_JSON)

    # --- Build en text section ---
    existing_en_text = existing_en.get("text", {})
    new_en_text: dict[str, str] = {}
    for key in text_keys:
        existing_value = existing_en_text.get(key, "")
        new_en_text[key] = existing_value if existing_value else key

    # --- Write legacy translate.json (flat template for merge pipeline) ---
    os.makedirs(os.path.dirname(OUTPUT_TRANSLATE), exist_ok=True)
    with open(OUTPUT_TRANSLATE, "w") as f:
        json.dump({"text": {k: "" for k in text_keys}}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # --- Write en.json ---
    en_output = {
        "component": existing_en.get("component", {}),
        "text": new_en_text,
    }
    with open(EN_JSON, "w") as f:
        json.dump(en_output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # --- Update all other language files ---
    for fname in os.listdir(TRANSLATIONS_DIR):
        if not fname.endswith(".json") or fname == "en.json":
            continue
        lang_path = os.path.join(TRANSLATIONS_DIR, fname)
        added, removed = update_lang_file(lang_path, text_keys)
        parts = []
        if added:
            parts.append(f"added {added}")
        if removed:
            parts.append(f"removed {removed}")
        if parts:
            print(f"{fname}: {', '.join(parts)} key(s)")


if __name__ == "__main__":
    main()

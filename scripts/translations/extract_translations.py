"""Extract translatable strings from Python and frontend JS sources.

Scans:
  - Python `.translate("...")` calls in the haui core package
  - Frontend `host._t("...")` / `t("...")` calls in the editor JS
  - `strings.json` for config/options sections (HA config flow)

Outputs:
  - ``scripts/translations/translate.json`` — flat text template for merge pipeline
  - ``custom_components/nspanel_haui/translations/en.json`` — HA
    custom_components translation format (preserves component section)
"""

from __future__ import annotations

import json
import os
import re

PYTHON_DIR = "custom_components/nspanel_haui"
FRONTEND_DIR = os.path.join(PYTHON_DIR, "frontend")
STRINGS_JSON = os.path.join(PYTHON_DIR, "strings.json")
EN_JSON = os.path.join(PYTHON_DIR, "translations", "en.json")
OUTPUT_TRANSLATE = "scripts/translations/translate.json"

# Match self.translate("...") or self.translate('...') in Python
PY_PATTERN = re.compile(r"\.translate\((['\"])(.*?)\1\)")

# Match host._t("..."), host._t('...'), t("..."), or t('...') in JS
JS_PATTERN = re.compile(r"(?:host\.)?_t\((['\"])(.*?)\1\)")


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
                strings.add(match.group(2))
    return strings


def read_json_or_empty(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> None:
    text_keys = extract_python_strings() | extract_frontend_strings()
    text_keys.discard("")
    text_keys = sorted(text_keys)

    existing_en = read_json_or_empty(EN_JSON)
    strings_data = read_json_or_empty(STRINGS_JSON)

    # --- Build text section ---
    existing_text = existing_en.get("text", {})
    new_text: dict[str, str] = {}
    for key in text_keys:
        existing_value = existing_text.get(key, "")
        new_text[key] = existing_value if existing_value else key

    # --- Write legacy translate.json (flat template for merge pipeline) ---
    os.makedirs(os.path.dirname(OUTPUT_TRANSLATE), exist_ok=True)
    with open(OUTPUT_TRANSLATE, "w") as f:
        json.dump({"text": {k: "" for k in text_keys}}, f, indent=2)

    # --- Write en.json (HA custom_components format) ---
    en_output = {
        "config": strings_data.get("config", existing_en.get("config", {})),
        "options": strings_data.get("options", existing_en.get("options", {})),
        "component": existing_en.get("component", {}),
        "text": new_text,
    }

    with open(EN_JSON, "w") as f:
        json.dump(en_output, f, indent=2)


if __name__ == "__main__":
    main()
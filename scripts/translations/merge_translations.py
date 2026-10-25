"""Merge a translation template back into the locale files.

Takes the text keys from ``scripts/translations/translate.json`` and writes them
into every ``custom_components/nspanel_haui/haui/locale/*.json``, keeping each
file's existing translations. Used for external translation-service round
trips; routine extraction is done by ``extract_translations.py``.
"""

from __future__ import annotations

import argparse
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
LOCALE_DIR = os.path.join(REPO_ROOT, "custom_components", "nspanel_haui", "haui", "locale")
SOURCE_FILE = os.path.join(SCRIPT_DIR, "translate.json")


def update_json_file(original_file_path: str, source_file_path: str) -> None:
    with open(original_file_path, encoding="utf-8") as original_file:
        original_json = json.load(original_file)

    with open(source_file_path, encoding="utf-8") as source_file:
        source_json = json.load(source_file)

    for text in source_json["text"].keys():
        if text in original_json["text"]:
            source_json["text"][text] = original_json["text"][text]

    original_json["text"] = source_json["text"]

    # Same format as extract_translations.py, so the two don't fight over diffs.
    with open(original_file_path, "w", encoding="utf-8") as original_file:
        json.dump(original_json, original_file, indent=2, ensure_ascii=False)
        original_file.write("\n")


def main() -> None:
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    ).parse_args()
    for file_name in os.listdir(LOCALE_DIR):
        if file_name.endswith(".json"):
            update_json_file(os.path.join(LOCALE_DIR, file_name), SOURCE_FILE)


if __name__ == "__main__":
    main()

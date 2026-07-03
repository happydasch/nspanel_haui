import json
import os


def update_json_file(original_file_path, source_file_path):
    with open(original_file_path) as original_file:
        original_json = json.load(original_file)

    with open(source_file_path) as source_file:
        source_json = json.load(source_file)

    for text in source_json["text"].keys():
        if text in original_json["text"]:
            source_json["text"][text] = original_json["text"][text]

    original_json["text"] = source_json["text"]

    with open(original_file_path, "w") as original_file:
        json.dump(original_json, original_file, indent=2)
    # print(json.dumps(original_json, indent=2))


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
dir_path = os.path.join(REPO_ROOT, "custom_components", "nspanel_haui", "haui", "locale")
source_file_path = os.path.join(SCRIPT_DIR, "translate.json")

for file_name in os.listdir(dir_path):
    if file_name.endswith(".json"):
        file_path = os.path.join(dir_path, file_name)
        update_json_file(file_path, source_file_path)

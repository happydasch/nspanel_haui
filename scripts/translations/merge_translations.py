import os
import json


def update_json_file(original_file_path, source_file_path):
    with open(original_file_path, 'r') as original_file:
        original_json = json.load(original_file)

    with open(source_file_path, 'r') as source_file:
        source_json = json.load(source_file)

    for text in source_json['text'].keys():
        if text in original_json['text']:
            source_json['text'][text] = original_json['text'][text]

    original_json['text'] = source_json['text']

    with open(original_file_path, 'w') as original_file:
        json.dump(original_json, original_file, indent=2)
    #print(json.dumps(original_json, indent=2))


dir_path = 'apps/nspanel_haui/haui/translations'
source_file_path = 'scripts/translations/translate.json'

for file_name in os.listdir(dir_path):
    if file_name.endswith('.json'):
        file_path = os.path.join(dir_path, file_name)
        update_json_file(file_path, source_file_path)

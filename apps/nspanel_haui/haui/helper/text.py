import os
import json


def get_translation(text, locale):
    translations = get_translations(locale)
    translation = text
    if 'text' in translations:
        if text in translations['text']:
            translation = translations['text'][text]
    return translation


def get_state_translation(entity_type, state, locale):
    translations = get_translations(locale)
    lookup = f'component.{entity_type}.state._.{state}'
    res = translations
    for k in lookup.split('.'):
        if k in res:
            res = res[k]
        else:
            res = None
            break
    if res is not None:
        return res
    return state


def get_translations(locale):
    lang = locale.split('_')[0]
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_file = os.path.join(dir_path, '..', 'translations', f'{lang}.json')
    if not os.path.isfile(path_file):
        path_file = os.path.join(dir_path, '..', 'translations', 'en.json')
    with open(path_file, 'r') as translation_file:
        translations = json.load(translation_file)
    return translations

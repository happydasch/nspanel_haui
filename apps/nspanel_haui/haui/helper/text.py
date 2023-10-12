import os
import json


def get_translation(text, locale):
    translations = get_translations(locale)
    translation = text
    if 'text' in translations:
        if text in translations['text']:
            translation = translations['text'][text]
    return translation


def get_state_translation(entity_type, state, locale, attr='state'):
    translations = get_translations(locale)
    lookup = f'component.{entity_type}.{attr}._.{state}'
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


def trim_text(text, num_chr, suffix='..'):
    """
    Trim text to a certain number of characters

    Args:
        text (str): Text to trim
        num_chr (int): Number of characters to trim to
        suffix (str): Suffix to add to the end of the trimmed text

    Returns:
        str: The trimmed text
    """
    if not suffix:
        suffix = ''
    if not text:
        return text
    if len(text) > num_chr:
        return text[:num_chr - len(suffix)] + suffix
    else:
        return text

from __future__ import annotations

from typing import Any


def scale(val: float, src: tuple | list, dst: tuple | list) -> float:
    """Scale the value

    Scale the given value from the scale of src
    to the scale of dst.

    Args:
        val (int): Value to scale
        src (list): List containing src min max values
        dst (list): List containing src min max values

    Returns:
        int: The scaled value
    """
    return ((val - src[0]) / (src[1] - src[0])) * (dst[1] - dst[0]) + dst[0]


def format_number(value: Any) -> str:
    """Text for a numeric attribute, a whole float without its trailing ".0".

    Integrations report the same reading as ``1012`` or ``1012.0``; the editor
    preview receives both as the JavaScript number ``1012``, so the panel
    prints both that way too.

    Args:
        value: Attribute value to print

    Returns:
        str: The value as text
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def merge_dicts(dict1: dict, dict2: dict) -> None:
    """Merge two dicts together

    This function will merge the source dict into
    the destination dict.

    Args:
        dict1 (dict): destination dict
        dict2 (dict): source dict
    """
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value

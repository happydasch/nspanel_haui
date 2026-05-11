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

def scale(val, src, dst):
    """ Scale the value

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


def merge_dicts(dict1, dict2):
    """ Merge two dicts together

    This function will merge the source dict into
    the destination dict.

    Args:
        dict1 (dict): destination dict
        dict2 (dict): source dict
    """
    for k in dict2.keys():
        if k in dict1 and isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
            merge_dicts(dict1[k], dict2[k])
        else:
            dict1[k] = dict2[k]

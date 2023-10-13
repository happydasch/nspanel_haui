from ..mapping.page import PANEL_MAPPING, PAGE_MAPPING


def get_page_id_for_panel(panel_type):
    """Returns the page id for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        int: Page id
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        page_id = get_page_id(panel[0])
        return page_id


def get_page_class_for_panel(panel_type):
    """Returns the page class for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        str: Page class
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return panel[1]


def get_page_id(page_name):
    """Returns the page id for the given page name.

    Args:
        page_name (str): Page name

    Returns:
        int: Page id
    """
    for i, v in PAGE_MAPPING.items():
        if v == page_name:
            return i


def get_page_name(page_id):
    """Returns the page name for the given page id.

    Args:
        page_id (int): Page id

    Returns:
        str: Page name
    """
    if page_id in PAGE_MAPPING:
        return PAGE_MAPPING[page_id]

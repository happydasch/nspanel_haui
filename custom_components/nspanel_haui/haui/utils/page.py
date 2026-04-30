from ..mapping.page import PAGE_MAPPING
from ..mapping.panel import PANEL_MAPPING
from ..page import HAUIPage


def get_page_id_for_panel(panel_type: str) -> int | None:
    """Returns the page id for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        int: Page id
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return get_page_id(panel[0])


def get_page_class_for_panel(panel_type: str) -> type[HAUIPage] | None:
    """Returns the page class for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        str: Page class
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return panel[1]


def get_page_id(page_name: str) -> int | None:
    """Returns the page id for the given page name.

    Args:
        page_name (str): Page name

    Returns:
        int: Page id
    """
    for i, v in PAGE_MAPPING.items():
        if v == page_name:
            return i


def get_page_name(page_id: int) -> str | None:
    """Returns the page name for the given page id.

    Args:
        page_id (int): Page id

    Returns:
        str: Page name
    """
    return PAGE_MAPPING.get(page_id)

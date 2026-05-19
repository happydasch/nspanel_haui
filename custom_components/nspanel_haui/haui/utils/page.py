from ..abstract.haui_page import HAUIPage
from ..mapping.page import PAGE_MAPPING
from ..mapping.panel import PANEL_MAPPING


def get_page_id_for_panel(panel_type: str) -> int:
    """Returns the page id for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        int: Page id

    Raises:
        KeyError: If the panel type is unknown.
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return get_page_id(panel[0])
    raise KeyError(f"No page ID found for panel type '{panel_type}'")


def get_page_class_for_panel(panel_type: str) -> type[HAUIPage]:
    """Returns the page class for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        str: Page class

    Raises:
        KeyError: If the panel type is unknown.
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return panel[1]
    raise KeyError(f"No page class found for panel type '{panel_type}'")


def get_page_id(page_name: str) -> int:
    """Returns the page id for the given page name.

    Args:
        page_name (str): Page name

    Returns:
        int: Page id

    Raises:
        KeyError: If the page name is unknown.
    """
    for i, v in PAGE_MAPPING.items():
        if v == page_name:
            return i
    raise KeyError(f"No page ID found for page name '{page_name}'")


def get_page_name(page_id: int) -> str:
    """Returns the page name for the given page id.

    Args:
        page_id (int): Page id

    Returns:
        str: Page name

    Raises:
        KeyError: If the page ID is unknown.
    """
    name = PAGE_MAPPING.get(page_id)
    if name is None:
        raise KeyError(f"No page name found for page ID {page_id}")
    return name

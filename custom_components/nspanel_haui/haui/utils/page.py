from ..abstract.haui_page import HAUIPage
from ..mapping.panel import PAGE_MAPPING, PANEL_MAPPING


def get_page_id_for_panel(panel_type: str) -> int | None:
    """Returns the page id for the given panel type.

    Returns None for an unknown type (e.g. a stored panel whose type was
    removed) so navigation can log and fall back instead of raising.

    Args:
        panel_type (str): Panel type

    Returns:
        int | None: Page id, or None if the panel type is unknown.

    Raises:
        KeyError: If the type is mapped to a page name that has no page id.
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return get_page_id(panel[0])
    return None


def get_page_class_for_panel(panel_type: str) -> type[HAUIPage] | None:
    """Returns the page class for the given panel type.

    Args:
        panel_type (str): Panel type

    Returns:
        type[HAUIPage] | None: Page class, or None if the panel type is unknown.
    """
    if panel_type in PANEL_MAPPING:
        panel = PANEL_MAPPING[panel_type]
        return panel[1]
    return None


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

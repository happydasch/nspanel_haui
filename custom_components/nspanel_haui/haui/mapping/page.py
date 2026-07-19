# page_id -> page_name
# Derived from DESCRIPTOR.page_id on each page class in panel.py.
# Popup aliases (e.g. UnlockPage) are excluded — they share a page_id
# with their parent page.
from __future__ import annotations

from .panel import PAGE_MAPPING  # noqa: F401

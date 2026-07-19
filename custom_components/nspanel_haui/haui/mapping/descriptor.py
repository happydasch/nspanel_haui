from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _(text: str) -> str:
    """Mark a string as translatable.

    At class-definition time this is a no-op identity so descriptors continue
    to hold their raw English strings (which the frontend t() then translates).
    Used purely as a signal to the extraction script.
    """
    return text


@dataclass
class PageOption:
    """Describes one configurable option that a page accepts in its panel config.

    Used by the integration's config flow to render appropriate form controls
    per panel type. ``kind`` determines the control:

      - bool         → toggle (ha-switch)
      - int / float  → number input
      - str          → text input
      - color        → text input with color picker button; primary format is RGB565 int,
                        also accepts "[r,g,b]" and "#rrggbb" strings
      - icon         → icon picker (searchable MDI grid)
      - generic      → generic text input (catch-all for custom values)
      - item         → item selector (filtered by ``domain`` if set)
      - select       → dropdown (uses ``choices``)
      - list_items   → list editor with one input per item plus add/remove buttons
                        (select if ``choices`` set, otherwise plain text input)
      - list_entities → list editor for entity IDs with one entity picker per item
                        plus add/remove buttons; ``domain`` filters the picker
      - list_str     → multi-line text input, one item per line
      - item_list    → item list editor with modal config dialog
    """

    key: str
    kind: str
    default: Any = None
    label: str | None = None
    description: str | None = None
    domain: str | None = None
    choices: list[tuple[str, str]] | None = None
    section: str | None = None
    max_items: int | None = None
    """Maximum number of items allowed in an item_list. ``None`` means unlimited (default)."""


@dataclass
class PageDescriptor:
    type_key: str
    page_name: str
    label: str
    description: str
    is_system: bool = False
    options: list[PageOption] = field(default_factory=list)
    item_options: list[str] = field(default_factory=list)
    """Panel-level option keys that can also be overridden per-item."""
    can_show_popup: bool = False
    """True if this panel type supports overlay (popup) display.

    Single-entity panels (light, climate, media, cover, vacuum, timer)
    and system popup panels set this to True. Multi-entity panels (grid,
    row, clock, weather) set this to False — they display as full-page
    subpanels when show_in_navigation is False.
    """
    icon: str = ""
    """MDI icon string to display alongside the panel type in the editor UI."""
    sys_panel_default: dict | None = None
    """Default panel config dict for system panels.

    When set, the page class defines its own system-panel default config.
    Keys include ``key``, ``show_in_navigation``, ``show_home_button``, etc.
    Only relevant for pages where ``is_system=True``.
    """
    popup_alias_for: str | None = None
    """When set, this page is a popup variant of another page type.

    The value is the ``type_key`` of the parent page (e.g. ``"alarm"``
    for ``popup_unlock``).  Popup aliases are auto-registered and do
    **not** appear as user-selectable panel types.
    """
    page_id: int | None = None
    """Nextion page ID number for this page.

    Each page maps to a numeric page ID in the Nextion firmware.  Popup
    aliases (``popup_alias_for``) share the aliased page's ID.
    ``None`` means the page class does not have a dedicated Nextion page
    (e.g. runtime-only overlay logic).
    """
    has_header: bool = True
    """Whether this page type displays the header bar (function buttons).

    Most panel pages show 4 function buttons at the top of the display.
    Clock, weather, blank, and system pages may omit the header bar
    and show content full-screen instead.
    """

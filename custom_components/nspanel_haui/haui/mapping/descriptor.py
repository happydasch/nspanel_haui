from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageOption:
    """Describes one configurable option that a page accepts in its panel config.

    Used by the integration's config flow to render appropriate form controls
    per panel type. ``kind`` determines the control:

      - bool         → toggle (ha-switch)
      - int / float  → number input
      - color_seed  → number input with randomize button + palette preview
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
    icon: str = ""
    """MDI icon string to display alongside the panel type in the editor UI."""

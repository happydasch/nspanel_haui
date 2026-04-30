from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageOption:
    """Describes one configurable option that a page accepts in its panel config.

    Used by the integration's config flow to render appropriate form controls
    per panel type. ``kind`` determines the control:

      - bool         → checkbox
      - int / float  → number input
      - str          → text input
      - color        → text input (RGB565 int or "[r,g,b]")
      - entity       → entity selector (filtered by ``domain`` if set)
      - select       → dropdown (uses ``choices``)
      - list_str     → multi-line text input, one item per line
    """

    key: str
    kind: str
    default: Any = None
    label: str | None = None
    description: str | None = None
    domain: str | None = None
    choices: list[tuple[str, str]] | None = None


@dataclass
class PageDescriptor:
    type_key: str
    page_name: str
    label: str
    description: str
    is_system: bool = False
    is_popup: bool = False
    options: list[PageOption] = field(default_factory=list)

"""Generic list-of-dicts editor for HA config flows."""

from __future__ import annotations

import copy
import logging

_LOGGER = logging.getLogger(__name__)


class ListEditor:
    """Generic list-of-dicts editor for HA config flows.

    Handles: add, edit, duplicate, move up/down, remove.
    Does NOT manage steps — just mutates the list safely.
    """

    def __init__(self, items: list[dict] | None = None) -> None:
        self.items: list[dict] = items if items is not None else []

    def add(self, item: dict) -> int:
        """Append item, return index."""
        self.items.append(item)
        return len(self.items) - 1

    def edit(self, idx: int, item: dict) -> None:
        """Replace item at idx."""
        if 0 <= idx < len(self.items):
            self.items[idx] = item

    def duplicate(self, idx: int) -> int:
        """Deep-copy item at idx, append copy, return new index."""
        if 0 <= idx < len(self.items):
            self.items.append(copy.deepcopy(self.items[idx]))
            return len(self.items) - 1
        return -1

    def move(self, idx: int, direction: int) -> int:
        """Move item up (-1) or down (+1). Returns new index or -1."""
        target = idx + direction
        if 0 <= target < len(self.items):
            self.items[idx], self.items[target] = (
                self.items[target],
                self.items[idx],
            )
            return target
        return -1

    def remove(self, idx: int) -> bool:
        """Remove item at idx. Returns True if removed."""
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            return True
        return False

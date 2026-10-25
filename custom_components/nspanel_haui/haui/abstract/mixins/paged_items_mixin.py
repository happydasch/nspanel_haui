"""Paging, state-listener and debounced redraw handling shared by grid and row pages.

Both pages show a window of ``HAUIItem`` entries, listen to the state of the
visible ones and redraw changed entries in one coalesced pass.  Only the page
size, the debounce key and the per-entry redraw differ.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ...utils.debounce import Debouncer
    from ..haui_item import HAUIItem
    from ..haui_panel import HAUIPanel


class PagedItemsMixin:
    """Mixin for pages that show ``_items`` in pages of fixed size.

    Depends on the host providing ``_DEBOUNCE_KEY`` and ``_update_entry(idx)``
    (redraws the 1-based entry), and on :class:`~haui.abstract.haui_page.HAUIPage`
    for listener handling and command batching.
    """

    _DEBOUNCE_KEY: ClassVar[str]

    if TYPE_CHECKING:
        _items: list[HAUIItem]
        _active_items: dict[Any, HAUIItem | None]
        _active_handles: list
        _current_page: int
        _pending_item_updates: set[str]
        debouncer: Debouncer
        panel: HAUIPanel | None
        rec_cmd: AbstractContextManager[None]

        def remove_item_listener(self, handle: str) -> None: ...
        def _update_entry(self, idx: int) -> None: ...

    def _init_paging(self) -> None:
        """Sets the paging defaults; call from ``prepare()``."""
        self._items = []
        self._active_items = {}
        self._active_handles = []
        self._current_page = 0
        self._pending_item_updates = set()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel any pending debounced item-state updates
        self.debouncer.cancel(self._DEBOUNCE_KEY)
        self._pending_item_updates.clear()
        self._clear_item_listeners()

    def _clear_item_listeners(self) -> None:
        while self._active_handles:
            handle = self._active_handles.pop()
            self.remove_item_listener(handle)

    def _page_items(self, page_size: int) -> list[HAUIItem]:
        """Returns the items of the current page."""
        start = int(self._current_page) * page_size
        return self._items[start : start + page_size]

    def _advance_page(self, page_size: int) -> None:
        """Moves to the next page (wrapping) and stores it on the panel."""
        count_pages = math.ceil(len(self._items) / page_size)
        self._current_page += 1
        if self._current_page >= count_pages:
            self._current_page = 0
        if self.panel is not None:
            self.panel.set_state("current_page", self._current_page)

    def callback_item_state(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        item_ids = {
            haui_item.get_item_id()
            for haui_item in self._active_items.values()
            if haui_item is not None
        }
        if item not in item_ids:
            return
        # Coalesce rapid attribute updates into a single redraw to avoid
        # flooding the Nextion UART, which delays touch-event delivery.
        self._pending_item_updates.add(item)
        self.debouncer.call(self._DEBOUNCE_KEY, self._flush_item_updates)

    def _flush_item_updates(self) -> None:
        # Swap pending set first so concurrent adds aren't lost on clear.
        pending = self._pending_item_updates
        if not pending:
            return
        self._pending_item_updates = set()
        with self.rec_cmd:
            idx = 0
            for haui_item in self._active_items.values():
                idx += 1
                if haui_item is None:
                    continue
                if haui_item.get_item_id() in pending:
                    self._update_entry(idx)

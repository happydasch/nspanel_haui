"""Setup and teardown shared by the clock, clocktwo and weather pages.

Module-level functions rather than a base class: the three pages share only
these identical blocks and nothing else of their lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..mapping.background import BACKGROUNDS

if TYPE_CHECKING:
    from ..abstract.haui_panel import HAUIPanel


def background_commands(page: Any, panel: HAUIPanel, page_name: str) -> list[str]:
    """The panel's background, if it is a known one; the page's load code draws it."""
    background = page.render_template(panel.get("background", "dark"), False)
    if background not in BACKGROUNDS:
        return []
    return [f"{page_name}.background.val={BACKGROUNDS[background]}"]


def subscribe_ticks(page: Any, *, with_date: bool = True) -> None:
    """Subscribes to the shared device-wide minute tick (and hour tick for the date)."""
    page.app.subscribe_tick("minute", page.callback_update_time)
    if with_date:
        page.app.subscribe_tick("hour", page.callback_update_date)


def release_ticks(page: Any, *, with_date: bool = True) -> None:
    """Undoes ``subscribe_ticks`` and unregisters the page from the shared notification blinker."""
    page.app.unsubscribe_tick("minute", page.callback_update_time)
    if with_date:
        page.app.unsubscribe_tick("hour", page.callback_update_date)
    page.app.controller["notification"].clear_blinker_callback()

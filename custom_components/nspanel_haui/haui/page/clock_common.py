"""Setup and teardown shared by the clock, clocktwo and weather pages.

Module-level functions rather than a base class: the three pages share only
these identical blocks and nothing else of their lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..mapping.background import BACKGROUNDS

LIGHT_BACKGROUND_TEXT_COLOR = 10565  # RGB565 #282828


def light_background_selected(page: Any, panel: HAUIPanel) -> bool:
    """Whether the panel selects the plain light background."""
    return page.render_template(panel.get("background", "dark"), False) == "light"


def readable_background_text_color(key: str, light: bool) -> int | None:
    """Return a high-contrast text color for a light background, when applicable."""
    if light and key in {"header_text", "component_text", "text"}:
        return LIGHT_BACKGROUND_TEXT_COLOR
    return None


def readable_foreground_color(color: int, light: bool) -> int:
    """Replace pure white foregrounds on the plain light background."""
    if light and color == 65535:
        return LIGHT_BACKGROUND_TEXT_COLOR
    return color


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

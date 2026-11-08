"""Setup and teardown shared by the clock, clocktwo and weather pages.

Module-level functions rather than a base class: the three pages share only
these identical blocks and nothing else of their lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..mapping.background import BACKGROUNDS, background_color_scheme
from ..mapping.descriptor import PageOption, _

LIGHT_BACKGROUND_TEXT_COLOR = 10565  # RGB565 #282828
BACKGROUND_CHOICES = [
    ("scheme", _("Use color scheme")),
    ("dark", _("Dark Color")),
    ("light", _("Light Color")),
    ("modern", _("Modern")),
    ("spring", _("Spring")),
    ("summer", _("Summer")),
    ("autumn", _("Autumn")),
    ("winter", _("Winter")),
    ("dog_1", _("Dog 1")),
    ("dog_2", _("Dog 2")),
    ("cat", _("Cat")),
]


def background_option() -> PageOption:
    """Return the shared background selector used by the clock-style pages."""
    return PageOption(
        key="background",
        kind="select",
        default="dark",
        allow_template=True,
        label=_("Background"),
        description=_("Choose a background image, or use the selected color scheme."),
        choices=BACKGROUND_CHOICES.copy(),
        section=_("Appearance"),
    )


def light_background_selected(page: Any, panel: HAUIPanel) -> bool:
    """Whether a static page background uses the light contrast palette."""
    background = page.render_template(panel.get("background", "dark"), False)
    return background != "scheme" and background_color_scheme(background) == "light"


def set_background_mode(page: Any, panel: HAUIPanel) -> None:
    """Resolve whether this page uses its selected scheme or a static background palette."""
    background = page.render_template(panel.get("background", "dark"), False)
    page._use_color_scheme = background == "scheme"
    page._background_variant = (
        page.app.color_theme.background_variant()
        if page._use_color_scheme
        else background_color_scheme(background)
    )
    page._light_background = page._background_variant == "light"


def readable_background_text_color(
    key: str, light: bool, scheme_color: int = LIGHT_BACKGROUND_TEXT_COLOR
) -> int | None:
    """Return the selected scheme's readable text color for a light background."""
    if light and key in {"header_text", "component_text", "text"}:
        return scheme_color
    return None


def readable_foreground_color(
    color: int,
    light: bool,
    text_color: int = LIGHT_BACKGROUND_TEXT_COLOR,
) -> int:
    """Replace pure white foregrounds on a light background with the scheme text role."""
    if light and color == 65535:
        return text_color
    return color


if TYPE_CHECKING:
    from ..abstract.haui_panel import HAUIPanel


def background_commands(page: Any, panel: HAUIPanel) -> list[str]:
    """Set the shared system-page picture id before loading a background page."""
    background = page.render_template(panel.get("background", "dark"), False)
    if background == "scheme":
        # Picture 0 is the HMI's layout-helper grid, not a blank background.
        # The TFT's solid dark/light fills are picture IDs 1 and 2.
        picture_id = page.app.color_theme.background_picture_id()
    elif background in BACKGROUNDS:
        picture_id = BACKGROUNDS[background]
    else:
        return []
    return [f"system.vBackground.val={picture_id}"]


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

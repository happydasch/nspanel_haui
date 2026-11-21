"""Setup and teardown shared by the clock, clocktwo and weather pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..mapping.background import BACKGROUNDS, background_variant
from ..mapping.descriptor import PageOption, _

LIGHT_BACKGROUND_TEXT_COLOR = 10565  # RGB565 #282828
BACKGROUND_CHOICES = [
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
        description=_("Choose the picture the panel is drawn on."),
        choices=BACKGROUND_CHOICES.copy(),
        section=_("Appearance"),
    )


def background_choice(page: Any, panel: HAUIPanel) -> str:
    """Resolve the panel's background picture.

    Unknown values fall back to the theme's fill, so the display never keeps
    the previous panel's picture.
    """
    background = page.render_template(page.option(panel, "background"), False)
    if background in BACKGROUNDS:
        return background
    page.log(f"Background {background!r} is not a picture; using the theme's fill", level="WARNING")
    return panel.theme.background_variant()


def set_background_mode(page: Any, panel: HAUIPanel) -> None:
    """Resolve the contrast palette paired with the page's background picture."""
    page._background_variant = background_variant(background_choice(page, panel))
    page._light_background = page._background_variant == "light"


def readable_foreground_color(
    color: int,
    light: bool,
    text_color: int = LIGHT_BACKGROUND_TEXT_COLOR,
) -> int:
    """Replace pure white foregrounds on a light background with its palette's text colour."""
    if light and color == 65535:
        return text_color
    return color


if TYPE_CHECKING:
    from ..abstract.haui_panel import HAUIPanel


def background_picture_id(page: Any, panel: HAUIPanel) -> int:
    """Return the picture the page shows as its background."""
    return BACKGROUNDS[background_choice(page, panel)]


def background_commands(page: Any, panel: HAUIPanel) -> list[str]:
    """Set the system picture id first, before the target page's Preinitialize reads it."""
    return [f"system.vBackground.val={background_picture_id(page, panel)}"]


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

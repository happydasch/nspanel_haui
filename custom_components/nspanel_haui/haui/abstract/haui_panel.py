from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from ..mapping.const import PANEL_CONFIG
from ..utils.value import merge_dicts
from .haui_base import HAUIBase

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI


class HAUIPanel(HAUIBase):
    """Represents a panel on the display.

    Its a description of what the page should look like and what
    entities to show. The page implements the logic.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initialize for config panel.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for panel. Defaults to None.
        """
        # build merged config before passing to base - keeps config immutable after init
        cfg = deepcopy(PANEL_CONFIG)
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        super().__init__(app, cfg)
        # store the initial config so apply_kwargs can always reset to it
        self._default_config: dict = deepcopy(cfg)

    # public

    def get_type(self) -> str:
        """Returns the type of this panel.

        Returns:
            str: Type
        """
        return self.get("type")

    def can_show_popup(self) -> bool:
        """Returns True if this panel type supports popup overlay display.

        Single-entity panels (light, climate, media, cover, vacuum, timer)
        and system popup panels return True. Multi-entity panels (grid, row,
        clock, weather) and blank/system pages return False — they display
        as full-page subpanels when show_in_navigation is False.

        Returns:
            bool: True if the panel's page class has can_show_popup set
        """
        from ..mapping.panel import PANEL_MAPPING

        entry = PANEL_MAPPING.get(self.get_type())
        if entry is None:
            return False
        cls = entry[1]
        d = getattr(cls, "DESCRIPTOR", None)
        return d.can_show_popup if d is not None else False

    def show_in_navigation(self) -> bool:
        """Returns True if this panel should appear in the navigation cycle.

        Checks runtime state override first, then falls back to config.
        Defaults to True.

        Returns:
            bool: True if the panel should appear in navigation
        """
        return self.get_state("show_in_navigation", self.get("show_in_navigation", True))

    def get_title(self, default_title: str | None = None) -> str:
        """Returns the title of this panel.

        Args:
            default_title (str, optional): Default title if not set. Defaults to None.

        Returns:
            str: Title
        """
        if default_title is None:
            default_title = self.translate("Unnamed")
        title = self.get("title", "")
        if title == "":
            title = default_title
        return title

    def show_button(self, name: str) -> bool:
        """Returns True if the named button should be shown.

        Falls back to the device-level setting, then False.

        Args:
            name: Button name, e.g. "home", "sleep", "notifications".

        Returns:
            bool: True if the button should be shown
        """
        key = f"show_{name}_button"
        return self.get(key, self.app.device.get(key))

    def show_home_button(self) -> bool:
        """Returns True if home button should be shown."""
        return self.show_button("home")

    def show_sleep_button(self) -> bool:
        """Returns True if sleep button should be shown."""
        return self.show_button("sleep")

    def show_notifications_button(self) -> bool:
        """Returns True if notifications button should be shown."""
        return self.show_button("notifications")

    def apply_kwargs(self, kwargs: dict) -> None:
        """Reset panel config to defaults and apply navigation kwargs.

        Called by the navigation controller each time a panel is opened,
        allowing callers to pass runtime parameters (e.g. entity overrides,
        unlock_panel references) without permanently mutating config.

        Note: kwargs are merged directly without deepcopy - they may contain
        object references (e.g. unlock_panel=<HAUIPanel>) that must stay live.

        Args:
            kwargs: Runtime parameters to overlay on the default config.
        """
        self.config = deepcopy(self._default_config)
        if kwargs:
            merge_dicts(self.config, kwargs)

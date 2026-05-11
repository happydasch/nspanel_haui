from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..mapping.const import PANEL_CONFIG
from ..utils.value import merge_dicts
from .base import HAUIBase
from .item import HAUIItem


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
        # load all entities
        self._items: list[HAUIItem] = []
        # single entity config
        item_val = self.get("item", None)
        if isinstance(item_val, dict):
            # Unified format: {item: "light.x", name: "Kitchen", ...}
            self._items.append(HAUIItem(self.app, item_val))
        elif item_val is not None:
            # Legacy plain string (override fields at panel level)
            self._items.append(HAUIItem(self.app, config))
        # multiple entities config
        for e in self.get("items", []):
            self._items.append(HAUIItem(self.app, e))

    # public

    def get_type(self) -> str:
        """Returns the type of this panel.

        Returns:
            str: Type
        """
        return self.get("type")

    def get_mode(self) -> str:
        """Returns the runtime panel mode. Internal use only.

        Returns "popup" when set by open_popup(), "panel" otherwise.
        Prefer show_in_navigation() for navigation decisions.

        Returns:
            str: Panel mode
        """
        return self.get_state("mode", self.get("mode", "panel"))

    def show_in_navigation(self) -> bool:
        """Returns True if this panel should appear in the navigation cycle.

        Popup panels are always excluded from navigation regardless of
        the show_in_navigation config value. Checks runtime state override
        first, then falls back to config.

        Returns:
            bool: True if the panel should appear in navigation
        """
        # Popup panels are never part of the navigation cycle
        if self.get_state("mode", self.get("mode", "panel")) == "popup":
            return False
        return self.get_state("show_in_navigation",
                              self.get("show_in_navigation", True))

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

    def get_items(self, return_copy: bool = True) -> list[HAUIItem]:
        """Returns all entities from this panel.

        Args:
            return_copy (bool, optional): Copy entities. Defaults to True.

        Returns:
            list: List with entities
        """
        if return_copy:
            return self._items.copy()
        return self._items

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

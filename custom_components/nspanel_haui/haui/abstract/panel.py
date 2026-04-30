from copy import deepcopy

from ..mapping.const import PANEL_CONFIG
from ..utils.value import merge_dicts
from .base import HAUIBase
from .entity import HAUIEntity


class HAUIPanel(HAUIBase):
    """Represents a panel on the display.

    Its a description of what the page should look like and what
    entities to show. The page implements the logic.
    """

    def __init__(self, app, config=None) -> None:
        """Initialize for config panel.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for panel. Defaults to None.
        """
        # build merged config before passing to base — keeps config immutable after init
        cfg = deepcopy(PANEL_CONFIG)
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        super().__init__(app, cfg)
        # store the initial config so apply_kwargs can always reset to it
        self._default_config: dict = deepcopy(cfg)
        # load all entities
        self._entities: list[HAUIEntity] = []
        # single entity config
        if self.get("entity") is not None:
            self._entities.append(HAUIEntity(self.app, config))
        # multiple entities config
        for e in self.get("entities", []):
            self._entities.append(HAUIEntity(self.app, e))

    # public

    def get_type(self) -> str:
        """Returns the type of this panel.

        Returns:
            str: Type
        """
        return self.get("type", "")

    def get_mode(self) -> str:
        """Returns the panel mode.

        Checks runtime state override first (set e.g. by unlock page),
        then falls back to the configured value.

        Possible panel modes:
        - panel (Default)
        - subpanel
        - popup

        Returns:
            str: Panel mode
        """
        return self.get_state("mode", self.get("mode", "panel"))

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

    def is_home_panel(self) -> bool:
        """Returns True if this is the home panel.

        Returns:
            bool: True if home panel
        """
        return self.get("home_panel", False)

    def is_sleep_panel(self) -> bool:
        """Returns True if this is the sleep panel.

        Returns:
            bool: True if sleep panel
        """
        return self.get("sleep_panel", False)

    def is_wakeup_panel(self) -> bool:
        """Returns True if this is the wakeup panel.

        Returns:
            bool: True if wakeup panel
        """
        return self.get("wakeup_panel", False)

    def show_button(self, name: str) -> bool:
        """Returns True if the named button should be shown.

        Falls back to the device-level setting, then False.

        Args:
            name: Button name, e.g. "home", "sleep", "notifications".

        Returns:
            bool: True if the button should be shown
        """
        key = f"show_{name}_button"
        return self.get(key, self.app.device.get(key, False))

    def show_home_button(self) -> bool:
        """Returns True if home button should be shown."""
        return self.show_button("home")

    def show_sleep_button(self) -> bool:
        """Returns True if sleep button should be shown."""
        return self.show_button("sleep")

    def show_notifications_button(self) -> bool:
        """Returns True if notifications button should be shown."""
        return self.show_button("notifications")

    def get_entities(self, return_copy=True) -> list[HAUIEntity]:
        """Returns all entities from this panel.

        Args:
            return_copy (bool, optional): Copy entities. Defaults to True.

        Returns:
            list: List with entities
        """
        if return_copy:
            return self._entities.copy()
        return self._entities

    def apply_kwargs(self, kwargs: dict) -> None:
        """Reset panel config to defaults and apply navigation kwargs.

        Called by the navigation controller each time a panel is opened,
        allowing callers to pass runtime parameters (e.g. entity overrides,
        unlock_panel references) without permanently mutating config.

        Note: kwargs are merged directly without deepcopy — they may contain
        object references (e.g. unlock_panel=<HAUIPanel>) that must stay live.

        Args:
            kwargs: Runtime parameters to overlay on the default config.
        """
        self.config = deepcopy(self._default_config)
        if kwargs:
            merge_dicts(self.config, kwargs)

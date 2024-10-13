from copy import deepcopy
from typing import List, Dict

from ..mapping.const import PANEL_CONFIG
from ..helper.value import merge_dicts

from .base import HAUIBase
from .entity import HAUIEntity


class HAUIPanel(HAUIBase):

    """ Represents a panel on the display.

    Its a description of what the page should look like and what
    entities to show. The page implements the logic.
    """

    def __init__(self, app, config=None):
        """Initialize for config panel.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for panel. Defaults to None.
        """
        # initialize with default panel values
        super().__init__(app, deepcopy(PANEL_CONFIG))
        # load config
        if config is not None:
            merge_dicts(self.config, config)
        # store the initial config in an additional var
        # so it is possible to restore the config to initial values
        self._default_config: dict = {}
        merge_dicts(self._default_config, self.config)
        # store persistent config
        self._persistent_config: dict = {}
        # load all entities
        self._entities: List[HAUIEntity] = []  # list of HAUIConfigEntity
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

        Possible panel modes:
        - panel (Default)
        - subpanel
        - popup

        Returns:
            str: Panel mode
        """
        return self.get("mode", "panel")

    def get_title(self, default_title: str = None) -> str:
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

    def show_home_button(self) -> bool:
        """Returns True if home button should be shown.

        Returns:
            bool: True if home button should be shown
        """
        show_home_button = self.get(
            "show_home_button", self.app.device.get("show_home_button", False)
        )
        return show_home_button

    def show_notifications_button(self) -> bool:
        """Returns True if notifications button should be shown.

        Returns:
            bool: True if notifications button should be shown
        """
        show_notifications_button = self.get(
            "show_notifications_button", self.app.device.get("show_notifications_button", False)
        )
        return show_notifications_button

    def get_entities(self, return_copy=True) -> List[HAUIEntity]:
        """Returns all entities from this panel.

        Args:
            return_copy (bool, optional): Copy entities. Defaults to True.

        Returns:
            list: List with entities
        """
        if return_copy:
            return self._entities.copy()
        return self._entities

    def get_default_config(self, return_copy=True) -> Dict:
        """Returns the initial config of this panel.

        Returns:
            dict: Initial config
            return_copy (bool, optional): Return copy of config. Defaults to True.
        """
        if return_copy:
            return self._default_config.copy()
        return self._default_config

    def get_persistent_config(self, return_copy=True) -> Dict:
        """Returns the persistent config of this panel.

        Returns:
            dict: Persistent config
            return_copy (bool, optional): Return copy of config. Defaults to True.
        """
        if return_copy:
            return self._persistent_config.copy()
        return self._persistent_config

    def restore_default_config(self) -> Dict:
        """Restore the initial config of this panel."""
        self.config = self.get_default_config(return_copy=True)

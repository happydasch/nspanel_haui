from copy import deepcopy
from typing import List

from ..helper.value import merge_dicts
from ..mapping.const import DEFAULT_CONFIG

from .base import HAUIBase
from .entity import HAUIConfigEntity
from .panel import HAUIConfigPanel


class HAUIConfig(HAUIBase):

    """
    Configuration helper
    """

    def __init__(self, app, config=None):
        """Initialize for config.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config. Defaults to None.
        """
        # initialize with default config
        super().__init__(app, deepcopy(DEFAULT_CONFIG))
        # load config
        if config is not None:
            merge_dicts(self.get_config(return_copy=False), config)
        # load all panels
        self._panels: List[HAUIConfigPanel] = []
        panels_to_load = self.get("panels", [])
        # append sys_panels so they can be overwritten by panels
        panels_to_load += self.get("sys_panels", [])
        for panel_config in panels_to_load:
            panel = HAUIConfigPanel(self.app, panel_config)
            self._panels.append(panel)

    # public

    def get_panels(self, filter_nav_panel=None) -> List[HAUIConfigPanel]:
        """Returns all panels as HAUIConfigPanel objects.

        Args:
            filter_nav_panel (bool, optional): Filter panels panel_nav attr. Defaults to None.

        Returns:
            list: List with panels
        """
        if filter_nav_panel is not None:
            # provide a filtered list if nav_panel provided
            # True means only nav_panels will be returned, False non nav_panels
            nav_panels = list(
                filter(
                    lambda panel: (filter_nav_panel and panel.get_mode() == "panel")
                    or (not filter_nav_panel and panel.get_mode() != "panel"),
                    self._panels,
                )
            )
            return nav_panels
        return self._panels

    def get_entities(self) -> List[HAUIConfigEntity]:
        """Returns all entities as HAUIConfigEntity objects.

        Returns:
            list: List with entities
        """
        entities = []
        for panel in self._panels:
            entities.extend(panel.get_entities())
        return entities

    def get_entity(self, entity_id) -> HAUIConfigEntity:
        """Returns a single entity.

        Args:
            entity_id (str): Entity id

        Returns:
            HAUIConfigEntity: Entity
        """
        for entity in self.get_entities():
            if entity.id == entity_id:
                return entity
        return None

    def get_panel(self, panel_id) -> HAUIConfigPanel:
        """Returns a single panel.

        Args:
            panel_id (str): Panel id or key

        Returns:
            HAUIConfigPanel: Panel
        """
        for panel in self._panels:
            # get by id
            if panel.id == panel_id:
                return panel
            # get by key
            if panel.get("key", "") == panel_id:
                return panel
        return None

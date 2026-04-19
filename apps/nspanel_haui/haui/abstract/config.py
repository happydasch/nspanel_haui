from copy import deepcopy

from ..config_models import validate_config
from ..helper.value import merge_dicts
from ..mapping.const import DEFAULT_CONFIG
from .base import HAUIBase
from .entity import HAUIEntity
from .panel import HAUIPanel


class HAUIConfig(HAUIBase):
    """HAUI Configuration."""

    def __init__(self, app, config=None) -> None:
        """Initialize for config.

        Args:
        app (NSPanelHAUI): App
        config (dict, optional): Config. Defaults to None.
        """
        # build merged config before passing to base — keeps config immutable after init
        cfg = deepcopy(DEFAULT_CONFIG)
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        super().__init__(app, cfg)
        # validate after base init so self.app etc. are available
        validate_config(cfg)
        # load all panels
        self._panels: list[HAUIPanel] = []
        self._panels_by_id: dict = {}
        self._panels_by_key: dict[str, HAUIPanel] = {}
        # user panels first: when a sys_panel shares a key with a user panel
        # the user panel wins and the duplicated sys_panel is skipped
        panels_to_load = self.get("panels", [])
        panels_to_load += self.get("sys_panels", [])
        for panel_config in panels_to_load:
            panel = HAUIPanel(self.app, panel_config)
            key = panel.get("key", "")
            if key and key in self._panels_by_key:
                continue
            self._panels.append(panel)
            self._panels_by_id[panel.id] = panel
            if key:
                self._panels_by_key[key] = panel

    # public

    # TODO update config based on time

    def get_panels(self, filter_nav_panel=None) -> list[HAUIPanel]:
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
                    lambda panel: (
                        (filter_nav_panel and panel.get_mode() == "panel")
                        or (not filter_nav_panel and panel.get_mode() != "panel")
                    ),
                    self._panels,
                )
            )
            return nav_panels
        return self._panels

    def get_entities(self) -> list[HAUIEntity]:
        """Returns all entities as HAUIConfigEntity objects.

        Returns:
            list: List with entities
        """
        entities = []
        for panel in self._panels:
            entities.extend(panel.get_entities())
        return entities

    def get_entity(self, entity_id: str) -> HAUIEntity | None:
        """Returns a single entity.

        Args:
            entity_id (str): Entity id

        Returns:
            HAUIEntity | None: Entity or None
        """
        for entity in self.get_entities():
            if entity.id == entity_id:
                return entity
        return None

    def get_panel(self, panel_id) -> HAUIPanel | None:
        """Returns a single panel by id (UUID) or key (str).

        Args:
            panel_id: Panel id (UUID) or key (str)

        Returns:
            HAUIPanel | None: Panel or None
        """
        return self._panels_by_id.get(panel_id) or self._panels_by_key.get(panel_id)

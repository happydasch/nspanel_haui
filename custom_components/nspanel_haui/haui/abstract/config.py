from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..config_models import validate_config
from ..mapping.const import DEFAULT_CONFIG
from ..utils.value import merge_dicts
from .base import HAUIBase
from .panel import HAUIPanel


class HAUIConfig(HAUIBase):
    """HAUI Configuration."""

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initialize for config.

        Args:
        app (NSPanelHAUI): App
        config (dict, optional): Config. Defaults to None.
        """
        # build merged config before passing to base - keeps config immutable after init
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
        panels_to_load = self.get("panels")
        panels_to_load += self.get("sys_panels")
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

    def get_panels(self, filter_nav_panel: bool | None = None) -> list[HAUIPanel]:
        """Returns all panels as HAUIPanel objects.

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
                        (filter_nav_panel and panel.show_in_navigation())
                        or (not filter_nav_panel and not panel.show_in_navigation())
                    ),
                    self._panels,
                )
            )
            return nav_panels
        return self._panels

    def get_panel(self, panel_id: UUID | str) -> HAUIPanel | None:
        """Returns a single panel by id (UUID) or key (str).

        Args:
            panel_id: Panel id (UUID) or key (str)

        Returns:
            HAUIPanel | None: Panel or None
        """
        if isinstance(panel_id, UUID):
            return self._panels_by_id.get(panel_id)
        return self._panels_by_key.get(panel_id)

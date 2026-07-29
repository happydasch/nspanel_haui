from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..config_models import validate_config
from ..mapping.const import DEFAULT_CONFIG
from ..utils.value import merge_dicts
from .haui_config_access import HAUIConfigAccess
from .haui_panel import HAUIPanel


class HAUIConfig(HAUIConfigAccess):
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
        # Always populate sys_panels from page descriptors when the list
        # is empty, since device._check_config() requires them all.
        if not cfg.get("sys_panels"):
            from ..mapping.panel import build_sys_panels_defaults

            cfg["sys_panels"] = build_sys_panels_defaults()
        # validate after base init so self.app etc. are available
        validate_config(cfg)
        # load all panels
        panels_to_load = self.get("panels")
        panels_to_load += self.get("sys_panels")
        self._panels, self._panels_by_id, self._panels_by_key = (
            self._build_panel_lists(self.app, panels_to_load)
        )

    @staticmethod
    def _build_panel_lists(
        app: NSPanelHAUI, panel_configs: list[dict[str, Any]]
    ) -> tuple[list[HAUIPanel], dict, dict[str, HAUIPanel]]:
        """Build panel lists and lookup dicts from panel configs.

        User panels take precedence over system panels with the same key.
        The first panel with a given key wins; subsequent duplicates are skipped.
        This de-duplication means user panels override system panels when they
        share a key.

        Args:
            app: The NSPanelHAUI application instance.
            panel_configs: List of panel config dicts.

        Returns:
            Tuple of (panels_list, panels_by_id, panels_by_key).
        """
        panels: list[HAUIPanel] = []
        panels_by_id: dict = {}
        panels_by_key: dict[str, HAUIPanel] = {}
        for panel_config in panel_configs:
            panel = HAUIPanel(app, panel_config)
            key = panel.get("key", "")
            if key and key in panels_by_key:
                continue
            panels.append(panel)
            panels_by_id[panel.id] = panel
            if key:
                panels_by_key[key] = panel
        return panels, panels_by_id, panels_by_key

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

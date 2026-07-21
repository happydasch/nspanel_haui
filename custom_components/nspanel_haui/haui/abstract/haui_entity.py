"""Representation of a single Home Assistant entity with optional config overrides."""

from __future__ import annotations

import re
import threading
from typing import TYPE_CHECKING, Any

from ..utils.color import rgb_to_rgb565

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI


class HAUIEntity:
    """Represents a single Home Assistant entity.

    Provides a synchronous interface for accessing entity state, attributes,
    and calling services.  All Home Assistant API access is bridged through
    ``self._app`` (the HAAdapter), so the core thread never touches HA's
    async API directly.

    This class is intentionally lightweight - it does *not* extend
    ``HAUIBase`` because it doesn't need config merging, display transport,
    or command batching.
    """

    def __init__(self, app: NSPanelHAUI, entity_id: str, config: dict | None = None) -> None:
        """Initialize a HA entity representation.

        Args:
            app: The NSPanelHAUI application instance (HAAdapter bridge).
            entity_id: The HA entity id, e.g. ``"light.kitchen"``.
            config: Optional override config (name, icon, color, state, value keys).
        """
        self._app = app
        self._entity_id = entity_id
        if not isinstance(entity_id, str) or "." not in entity_id:
            raise ValueError(f"Invalid entity_id: {entity_id!r}")
        self._entity_type = entity_id.split(".")[0]
        self._config = config or {}

    # -- public ---------------------------------------------------------------

    def has_entity(self) -> bool:
        """Check whether this entity exists in Home Assistant.

        Returns:
            True if the entity is registered in HA's state machine.
        """
        return self._app.item_exists(self._entity_id)

    def get_entity(self) -> Any:
        """Return the synchronous entity proxy (ItemProxy).

        Returns:
            The ``ItemProxy`` for this entity, or ``None`` if it doesn't exist.
        """
        if self.has_entity():
            return self._app.get_item(self._entity_id)
        return None

    def get_entity_id(self) -> str:
        """Return the entity id.

        Returns:
            The entity id, e.g. ``"light.kitchen"``.
        """
        return self._entity_id

    def get_entity_type(self) -> str:
        """Return the HA domain (the first part of the entity id).

        Returns:
            The domain, e.g. ``"light"``.
        """
        return self._entity_type

    def get_entity_attr(self, attr: str | list[str], default: Any = None) -> Any:
        """Read a value from the entity's attributes dict.

        Supports nested attribute access via a list of keys (see
        ``HAUIItem.get_item_attr`` for examples).

        Args:
            attr: An attribute name or a list of keys for nested access.
            default: Value returned when the entity or attribute is missing.

        Returns:
            The attribute value, or *default*.
        """
        entity = self.get_entity()
        if entity is None:
            self._app.log(
                f"Entity '{self._entity_id}' not available for attr '{attr}'",
                level="WARNING",
            )
            return default
        if isinstance(attr, str):
            res = entity.attributes.get(attr)
        elif isinstance(attr, list):
            res = entity.attributes
            for a in attr:
                if res is None:
                    break
                try:
                    res = res[a]
                except (IndexError, KeyError, TypeError):
                    res = None
                    break
        else:
            res = None
        return default if res is None else res

    def get_entity_state(self) -> str | None:
        """Return the entity's current state.

        Returns:
            The state string, or ``None`` if the entity doesn't exist.
        """
        entity = self.get_entity()
        if entity is None:
            self._app.log(f"Entity '{self._entity_id}' not available for state", level="WARNING")
            return None
        return entity.get_state()

    # -- display value helpers (with config overrides) --------------------------

    def _get_config(self, key: str, default: Any = None) -> Any:
        """Read a value from config, returning *default* when missing or empty."""
        val = self._config.get(key, default)
        return val if val else default

    def get_name(self) -> str:
        """Return the display name, using config override or entity friendly_name.

        Returns:
            The name string, or empty string if unavailable.
        """
        cfg_name = self._get_config("name")
        if cfg_name:
            return cfg_name
        entity = self.get_entity()
        if entity is not None:
            return entity.get_name()
        return ""

    def get_icon(self) -> str:
        """Return the display icon, using config override or entity-derived icon.

        Returns:
            The icon string (mdi:...), or empty string if unavailable.
        """
        cfg_icon = self._get_config("icon")
        if cfg_icon:
            return cfg_icon
        entity = self.get_entity()
        if entity is not None:
            # Return the entity's icon attribute if available
            icon_attr = entity.attributes.get("icon", "")
            return str(icon_attr) if icon_attr else ""
        return ""

    def get_color(self) -> int | None:
        """Return the display color, using config override or state-based color.

        Returns:
            RGB565 color int, or None.
        """
        cfg_color = self._get_config("color")
        if cfg_color is not None:
            # Parse bracket "[r,g,b]" and hex "#rrggbb" formats to RGB565 int
            if isinstance(cfg_color, str) and cfg_color:
                rgb_match = re.match(
                    r"\[\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]",
                    cfg_color.strip(),
                )
                if rgb_match:
                    return rgb_to_rgb565(
                        [
                            int(rgb_match.group(1)),
                            int(rgb_match.group(2)),
                            int(rgb_match.group(3)),
                        ]
                    )
                if re.match(r"^#([0-9a-fA-F]{6})$", cfg_color.strip()):
                    hex_str = cfg_color.strip()[1:]
                    return rgb_to_rgb565(
                        [
                            int(hex_str[0:2], 16),
                            int(hex_str[2:4], 16),
                            int(hex_str[4:6], 16),
                        ]
                    )
                if isinstance(cfg_color, int):
                    return cfg_color
            if isinstance(cfg_color, int):
                return cfg_color
        # Fall back to entity state-based color
        entity = self.get_entity()
        if entity is not None:
            state = entity.get_state()
            if state:
                from ..mapping.color import COLORS  # noqa: PLC0415

                return COLORS.get(state.lower(), COLORS.get("default", None))
        return None

    def get_value(self) -> str:
        """Return the display value, using config override or entity state.

        Returns:
            The value string, or empty string.
        """
        cfg_value = self._get_config("value")
        if cfg_value:
            return cfg_value
        entity = self.get_entity()
        if entity is not None:
            return entity.get_state() or ""
        return ""

    def get_state_override(self) -> str | None:
        """Return the state override key from config, if set.

        When non-None, the page should use this attribute key to read
        the entity's state from its attributes rather than from the
        top-level state.

        Returns:
            The attribute key string, or None.
        """
        return self._get_config("state")

    def call_entity_service(self, service: str, **kwargs: Any) -> None:
        """Call a service on this entity.

        The service call is dispatched on a daemon thread so the ESPHome
        dispatch thread isn't blocked while Home Assistant processes the
        request - some integrations (e.g. Sonos ``select_source``) can take
        many seconds.

        Args:
            service: The service name, e.g. ``"turn_on"``.
            **kwargs: Additional keyword arguments for the service.
        """
        entity = self.get_entity()
        if entity is None:
            self._app.log(
                f"Entity '{self._entity_id}' not available for service '{service}'",
                level="WARNING",
            )
            return
        threading.Thread(
            target=entity.call_service,
            args=(service,),
            kwargs=kwargs,
            daemon=True,
        ).start()

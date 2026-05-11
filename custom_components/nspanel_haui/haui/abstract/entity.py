from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

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

    def __init__(self, app: NSPanelHAUI, entity_id: str) -> None:
        """Initialize a HA entity representation.

        Args:
            app: The NSPanelHAUI application instance (HAAdapter bridge).
            entity_id: The HA entity id, e.g. ``"light.kitchen"``.
        """
        self._app = app
        self._entity_id = entity_id
        if not isinstance(entity_id, str) or "." not in entity_id:
            raise ValueError(f"Invalid entity_id: {entity_id!r}")
        self._entity_type = entity_id.split(".")[0]

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
                if a in res:
                    res = res[a]
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

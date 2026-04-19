from copy import deepcopy
from typing import Any

from appdaemon.entity import Entity

from ..helper.color import rgb_to_rgb565
from ..helper.entity import (
    execute_entity,
    get_entity_color,
    get_entity_icon,
    get_entity_name,
    get_entity_value,
)
from ..helper.text import get_state_translation
from ..helper.value import merge_dicts
from ..mapping.color import COLORS
from ..mapping.const import (
    ENTITY_CONFIG,
    INTERNAL_ENTITY_TYPE,
)
from .base import HAUIBase


class HAUIEntity(HAUIBase):
    """Represents a entity from a panel"""

    def __init__(self, app, config=None) -> None:
        """Initialize for config entity.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for entity. Defaults to None.
        """
        # build merged config before passing to base — keeps config immutable after init
        cfg = deepcopy(ENTITY_CONFIG)
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        super().__init__(app, cfg)
        # type of entity
        self._internal: bool = False  # is it an internal entity
        self._internal_type: str | None = None  # internal entity type
        self._internal_data: str = ""  # internal entity data
        self._entity_type: str | None = None  # entity type
        self._entity_id: str | None = None  # entity id
        # prepare the entity
        self._prepare_entity(self.get("entity"))

    def _dbg(self, msg: str) -> None:
        """Log a debug message when log_entities is enabled in device config."""
        device = getattr(self.app, "device", None)
        if device and device.get("log_entities"):
            self.log(msg)

    def _prepare_entity(self, entity_id: str) -> None:
        """Prepares internal values from entity.

        Args:
            entity_id (str): The entity id
        """
        if entity_id is None:
            self._internal = True
            self._internal_type = "skip"
            self._dbg("Entity: None -> skip")
            return

        # check if entity is internal
        for internal in INTERNAL_ENTITY_TYPE:
            if entity_id == internal or entity_id.startswith(f"{internal}:"):
                self._internal = True
                self._internal_type = internal
                break
        if self._internal:
            if ":" in entity_id:
                self._internal_data = "".join(entity_id.split(":")[1:])
            self._dbg(
                f"Entity: {entity_id} -> internal type={self._internal_type} data={self._internal_data!r}"
            )
        else:
            self._entity_id = entity_id
            self._entity_type = entity_id.split(".")[0]
            self._dbg(f"Entity: {entity_id} -> external type={self._entity_type}")

    def execute(self):
        """Executes the entity."""
        # internal entity
        if self.is_internal():
            internal_type = self.get_internal_type()
            internal_data = self.get_internal_data()
            # check internal
            if internal_type == "navigate":
                # internal navigate to using key
                navigation = self.app.controller["navigation"]
                navigation.open_panel(internal_data)
            elif internal_type == "action":
                # internal action to run
                action_data = self.get("action_data", {})
                action_call = internal_data.replace(".", "/", 1)
                self.app.call_service(action_call, **action_data)

        # external entity
        else:
            # execute external entity
            execute_entity(self)

    def is_internal(self) -> bool:
        """Returns if the entity is internal.

        Returns:
            bool: True if internal
        """
        return self._internal

    def get_internal_type(self) -> str:  # TODO return None
        """Returns the internal entity type.

        Returns:
            str: Internal Entity Type
        """
        return self._internal_type or ""

    def get_internal_data(self) -> str:
        """Returns the internal entity data.

        Returns:
            str: Internal Entity Data
        """
        return self._internal_data

    def has_entity_id(self) -> bool:
        """Returns if a entity id is available.

        Returns:
            bool: True if entity id is available
        """
        return self._entity_id is not None

    def get_entity_id(self) -> str:  # TODO return None
        """Returns the entity id, or empty string if not set.

        Check has_entity_id() first if you need to distinguish an unset id.

        Returns:
            str: entity id (empty if unset)
        """
        return self._entity_id or ""

    def has_entity(self) -> bool:
        """Returns if a entity is available.

        Returns:
            bool: True if entity is available
        """
        return self._entity_id is not None and self.app.entity_exists(self._entity_id)

    def get_entity(self) -> Entity | None:
        """Returns the entity.

        Returns:
            Entity: Entity
        """
        if self.has_entity() and self._entity_id is not None:
            return self.app.get_entity(self._entity_id)
        return None

    def get_entity_type(self) -> str:
        """Returns the type of the entity.

        The entity type is the first part of the entity id.

        Returns:
            str: Entity Type
        """
        return self._entity_type or ""

    def get_entity_attr(self, attr, default: Any = None) -> Any:  # TODO or None
        """Returns a value from the attributes dict.

        The attribute value can be either a string or a list of strings. Using
        a single str, the attribute with that name will be returned. Using a list
        will return the value of a more complex attribute.

        For example:

            ```
            self.get_entity_attr("temperature")
            returns: entity.attributes.temperature

            self.get_entity_attr(["forecast", 1, "temperature"])
            returns entity.attributes.forecast[1].temperature
            ```

        Args:
            attr (str|list): The attribute to return the value for
            default (any, optional): Default value. Defaults to None.

        Returns:
            str: Value of entity attribute
        """
        if not self.has_entity():
            return default
        entity = self.get_entity()
        if entity is None:
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
        if res is None:
            return default
        return res

    def get_entity_state(self) -> str | None:
        """Returns the state of the entity, or None if unavailable.

        Returns:
            str | None: Entity State
        """
        if not self.has_entity():
            return None
        state = self.get("state", "")
        if state == "":
            entity = self.get_entity()
            if entity is None:
                return None
            return entity.get_state()
        # state is overriden
        return self.get_entity_attr(state, None)

    def call_entity_service(self, service: str, **kwargs) -> None:
        """Calls a service on the entity.

        Args:
            service (str): Service to call
            **kwargs (any): Service arguments
        """
        if not self.has_entity():
            return
        entity = self.get_entity()
        if entity is None:
            return
        entity.call_service(service, **kwargs)

    def _resolve_state_field(self, key: str, default: str = "") -> str:
        """Resolve a config field that may be state-based (dict) or a template string.

        1. Reads the field from config.
        2. If the value is a dict, looks up the current entity state as a key.
        3. If the result is a non-empty string, renders it as a template.

        Args:
            key: Config key to look up.
            default: Value to return when nothing is found.

        Returns:
            str: Resolved value.
        """
        value = self.get(key, default)
        if isinstance(value, dict):
            value = value.get(self.get_entity_state(), default)
        if isinstance(value, str) and value:
            return self.render_template(value)
        return default

    def get_value(self) -> str:
        """Returns the value of the entity.

        Returns:
            str: The value
        """
        value = self._resolve_state_field("value")

        # internal text entity
        if not value and self.is_internal() and self.get_internal_type() == "text":
            value = self.get_internal_data()

        return value or get_entity_value(self, "")

    def get_name(self) -> str:
        """Returns the name of the entity.

        Returns:
            str: Name of the entity
        """
        name = self._resolve_state_field("name")

        # internal navigate entity uses panel title
        if not name and self.is_internal():
            if self.get_internal_type() == "navigate":
                panel = self.app.device_config.get_panel(self.get_internal_data())
                if panel:
                    name = panel.get_title()

        return name or get_entity_name(self, "")

    def get_color(self) -> int:
        """Returns the color of the entity.

        Returns:
            int: the color of the entry in rgb565
        """
        color = self.get("color")
        if isinstance(color, dict):
            color = color.get(self.get_entity_state())
        if isinstance(color, str) and color:
            color = self.render_template(color)
        elif isinstance(color, list) and len(color) == 3:
            color = rgb_to_rgb565(color)
        return color or get_entity_color(self, COLORS["entity_unavailable"])

    def get_icon(self) -> str:
        """Returns the icon of the entry.

        Returns:
            str: Icon chr of entry
        """
        icon = self._resolve_state_field("icon")
        return icon or get_entity_icon(self, "alert-circle-outline")

    def translate_entity_state(self) -> str:
        """Returns the translation of this entity's current state.

        Returns:
            str: Translated state
        """
        if not self.has_entity():
            return ""
        return get_state_translation(
            self.get_entity_type(), self.get_entity_state(), self.get_locale()
        )

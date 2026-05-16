from __future__ import annotations

import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..mapping.color import COLORS
from ..mapping.const import ITEM_CONFIG, InternalItemType
from ..utils.color import rgb_to_rgb565
from ..utils.item import execute_item, get_item_color, get_item_icon, get_item_name, get_item_value
from ..utils.text import get_state_translation
from ..utils.value import merge_dicts
from .base import HAUIBase
from .entity import HAUIEntity


class HAUIItem(HAUIBase):
    """Represents an item from a panel"""

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initialize for config entity.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for item. Defaults to None.
        """
        # build merged config before passing to base - keeps config immutable after init
        cfg = deepcopy(ITEM_CONFIG)
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        # Strip empty value field so the runtime correctly falls through
        # to entity-derived display values.
        if not cfg.get("value"):
            cfg.pop("value", None)
        super().__init__(app, cfg)
        # type of item
        self._internal: bool = False  # is it an internal item
        self._internal_type: str | None = None  # internal item type
        self._internal_data: str = ""  # internal item data
        self._item_type: str | None = None  # item type
        self._item_id: str | None = None  # item id
        self._entity: HAUIEntity | None = None  # entity representation (external items only)
        # prepare the item
        self._prepare_item(self.get("item", None))

    def _dbg(self, msg: str) -> None:
        """Log a debug message when log_items is enabled in device config."""
        device = getattr(self.app, "device", None)
        if device and device.get("log_items"):
            self.log(msg)

    def _prepare_item(self, item_id: str | None) -> None:
        """Prepares internal values from entity.

        Args:
            item_id: The item id (string entity id, internal prefix, or None).
        """
        if not isinstance(item_id, str):
            self._internal = True
            self._internal_type = "skip"
            return

        # check if item is internal
        for internal in InternalItemType:
            if item_id == internal or item_id.startswith(f"{internal}:"):
                self._internal = True
                self._internal_type = internal
                break
        if self._internal:
            if ":" in item_id:
                self._internal_data = "".join(item_id.split(":")[1:])
            self._dbg(
                f"Item: {item_id} ->"
                f" internal type={self._internal_type} data={self._internal_data!r}"
            )
        else:
            self._item_id = item_id
            self._item_type = item_id.split(".")[0]
            self._entity = HAUIEntity(self.app, item_id)
            self._dbg(f"Item: {item_id} -> external type={self._item_type}")

    def execute(self) -> None:
        """Executes the item."""
        # internal item
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

        # external item
        else:
            # execute external item
            execute_item(self)

    def is_internal(self) -> bool:
        """Returns if the entity is internal.

        Returns:
            bool: True if internal
        """
        return self._internal

    def get_internal_type(self) -> str:
        """Returns the internal entity type.

        Returns:
            str: Internal Item Type
        """
        return self._internal_type or ""

    def get_internal_data(self) -> str:
        """Returns the internal entity data.

        Returns:
            str: Internal Item Data
        """
        return self._internal_data

    def has_item_id(self) -> bool:
        """Returns if a entity id is available.

        Returns:
            bool: True if item id is available
        """
        return self._item_id is not None

    def get_item_id(self) -> str:
        """Returns the entity id, or empty string if not set.

        Check has_item_id() first if you need to distinguish an unset id.

        Returns:
            str: item id (empty if unset)
        """
        if self._entity is not None:
            return self._entity.get_entity_id()
        return self._item_id or ""

    def has_item(self) -> bool:
        """Returns if a entity is available.

        Returns:
            bool: True if item is available
        """
        if self._entity is not None:
            return self._entity.has_entity()
        return False

    def get_item(self) -> Any:
        """Returns the entity.

        Returns:
            Entity: Entity
        """
        if self._entity is not None:
            return self._entity.get_entity()
        return None

    def get_item_type(self) -> str:
        """Returns the type of the entity.

        The item type is the first part of the item id.

        Returns:
            str: Item Type
        """
        if self._entity is not None:
            return self._entity.get_entity_type()
        return self._item_type or ""

    def get_item_attr(self, attr: str | list[str], default: Any = None) -> Any:
        """Returns a value from the attributes dict.

        The attribute value can be either a string or a list of strings. Using
        a single str, the attribute with that name will be returned. Using a list
        will return the value of a more complex attribute.

        For example:

            ```
            self.get_item_attr("temperature")
            returns: entity.attributes.temperature

            self.get_item_attr(["forecast", 1, "temperature"])
            returns entity.attributes.forecast[1].temperature
            ```

        Args:
            attr (str|list): The attribute to return the value for
            default (any, optional): Default value. Defaults to None.

        Returns:
            str: Value of item attribute
        """
        if self._entity is not None:
            return self._entity.get_entity_attr(attr, default)
        return default

    def get_item_state(self) -> str | None:
        """Returns the state of the entity, or None if unavailable.

        Returns:
            str | None: Item State
        """
        if self._entity is None:
            return None
        state = self.get("state", "")
        if state == "":
            return self._entity.get_entity_state()
        # state is overridden - use config state key as an attribute lookup
        return self._entity.get_entity_attr(state, None)

    def call_item_service(self, service: str, **kwargs: Any) -> None:
        """Calls a service on the entity.

        The call is dispatched on a daemon thread so the ESPHome dispatch thread
        isn't blocked while Home Assistant completes the service - some
        integrations (e.g. Sonos `select_source`) can take many seconds,
        which would stall heartbeats and trip a false disconnect.

        Args:
            service (str): Service to call
            **kwargs (any): Service arguments
        """
        if self._entity is not None:
            self._entity.call_entity_service(service, **kwargs)

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
            value = value.get(self.get_item_state(), default)
        if isinstance(value, str) and value:
            return self.render_template(value)
        return default

    def get_value(self) -> str:
        """Returns the value of the entity.

        Returns:
            str: The value
        """
        value = self._resolve_state_field("value")

        # internal text item
        if not value and self.is_internal() and self.get_internal_type() == "text":
            value = self.get_internal_data()

        return value if value is not None else get_item_value(self, "")

    def get_name(self) -> str:
        """Returns the name of the entity.

        Returns:
            str: Name of the item
        """
        name = self._resolve_state_field("name")

        # internal navigate item uses panel title
        if not name and self.is_internal():
            if self.get_internal_type() == "navigate":
                panel = self.app.device_config.get_panel(self.get_internal_data())
                if panel:
                    name = panel.get_title()

        return name or get_item_name(self, "")

    def get_color(self) -> int:
        """Returns the color of the entity.

        Returns:
            int: the color of the entry in rgb565
        """
        color = self.get("color", None)
        if isinstance(color, dict):
            color = color.get(self.get_item_state())
        if isinstance(color, str) and color:
            color = self.render_template(color)
            # Parse bracket "[r,g,b]" and hex "#rrggbb" formats to RGB565 int
            if isinstance(color, str) and color:
                rgb_match = re.match(
                    r"\[\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]",
                    color.strip(),
                )
                if rgb_match:
                    color = rgb_to_rgb565(
                        [
                            int(rgb_match.group(1)),
                            int(rgb_match.group(2)),
                            int(rgb_match.group(3)),
                        ]
                    )
                elif re.match(r"^#([0-9a-fA-F]{6})$", color.strip()):
                    hex_str = color.strip()[1:]
                    color = rgb_to_rgb565(
                        [
                            int(hex_str[0:2], 16),
                            int(hex_str[2:4], 16),
                            int(hex_str[4:6], 16),
                        ]
                    )
        elif isinstance(color, list) and len(color) == 3:
            color = rgb_to_rgb565(color)
        return color if color is not None else get_item_color(self, COLORS["item_unavailable"])

    def get_icon(self) -> str:
        """Returns the icon of the entry.

        Returns:
            str: Icon chr of entry
        """
        icon = self._resolve_state_field("icon")
        return icon or get_item_icon(self, "alert-circle-outline")

    def translate_item_state(self) -> str:
        """Returns the translation of this entity's current state.

        Returns:
            str: Translated state
        """
        if self._entity is None:
            return ""
        return get_state_translation(
            self.get_item_type(), self.get_item_state() or "", self.get_locale()
        )

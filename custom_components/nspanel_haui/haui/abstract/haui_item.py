from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, overload

from ..mapping.const import InternalItemType
from ..mapping.item_options import ItemOptions
from ..utils.color import parse_color_value
from ..utils.item import execute_item, get_item_color, get_item_icon, get_item_name, get_item_value
from ..utils.text import get_state_translation
from ..utils.value import merge_dicts
from .haui_config_access import HAUIConfigAccess
from .haui_entity import HAUIEntity

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI


class HAUIItem(HAUIConfigAccess):
    """Represents an item from a panel"""

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        """Initialize for config entity.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for item. Defaults to None.
        """
        # build merged config before passing to base - keeps config immutable after init
        cfg = {opt.key: opt.default for opt in ItemOptions.STANDARD_OPTIONS}
        if config is not None:
            merge_dicts(cfg, deepcopy(config))
        # Strip an empty value field so the runtime falls through to the
        # entity-derived display value; 0 and False are real overrides.
        if cfg.get("value") in (None, ""):
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
        if not isinstance(item_id, str) or not item_id:
            self._internal = True
            self._internal_type = InternalItemType.SKIP
            return

        # check if item is internal
        for internal in InternalItemType:
            if item_id == internal or item_id.startswith(f"{internal}:"):
                self._internal = True
                self._internal_type = internal
                break
        if self._internal:
            if ":" in item_id:
                self._internal_data = item_id.split(":", 1)[1]
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
            if internal_type == InternalItemType.NAVIGATE:
                # internal navigate to using key
                navigation = self.app.controller["navigation"]
                navigation.open_panel(internal_data)
            elif internal_type == InternalItemType.ACTION:
                # internal action to run
                service_data = self.get("service_data", {})
                action_call = internal_data.replace(".", "/", 1)
                self.app.call_service(action_call, service_data=service_data)

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

    def supports(self, flag: int) -> bool:
        """Returns whether the entity advertises any bit of ``flag`` in ``supported_features``.

        A missing entity has no attributes, so it supports nothing.

        Args:
            flag (int): Feature flag (or several OR-ed flags) to test

        Returns:
            bool: True if at least one of the flag bits is supported
        """
        return bool(self.get_item_attr("supported_features", 0) & flag)

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
        # Support JSON array string (e.g. '["forecast", 0, "temperature"]')
        # for nested attribute access.
        if isinstance(state, str) and state.startswith("["):
            try:
                state = json.loads(state)
            except json.JSONDecodeError, TypeError:
                pass
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

    def is_stale(self, max_age_seconds: int) -> bool:
        """Whether the entity behind this item has not updated for too long.

        Pages use this to mark stale sensor readouts (dimmed text plus a
        "…" suffix) so a wall panel does not silently pretend an old value
        is current.  Internal items (navigate/action/text) have no entity
        and are never stale.

        Args:
            max_age_seconds: Threshold in seconds.  0 or negative disables
                the check entirely (returns False for every item).

        Returns:
            True when the item has an entity whose ``last_updated`` is older
            than the threshold, False otherwise (no entity, unknown
            timestamp, or threshold disabled).
        """
        if not max_age_seconds or max_age_seconds <= 0:
            return False
        if self._entity is None:
            return False
        entity = self.get_item()
        if entity is None:
            return False
        last_updated = getattr(entity, "last_updated", None)
        if last_updated is None:
            return False
        if getattr(last_updated, "tzinfo", None) is None:
            now = datetime.now()
        else:
            now = datetime.now(UTC)
        age = (now - last_updated).total_seconds()
        return age > max_age_seconds

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
        # the editor stores numeric input (e.g. "42") as a number
        if isinstance(value, int | float) and not isinstance(value, bool):
            return str(value)
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
        if not value and self.is_internal() and self.get_internal_type() == InternalItemType.TEXT:
            value = self.get_internal_data()

        return value or get_item_value(self, "")

    def get_name(self) -> str:
        """Returns the name of the entity.

        Returns:
            str: Name of the item
        """
        name = self._resolve_state_field("name")

        # internal navigate item uses panel title
        if not name and self.is_internal():
            if self.get_internal_type() == InternalItemType.NAVIGATE:
                panel = self.app.device_config.get_panel(self.get_internal_data())
                if panel:
                    name = panel.get_title()

        return name or get_item_name(self, "")

    @overload
    def get_color_field(
        self, key: str, default: int | str | list | tuple
    ) -> int | str | list | tuple: ...

    @overload
    def get_color_field(
        self, key: str, default: None = None
    ) -> int | str | list | tuple | None: ...

    def get_color_field(
        self, key: str, default: int | str | list | tuple | None = None
    ) -> int | str | list | tuple | None:
        """Resolve a per-item colour option that may be state-keyed or templated.

        Tile options such as ``text_color`` and ``back_color`` support the same
        state-dict and Jinja forms as the main ``color`` option.  Resolve them
        before they reach ``parse_color_value``: a raw dict is treated as an
        invalid colour (black) by that parser.

        Args:
            key: Config key to look up.
            default: Value returned when the item has no override.

        Returns:
            The resolved colour value (int, string, or list) or ``default``.
        """
        value = self.get(key, None)
        if isinstance(value, dict):
            value = value.get(self.get_item_state())
        if isinstance(value, str) and value:
            value = self.render_template(value)
        if value is None or value == "":
            return default
        return value

    def get_color(self) -> int:  # type: ignore[override]
        """Returns the color of the entity.

        Returns:
            int: the color of the entry in rgb565
        """
        color = self.get("color", None)
        if isinstance(color, dict):
            color = color.get(self.get_item_state())
        if isinstance(color, str) and color:
            color = self.render_template(color)
        # None means no explicit color config — fall through to
        # get_item_color() for automatic condition-based color resolution.
        if color is None:
            return get_item_color(
                self, super().get_color("entity_unavailable"), color_getter=super().get_color
            )
        # Parse any remaining string/list format to RGB565 int via the
        # canonical parse_color_value utility (handles "[r,g,b]", "#rrggbb",
        # plain int strings, and list/tuple of 3 ints).
        if not isinstance(color, int):
            color = parse_color_value(color)
        return color

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
        return (
            get_state_translation(
                self.get_item_type(), self.get_item_state() or "", self.get_locale()
            )
            or ""
        )

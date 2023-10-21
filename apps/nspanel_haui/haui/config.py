from .mapping.color import COLORS
from .mapping.const import (
    DEFAULT_CONFIG,
    PANEL_CONFIG,
    ENTITY_CONFIG,
    INTERNAL_ENTITY_TYPE,
)

from .helper.color import rgb_to_rgb565
from .helper.entity import (
    get_entity_icon,
    get_entity_color,
    get_entity_name,
    get_entity_value,
    execute_entity,
)
from .helper.text import get_state_translation
from .helper.value import merge_dicts

from .base import HAUIBase


class HAUIConfigEntity(HAUIBase):

    """
    Represents a entity from a panel
    """

    def __init__(self, app, config=None):
        """Initialize for config entity.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for entity. Defaults to None.
        """
        # initialize with default entity values
        super().__init__(app, ENTITY_CONFIG.copy())
        # load config
        if config is not None:
            merge_dicts(self._config, config)
        # type of entity
        self._internal = False  # is it an internal entity
        self._internal_type = None  # internal entity type
        self._internal_data = None  # internal entity data
        self._entity_type = None  # entity type
        self._entity_id = None  # entity id
        # prepare the entity
        self._prepare_entity(self.get("entity"))

    def _prepare_entity(self, entity_id):
        """Prepares internal values from entity.

        Args:
            entity_id (str): The entity id
        """
        if entity_id is None:
            self._internal = True
            self._internal_type = "skip"
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
        else:
            self._entity_id = entity_id
            self._entity_type = entity_id.split(".")[0]

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
            elif internal_type == "service":
                # internal service to run
                service_data = self.get("service_data", {})
                service_call = internal_data.replace(".", "/", 1)
                self.app.call_service(service_call, **service_data)

        # external entity
        else:
            # execute external entity
            execute_entity(self)

    def is_internal(self):
        """Returns if the entity is internal.

        Returns:
            bool: True if internal
        """
        return self._internal

    def get_internal_type(self):
        """Returns the internal entity type.

        Returns:
            str: Internal Entity Type
        """
        return self._internal_type

    def get_internal_data(self):
        """Returns the internal entity data.

        Returns:
            str: Internal Entity Data
        """
        return self._internal_data

    def has_entity_id(self):
        """Returns if a entity id is available.

        Returns:
            bool: True if entity id is available
        """
        return self._entity_id is not None

    def get_entity_id(self):
        """Returns the entity id.

        Returns:
            str: entity id
        """
        return self._entity_id

    def has_entity(self):
        """Returns if a entity is available.

        Returns:
            bool: True if entity is available
        """
        return self._entity_id is not None and self.app.entity_exists(self._entity_id)

    def get_entity(self):
        """Returns the entity.

        Returns:
            Entity: Entity
        """
        if self.has_entity():
            return self.app.get_entity(self._entity_id)
        return None

    def get_entity_type(self):
        """Returns the type of the entity.

        The entity type is the first part of the entity id.

        Returns:
            str: Entity Type
        """
        return self._entity_type

    def get_entity_attr(self, attr, default=None):
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

    def get_entity_state(self):
        """Returns the state of the entity.

        Returns:
            str: Entity State
        """
        if not self.has_entity():
            return ""
        state = self.get("state", "")
        if state == "":
            entity = self.get_entity()
            return entity.get_state()
        # state is overriden
        return self.get_entity_attr(state, "")

    def call_entity_service(self, service, **kwargs):
        """Calls a service on the entity.

        Args:
            service (str): Service to call
            **kwargs (any): Service arguments
        """
        if not self.has_entity():
            return
        entity = self.get_entity()
        entity.call_service(service, **kwargs)

    def get_value(self):
        """Returns the value of the entity.

        Returns:
            str: The value
        """
        value = self.get("value", "")
        if isinstance(value, dict):
            entity_state = self.get_entity_state()
            if entity_state in value:
                value = value[entity_state]
            else:
                value = ""
        if value != "":
            value = self.render_template(value)

        # check internal entity: value
        if self.is_internal() and value == "":
            internal_type = self.get_internal_type()
            internal_data = self.get_internal_data()
            # text
            if internal_type == "text":
                value = internal_data

        # use default value
        if value == "":
            value = get_entity_value(self, "")

        return value

    def get_name(self):
        """Returns the name of the entity.

        Returns:
            str: Name of the entity
        """
        name = self.get("name", "")
        # state based name
        if isinstance(name, dict):
            entity_state = self.get_entity_state()
            if entity_state in name:
                name = name[entity_state]
            else:
                name = ""
        # use name from config
        if isinstance(name, str) and name != "":
            return self.render_template(name)

        # check internal entity: name
        if self.is_internal() and name == "":
            internal_type = self.get_internal_type()
            internal_data = self.get_internal_data()
            # navigate
            if internal_type == "navigate":
                panel = self.app.config.get_panel(internal_data)
                # use the panels title
                if panel:
                    name = panel.get_title()

        # default name
        if name == "":
            name = get_entity_name(self, self.translate("Unknown"))

        return name

    def get_color(self):
        """Returns the color of the entity.

        Returns:
            int: the color of the entry in rgb565
        """
        color = self.get("color")
        # state based color
        if isinstance(color, dict):
            entity_state = self.get_entity_state()
            if entity_state in color:
                color = color[entity_state]
            else:
                color = None
        # use color from config
        if isinstance(color, str) and color != "":
            color = self.render_template(color)
        elif isinstance(color, list) and len(color) == 3:
            color = rgb_to_rgb565(color)
        # use default color
        if not color:
            color = get_entity_color(self, COLORS["entity_unavailable"])
        return color

    def get_icon(self):
        """Returns the icon of the entry.

        Returns:
            str: Icon chr of entry
        """
        icon = self.get("icon", "")
        # state based icon
        if isinstance(icon, dict):
            entity_state = self.get_entity_state()
            if entity_state in icon:
                # overwrite icon with matching state
                icon = icon[entity_state]
            else:
                # reset icon if no state defined
                icon = ""
        # use icon from config
        if isinstance(icon, str) and icon != "":
            icon = self.render_template(icon)
        # use default icon
        if not icon:
            icon = get_entity_icon(self, "alert-circle-outline")
        return icon

    def translate_state(self):
        """Returns the translation of entity state.

        Returns:
            str: Translated state
        """
        if not self.has_entity():
            return ""
        return get_state_translation(
            self.get_entity_type(), self.get_entity_state(), self.get_locale()
        )


class HAUIConfigPanel(HAUIBase):

    """
    Represents a panel on the display.

    Its a description of what the page should look like and what
    entities to show
    """

    def __init__(self, app, config=None):
        """Initialize for config panel.

        Args:
            app (NSPanelHAUI): App
            config (dict, optional): Config for panel. Defaults to None.
        """
        # initialize with default panel values
        super().__init__(app, PANEL_CONFIG.copy())
        # load config
        if config is not None:
            merge_dicts(self._config, config)
        # store the initial config in an additional var
        # so it is possible to restore the config to initial values
        self._default_config = {}
        merge_dicts(self._default_config, self._config)
        # store persistent config
        self._persistent_config = {}
        # load all entities
        self._entities = []  # list of HAUIConfigEntity
        # single entity config
        if self.get("entity") is not None:
            self._entities.append(HAUIConfigEntity(self.app, config))
        # multiple entities config
        for e in self.get("entities", []):
            self._entities.append(HAUIConfigEntity(self.app, e))

    # public

    def get_type(self):
        """Returns the type of this panel.

        Returns:
            str: Type
        """
        return self.get("type", "")

    def get_mode(self):
        """Returns the panel mode.

        Possible panel modes:
        - panel (Default)
        - subpanel
        - popup

        Returns:
            str: Panel mode
        """
        return self.get("mode", "panel")

    def get_title(self, default_title=None):
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

    def is_home_panel(self):
        """Returns True if this is the home panel.

        Returns:
            bool: True if home panel
        """
        return self.get("home_panel", False)

    def is_sleep_panel(self):
        """Returns True if this is the sleep panel.

        Returns:
            bool: True if sleep panel
        """
        return self.get("sleep_panel", False)

    def is_wakeup_panel(self):
        """Returns True if this is the wakeup panel.

        Returns:
            bool: True if wakeup panel
        """
        return self.get("wakeup_panel", False)

    def show_home_button(self):
        """Returns True if home button should be shown.

        Returns:
            bool: True if home button should be shown
        """
        return self.get(
            "show_home_button", self.app.device.get("show_home_button", False)
        )

    def get_entities(self, return_copy=True):
        """Returns all entities from this panel.

        Args:
            return_copy (bool, optional): Copy entities. Defaults to True.

        Returns:
            list: List with entities
        """
        if return_copy:
            return self._entities.copy()
        return self._entities

    def get_default_config(self, return_copy=True):
        """Returns the initial config of this panel.

        Returns:
            dict: Initial config
            return_copy (bool, optional): Return copy of config. Defaults to True.
        """
        if return_copy:
            return self._default_config.copy()
        return self._default_config

    def get_persistent_config(self, return_copy=True):
        """Returns the persistent config of this panel.

        Returns:
            dict: Persistent config
            return_copy (bool, optional): Return copy of config. Defaults to True.
        """
        if return_copy:
            return self._persistent_config.copy()
        return self._persistent_config

    def restore_default_config(self):
        """Restore the initial config of this panel."""
        self._config = self.get_default_config(return_copy=True)


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
        super().__init__(app, DEFAULT_CONFIG.copy())
        # load config
        if config is not None:
            merge_dicts(self.get_config(return_copy=False), config)
        # load all panels
        self._panels = []
        panels_to_load = self.get("panels", [])
        # append sys_panels so they can be overwritten by panels
        panels_to_load += self.get("sys_panels", [])
        for panel_config in panels_to_load:
            panel = HAUIConfigPanel(self.app, panel_config)
            self._panels.append(panel)

    # public

    def get_panels(self, filter_nav_panel=None):
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

    def get_entities(self):
        """Returns all entities as HAUIConfigEntity objects.

        Returns:
            list: List with entities
        """
        entities = []
        for panel in self._panels:
            entities.extend(panel.get_entities())
        return entities

    def get_entity(self, entity_id):
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

    def get_panel(self, panel_id):
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

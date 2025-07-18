from typing import List, Union
from ..mapping.const import ESP_EVENT, NOTIF_EVENT
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..helper.color import rgb_to_rgb565
from ..abstract.event import HAUIEvent
from ..abstract.part import HAUIPart
from ..abstract.entity import HAUIEntity
from ..abstract.panel import HAUIPanel


class HAUIPage(HAUIPart):
    """Represents a page on the nextion display.

    Every page on the display needs a page defined here to
    be able to interact with the components.

    - Process events on page
    - Render panel on page
    - Main logic for panels
    """

    # internal function button ids
    FNC_BTN_L_PRI = "fnc_btn_left_pri"
    FNC_BTN_L_SEC = "fnc_btn_left_sec"
    FNC_BTN_R_PRI = "fnc_btn_right_pri"
    FNC_BTN_R_SEC = "fnc_btn_right_sec"

    # default function component icons
    ICO_DEFAULT = get_icon("mdi:alert-circle-outline")
    ICO_NAV_PREV = get_icon("mdi:chevron-left")
    ICO_NAV_NEXT = get_icon("mdi:chevron-right")
    ICO_NAV_UP = get_icon("mdi:chevron-up")
    ICO_NAV_CLOSE = get_icon("mdi:close")
    ICO_NAV_HOME = get_icon("mdi:home-outline")
    ICO_NAV_MESSAGE = get_icon("mdi:email-outline")
    ICO_ZOOM = get_icon("mdi:loupe")
    ICO_LOCKED = get_icon("mdi:lock-outline")
    ICO_UNLOCKED = get_icon("mdi:lock-open-variant-outline")
    ICO_PASSWORD = get_icon("mdi:circle-medium")
    ICO_ENTITY_POWER = get_icon("mdi:power")
    ICO_ENTITY_UNAVAILABLE = get_icon("mdi:cancel")
    ICO_PREV_PAGE = get_icon("mdi:chevron-double-up")
    ICO_NEXT_PAGE = get_icon("mdi:chevron-double-down")
    ICO_PREV_MESSAGE = get_icon("mdi:chevron-double-left")
    ICO_NEXT_MESSAGE = get_icon("mdi:chevron-double-right")
    ICO_MESSAGE = get_icon("mdi:email")
    ICO_SLEEP = get_icon("mdi:sleep")

    # functions for function components
    FNC_TYPE_NAV_NEXT = "nav_next"
    FNC_TYPE_NAV_PREV = "nav_prev"
    FNC_TYPE_NAV_UP = "nav_up"
    FNC_TYPE_NAV_CLOSE = "nav_close"
    FNC_TYPE_NAV_HOME = "nav_home"
    FNC_TYPE_NAV_SLEEP = "nav_sleep"
    FNC_TYPE_NAV_NOTIF = "nav_notif"
    FNC_TYPE_UNLOCK = "unlock"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.page_id = int(self.get("page_id", 0))
        self.page_id_recv = None  # will be set to the page id when a page event is recieved
        # current panel
        self.panel: HAUIPanel = None
        # function items, components
        self._fnc_items = {}
        # physical buttons, components
        self._btn_state_left: tuple = None
        self._btn_state_right: tuple = None
        # component callbacks
        self._callbacks: List[callable] = []
        # entity handles
        self._handles: List[str] = []

    # part

    def start_part(self) -> None:
        """Starts the part.

        This is called when the part is started.
        """
        self.log(f"Starting page: {self.page_id}")
        # notify about page start
        self.start_page()

    def stop_part(self) -> None:
        """Stops of part.

        This is called when the part is stopped.
        """
        self.log(f"Stopping page: {self.page_id}")
        self.set_panel(None)
        # notify about page stop
        self.stop_page()
        # clean up entity handles
        for handle in self._handles.copy():
            self.remove_entity_listener(handle)

    # page

    def start_page(self) -> None:
        """Starts the page.

        Put callback registration in here and code that should be run
        only once on start.

        When changing components, prefer using start_panel.
        """

    def stop_page(self) -> None:
        """Stops the page.

        Put callback deregistration in here and other code that should
        be run when stopping a part.
        """

    # panel functionality

    def refresh_panel(self) -> None:
        """Refreshes the current panel.

        This gives the possibility to update the panel.
        """
        if self.panel is None:
            return
        # start recording of commands to be sent
        self.start_rec_cmd()
        # 3. call render for panel
        self.render_panel(self.panel)
        # stop recording of commands to be sent
        self.stop_rec_cmd(send_commands=True)

    def set_panel(self, panel: HAUIPanel) -> None:
        """Sets a panel for the page.

        This is used to set a panel for current page.
        The panel is set to the page and the panel is then being rendered.

        Args:
            panel (HAUIConfigPanel): The panel to set.
        """
        # prepare panel
        if self.panel is not None:
            self.log(f"Stopping panel: {self.panel.id}")
            self.stop_panel(self.panel)
        self.panel = panel
        if self.panel is None:
            return
        self.log(f"Starting panel: {self.panel.id}")
        self.start_panel(panel)

        # 1. call config for panel
        self.config_panel(panel)
        # 2. call before render for panel
        rendered = False
        if self.before_render_panel(panel):
            # start recording of commands to be sent
            self.start_rec_cmd()
            # 3. call render for panel
            self.render_panel(panel)
            # stop recording of commands to be sent
            self.stop_rec_cmd(send_commands=True)
            rendered = True
        # 4. call after render for panel
        self.after_render_panel(panel, rendered)

    def config_panel(self, panel: HAUIPanel) -> None:
        """Configures the currently set panel.

        Args:
            panel (HAUIConfigPanel): Current panel
        """
        self.start_rec_cmd()

        # physical button state
        if self._btn_state_left is not None:
            self.add_component_callback(self._btn_state_left, self.callback_button_state_buttons)
            self.set_component_value(self._btn_state_left, self.app.device.get_left_button_state())
        if self._btn_state_right is not None:
            self.add_component_callback(self._btn_state_right, self.callback_button_state_buttons)
            self.set_component_value(
                self._btn_state_right, self.app.device.get_right_button_state()
            )

        # prepare function items
        nav_panels = self.app.config.get_panels(True)
        for fnc_id, fnc_item in self._fnc_items.items():
            mode = panel.get_mode()
            # set default function if not set for header buttons
            if fnc_item["fnc_name"] is None:
                # left primary button
                if fnc_id == self.FNC_BTN_L_PRI:
                    if mode == "panel":
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_PREV
                    elif mode == "subpanel":
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_UP
                    elif mode == "popup":
                        if not panel.is_home_panel() and panel.show_home_button():
                            fnc_item["fnc_name"] = self.FNC_TYPE_NAV_HOME
                # left secondary button
                if fnc_id == self.FNC_BTN_L_SEC:
                    if (mode in ["panel", "subpanel"]) and not panel.is_home_panel():
                        if panel.show_home_button():
                            fnc_item["fnc_name"] = self.FNC_TYPE_NAV_HOME
                    elif (mode in ["panel", "subpanel"]) and panel.is_home_panel():
                        if panel.show_notifications_button():
                            notification = self.app.controller["notification"]
                            fnc_item["fnc_name"] = self.FNC_TYPE_NAV_NOTIF
                            fnc_item["fnc_args"]["visible"] = notification.has_notifications()
                        if fnc_item["fnc_args"]["visible"] is False:
                            fnc_item["fnc_name"] = self.FNC_TYPE_NAV_SLEEP
                            fnc_item["fnc_args"]["visible"] = True

                # right primary button
                elif fnc_id == self.FNC_BTN_R_PRI:
                    if mode == "panel":
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_NEXT
                    elif mode == "popup":
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_CLOSE
                # right secondary button
                if fnc_id == self.FNC_BTN_R_SEC:
                    config = panel.get_persistent_config()
                    locked = config.get("locked", None)
                    if locked is not None:
                        fnc_item["fnc_name"] = self.FNC_TYPE_UNLOCK
                        fnc_item["fnc_args"]["locked"] = locked
            # visibility
            if fnc_item["fnc_args"].get("visible", None) is None:
                if fnc_item["fnc_name"] is None:
                    fnc_item["fnc_args"]["visible"] = False
                else:
                    fnc_item["fnc_args"]["visible"] = True

        # special case, single nav panel
        # switch secondary buttons with primary buttons, since nav is not used
        # with a single nav panel
        if len(nav_panels) <= 1:
            # check primary left button
            if self.FNC_BTN_L_PRI in self._fnc_items:
                left_pri = self._fnc_items[self.FNC_BTN_L_PRI]
                if left_pri["fnc_name"] is None or left_pri["fnc_name"] == self.FNC_TYPE_NAV_PREV:
                    left_pri["fnc_args"]["visible"] = False
                    # swap pri with secondary
                    if self.FNC_BTN_L_SEC in self._fnc_items:
                        left_sec = self._fnc_items[self.FNC_BTN_L_SEC]
                        pri_comp = left_pri["fnc_component"]
                        sec_comp = left_sec["fnc_component"]
                        left_pri["fnc_component"] = sec_comp
                        left_sec["fnc_component"] = pri_comp
                        self._fnc_items[self.FNC_BTN_L_PRI] = left_sec
                        self._fnc_items[self.FNC_BTN_L_SEC] = left_pri
            # check primary right button
            if self.FNC_BTN_R_PRI in self._fnc_items:
                right_pri = self._fnc_items[self.FNC_BTN_R_PRI]
                if right_pri["fnc_name"] is None or right_pri["fnc_name"] == self.FNC_TYPE_NAV_NEXT:
                    right_pri["fnc_args"]["visible"] = False
                    # swap pri with secondary
                    if self.FNC_BTN_R_SEC in self._fnc_items:
                        right_sec = self._fnc_items[self.FNC_BTN_R_SEC]
                        pri_comp = right_pri["fnc_component"]
                        sec_comp = right_sec["fnc_component"]
                        right_pri["fnc_component"] = sec_comp
                        right_sec["fnc_component"] = pri_comp
                        self._fnc_items[self.FNC_BTN_R_PRI] = right_sec
                        self._fnc_items[self.FNC_BTN_R_SEC] = right_pri

        # register function items
        for fnc_id, fnc_item in self._fnc_items.items():
            # FIXME log type self.log(f'Set function button: {fnc_id} -> {fnc_item["fnc_name"]}')
            self.add_component_callback(
                fnc_item["fnc_component"], self.callback_function_components
            )
            self.update_function_component(fnc_id)

        self.stop_rec_cmd(send_commands=True)

    def create_panel(self, panel: HAUIPanel) -> None:
        """Called when a new panel is created.

        This method should be overwritten in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def start_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is started.

        This method should be overwritten in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def stop_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is stopped.

        This method should be overwritten in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def before_render_panel(self, panel: HAUIPanel) -> bool:
        """Called before the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIConfigPanel): Current panel

        Returns:
            bool, if False then panel will not be rendered
        """
        return True

    def render_panel(self, panel: HAUIPanel) -> None:
        """Called when the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def after_render_panel(self, panel: HAUIPanel, rendered: bool) -> None:
        """Called after the panel is rendered.

        This gives the possibility to execute some checks after showing panel.

        Args:
            panel (HAUIConfigPanel): Current panel
            rendered (bool): Was the panel rendered
        """

    # entity

    def execute_entity(self, entity: HAUIEntity) -> None:
        """Executes the given entity.

        Args:
            entity (HAUIConfigEntity): entity
        """
        entity_type = entity.get_entity_type()
        entity_state = entity.get_entity_state()
        navigation = self.app.controller["navigation"]
        available = entity_state != "unavailable"

        # entity is not available
        if not available:
            msg = self.translate("The entity {} is currently unavailable.")
            msg = msg.format(entity.get_name())
            msg += "\r\n\r\n"
            msg += self.translate("Entity:")
            msg += "\r\n"
            msg += entity.get_entity_id()
            # open notification
            navigation.open_popup(
                "popup_notify",
                title=self.translate("Entity unavailable"),
                btn_right=self.translate("Close"),
                icon=entity.get_icon(),
                notification=msg,
            )

        # execute popup
        elif entity_type in ["light", "media_player", "vacuum", "cover", "climate"]:
            popup_name = entity.get("popup_key", None)
            if popup_name is None:
                popup_name = f"popup_{entity_type}"
            kwargs = entity.get_config()
            kwargs["entity_id"] = entity.get_entity_id()
            # open popup
            navigation.open_popup(popup_name, **kwargs)
        # execute default
        else:
            self.log(f"Executing entity {entity.get_name()} - {entity_type}")
            entity.execute()

    def turn_on_entity(self, entity: HAUIEntity) -> None:
        """Turns on the given entity.

        Args:
            entity (HAUIConfigEntity): entity
        """
        self.log(f"Switching entity on: {entity.get_name()} ({entity.get_entity_id()})")
        entity_type = entity.get_entity_type()
        if entity_type == "media_player":
            entity.call_entity_service("media_play")
        else:
            entity.call_entity_service("turn_on")

    def turn_off_entity(self, entity: HAUIEntity) -> None:
        """Turns off the given entity.

        Args:
            entity (HAUIConfigEntity): entity
        """
        self.log(f"Switching entity off: {entity.get_name()} ({entity.get_entity_id()})")
        entity_type = entity.get_entity_type()
        if entity_type == "media_player":
            entity.call_entity_service("media_stop")
        else:
            entity.call_entity_service("turn_off")

    def add_entity_listener(self, entity_id: str, callback: callable, attribute: str = None) -> str:
        """Adds a entity state listener.

        Args:
            entity_id (str): Entity ID
            callback (function): Callback
            attribute (str): Attribute

        Returns:
            handle (str): Handle
        """
        handle = self.app.listen_state(callback, entity_id, attribute=attribute)
        # FIXME log type self.log(
        #     f"Adding listener for {entity_id},"
        #     f" attribute {attribute} - handle: {handle}"
        # )
        self._handles.append(handle)
        return handle

    def remove_entity_listener(self, handle: str) -> None:
        """Removes a entity state listener.

        Args:
            handle (str): Handle
        """
        if handle in self._handles:
            self.app.cancel_listen_state(handle)
            # FIXME log type self.log(f"Removing listener - handle: {handle}")
            del self._handles[self._handles.index(handle)]

    # basic page functionality (see HAUIBase for generic methods)

    def parse_color(self, color: Union[int, str, list, tuple]) -> int:
        """Parses the given color.

        Args:
            color (int|str|list|tuple): Color

        Returns:
            int: Color
        """
        component_color = 0

        if isinstance(color, (list, tuple)):
            component_color = rgb_to_rgb565(color)
        else:
            if isinstance(color, str):
                try:
                    component_color = int(self.app.render_template(color))
                except Exception:
                    self.log(f"Invalid color {color}")
            else:
                try:
                    component_color = int(color)
                except Exception:
                    self.log(f"Invalid color {color}")
        return int(component_color)

    def set_component_text_color(
        self, component: tuple, color: Union[int, str, list, tuple]
    ) -> None:
        """Sets the text color of the given component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} text color {component_color}')
        self.send_cmd(f"{component[1]}.pco={component_color}")

    def set_component_text_color_pressed(
        self, component: tuple, color: Union[int, str, list, tuple]
    ) -> None:
        """Sets the text color pressed of the given component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} text color pressed {component_color}')
        self.send_cmd(f"{component[1]}.pco2={component_color}")

    def set_component_back_color(
        self, component: tuple, color: Union[int, str, list, tuple]
    ) -> None:
        """Sets the back color of the component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} back color {component_color}')
        self.send_cmd(f"{component[1]}.bco={component_color}")

    def set_component_back_color_pressed(
        self, component: tuple, color: Union[int, str, list, tuple]
    ) -> None:
        """Sets the back color pressed of the component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} back color pressed {component_color}')
        self.send_cmd(f"{component[1]}.bco2={component_color}")

    def set_component_password(self, component: tuple, input_password: bool) -> None:
        """Sets a text component to as a password input.

        Args:
            component (tuple): Component
            input_password (bool): should input be used as a password input
        """
        # self.log(f'Setting password text {component[1]}: {input_password}')
        if input_password:
            self.send_cmd(f"{component[1]}.pw=1")
        else:
            self.send_cmd(f"{component[1]}.pw=0")

    def set_component_touch(self, component: tuple, state: bool) -> None:
        """Sets a components touch events.

        Args:
            component (tuple): Component
            state (bool): Should the component recieve touch events
        """
        # self.log(f'Setting component touch {component[1]}: {state}')
        self.send_cmd(f"tsw {component[1]},{int(state)}")

    def add_component_callback(self, component: tuple, callback: callable) -> None:
        """Adds a callback for the given component.

        Args:
            component (tuple): Component
            callback (function): Callback
        """
        self._callbacks.append((component, callback))

    def show_component(self, component: tuple) -> None:
        """Shows the component.

        Args:
            component (tuple): Component
        """
        # self.log(f'Showing {component[1]}')
        self.send_cmd(f"vis {component[1]},1")

    def hide_component(self, component: tuple) -> None:
        """Hides the component.

        Args:
            component (tuple): Component
        """
        # self.log(f'Hiding {component[1]}')
        self.send_cmd(f"vis {component[1]},0")

    def set_function_buttons(self, btn_l_pri, btn_l_sec, btn_r_pri, btn_r_sec):
        """Sets all function buttons at once.

        can be a dict:
        item = {'fnc_component': (..., ...), 'fnc_name': 'name', fnc_args={}}

        can be list|tuple (component):
        item = (..., ...)

        Args:
            btn_l_pri (tuple|list|dict): Primary left function button
            btn_l_sec (tuple|list|dict): Secondary left function button
            btn_r_pri (tuple|list|dict): Primary right function button
            btn_r_sec (tuple|list|dict): Secondary right function button
        """
        for fnc_id, item in [
            (self.FNC_BTN_L_PRI, btn_l_pri),
            (self.FNC_BTN_L_SEC, btn_l_sec),
            (self.FNC_BTN_R_PRI, btn_r_pri),
            (self.FNC_BTN_R_SEC, btn_r_sec),
        ]:
            if isinstance(item, (list, tuple)):
                self.set_function_component(item, fnc_id)
            elif isinstance(item, dict):
                btn = item.get("fnc_component", None)
                fnc_name = item.get("fnc_name", None)
                fnc_args = item.get("fnc_args", {})
                self.set_function_component(btn, fnc_id, fnc_name, **fnc_args)
            else:
                self.set_function_component(None, fnc_id)

    def get_button_colors(self, active: bool) -> None:
        """Returns default colors for buttons.

        Args:
            active (bool): is the button active

        Returns:
            tuple: (color, color_pressed, back_color, back_color_pressed)
        """
        if active:
            color = COLORS["component_active"]
            color_pressed = COLORS["component"]
            back_color_pressed = COLORS["component_pressed"]
        else:
            color = COLORS["text_disabled"]
            color_pressed = COLORS["text_disabled"]
            back_color_pressed = COLORS["background"]
        back_color = COLORS["background"]
        return color, color_pressed, back_color, back_color_pressed

    # button state related

    def set_button_state_buttons(self, btn_left: tuple, btn_right, tuple) -> None:
        """Sets the button state buttons.

        Args:
            btn_left (tuple): Component
            btn_right (tuple): Component
        """
        self._btn_state_left = btn_left
        self._btn_state_right = btn_right

    def set_button_left_state(self, state: bool) -> None:
        """Sets the state of button left.

        Args:
            state (bool): state
        """
        if self._btn_state_left:
            self.set_component_value(self._btn_state_left, state)

    def set_button_right_state(self, state: bool) -> None:
        """Sets the state of button right.

        Args:
            state (bool): state
        """
        if self._btn_state_right:
            self.set_component_value(self._btn_state_right, state)

    # function component related

    def get_function_components(self, return_copy: bool = True) -> dict:
        """Returns the function buttons.

        Args:
            return_copy (bool): should a copy of the buttons be returned

        Returns:
            dict: Function buttons
        """
        if return_copy:
            return self._fnc_items.copy()
        return self._fnc_items

    def set_function_component(
        self, component: tuple, fnc_id: str, fnc_name: str = None, **fnc_args
    ):
        """Sets the function component.

        To remove a function component:

        self.set_function_component(None, fnc_id)

        To add a function component, do the following:

        - set button as a function component
          self.set_function_component(btn, fnc_id)
          This will use a default function and a default icon

        or

        - set button as a function component
          self.set_function_component(btn, fnc_id, fnc_name='functionname',
                                    icon='icon', color=0)
          This will use a custom function and a custom icon

        To add a custom function component, do the following:

        - set component as a function component
          self.set_function_component(component, fnc_id,
                                    fnc_name='functionname',
                                    fnc_args={'icon': icon, 'color': 0})
        - overwrite callback_function_component(fnc_id, fnc_name)
          and check for fnc_id
        - do action if fnc_id matches

        Args:
            component (tuple): Component
            fnc_id (str): Function Component ID
            fnc_name (str, optional): Function name, if not defined, default
                                      function will be used
            fnc_args (dict): Function arguments
        """
        if component is not None:
            item = {}
            if fnc_id in self._fnc_items:
                item = self._fnc_items
            item = {
                **item,
                **{
                    "fnc_component": component,
                    "fnc_name": fnc_name,
                    "fnc_args": fnc_args,
                },
            }
            # FIXME log type self.log(f"Adding function component {fnc_id}-{fnc_name}")
            self._fnc_items[fnc_id] = item
        elif fnc_id in self._fnc_items:
            self.log(f"Removing function component {fnc_id}")
            del self._fnc_items[fnc_id]

    def update_function_component(self, fnc_id: str, update_fnc_name: str = None, **kwargs) -> None:
        """Updates the function component.

        Args:
            fnc_id (str): Function Component ID
            update_fnc_name (str): Optional, new function name
            kwargs (dict): Arguments
        """

        if fnc_id not in self._fnc_items:
            self.log(f"function component {fnc_id} not found")
            return
        fnc_item = self._fnc_items[fnc_id]
        fnc_component = fnc_item["fnc_component"]
        fnc_args = fnc_item["fnc_args"]
        fnc_args = fnc_item["fnc_args"] = {**fnc_args, **kwargs}
        if update_fnc_name is not None:
            fnc_item["fnc_name"] = update_fnc_name
        fnc_name = fnc_item["fnc_name"]

        # get infos for component
        value = fnc_args.get("value", None)
        text = fnc_args.get("text", None)
        icon = fnc_args.get("icon", None)
        touch = fnc_args.get("touch_events", None)
        color = fnc_args.get("color", None)
        visible = fnc_args.get("visible", True)

        # set value
        if value is not None and fnc_item.get("current_value") != value:
            self.set_component_value(fnc_component, value)
            fnc_item["current_value"] = value

        # set text (can also contain icons)
        elif text is not None and fnc_item.get("current_text") != text:
            self.set_component_text(fnc_component, text)
            fnc_item["current_text"] = text

        # set icon
        else:
            if icon is None:
                if fnc_name == self.FNC_TYPE_NAV_PREV:
                    icon = self.ICO_NAV_PREV
                elif fnc_name == self.FNC_TYPE_NAV_NEXT:
                    icon = self.ICO_NAV_NEXT
                elif fnc_name == self.FNC_TYPE_NAV_HOME:
                    icon = self.ICO_NAV_HOME
                elif fnc_name == self.FNC_TYPE_NAV_SLEEP:
                    icon = self.ICO_SLEEP
                elif fnc_name == self.FNC_TYPE_NAV_NOTIF:
                    icon = self.ICO_NAV_MESSAGE
                elif fnc_name == self.FNC_TYPE_NAV_UP:
                    icon = self.ICO_NAV_UP
                elif fnc_name == self.FNC_TYPE_NAV_CLOSE:
                    icon = self.ICO_NAV_CLOSE
                elif fnc_name == self.FNC_TYPE_UNLOCK:
                    if fnc_args.get("locked", False):
                        icon = self.ICO_LOCKED
                    else:
                        icon = self.ICO_UNLOCKED
            if icon is not None and fnc_item.get("current_icon") != icon:
                self.set_component_text(fnc_component, icon)
                fnc_item["current_icon"] = icon

        # set touch events
        if touch is not None and fnc_item.get("current_touch_events") != touch:
            self.set_component_touch(fnc_component, touch)
            fnc_item["current_touch_events"] = touch

        # set colors
        if color is None and fnc_args.get("locked", None) is not None:
            if fnc_name == self.FNC_TYPE_UNLOCK and not fnc_args.get("locked", False):
                color = COLORS["component_accent"]
        color_pressed = fnc_args.get("color_pressed")
        back_color = fnc_args.get("back_color")
        back_color_pressed = fnc_args.get("back_color_pressed")
        if color is not None and fnc_item.get("current_color") != color:
            self.set_component_text_color(fnc_component, color)
            fnc_item["current_color"] = color
        if color_pressed is not None and fnc_item.get("current_color_pressed") != color_pressed:
            self.set_component_text_color_pressed(fnc_component, color_pressed)
            fnc_item["current_color_pressed"] = color_pressed
        if back_color is not None and fnc_item.get("current_back_color") != back_color:
            self.set_component_back_color(fnc_component, back_color)
            fnc_item["current_back_color"] = back_color
        if (
            back_color_pressed is not None
            and fnc_item.get("current_back_color_pressed") != back_color_pressed
        ):
            self.set_component_back_color_pressed(fnc_component, back_color_pressed)
            fnc_item["current_back_color_pressed"] = back_color_pressed

        # set visibility
        if visible is not None and fnc_item.get("current_visible", None) is not visible:
            if visible:
                self.show_component(fnc_component)
            else:
                self.hide_component(fnc_component)
            fnc_item["current_visible"] = visible

    # callback

    def callback_button_state_buttons(
        self, event: HAUIEvent, component: tuple, button_state: bool
    ) -> None:
        """Callback method for button state buttons.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (bool): Button state
        """
        # process button state button press callback
        self.log(f"Got button state button press: {component}-{button_state}")
        if button_state != 0:
            return

        # parse json response, set button state on device
        data = event.as_json()
        if self._btn_state_left and self._btn_state_left[1] == data.get("name", ""):
            self.app.device.set_left_button_state(button_state)
        elif self._btn_state_right and self._btn_state_right[1] == data.get("name", ""):
            self.app.device.set_right_button_state(button_state)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        """Gets called when a function component was pressed.

        This method is intended to be overwritten if a custom function component is used.

        Args:
            fnc_id (str): Function Component ID
            fnc_name (str): Function Name
        """

    def callback_function_components(
        self, event: HAUIEvent, component: tuple, button_state: int
    ) -> None:
        """Callback method for function component events.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (int): Value of the component event
        """
        # process function button press callback
        if button_state != 0:
            return

        # check what button was pressed
        fnc_id = None
        fnc_item = None
        for _fnc_id, _fnc_cnt in self._fnc_items.items():
            if _fnc_cnt["fnc_component"] == component:
                fnc_id = _fnc_id
                fnc_item = _fnc_cnt
                break

        # if unknown function do nothing
        if fnc_item is None:
            self.log(f"Unknown function component {component}")
            return
        navigation = self.app.controller["navigation"]
        fnc_name = fnc_item["fnc_name"]
        fnc_args = fnc_item["fnc_args"]

        # check the function that is defined for the button
        if fnc_name == self.FNC_TYPE_NAV_PREV:
            navigation.open_prev_panel()
        elif fnc_name == self.FNC_TYPE_NAV_NEXT:
            navigation.open_next_panel()
        elif fnc_name == self.FNC_TYPE_NAV_HOME:
            navigation.open_home_panel()
        elif fnc_name == self.FNC_TYPE_NAV_SLEEP:
            navigation.open_sleep_panel()
        elif fnc_name == self.FNC_TYPE_NAV_NOTIF:
            navigation.open_popup("popup_notification")
        elif fnc_name == self.FNC_TYPE_NAV_UP:
            navigation.close_panel()
        elif fnc_name == self.FNC_TYPE_NAV_CLOSE:
            navigation.close_panel()
        elif fnc_name == self.FNC_TYPE_UNLOCK:
            locked = fnc_args.get("locked", False)
            navigation = self.app.controller["navigation"]
            # lock panel if not locked
            if not locked:
                config = self.panel.get_persistent_config(return_copy=False)
                config["locked"] = False
                navigation.reload_panel()

        # notify about function button press
        self.callback_function_component(fnc_id, fnc_name)

    # processing

    def process_event(self, event: HAUIEvent) -> None:
        """Processes app events.

        Args:
            event (HAUIEvent): Event
        """
        # component event
        if event.name == ESP_EVENT["component"]:
            self.process_component_event(event)
        # notifications
        if self.FNC_BTN_L_SEC in self._fnc_items:
            left_sec = self._fnc_items[self.FNC_BTN_L_SEC]
            if left_sec["fnc_name"] == self.FNC_TYPE_NAV_NOTIF and event.name in [
                NOTIF_EVENT["notif_add"],
                NOTIF_EVENT["notif_remove"],
                NOTIF_EVENT["notif_clear"],
            ]:
                if event.name == NOTIF_EVENT["notif_add"]:
                    color = COLORS["component_accent"]
                else:
                    color = COLORS["component"]
                notification = self.app.controller["notification"]
                visible = False
                if notification.has_notifications():
                    visible = True
                self.update_function_component(self.FNC_BTN_L_SEC, color=color, visible=visible)

    def process_component_event(self, event: HAUIEvent) -> None:
        """Processes component events from component callback.

        Args:
            event (str): Event
        """
        component_info = [int(x) for x in event.as_str().split(",")]
        if len(component_info) != 3:
            return
        if component_info[0] != self.page_id:
            return
        for component, callback in self._callbacks:
            if component_info[1] == component[0]:
                callback(event, component, component_info[2])

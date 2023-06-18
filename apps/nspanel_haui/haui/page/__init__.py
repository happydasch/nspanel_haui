from ..helper.icon import get_icon
from ..helper.color import rgb_to_rgb565
from ..const import ESP_EVENT, ESP_REQUEST, ESP_RESPONSE
from ..base import HAUIPart


# class for pages / panels
class HAUIPage(HAUIPart):

    """ Represents a page on the nextion display.

    Every page on the display needs a page defined here to
    be able to interact with the components.

    - Process events on page
    - Render panel on page
    - Main logic for panels
    """

    ICO_NAV_LEFT = get_icon('arrow-left-thick')
    ICO_NAV_RIGHT = get_icon('arrow-right-thick')
    ICO_NAV_UP = get_icon('arrow-up-thick')
    ICO_NAV_CLOSE = get_icon('close-thick')

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.page_id = int(self.get('page_id', 0))
        self.page_id_recv = None  # will be set to the page id when a page event is recieved
        self.panel = None
        # nav buttons, components
        self._nav_prev = None
        self._nav_next = None
        self._nav_close = None
        self._nav_up = None
        # physical buttons, components
        self._btn_state_left = None
        self._btn_state_right = None
        # component callbacks
        self._callbacks = []
        # entity handles
        self._handles = []

    # part

    def start_part(self):
        """ Starts the part.

        This is called when the part is started.
        """
        self.log(f'Starting page: {self.page_id}')
        # notify about page start
        self.start_page()

    def stop_part(self):
        """ Stops of part.

        This is called when the part is stopped.
        """
        self.log(f'Stopping page: {self.page_id}')
        self.set_panel(None)
        # notify about page stop
        self.stop_page()
        # clean up entity handles
        for handle in self._handles.copy():
            self.remove_entity_listener(handle)

    # page

    def start_page(self):
        """ Starts the page.

        Put callback registration in here and code that should be run only once on start.

        When changing components, prefer using start_panel.
        """

    def stop_page(self):
        """ Stops the page.

        Put callback deregistration in here and other code that should be run when
        stopping a part.
        """

    # panel functionality

    def set_panel(self, panel):
        """ Sets a panel for the page.

        This is used to set a panel for current page.
        The panel is set to the page and the panel is then being rendered.

        Args:
            panel (HAUIConfigPanel): The panel to set.
        """
        # prepare panel
        if self.panel is not None:
            self.log(f'Stopping panel: {self.panel.id}')
            self.stop_panel(self.panel)
        self.panel = panel
        if self.panel is None:
            return
        self.log(f'Starting panel: {self.panel.id}')
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

    def config_panel(self, panel):
        """ Configures the currently set panel.

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
            self.set_component_value(self._btn_state_right, self.app.device.get_right_button_state())
        self.update_button_states()
        # prev and next buttons
        if panel.is_nav_panel():
            if self._nav_prev is not None:
                self.add_component_callback(self._nav_prev, self.callback_nav_buttons)
                self.set_component_text(self._nav_prev, self.ICO_NAV_LEFT)
                self.show_component(self._nav_prev)
            if self._nav_next is not None:
                self.add_component_callback(self._nav_next, self.callback_nav_buttons)
                self.set_component_text(self._nav_next, self.ICO_NAV_RIGHT)
                self.show_component(self._nav_next)
        else:
            # subpanels will just use prev as up button
            if self._nav_prev is not None:
                self._nav_up = self._nav_prev
                self._nav_prev = None
            if self._nav_next is not None:
                # unset next button on subpanels
                self.hide_component(self._nav_next)
                self._nav_next = None
        # close button
        if self._nav_close is not None:
            self.add_component_callback(self._nav_close, self.callback_nav_buttons)
            self.set_component_text(self._nav_close, self.ICO_NAV_CLOSE)
            self.show_component(self._nav_close)
        # up button
        if self._nav_up is not None:
            self.add_component_callback(self._nav_up, self.callback_nav_buttons)
            self.set_component_text(self._nav_up, self.ICO_NAV_UP)
            self.show_component(self._nav_up)
        self.stop_rec_cmd(send_commands=True)

    def start_panel(self, panel):
        """ Starts the panel.

        This is called when the panel is started. This method should be overwritten
        in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def stop_panel(self, panel):
        """ Stops the panel.

        This is called when the panel is stopped. This method should be overwritten
        in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def before_render_panel(self, panel):
        """ Before the panel is being rendered.

        This is called before the panel is rendered. This method should be overwritten
        in the page.

        Args:
            panel (HAUIConfigPanel): Current panel

        Returns:
            bool, if False then panel will not be rendered
        """
        return True

    def render_panel(self, panel):
        """ Renders the panel.

        This is called when the panel is rendered. This method should be overwritten
        in the page.

        Args:
            panel (HAUIConfigPanel): Current panel
        """

    def after_render_panel(self, panel, rendered):
        """ After the panel was rendered.

        This gives the possibility to execute some checks after showing panel.

        Args:
            panel (HAUIConfigPanel): Current panel
            rendered (bool): Was the panel rendered
        """

    def refresh_panel(self):
        """ Refreshes the current panel.

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

    # entity

    def execute_entity(self, entity):
        """ Executes the given entity.

        Args:
            entity (HAUIConfigEntity): entity
        """
        entity_type = entity.get_entity_type()
        entity_state = entity.get_entity_state()
        navigation = self.app.controller['navigation']
        if entity_type == 'light':
            if entity_state != 'unavailable':
                # open popup
                navigation.open_panel('popup_light', entity=entity)
            else:
                # format msg string
                light_name = self.translate('The light {} is currently not available.')
                msg = light_name.format(entity.get_name())
                msg += '\r\n\r\n'
                msg += self.translate('Entity:')
                msg += '\r\n'
                msg += entity.get_entity_id()
                # open notification
                navigation.open_panel(
                    'popup_notify',
                    title=self.translate('Entity unavailable'),
                    btn_right=self.translate('Close'),
                    icon='alert-circle-outline',
                    notification=msg)
        else:
            entity.execute()

    def add_entity_listener(self, entity_id, callback, attribute=None):
        """ Adds a entity state listener.

        Args:
            entity_id (str): Entity ID
            callback (function): Callback
            attribute (str): Attribute
        """
        handle = self.app.listen_state(callback, entity_id, attribute=attribute)
        self.log(f'Adding entity listener for {entity_id}, attribute {attribute} - handle: {handle}')
        self._handles.append(handle)

    def remove_entity_listener(self, handle):
        """ Removes a entity state listener.

        Args:
            handle (str): Handle
        """
        if handle in self._handles:
            self.app.cancel_listen_state(handle)
            self.log(f'Removing entity listener - handle: {handle}')
            del self._handles[self._handles.index(handle)]

    # basic page functionality (see HAUIBase for generic methods)

    def parse_color(self, color):
        """ Parses the given color.

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
                    self.log(f'Invalid color {color}')
            else:
                try:
                    component_color = int(color)
                except Exception:
                    self.log(f'Invalid color {color}')
        return int(component_color)

    def set_component_text_color(self, component, color):
        """ Sets the text color of the given component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} text color {component_color}')
        self.send_cmd(f'{component[1]}.pco={component_color}')

    def set_component_back_color(self, component, color):
        """ Sets the back color of the component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        # self.log(f'Setting {component[1]} back color {component_color}')
        self.send_cmd(f'{component[1]}.bco={component_color}')

    def set_component_password(self, component, input_password):
        """ Sets a text component to as a password input.

        Args:
            component (tuple): Component
            input_password (bool): should input be used as a password input
        """
        # self.log(f'Setting password text {component[1]}: {input_password}')
        if input_password:
            self.send_cmd(f'{component[1]}.pw=1')
        else:
            self.send_cmd(f'{component[1]}.pw=0')

    def add_component_callback(self, component, callback):
        """ Adds a callback for the given component.

        Args:
            component (tuple): Component
            callback (function): Callback
        """
        self._callbacks.append((component, callback))

    def show_component(self, component):
        """ Shows the component.

        Args:
            component (tuple): Component
        """
        # self.log(f'Showing {component[1]}')
        self.send_cmd(f'vis {component[1]},1')

    def hide_component(self, component):
        """ Hides the component.

        Args:
            component (tuple): Component
        """
        # self.log(f'Hiding {component[1]}')
        self.send_cmd(f'vis {component[1]},0')

    # button state related

    def set_button_state_buttons(self, btn_left, btn_right):
        """ Sets the button state buttons.

        Args:
            btn_left (tuple): Component
            btn_right (tuple): Component
        """
        self._btn_state_left = btn_left
        self._btn_state_right = btn_right

    def update_button_left_state(self, state):
        """ Updates the state of button left.

        Args:
            state (bool): state
        """
        if self._btn_state_left:
            self.set_component_value(self._btn_state_left, state)

    def update_button_right_state(self, state):
        """ Updates the state of button right.

        Args:
            state (bool): state
        """
        if self._btn_state_right:
            self.set_component_value(self._btn_state_right, state)

    def update_button_states(self):
        """ Updates the button state of both buttons.
        """
        self.update_button_left_state(self.app.device.get_left_button_state())
        self.update_button_right_state(self.app.device.get_right_button_state())

    # navigation related

    def unset_nav_buttons(self):
        """ Unsets all nav buttons.
        """
        self._nav_prev = None
        self._nav_next = None
        self._nav_close = None
        self._nav_up = None

    def set_prev_next_nav_buttons(self, nav_prev, nav_next, unset=True):
        """ Sets the prev and next nav buttons.

        Args:
            nav_prev (tuple): component
            nav_next (tuple): component

        Returns:
            None
        """
        if unset:
            self.unset_nav_buttons()
        self._nav_prev = nav_prev
        self._nav_next = nav_next

    def set_close_nav_button(self, nav_close, unset=True):
        """ Sets the close nav button.

        Args:
            nav_close (tuple): component
            unset (bool): Unset the nav buttons, Optional

        """
        if unset:
            self.unset_nav_buttons()
        self._nav_close = nav_close

    def set_up_nav_button(self, nav_up, unset=True):
        """ Sets the up nav button.

        Args:
            nav_up (tuple): component
            unset (bool): Unset the nav buttons, Optional
        """
        if unset:
            self.unset_nav_buttons()
        self._nav_up = nav_up

    # callback

    def callback_button_state_buttons(self, event, component, button_state):
        """ Callback method for button state buttons.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (bool): Button state
        """
        # process button state button press callback
        self.log(f'Got button state button press: {component}-{button_state}')
        if button_state != 0:
            return
        # process button state press
        if component == self._btn_state_left:
            self.send_mqtt(ESP_REQUEST['req_component_int'], self._btn_state_left[1])
        elif component == self._btn_state_right:
            self.send_mqtt(ESP_REQUEST['req_component_int'], self._btn_state_right[1])

    def callback_nav_buttons(self, event, component, button_state):
        """ Callback method for nav button events.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (int): Value of the component event
        """
        # process navigation button press callback
        self.log(f'Got navigation button press: {component}-{button_state}')
        navigation = self.app.controller['navigation']
        # check what button was pressed
        if button_state != 0:
            return
        if self._nav_prev and component[0] == self._nav_prev[0]:
            navigation.open_prev_panel()
        elif self._nav_next and component[0] == self._nav_next[0]:
            navigation.open_next_panel()
        elif self._nav_close and component[0] == self._nav_close[0]:
            navigation.close_panel()
        elif self._nav_up and component[0] == self._nav_up[0]:
            navigation.close_panel()

    # processing

    def process_event(self, event):
        """ Processes app events.

        Args:
            event (HAUIEvent): Event
        """
        # compoment value
        if event.name == ESP_RESPONSE['res_component_int']:
            # parse json response, set brightness
            data = event.as_json()
            if data.get('name', '') == self._btn_state_left[1]:
                self.app.device.set_left_button_state(bool(data['value']))
            elif data.get('name', '') == self._btn_state_right[1]:
                self.app.device.set_right_button_state(bool(data['value']))
        # component event
        if event.name == ESP_EVENT['component']:
            self.process_component_event(event)

    def process_component_event(self, event):
        """ Processes component events from component callback.

        Args:
            event (str): Event
        """
        component_info = [int(x) for x in event.as_str().split(',')]
        if len(component_info) != 3:
            return
        if component_info[0] != self.page_id:
            return
        for component, callback in self._callbacks:
            if component_info[1] == component[0]:
                callback(event, component, component_info[2])

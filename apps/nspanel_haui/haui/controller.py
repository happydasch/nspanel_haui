import requests

from .version import __version__ as haui_version
import threading
import time
import json

from .helper.page import get_page_id_for_panel, get_page_class_for_panel
from .const import (
    SERVER_REQUEST, SERVER_RESPONSE, ESP_EVENT, ESP_REQUEST,
    ESP_RESPONSE, ALL_RECV, ALL_CMD)
from .utils import merge_dicts
from .base import HAUIPart, HAUIEvent


class HAUIMQTTController(HAUIPart):

    """
    MQTT controller

    Provides access to MQTT functionality.
    """

    def __init__(self, app, config, mqtt, event_callback):
        """ Initialize for MQTT controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller

            mqtt (): MQTT client
            event_callback (method): Callback for events
        """
        super().__init__(app, config)
        self.log(f'Creating MQTT Controller with config: {config}')
        self.mqtt = mqtt
        self.prev_cmd = None
        # callback for events
        self._event_callback = event_callback

    # part

    def start_part(self):
        """ Starts the part.
        """
        # topics for communication with panel
        device_name = self.app.device.get_device_name()
        self._topic_prefix = f'nspanel_haui/{device_name}'
        if self._topic_prefix.endswith('/'):
            self._topic_prefix = self._topic_prefix[:-1]
        self._topic_cmd = f'{self._topic_prefix}/cmd'
        self._topic_recv = f'{self._topic_prefix}/recv'
        # setup listener
        self.mqtt.mqtt_subscribe(topic=self._topic_recv)
        self.mqtt.listen_event(
            self.callback_event, 'MQTT_MESSAGE', topic=self._topic_recv)

    # public

    def send_cmd(self, name, value='', force=False):
        """ Sends a command to the panel.

        Args:
            name (str): Command name
            value (str, optional): Value for command. Defaults to ''.
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        if name not in ALL_CMD:
            self.log(
                f'Unknown command {name} received.'
                f' content: {value}')
        cmd = json.dumps({'name': name, 'value': value})
        if not force and self.prev_cmd == cmd:
            self.log(f'Dropping identical consecutive message: {cmd}')
            return
        self.mqtt.mqtt_publish(self._topic_cmd, cmd)
        self.prev_cmd = cmd

    def callback_event(self, event_name, data, kwargs):
        """ Callback for events.

        Args:
            event_name (str): Event name
            data (dict): Event data
            kwargs (dict): Additional arguments
        """
        if event_name != 'MQTT_MESSAGE':
            return
        if data['payload'] == '':
            return
        try:
            event = json.loads(data['payload'])
        except Exception:
            self.log(f'Got invalid json: {data}')
            return
        name = event['name']
        value = event['value']
        if name not in ALL_RECV:
            self.log(
                f'Unknown message {name} received.'
                f' content: {value}')
        # notify about event
        event = HAUIEvent(name, value)
        self._event_callback(event)


class HAUIConnectionController(HAUIPart):

    """
    Connection Controller

    Provides connection related handling. All needed functionality
    to keep a connection alive is here.
    Timeouts and heartbeats from client will be dispatched to
    the provided callback.

    - Connects / disconnects device
    - Sends out heartbeat responses when client is connected
    - Waits for heartbeat messages from client, timeout if server
        stops receiving heartbeat messages
    """

    def __init__(self, app, config, connection_callback):
        """ Initialize for Connection Controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller

            connection_callback (method): Callback for connection
                state changes
        """
        super().__init__(app, config)
        self.log(f'Creating Connection Controller with config: {config}')
        # initialize heartbeat variables
        self.connected = False
        self._interval = 0
        self._last_time = 0
        self._timer = None
        # callbacks
        self._connection_callback = connection_callback

    # internal

    def _check_timeout(self):
        """ Checks if a timeout occured.
        """
        overdue_factor = self.get('overdue_factor', 2.0)
        time_max = self._last_time + (self._interval * overdue_factor)
        if time.monotonic() > time_max:
            if self.connected:
                self.log('Heartbeat timeout from device')
                self._set_connected(False)
        if self.is_started():
            self._restart_timer()

    def _start_timer(self):
        """ Starts the check timer.
        """
        self._timer = threading.Timer(
            self._interval, self._check_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _stop_timer(self):
        """ Stops the check timer.
        """
        if self._timer:
            self._timer.cancel()

    def _restart_timer(self):
        """ Restarts the check timer.
        """
        self._stop_timer()
        self._start_timer()

    def _update_last_time(self):
        """ Updates the last time a heartbeat was received.
        """
        self._last_time = time.monotonic()

    def _set_connected(self, connected):
        """ Sets the connection state.

        Args:
            connected (bool): Connected state
        """
        if not connected and self.connected:
            # if device set to disconnected then send
            # a connection closed if there was a connection
            # before
            self.send_mqtt(SERVER_RESPONSE['ad_connection_closed'], '', True)
        self.connected = connected
        self._connection_callback(connected)

    # part

    def start_part(self):
        """ Starts the part.
        """
        # set interval
        device_interval = self.app.device.device_vars.get(
            'heartbeat_interval', 5.0)
        self._interval = int(self.get('heartbeat_interval', device_interval))
        self.log(f'Using heartbeat interval: {self._interval}')
        self._start_timer()

    # events

    def process_event(self, event):
        """ Process events.

        Args:
            event (HAUIEvent): Event to process
        """
        device = self.app.device

        # heartbeat handling
        if event.name == SERVER_REQUEST['heartbeat']:
            self._update_last_time()
            if not self.connected:
                # answer with a reconnection request
                self.log(
                    'Device sent heartbeat but is not connected,'
                    ' requesting reconnect')
                self.send_mqtt(ESP_REQUEST['req_reconnect'])
            else:
                # answer with a server heartbeat
                self.send_mqtt(SERVER_RESPONSE['ad_heartbeat'], 'alive', True)

        # connection request handling
        if event.name in ['req_connection', 'res_connection']:
            # make sure the device does not timeout while connecting
            self._update_last_time()
        if event.name == SERVER_REQUEST['req_connection']:
            connection_request = json.loads(event.value)
            device.set_device_vars(connection_request, append=False)
            self.log(f'Connection request from device: {connection_request}')
            # notify device about next step
            self.send_mqtt(
                SERVER_RESPONSE['ad_connection_response'],
                {'version': haui_version},
                True)
        elif event.name == SERVER_REQUEST['res_connection']:
            connection_response = json.loads(event.value)
            device.set_device_vars(connection_response, append=True)
            self.log(f'Connection response from device: {connection_response}')
            # request latest device state infos
            self.send_mqtt(ESP_REQUEST['req_device_state'])
        elif event.name == ESP_RESPONSE['res_device_state']:
            # self.log(f'Device state received {event.value}')
            device_state = json.loads(event.value)
            device.set_device_vars(device_state, append=True)
            # after getting device state the device is connected
            if not self.connected:
                self._set_connected(True)
                # notify device about successful connection
                self.send_mqtt(
                    SERVER_RESPONSE['ad_connection_initialized'], '', True)


class HAUIGestureController(HAUIPart):

    """
    Gesture Controller

    Provides access to advanced gesture control.
    Supports gesture sequences.
    """

    def __init__(self, app, config):
        """ Initialize for gesture controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f'Creating Gesture Controller with config: {config}')
        self._current_seq = {}

    # public

    def process_gesture(self, gesture_name):
        """ Processes the gesture with the given name.

        Args:
            gesture_name (str): Name of the gesture
        """
        # remove currently active sequences if they timed out
        time_now = int(time.time())
        for seq_index in range(len(self._current_seq)):
            time_start = self._current_seq[seq_index]['time_start']
            time_max = self._current_seq[seq_index]['time_max']
            if time_max < time_now:
                # stop processing if time passed max time for gesture
                self.log(f'Seqence timeout for {seq_index}')
                del self._current_seq[seq_index]
                continue

        # find all matching sequences for this gesture
        for seq_index, seq_data in enumerate(self._config):
            # check timeframe, if no timeframe defined, skip this
            timeframe = int(seq_data.get('timeframe', 0))
            if not timeframe:
                continue
            # check sequence config
            gestures = seq_data.get('sequence', [])
            if not len(gestures):
                self.log(f'No gestures for sequence {seq_index} defined')
                continue
            # check for sequence begin
            if seq_index not in self._current_seq:
                # current gesture is the first in sequence
                if gesture_name == gestures[0]:
                    # start seq
                    time_start = int(time.time())
                    time_max = int(time_start + timeframe)
                    self._current_seq[seq_index] = {
                        'time_start': time_start,
                        'time_max': time_max,
                        'index': 0
                    }
                    self.log(f'Gesture sequence {seq_index} started')
            # check while in sequence
            else:
                # check if gesture is in sequence
                current_index = self._current_seq[seq_index]['index'] + 1
                if gesture_name != gestures[current_index]:
                    self.log(
                        f'Invalid gesture {gesture_name} ({gestures[current_index]}) at'
                        f' index {current_index} for sequence {seq_index} ({gestures}) occured')
                    # invalid gesture for this sequence
                    del self._current_seq[seq_index]
                else:
                    # current gesture is in sequence
                    if current_index < len(gestures) - 1:
                        # sequence is not yet complete
                        self._current_seq[seq_index]['index'] = current_index
                    else:
                        # complete sequence, last gesture in sequence
                        self.log(f'Gesture sequence {seq_index} completed')
                        # remove sequence from currently active seqences
                        # when completed
                        del self._current_seq[seq_index]
                        # process finished gesture sequence
                        self.process_gesture_sequence(seq_data)

    def process_gesture_sequence(self, seq_data):
        """ Processes a complete gesture sequence.
        """
        panel_key = seq_data.get('open', '')
        if panel_key == '':
            return
        # process the gesture
        navigation = self.app.controller['navigation']
        navigation.open_panel(panel_key)

    # event

    def process_event(self, event):
        """ Processes an event.

        Args:
            event (Event): Event
        """
        if not self.is_started():
            return
        # check for gesture
        if event.name == ESP_EVENT['gesture']:
            # process gesture
            self.process_gesture(event.value)


class HAUINavigationController(HAUIPart):

    """
    Navigation Controller

    Provides the whole navigation functionality. Implemented as a controller
    so full app access is possible when navigating.
    """

    def __init__(self, app, config):
        """ Initialize for navigation controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f'Creating Navigation Controller with config: {config}')
        self.page = None
        self.panel = None  # current panel config
        self.panel_kwargs = {}  # current panel kwargs
        self._current_nav = None  # current nav panel config
        self._current_nav_kwargs = {}  # current nav panel kwargs
        self._ids = None  # ids of nav panels
        self._home_panel = None  # home panel config
        self._sleep_panel = None  # sleep panel config
        self._sleep_panel_active = False  # sleep panel state
        self._wakeup_panel = None  # wakeup panel config
        self._page_timeout = None  # Timer for switching pages
        self._close_timeout = None  # Timer for panel auto close
        self._stack = []  # stack for non-nav panels

    # part

    def start_part(self):
        """ Starts the part.
        """
        # get panels
        all_panels = self.app.config.get_panels()
        nav_panels = self.app.config.get_panels(filter_nav_panel=True)
        # store all navigateable panel ids
        self._ids = [panel.id for panel in nav_panels]
        # set special panels
        for panel in all_panels:
            if panel.is_home_panel():
                if self._home_panel is None:
                    self.log(f'Home panel using panel {panel.id}')
                    self._home_panel = panel
                else:
                    self.log(
                        'Multiple home panels defined in config, using first')
            if panel.is_sleep_panel():
                if self._sleep_panel is None:
                    self.log(f'Sleep panel using panel {panel.id}')
                    self._sleep_panel = panel
                else:
                    self.log(
                        'Multiple sleep panels defined in config, using first')
            if panel.is_wakeup_panel():
                if self._wakeup_panel is None:
                    self.log(f'Wakeup panel using panel {panel.id}')
                    self._wakeup_panel = panel
                else:
                    self.log(
                        'Multiple wakeup panels defined in config, using first')
        # set home panel
        if self._home_panel is None and not len(self._ids):
            self.log(f'Using first panel {self._ids[0]} as home panel')
            self._home_panel = self._ids[0]
        # log start
        self.log(f'Panels used for navigation: {", ".join([str(x) for x in self._ids])}')

    # public

    def goto_page(self, page_id):
        """ Goto page method.

        Args:
            page_id (str): Page name or id
        """
        self.log(f'Goto page: {page_id}')
        self.send_mqtt('goto_page', str(page_id))

    def unset_page(self):
        """ Unsets the currently set page.
        """
        if self.page is not None:
            if self.page.is_started():
                self.page.stop()
            self.page = None

    def get_current_panel(self):
        """ Returns the current panel.

        Returns:
            HAUIConfigPanel|None
        """
        return self.panel

    def get_current_nav_panel(self):
        """ Returns the current nav panel.

        Returns:
            HAUIConfigPanel|None
        """
        return self._current_nav

    def has_prev_panel(self):
        """ Returns if a previous panel is available.

        Returns:
            bool: True if current panel has a previous panel
        """
        if self._current_nav is None:
            return False
        try:
            idx = self._ids.index(self._current_nav.id)
            if idx != 0:
                return True
        except ValueError:
            pass
        return False

    def has_next_panel(self):
        """ Returns if a next panel is available.

        Returns:
            bool: True if current panel has a next panel
        """
        if self._current_nav is None:
            return False
        try:
            idx = self._ids.index(self._current_nav.id)
            if len(self._ids) > 1 and idx != len(self._ids) - 1:
                return True
        except ValueError:
            pass
        return False

    def has_up_panel(self):
        """ Returns if a up panel is available.

        Returns:
            bool: True if current panel has a up panel
        """
        if len(self._stack) == 0:
            return False
        return True

    # main

    def reload_panel(self):
        """ Reloads the current panel.
        """
        self.log(f'Reloading panel: {self.panel.id}')
        self.unset_page()
        self.open_panel(self.panel.id, **self.panel_kwargs)

    def refresh_panel(self):
        """ Refreshes the current panel.
        """
        if self.page is None:
            return
        self.log(f'Refreshing panel: {self.panel.id}')
        self.page.refresh_panel()

    def display_panel(self, panel):
        """ Displays the given panel.

        Args:
            panel (HAUIConfigPanel): Panel to display.
        """
        page_id = get_page_id_for_panel(panel.get_type())
        if self.page is not None and self.page.page_id == page_id:
            self.log(f'Setting new panel: {panel.get_type()}')
            # only start the page if it was not started before
            if not self.page.is_started():
                self.page.start()
            self.page.set_panel(panel)

    def open_popup(self, panel_id, **kwargs):
        """ Opens a panel as a popup.

        Args:
            panel_id (str): Id of panel
            kwargs (dict): Additional arguments for panel
        """
        kwargs['mode'] = 'popup'
        self.open_panel(panel_id, **kwargs)

    def open_panel(self, panel_id, **kwargs):
        """ Opens the panel with the given id.

        Args:
            panel_id (str): Id of panel
            kwargs (dict): Additional arguments for panel
        """
        self.log(f'Opening panel: {panel_id}-{kwargs}')

        # create and check page of new panel
        panel = self.app.config.get_panel(panel_id)
        if panel is None:
            self.log(f'Panel {panel_id} not found')
            self.open_home_panel()
            return
        page_id = get_page_id_for_panel(panel.get_type())
        page_class = get_page_class_for_panel(panel.get_type())
        if page_id is None or page_class is None:
            if page_id is None:
                self.log(f'Panel {panel_id} ({panel.get_type()}) has no page defined')
            if page_class is None:
                self.log(f'Panel {panel_id} ({panel.get_type()}) has no page class defined')
            self.open_home_panel()
            return

        # create new config and make kwargs available in new panel
        config = panel.get_default_config(return_copy=True)
        merge_dicts(config, kwargs)
        panel.set_config(config)
        # lock current panel before setting new
        if self.panel is not None:
            # only if has a locked attr
            if hasattr(self.panel, 'locked'):
                self.panel.locked = True
        # set new panel as current panel
        self.panel = panel
        self.panel_kwargs = kwargs

        # new panel is a navigatable panel
        if panel.get_mode() == 'panel':
            self._current_nav = panel
            self._current_nav_kwargs = kwargs
            # new panel is a nav panel, clear stack
            if len(self._stack):
                self._stack = []
        # new panel is not a navigatable panel
        else:
            # add to the navigation stack
            self._stack.append((panel, kwargs))

        # if new panel has an unlock code set and panel is locked,
        # open unlock panel instead
        if panel.get('unlock_code', '') != '' and getattr(panel, 'locked', True):
            self.log(f'Unlock code set, locking panel {panel.id}')
            panel.locked = True
            # open the unlock panel with the panel to unlock as a param
            self.open_popup('popup_unlock', unlock_panel=panel)
            return

        # check current page
        curr_page_id = None
        if self.page is not None:
            curr_page_id = self.page.page_id
            self.page.stop()
        # set new current page and panel
        self.page = page_class(self.app, {'page_id': page_id})
        # notify about panel creation early in process
        self.page.create_panel(panel)

        # set new page for panel
        if curr_page_id != page_id:
            self.log(f'Switching to page {page_id} from {curr_page_id}')
            self.goto_page(page_id)

        # page autostart
        #
        # at this point, it is possible to return
        # and let the page event handle the page switch but this will add a big delay, since
        # it will be needed to wait until a mqtt event is received so just assume the
        # correct page is set already here and continue without return
        #
        # If autostart then it is assumed that the new page is available when called
        # goto_page. If autostart is false, the page will get started when it is
        # active (when a page event is received)
        if kwargs.get('autostart', True):
            self.display_panel(self.panel)
        else:
            self.log('No autostart, waiting for page event')
            # add timer for timeout
            timeout = self.get('page_timeout', 10.0)
            if self._page_timeout is not None:
                self._page_timeout.cancel()
            self._page_timeout = threading.Timer(
                timeout, self.open_panel,
                # provide current params and make sure that autostart is on for timeout call
                kwargs={**kwargs, **{'panel_id': panel_id, 'autostart': True}})
            self._page_timeout.start()

        # check for close timeout in panel config (contains also kwargs)
        timeout = panel.get('close_timeout', 0)
        if timeout > 0:
            self._close_timeout = threading.Timer(timeout, self.close_panel)
            self._close_timeout.start()

    def close_panel(self):
        """ Closes the current panel.
        """
        # check for active timer
        if self._close_timeout is not None:
            self._close_timeout.cancel()
            self._close_timeout = None
        prev_panel, prev_kwargs = None, None
        # check stack
        if len(self._stack):
            # remove last stacked panel
            curr_panel, curr_kwargs = self._stack.pop()
            unlock_panel = curr_kwargs['unlock_panel'] if 'unlock_panel' in curr_kwargs else None
            self.log(f'Closing panel: {curr_panel.id}')
            # get previous panel
            while len(self._stack):
                panel, kwargs = self._stack.pop()
                # if a unlock panel is set, check if it should be skipped (if not unlocked)
                if unlock_panel and panel.id == unlock_panel.id:
                    if getattr(panel, 'locked', False):
                        continue
                prev_panel, prev_kwargs = panel, kwargs
                break
        # no stack, use current nav panel
        if prev_panel is None:
            if self._current_nav:
                prev_panel, prev_kwargs = self._current_nav, self._current_nav_kwargs
        # fallback panel home panel
        if prev_panel is None:
            prev_panel, prev_kwargs = self._home_panel, {}
        # check for locked panel before opening
        if prev_panel is not None:
            unlock_panel = prev_panel.get('unlock_panel')
            if unlock_panel is not None:
                if prev_panel.id == unlock_panel.id and getattr(prev_panel, 'locked', False):
                    prev_panel, prev_kwargs = None, None
        # open new panel
        if prev_panel is not None:
            self.open_panel(prev_panel.id, **prev_kwargs)

    # helper

    def open_next_panel(self):
        """ Opens the next panel.
        """
        # self.log('Open next panel')
        if self._current_nav is None:
            return
        if self._current_nav.id not in self._ids:
            return
        idx = self._ids.index(self._current_nav.id)
        if idx < len(self._ids) - 1:
            panel_id = self._ids[idx + 1]
        else:
            panel_id = self._ids[0]
        self.open_panel(panel_id)

    def open_prev_panel(self):
        """ Opens the previous panel.
        """
        # self.log('Open prev panel')
        if self._current_nav is None:
            return
        if self._current_nav.id not in self._ids:
            self.log(f'current nav not in ids {self._current_nav} - {self._ids}')
            return
        idx = self._ids.index(self._current_nav.id)
        if idx > 0:
            panel_id = self._ids[idx - 1]
        else:
            panel_id = self._ids[len(self._ids) - 1]
        self.open_panel(panel_id)

    def open_home_panel(self, autostart=True):
        """Opens the home panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to True.
        """
        if self._home_panel is None:
            self.close_panel()
            self.log('No home panel available')
            return
        self.open_panel(self._home_panel.id, autostart=autostart)

    def open_sleep_panel(self, autostart=True):
        """Opens the sleep panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to True.
        """
        if self._sleep_panel is None:
            self.close_panel()
            self.log('No sleep panel available')
            return
        self.open_panel(self._sleep_panel.id, autostart=autostart)

    def open_wakeup_panel(self, autostart=True):
        """ Opens the wakeup panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to True.
        """
        if self._wakeup_panel is None:
            self.close_panel()
            self.log('No wakeup panel available')
            return
        self.open_panel(self._wakeup_panel.id, autostart=autostart)

    # event

    def process_event(self, event):
        """ Process events.

        Args:
            event (HAUIEvent): Event
        """
        device = self.app.device

        # check for page
        if event.name == ESP_EVENT['page']:
            # cancel page timeout if any
            if self._page_timeout is not None:
                self._page_timeout.cancel()
                self._page_timeout = None
            # check current page is not blank page
            if self.page is not None and event.as_int() != 0:
                # wrong page id
                if self.page.page_id != event.as_int():
                    self.log(
                        f'Wrong page {event.as_int()} for current panel page activated,'
                        f' reloading panel to reset page to {self.page.page_id}')
                    self.reload_panel()
                # check received page id
                elif self.page.page_id_recv is not None:
                    self.log(
                        f'Page already got a page_id {event.as_int()} for current panel,'
                        f' refreshing panel to reset page to {self.page.page_id}')
                    self.refresh_panel()
                # page is correct
                else:
                    # update page id
                    if self.page.page_id_recv is None:
                        self.page.page_id_recv = event.as_int()
                    # page not started yet
                    if not self.page.is_started():
                        self.display_panel(self.panel)

        # check timeout page event (sleep)
        if event.name == ESP_EVENT['timeout']:
            if event.value == 'page':
                self._sleep_panel_active = True
                self.open_sleep_panel()

        # check for display state event (dimmed/off/on)
        if event.name == ESP_EVENT['display_state']:
            prev_state = device.device_vars.get('display_state')
            # previous state was off
            if prev_state is not None and prev_state == 'off':
                self.log(f'Display state changed from sleep to {event.as_str()}')
                self._sleep_panel_active = False
            # previous state was dimmed
            elif event.as_str() == 'on':
                if self._sleep_panel_active:
                    self.log(f'Display state changed to {event.as_str()}')
                    self._sleep_panel_active = False
                    self.open_wakeup_panel()

        # wakeup handling, ensure the correct page is set
        # when waking up from sleep
        if event.name == ESP_EVENT['wakeup']:
            if self._wakeup_panel is not None:
                self.log(f'Wakeup panel: {self._wakeup_panel.id}')
                self.open_wakeup_panel()
            else:
                # if no wakeup panel is set, use home panel instead of
                # previous panel
                self.log('No wakeup panel available, using home panel')
                self.open_home_panel()

        # sleep handling
        if event.name == ESP_EVENT['sleep']:
            if self.page:
                # unset current page
                self.unset_page()

        # allow page to process events
        if self.page is not None:
            self.page.process_event(event)


class HAUIUpdateController(HAUIPart):

    """
    Update Controller

    TODO
    - check for esphome version
    - check for display tft version
    - check for haui version
    """

    RELEASES_URL = 'https://api.github.com/repos/happydasch/nspanel_haui/releases'

    def __init__(self, app, config):
        """ Initialize for update controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f'Creating Update Controller with config: {config}')
        self._timer = None
        self._connected_timer = None

    # part

    def start_part(self):
        """ Starts the part.
        """
        interval = self.get('update_interval', 0)
        if interval > 0:
            self._timer = threading.Timer(
                interval,
                lambda: self.send_device_info_request())
            self._timer.daemon = True
            self._timer.start()

    def stop_part(self):
        """ Stops the part.
        """
        if self._timer is not None:
            self._timer.cancel()

    # public

    def send_device_info_request(self):
        """ Sends a device info request to the panel.
        """
        self.log('Sending device_info request')
        self.send_mqtt(ESP_REQUEST['req_device_info'])

    def check_for_update(self, device_info):
        # TODO
        self.log('Checking for update')
        resp = requests.get(self.RELEASES_URL)
        self.log(f'Got resp {resp}')
        try:
            json_decoded = resp.json()
            tag = json_decoded[0]['tag_name']
            assets = json_decoded[0]['assets']
            self.log(f'Got resp {tag}-{assets}')
        except Exception:
            pass

        '''if True:
            navigation = self.app.controller['navigation']
            msg = self.translate('A new display version is available.')
            msg += '\r\n'
            msg += self.translate('Current Version:')
            msg += ' ' + str(device_info['tft_version'])
            msg += '\r\n'
            msg += self.translate('New Version:')
            msg += ' ' + str(new_version)
            msg += '\r\n'
            msg += self.translate('Do you want to update?')

            # open notification
            navigation.open_panel(
                'popup_notify',
                title=self.translate('Update available'),
                btn_left_back_color=(255, 0, 0),
                btn_right_back_color=(0, 255, 0),
                btn_left=self.translate('No'),
                btn_right=self.translate('Yes'),
                button_callback_fnc=self.callback_update_response,
                notification=msg)'''

    # callback

    def callback_update_response(self, btn_left, btn_right):
        self.log('Would start update')

    # event

    def process_event(self, event):
        """ Process events.

        Args:
            event (HAUIEvent): Event
        """
        if event.name == ESP_EVENT['connected']:
            if self._connected_timer is not None:
                self._connected_timer.cancel()
                self._connected_timer = None
            # request device infos when device connects
            # FIXME remove the need of req_device_info as a trigger
            if self.get('check_on_connect', False):
                delay_interval = self.get('on_connect_delay', 30)
                self.log(f'Checking for update on connect in {delay_interval} seconds')
                self._connected_timer = threading.Timer(
                    delay_interval, lambda: self.send_device_info_request())
                self._connected_timer.start()
        if event.name == ESP_RESPONSE['res_device_info']:
            self.log('Got device_info response')
            device_info = json.loads(event.value)
            self.app.device.set_device_vars(device_info, append=True)
            self.check_for_update(device_info)

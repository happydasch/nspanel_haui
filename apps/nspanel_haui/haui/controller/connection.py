import threading
import time
import json

from ..version import __version__ as haui_version
from ..mapping.const import SERVER_REQUEST, SERVER_RESPONSE, ESP_REQUEST, ESP_RESPONSE
from ..base import HAUIPart


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
        """Initialize for Connection Controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller

            connection_callback (method): Callback for connection
                state changes
        """
        super().__init__(app, config)
        self.log(f"Creating Connection Controller with config: {config}")
        # initialize heartbeat variables
        self.connected = False
        self._interval = 0
        self._last_time = 0
        self._timer = None
        # callbacks
        self._connection_callback = connection_callback

    # internal

    def _check_timeout(self):
        """Checks if a timeout occured."""
        overdue_factor = self.get("overdue_factor", 2.0)
        time_max = self._last_time + (self._interval * overdue_factor)
        if time.monotonic() > time_max:
            if self.connected:
                self.log("Heartbeat timeout from device")
                self._set_connected(False)
        if self.is_started():
            self._restart_timer()

    def _start_timer(self):
        """Starts the check timer."""
        self._timer = threading.Timer(self._interval, self._check_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _stop_timer(self):
        """Stops the check timer."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _restart_timer(self):
        """Restarts the check timer."""
        self._stop_timer()
        self._start_timer()

    def _update_last_time(self):
        """Updates the last time a heartbeat was received."""
        self._last_time = time.monotonic()

    def _set_connected(self, connected):
        """Sets the connection state.

        Args:
            connected (bool): Connected state
        """
        if not connected and self.connected:
            # if device set to disconnected then send
            # a connection closed if there was a connection
            # before
            self.send_mqtt(SERVER_RESPONSE["ad_connection_closed"], "", True)
        self.connected = connected
        self._connection_callback(connected)

    # part

    def start_part(self):
        """Called when part is started."""
        # set interval
        device_interval = self.app.device.device_info.get("heartbeat_interval", 5.0)
        self._interval = int(self.get("heartbeat_interval", device_interval))
        self.log(f"Using heartbeat interval: {self._interval}")
        self._start_timer()

    def stop_part(self):
        """Called when part is stopped."""
        self._stop_timer()

    # events

    def process_event(self, event):
        """Process events.

        Args:
            event (HAUIEvent): Event to process
        """
        device = self.app.device

        # heartbeat handling
        if event.name == SERVER_REQUEST["heartbeat"]:
            self._update_last_time()
            if not self.connected:
                # answer with a reconnection request
                self.log(
                    "Device sent heartbeat but is not connected,"
                    " requesting reconnect"
                )
                self.send_mqtt(ESP_REQUEST["req_reconnect"])
            else:
                # answer with a server heartbeat
                self.send_mqtt(SERVER_RESPONSE["ad_heartbeat"], "alive", True)

        # connection request handling
        if event.name in ["req_connection", "res_connection"]:
            # make sure the device does not timeout while connecting
            self._update_last_time()
        if event.name == SERVER_REQUEST["req_connection"]:
            connection_request = json.loads(event.value)
            device.set_device_info(connection_request, append=False)
            self.log(f"Connection request from device: {connection_request}")
            # notify device about next step
            self.send_mqtt(
                SERVER_RESPONSE["ad_connection_response"],
                {"version": haui_version},
                True,
            )
        elif event.name == SERVER_REQUEST["res_connection"]:
            connection_response = json.loads(event.value)
            device.set_device_info(connection_response, append=True)
            self.log(f"Connection response from device: {connection_response}")
            # request latest device state infos
            self.send_mqtt(ESP_REQUEST["req_device_state"])
        elif event.name == ESP_RESPONSE["res_device_state"]:
            # self.log(f'Device state received {event.value}')
            device_state = json.loads(event.value)
            device.set_device_info(device_state, append=True)
            # after getting device state the device is connected
            if not self.connected:
                self._set_connected(True)
                # notify device about successful connection
                self.send_mqtt(SERVER_RESPONSE["ad_connection_initialized"], "", True)

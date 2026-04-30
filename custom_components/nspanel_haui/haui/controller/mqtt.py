import json

from ..abstract.base import HAUIBase
from ..abstract.event import HAUIEvent
from ..mapping.const import ALL_CMD, ALL_RECV


class HAUIMQTTController(HAUIBase):
    """MQTT controller

    Provides access to MQTT functionality.
    """

    def __init__(self, app, config, mqtt, event_callback):
        """Initialize for MQTT controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller

            mqtt (): MQTT client
            event_callback (method): Callback for events
        """
        super().__init__(app, config)
        self.mqtt = mqtt
        self.prev_cmd = None
        self._topic_prefix = None
        self._topic_cmd = None
        self._topic_recv = None
        self._device_cmd_topics: list[str] = []
        # callback for events
        self._event_callback = event_callback
        # status publishing
        topic_prefix = self.config.get("mqtt", {}).get("topic_prefix", "nspanel_haui_test")
        self._status_topic = f"{topic_prefix}/status"
        self._status_timer = None

    # part

    def start_part(self):
        """Starts the part."""
        # topics for communication with panel
        topic_prefix = self.config.get("mqtt", {}).get("topic_prefix", "nspanel_haui_test")
        devices = self.config.get("devices", [])

        if devices:
            # Multi-device mode: subscribe to each device's recv topic
            self._device_cmd_topics = []
            for device in devices:
                device_name = device.get("name", self.app.name)
                if not device_name:
                    continue
                recv_topic = f"{topic_prefix}/{device_name}/recv"
                cmd_topic = f"{topic_prefix}/{device_name}/cmd"
                self.log(f"Subscribing to device '{device_name}': recv={recv_topic}")
                self.mqtt.mqtt_subscribe(topic=recv_topic)
                self.mqtt.listen_event(
                    self.callback_event, "MQTT_MESSAGE", topic=recv_topic
                )
                self._device_cmd_topics.append(cmd_topic)

            # Use first device's prefix for backward compat
            first_device = devices[0].get("name", self.app.name)
            self._topic_prefix = f"{topic_prefix}/{first_device}"
            self._topic_cmd = self._device_cmd_topics[0] if self._device_cmd_topics else f"{self._topic_prefix}/cmd"
            self._topic_recv = f"{self._topic_prefix}/recv"
            self.log(f"Multi-device mode with {len(devices)} device(s)")
        else:
            # Backward compat: single-device mode
            name = self.app.name
            self._topic_prefix = f"{topic_prefix}/{name}"
            if self._topic_prefix.endswith("/"):
                self._topic_prefix = self._topic_prefix[:-1]
            self._topic_cmd = f"{self._topic_prefix}/cmd"
            self._topic_recv = f"{self._topic_prefix}/recv"
            self._device_cmd_topics = [self._topic_cmd]
            self.log(f"Single-device mode: using MQTT topic prefix: {self._topic_prefix}")

        self._publish_status("online")

        # Republish status every 30 seconds to ensure it stays current
        self._start_status_timer()

    def stop_part(self):
        """Stops the part."""
        # Stop status timer
        self._stop_status_timer()
        # Publish offline status
        self._publish_status("offline")

    def _publish_status(self, status):
        """Publishes integration status to MQTT.

        Args:
            status (str): Status value ("online" or "offline")
        """
        try:
            self.mqtt.mqtt_publish(self._status_topic, status, retain=True)
        except Exception as e:
            self.log(f"ERROR publishing status: {e}")

    def _start_status_timer(self):
        """Starts timer to republish status periodically."""
        if self._status_timer is not None:
            return
        self._status_timer = self.app.run_every(
            self._status_timer_callback, "now+30", 30
        )

    def _stop_status_timer(self):
        """Stops the status timer."""
        if self._status_timer is not None:
            self.app.cancel_timer(self._status_timer)
            self._status_timer = None

    def _status_timer_callback(self, kwargs):
        """Callback for status timer - republishes status."""
        self._publish_status("online")

    # public

    def send_cmd(self, cmd, value="", force=False):
        """Sends a command to the panel(s).

        In multi-device mode the command is broadcast to every device's cmd topic.

        Args:
            cmd (str): Command
            value (str, optional): Value for command. Defaults to ''.
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        if cmd not in ALL_CMD:
            self.log(f"Unknown command {cmd} received. content: {value}")
        cmd_json = json.dumps({"name": cmd, "value": value})
        if not force and self.prev_cmd == cmd_json:
            self.log(f"Dropping identical consecutive message: {cmd_json}")
            return
        # Publish to all device cmd topics (multi-device broadcast)
        for topic in self._device_cmd_topics:
            self.mqtt.mqtt_publish(topic, cmd_json)
        self.prev_cmd = cmd_json

    def callback_event(self, event_name, data, kwargs):
        """Callback for events.

        Args:
            event_name (str): Event name
            data (dict): Event data
            kwargs (dict): Additional arguments
        """
        if event_name != "MQTT_MESSAGE":
            return

        # Log all MQTT messages for debugging
        topic = data.get("topic", "unknown")
        payload = data.get("payload", "")

        self.log(
            f"MQTT message received - Topic: {topic}, Payload: {payload}", level="DEBUG"
        )

        if payload == "":
            return
        try:
            event = json.loads(payload)
        except Exception:
            self.log(f"Got invalid json: {data}")
            return
        name = event.get("name", "unknown")
        value = event.get("value", "")

        self.log(
            f"Parsed MQTT event - name: {name}, value: {str(value)[:100]}",
            level="DEBUG",
        )

        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received. content: {value}")
        # notify about event
        event = HAUIEvent(name, value)
        self._event_callback(event)

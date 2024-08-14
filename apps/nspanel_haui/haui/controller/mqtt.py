import json

from ..mapping.const import ALL_RECV, ALL_CMD
from ..abstract.part import HAUIPart
from ..abstract.event import HAUIEvent


class HAUIMQTTController(HAUIPart):

    """
    MQTT controller

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
        self.log(f"Creating MQTT Controller with config: {config}")
        self.mqtt = mqtt
        self.prev_cmd = None
        self._topic_prefix = None
        self._topic_cmd = None
        self._topic_recv = None
        # callback for events
        self._event_callback = event_callback

    # part

    def start_part(self):
        """Starts the part."""
        # topics for communication with panel
        name = self.app.device.get_name()
        self._topic_prefix = f"nspanel_haui/{name}"
        if self._topic_prefix.endswith("/"):
            self._topic_prefix = self._topic_prefix[:-1]
        self._topic_cmd = f"{self._topic_prefix}/cmd"
        self._topic_recv = f"{self._topic_prefix}/recv"
        # setup listener
        self.mqtt.mqtt_subscribe(topic=self._topic_recv)
        self.mqtt.listen_event(
            self.callback_event, "MQTT_MESSAGE", topic=self._topic_recv
        )

    # public

    def send_cmd(self, cmd, value="", force=False):
        """Sends a command to the panel.

        Args:
            cmd (str): Command
            value (str, optional): Value for command. Defaults to ''.
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        if cmd not in ALL_CMD:
            self.log(f"Unknown command {cmd} received." f" content: {value}")
        cmd = json.dumps({"name": cmd, "value": value})
        if not force and self.prev_cmd == cmd:
            self.log(f"Dropping identical consecutive message: {cmd}")
            return
        self.mqtt.mqtt_publish(self._topic_cmd, cmd)
        self.prev_cmd = cmd

    def callback_event(self, event_name, data, kwargs):
        """Callback for events.

        Args:
            event_name (str): Event name
            data (dict): Event data
            kwargs (dict): Additional arguments
        """
        if event_name != "MQTT_MESSAGE":
            return
        if data["payload"] == "":
            return
        try:
            event = json.loads(data["payload"])
        except Exception:
            self.log(f"Got invalid json: {data}")
            return
        name = event["name"]
        value = event["value"]
        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received." f" content: {value}")
        # notify about event
        event = HAUIEvent(name, value)
        self._event_callback(event)

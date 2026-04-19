import json
import os
import sys

import pytest

# Ensure repository root is in sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the required classes
from apps.nspanel_haui.haui.abstract.event import HAUIEvent
from apps.nspanel_haui.haui.controller.notification import HAUINotificationController
from apps.nspanel_haui.haui.device import HAUIDevice
from apps.nspanel_haui.haui.mapping.const import NOTIF_EVENT


class DummyEntity:
    def __init__(self):
        self.calls = []

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class DummyApp:
    def __init__(self):
        self.controller = {}
        self.log_calls = []
        self.call_service_calls = []
        self.entity_calls = []
        self.callback_event_calls = []

    def log(self, msg, **kwargs):  # pragma: no cover
        self.log_calls.append(msg)

    def get_name(self):
        return "testdevice"

    def call_service(self, service, **kwargs):
        self.call_service_calls.append((service, kwargs))

    def get_entity(self, entity_id):
        return DummyEntity()

    def entity_exists(self, entity_id):
        return True

    def listen_state(self, callback, entity):
        return f"handle-{entity}"

    def cancel_listen_state(self, handle):
        pass

    def callback_event(self, event):
        self.callback_event_calls.append(event)


class DummyMQTT:
    def __init__(self):
        self.calls = []

    def send_cmd(self, command, payload, force=False):
        self.calls.append((command, payload, force))


@pytest.fixture
def dummy_app():
    return DummyApp()


@pytest.fixture
def dummy_mqtt():
    return DummyMQTT()


def test_notification_controller_add_remove_clear_get(dummy_app):
    """Verify add, remove, clear and get notifications on the controller."""
    controller = HAUINotificationController(dummy_app, {})

    # Add two notifications
    notif1 = controller.add_notification("Test1", "Message1", "icon1", 5)
    notif2 = controller.add_notification("Test2", "Message2", "icon2", 10)

    all_notifs = controller.get_notifications()
    assert notif1 in all_notifs and notif2 in all_notifs
    assert len(all_notifs) == 2

    # Remove one notification
    removed = controller.remove_notification(notif1)
    assert removed is True
    remaining = controller.get_notifications()
    assert notif1 not in remaining and notif2 in remaining
    assert len(remaining) == 1

    # Clear all
    controller.clear_notifications()
    assert controller.get_notifications() == []


def test_notification_controller_send_mqtt(dummy_app, dummy_mqtt):
    """Ensure send_notification forwards the correct payload to the MQTT controller."""
    # Attach dummy MQTT controller before creating notification controller
    dummy_app.controller["mqtt"] = dummy_mqtt
    controller = HAUINotificationController(dummy_app, {})

    title = "Alert"
    message = "This is a test"
    icon = "bell"
    timeout = 15
    controller.send_notification(title, message, icon, timeout)

    assert len(dummy_mqtt.calls) == 1
    command, payload, force = dummy_mqtt.calls[0]
    assert command == "send_notification"
    assert force is True
    payload_dict = json.loads(payload)
    assert payload_dict == {
        "title": title,
        "message": message,
        "icon": icon,
        "timeout": timeout,
    }


def test_device_play_sound_on_notification_event(dummy_app):
    """Test that a notification event triggers a sound when enabled in config."""
    config = {"sound_on_notification": True}
    device = HAUIDevice(dummy_app, config)

    # Monkey‑patch play_sound to record calls
    device._played = None

    def mock_play(name):
        device._played = name

    device.play_sound = mock_play

    event = HAUIEvent(NOTIF_EVENT["notif_add"], ("Title", "Msg", "Icon", 0))
    device.process_event(event)

    assert device._played == "notification"


# End of file

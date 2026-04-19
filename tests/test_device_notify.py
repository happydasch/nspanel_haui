import os
import sys

# Ensure repository root is in sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.nspanel_haui.haui.controller.notification import HAUINotificationController
from apps.nspanel_haui.haui.device import HAUIDevice


class DummyNavigation:
    def __init__(self):
        self.opened_panel = None

    def open_panel(self, panel):
        self.opened_panel = panel


class DummyMQTT:
    def __init__(self):
        self.calls = []

    def send_cmd(self, command, payload, force=False):
        self.calls.append((command, payload, force))


class DummyApp:
    def __init__(self):
        self.controller = {
            "navigation": DummyNavigation(),
            "notification": None,  # Will be set up in test
        }
        self.service_calls = []
        self.log_calls = []

    def log(self, msg, *args, **kwargs):
        self.log_calls.append(msg)

    def call_service(self, service, **kwargs):
        self.service_calls.append((service, kwargs))

    def entity_exists(self, entity_id):
        return False

    def get_entity(self, entity_id):
        raise RuntimeError("Not implemented")

    def callback_event(self, event):
        pass


def test_device_notify_method():
    """Test that the notify method correctly forwards to the notification controller."""
    app = DummyApp()

    # Create a mock notification controller
    mock_notification_controller = HAUINotificationController(app, {})

    # Set up the notification controller in the app
    app.controller["notification"] = mock_notification_controller

    device = HAUIDevice(app, {})

    # Test the notify method
    title = "Test Notification"
    message = "This is a test message"
    icon = "test_icon"
    timeout = 30

    # Mock the send_notification method to capture the call
    original_send_notification = mock_notification_controller.send_notification
    captured_call = []

    def mock_send_notification(title, message, icon, timeout):
        captured_call.append(
            {"title": title, "message": message, "icon": icon, "timeout": timeout}
        )
        # Call the original method to maintain functionality
        return original_send_notification(title, message, icon, timeout)

    mock_notification_controller.send_notification = mock_send_notification

    # Call the notify method
    device.notify(title, message, icon, timeout)

    # Verify the call was forwarded correctly
    assert len(captured_call) == 1
    call = captured_call[0]
    assert call["title"] == title
    assert call["message"] == message
    assert call["icon"] == icon
    assert call["timeout"] == timeout


def test_device_notify_method_defaults():
    """Test that the notify method works with default parameters."""
    app = DummyApp()

    # Create a mock notification controller
    mock_notification_controller = HAUINotificationController(app, {})

    # Set up the notification controller in the app
    app.controller["notification"] = mock_notification_controller

    device = HAUIDevice(app, {})

    # Test the notify method with default parameters
    title = "Default Notification"

    # Mock the send_notification method to capture the call
    original_send_notification = mock_notification_controller.send_notification
    captured_call = []

    def mock_send_notification(title, message="", icon="", timeout=0):
        captured_call.append(
            {"title": title, "message": message, "icon": icon, "timeout": timeout}
        )
        # Call the original method to maintain functionality
        return original_send_notification(title, message, icon, timeout)

    mock_notification_controller.send_notification = mock_send_notification

    # Call the notify method
    device.notify(title)

    # Verify the call was forwarded correctly
    assert len(captured_call) == 1
    call = captured_call[0]
    assert call["title"] == title
    assert call["message"] == ""
    assert call["icon"] == ""
    assert call["timeout"] == 0


def test_device_notify_method_integration():
    """Test full integration of notify method with MQTT communication."""
    app = DummyApp()

    # Create a mock MQTT controller
    mock_mqtt = DummyMQTT()
    app.controller["mqtt"] = mock_mqtt

    # Create a notification controller
    notification_controller = HAUINotificationController(app, {})
    app.controller["notification"] = notification_controller

    device = HAUIDevice(app, {})

    # Test the notify method
    title = "Integration Test"
    message = "Integration test message"
    icon = "integration_icon"
    timeout = 45

    # Call the notify method
    device.notify(title, message, icon, timeout)

    # Verify the MQTT call was made
    assert len(mock_mqtt.calls) == 1
    command, payload, force = mock_mqtt.calls[0]
    assert command == "send_notification"
    assert force is True

    # Verify payload structure
    import json

    payload_dict = json.loads(payload)
    assert payload_dict["title"] == title
    assert payload_dict["message"] == message
    assert payload_dict["icon"] == icon
    assert payload_dict["timeout"] == timeout

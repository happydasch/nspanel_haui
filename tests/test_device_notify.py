from nspanel_haui.haui.controller.notification import HAUINotificationController
from nspanel_haui.haui.device import HAUIDevice


class DummyNavigation:
    def __init__(self):
        self.opened_panel = None

    def open_panel(self, panel):
        self.opened_panel = panel

    def cancel_timeouts(self):
        pass


class DummyESPHome:
    def __init__(self):
        self.calls = []

    def send_cmd(self, command, payload, force=False):
        self.calls.append((command, payload, force))


class _DevStub:
    """Stub for self.app.device required by HAUIBase.debug_log()."""

    def get(self, key: str, default=0):
        return default


class DummyApp:
    def __init__(self):
        self.device = _DevStub()
        self.controller = {
            "navigation": DummyNavigation(),
            "notification": None,  # Will be set up in test
        }
        self.service_calls = []
        self.log_calls = []
        self.callback_event_calls = []
        self._timer_handles: dict[str, bool] = {}

    def log(self, msg, *args, **kwargs):
        self.log_calls.append(msg)

    def call_service(self, service, **kwargs):
        self.service_calls.append((service, kwargs))

    def entity_exists(self, entity_id):
        return False

    def get_entity(self, entity_id):
        raise RuntimeError("Not implemented")

    def callback_event(self, event):
        self.callback_event_calls.append(event)

    def run_in(self, cb, delay, **kwargs):
        handle = f"timer_{len(self._timer_handles)}"
        self._timer_handles[handle] = True
        return handle

    def cancel_timer(self, handle):
        self._timer_handles.pop(handle, None)


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

    def mock_send_notification(
        title, message, icon, timeout, persistent=False,
        notif_type="info", force_show=False,
    ):
        captured_call.append(
            {
                "title": title,
                "message": message,
                "icon": icon,
                "timeout": timeout,
                "persistent": persistent,
                "notif_type": notif_type,
                "force_show": force_show,
            }
        )
        # Call the original method to maintain functionality
        return original_send_notification(
            title, message, icon, timeout, persistent, notif_type, force_show,
        )

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

    def mock_send_notification(
        title, message="", icon="", timeout=0, persistent=False,
        notif_type="info", force_show=False,
    ):
        captured_call.append(
            {
                "title": title,
                "message": message,
                "icon": icon,
                "timeout": timeout,
                "persistent": persistent,
                "notif_type": notif_type,
                "force_show": force_show,
            }
        )
        # Call the original method to maintain functionality
        return original_send_notification(
            title, message, icon, timeout, persistent, notif_type, force_show,
        )

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
    """Test full integration of notify method: fires notif_add callback_event."""
    app = DummyApp()

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

    # Verify callback_event was called with the correct notif_add event
    assert len(app.callback_event_calls) == 1
    event = app.callback_event_calls[0]
    assert event.name == "notif_add"
    expected_value = (title, message, icon, timeout, False, "info", False)
    assert event.value == expected_value

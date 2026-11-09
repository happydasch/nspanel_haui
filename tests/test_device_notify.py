from custom_components.nspanel_haui.haui.controller.notification import HAUINotificationController
from custom_components.nspanel_haui.haui.device import HAUIDevice
from custom_components.nspanel_haui.haui.device_config import DEVICE_CONFIG


class DummyNavigation:
    def __init__(self):
        self.opened_panel = None

    def open_panel(self, panel):
        self.opened_panel = panel

    def get_current_panel(self):
        return None

    def cancel_timeouts(self):
        pass


class DummyESPHome:
    def __init__(self):
        self.calls = []

    def send_cmd(self, command, payload, force=False):
        self.calls.append((command, payload, force))


class _DevStub:
    """Stub for self.app.device required by HAUIBase.debug_log()."""

    sleeping = False

    def get(self, key: str, default=0):
        return default

    def get_name(self):
        return "testdevice"


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
        self.fire_event_calls = []
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

    def fire_event(self, event_type, data=None):
        self.fire_event_calls.append((event_type, data))

    def run_in(self, cb, delay, **kwargs):
        handle = f"timer_{len(self._timer_handles)}"
        self._timer_handles[handle] = True
        return handle

    def run_every(self, cb, start, interval, **kwargs):
        handle = f"timer_{len(self._timer_handles)}"
        self._timer_handles[handle] = True
        return handle

    def cancel_timer(self, handle):
        self._timer_handles.pop(handle, None)


def test_add_notification_queues_and_fires_the_event():
    """add_notification queues the notification and fires the notif_add event."""
    app = DummyApp()
    controller = HAUINotificationController(app, {})
    app.controller["notification"] = controller

    notification = controller.add_notification(
        "Test Notification", "This is a test message", "test_icon"
    )

    assert controller.get_notifications() == [notification]
    assert len(app.callback_event_calls) == 1
    event = app.callback_event_calls[0]
    assert event.name == "notif_add"
    assert event.value.title == "Test Notification"
    assert event.value.message == "This is a test message"
    assert event.value.icon == "test_icon"
    assert event.value.persistent is False
    assert event.value.notif_id


def test_add_notification_defaults():
    """A notification without optional fields gets the generic defaults."""
    app = DummyApp()
    controller = HAUINotificationController(app, {})
    app.controller["notification"] = controller

    notification = controller.add_notification("Default Notification")

    assert notification.message == ""
    assert notification.icon == ""
    assert notification.persistent is False
    assert notification.force_show is False
    assert notification.icon_color is None
    assert notification.sound == "notification"
    assert notification.text_size == "auto"


def test_device_plays_the_notifications_sound():
    """The device plays the sound carried by the queued notification."""
    app = DummyApp()
    controller = HAUINotificationController(app, {})
    app.controller["notification"] = controller
    device = HAUIDevice(app, {**DEVICE_CONFIG, "sound_on_notification": True})
    played = []
    device.play_sound = played.append

    controller.add_notification("Door", "open", sound="tone")

    (event,) = app.callback_event_calls
    device.process_event(event)

    assert played == ["tone"]

from ..mapping.const import ESP_RESPONSE, NOTIF_EVENT
from ..abstract.part import HAUIPart
from ..abstract.event import HAUIEvent


class HAUINotificationController(HAUIPart):

    """Notification Controller

    Provides functionality for notifications.
    """

    def __init__(self, app, config):
        """Initialize for notification controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Notification Controller with config: {config}")
        self._notifications = []  # list for notifications

    # notifications

    def add_notification(self, title: str, message: str = "", icon: str = "", timeout: int = 0) -> tuple:
        notification = (title, message, icon, timeout,)
        self._notifications.append(notification)
        event = HAUIEvent(NOTIF_EVENT["notif_add"], value=notification)
        self.app.callback_event(event)
        return notification

    def remove_notification(self, notification: tuple) -> bool:
        if notification in self._notifications:
            self._notifications.remove(notification)
            event = HAUIEvent(NOTIF_EVENT["notif_remove"], value=notification)
            self.app.callback_event(event)
            return True
        return False

    def clear_notifications(self) -> None:
        self._notifications = []
        event = HAUIEvent(NOTIF_EVENT["notif_clear"], value=None)
        self.app.callback_event(event)

    def get_notifications(self) -> list:
        return self._notifications.copy()

    def has_notifications(self) -> bool:
        return len(self._notifications) > 0

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process events.

        Args:
            event (HAUIEvent): Event
        """
        if event.name == ESP_RESPONSE["send_notification"]:
            self.log(f"Send notification: {event.as_str()}")
            notification = event.as_json()
            self.add_notification(**notification)

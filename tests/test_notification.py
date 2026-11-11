import copy
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.controller.notification import (
    HAUINotificationController,
    Notification,
)
from custom_components.nspanel_haui.haui.device import HAUIDevice
from custom_components.nspanel_haui.haui.device_config import DEVICE_CONFIG
from custom_components.nspanel_haui.haui.mapping.const import (
    ESPAction,
    ESPResponse,
    NotifEvent,
    PopupPanelKey,
)
from custom_components.nspanel_haui.haui.mapping.panel import POPUP_PANEL_MAPPING
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.clocktwo import ClockTwoPage
from custom_components.nspanel_haui.haui.page.weather import WeatherPage


class DummyEntity:
    def __init__(self):
        self.calls = []

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class _DevStub:
    """Stub for self.app.device required by HAUIBase.debug_log()."""

    display_visible = True

    def __init__(self, app=None):
        self._app = app
        self.wakes = 0

    def wake_for_notification(self):
        self.wakes += 1

    @property
    def sleeping(self):
        """Mirror HAUIDevice: sleep means the idle page is shown."""
        navigation = self._app.controller.get("navigation") if self._app else None
        return getattr(navigation, "idle_panel_active", False) is True

    def get(self, key: str, default=0):
        return default

    def get_name(self):
        return "testdevice"

    def get_locale(self):
        return "en_US"


class DummyApp:
    def __init__(self):
        self.controller = {}
        self.device = _DevStub(self)
        self.log_calls = []
        self.call_service_calls = []
        self.entity_calls = []
        self.callback_event_calls = []
        self.fire_event_calls = []
        self._timer_handles: dict[str, bool] = {}

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


class DummyESPHome:
    def __init__(self):
        self.calls = []

    def send_cmd(self, command, payload, force=False):
        self.calls.append((command, payload, force))


@pytest.fixture
def dummy_app():
    return DummyApp()


@pytest.fixture
def dummy_esphome():
    return DummyESPHome()


def test_notification_controller_add_remove_clear_get(dummy_app):
    """Verify add, remove, clear and get notifications on the controller."""
    controller = HAUINotificationController(dummy_app, {})

    # Add two notifications
    notif1 = controller.add_notification("Test1", "Message1", "icon1")
    notif2 = controller.add_notification("Test2", "Message2", "icon2")

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


def test_queued_notification_exposes_named_fields(dummy_app):
    dummy_app.controller["navigation"] = MagicMock()
    controller = HAUINotificationController(dummy_app, {})

    notif = controller.add_notification(
        "Door",
        "Front door open",
        "mdi:door",
        persistent=True,
        icon_color="#4aa5ee",
        sound="alert_fast",
    )

    assert (notif.title, notif.message, notif.icon) == (
        "Door",
        "Front door open",
        "mdi:door",
    )
    assert notif.persistent is True
    assert notif.force_show is True
    assert notif.icon_color == "#4aa5ee"
    assert notif.sound == "alert_fast"
    assert dummy_app.fire_event_calls[-1][1]["force_show"] is True


def test_notification_controller_send_esphome(dummy_app, dummy_esphome):
    """Ensure add_notification fires notif_add callback_event with correct data."""
    controller = HAUINotificationController(dummy_app, {})

    title = "Alert"
    message = "This is a test"
    icon = "bell"
    controller.add_notification(title, message, icon)

    assert len(dummy_app.callback_event_calls) == 1
    event = dummy_app.callback_event_calls[0]
    assert event.name == "notif_add"
    assert event.value.title == title
    assert event.value.message == message
    assert event.value.icon == icon
    assert event.value.persistent is False
    assert event.value.icon_color is None
    assert event.value.sound == "notification"
    assert event.value.notif_id


def test_notification_event_includes_timeout(dummy_app):
    """Automations can distinguish a timed notification from one that stays queued."""
    controller = HAUINotificationController(dummy_app, {})

    controller.add_notification("Door", "open", timeout=15)

    event_type, payload = dummy_app.fire_event_calls[-1]
    assert event_type == "nspanel_haui.notification"
    assert payload["timeout"] == 15
    assert payload["icon_color"] is None
    assert payload["sound"] == "notification"
    assert payload["force_show"] is False


def test_empty_icon_color_and_none_sound_are_normalized(dummy_app):
    controller = HAUINotificationController(dummy_app, {})

    notification = controller.add_notification("Door", "open", icon_color="", sound="none")

    assert notification.icon_color is None
    assert notification.sound == ""


def test_unknown_notification_sound_is_rejected(dummy_app):
    controller = HAUINotificationController(dummy_app, {})

    with pytest.raises(ValueError, match="Unknown notification sound"):
        controller.add_notification("Door", "open", sound="airhorn")


def test_old_esphome_payload_defaults_missing_fields(dummy_app):
    """Firmware without the new variables keeps working for one release."""
    controller = HAUINotificationController(dummy_app, {})
    payload = (
        '{"title": "Door", "message": "open", "icon": "", "persistent": false, "text_size": "auto"}'
    )

    controller.process_event(HAUIEvent(ESPResponse.SEND_NOTIFICATION, payload))

    (notification,) = controller.get_notifications()
    assert notification.icon_color is None
    assert notification.sound == "notification"


def test_device_play_sound_on_notification_event(dummy_app):
    """Test that a notification event triggers its configured sound."""
    device = _device(dummy_app, sound_on_notification=True)

    played = []
    device.play_sound = played.append

    event = HAUIEvent(
        NotifEvent.NOTIF_ADD,
        Notification(title="Title", message="Msg", icon="Icon", sound="notification"),
    )
    device.process_event(event)

    assert played == ["notification"]


# --- device sounds and quiet hours ---------------------------------------------


def _device(app, **cfg):
    return HAUIDevice(app, {**copy.deepcopy(DEVICE_CONFIG), **cfg})


def _quiet_window_around_now():
    now = datetime.now()
    return {
        "quiet_hours_start": (now - timedelta(hours=1)).strftime("%H:%M"),
        "quiet_hours_end": (now + timedelta(hours=1)).strftime("%H:%M"),
    }


def test_quiet_hours_ignored_when_do_not_disturb_is_off(dummy_app):
    device = _device(dummy_app, use_do_not_disturb=False, **_quiet_window_around_now())

    assert device._is_quiet_hours() is False


def test_quiet_hours_apply_when_do_not_disturb_is_on(dummy_app):
    device = _device(dummy_app, use_do_not_disturb=True, **_quiet_window_around_now())

    assert device._is_quiet_hours() is True


def test_play_sound_is_silent_during_quiet_hours(dummy_app):
    esphome = MagicMock()
    dummy_app.controller["esphome"] = MagicMock(esphome=esphome)
    device = _device(dummy_app, use_do_not_disturb=True, **_quiet_window_around_now())

    device.play_sound("startup")

    esphome.publish.assert_not_called()


def test_notification_is_silent_by_default(dummy_app):
    device = _device(dummy_app)
    played = []
    device.play_sound = played.append

    device.process_event(
        HAUIEvent(
            NotifEvent.NOTIF_ADD,
            Notification(title="Smoke", message="Kitchen", icon="", persistent=True, sound="alert"),
        )
    )

    assert played == []


def test_notification_plays_its_own_sound(dummy_app):
    device = _device(dummy_app, sound_on_notification=True)
    played = []
    device.play_sound = played.append

    device.process_event(
        HAUIEvent(
            NotifEvent.NOTIF_ADD,
            Notification(title="Smoke", message="Kitchen", icon="", sound="alert"),
        )
    )

    assert played == ["alert"]


def test_notification_sound_is_suppressed_during_quiet_hours(dummy_app):
    device = _device(
        dummy_app,
        sound_on_notification=True,
        use_do_not_disturb=True,
        **_quiet_window_around_now(),
    )
    played = []
    device.play_sound = played.append

    device.process_event(
        HAUIEvent(
            NotifEvent.NOTIF_ADD,
            Notification(title="Door", message="open", icon="", sound="alert"),
        )
    )

    assert played == []


def test_silent_notification_plays_nothing(dummy_app):
    device = _device(dummy_app, sound_on_notification=True)
    played = []
    device.play_sound = played.append

    device.process_event(
        HAUIEvent(
            NotifEvent.NOTIF_ADD,
            Notification(title="Smoke", message="Kitchen", icon="", sound=""),
        )
    )

    assert played == []


def test_persistent_notification_repeats_its_sound(dummy_app):
    notification = Notification(
        title="Smoke", message="Kitchen", icon="", persistent=True, sound="alert"
    )
    notif_ctrl = MagicMock()
    notif_ctrl.get_notifications.return_value = [notification]
    notif_ctrl.has_persistent_notifications.return_value = True
    dummy_app.controller["notification"] = notif_ctrl
    loops = []
    dummy_app.run_every = lambda cb, start, interval: loops.append((cb, interval)) or "loop"
    device = _device(dummy_app, sound_on_notification=True, persistent_sound_interval=7)
    played = []
    device.play_sound = played.append

    device.process_event(HAUIEvent(NotifEvent.NOTIF_ADD, notification))
    ((repeat, interval),) = loops
    repeat({})

    assert played == ["alert", "alert"]
    assert interval == 7


def _persistent_alert_device(app, **cfg):
    """Device with one queued audible persistent alert; returns its sound loop."""
    notification = Notification(
        title="Smoke", message="Kitchen", icon="", persistent=True, sound="alert"
    )
    notif_ctrl = MagicMock()
    notif_ctrl.get_notifications.return_value = [notification]
    notif_ctrl.has_persistent_notifications.return_value = True
    app.controller["notification"] = notif_ctrl
    loops = []
    app.run_every = lambda cb, start, interval: loops.append(cb) or "loop"
    device = _device(app, sound_on_notification=True, **cfg)
    played = []
    device.play_sound = played.append
    return device, notification, loops, played


def _device_with_persistent_queue(app, *notifications):
    notif_ctrl = MagicMock()
    notif_ctrl.get_notifications.return_value = list(notifications)
    notif_ctrl.has_persistent_notifications.return_value = True
    app.controller["notification"] = notif_ctrl
    return _device(app, sound_on_notification=True)


def test_removing_persistent_notifications_with_no_audible_sound_stops_the_loop(dummy_app):
    silent = Notification(title="Quiet", message="", icon="", persistent=True, sound="")
    device = _device_with_persistent_queue(dummy_app, silent)
    device._stop_persistent_sound = MagicMock()

    device.process_event(HAUIEvent(NotifEvent.NOTIF_REMOVE, silent))

    device._stop_persistent_sound.assert_called_once()


def test_removing_one_persistent_notification_keeps_the_loop_for_another(dummy_app):
    first = Notification(title="First", message="", icon="", persistent=True, sound="tone")
    second = Notification(title="Second", message="", icon="", persistent=True, sound="alert")
    device = _device_with_persistent_queue(dummy_app, first, second)
    device._stop_persistent_sound = MagicMock()

    device.process_event(HAUIEvent(NotifEvent.NOTIF_REMOVE, first))

    device._stop_persistent_sound.assert_not_called()


def test_persistent_loop_skips_silent_notifications(dummy_app):
    silent = Notification(title="Quiet", message="", icon="", persistent=True, sound="")
    audible = Notification(title="Loud", message="", icon="", persistent=True, sound="tone")
    device = _device_with_persistent_queue(dummy_app, silent, audible)

    assert device._persistent_sound() == "tone"


def test_persistent_loop_follows_the_queue_order(dummy_app):
    first = Notification(title="First", message="", icon="", persistent=True, sound="tone")
    second = Notification(title="Second", message="", icon="", persistent=True, sound="alert")
    device = _device_with_persistent_queue(dummy_app, first, second)

    assert device._persistent_sound() == "tone"


def test_silent_persistent_notification_does_not_start_the_loop(dummy_app):
    silent = Notification(title="Quiet", message="", icon="", persistent=True, sound="")
    device = _device_with_persistent_queue(dummy_app, silent)
    loops = []
    dummy_app.run_every = lambda cb, start, interval: loops.append(cb) or "loop"

    device.process_event(HAUIEvent(NotifEvent.NOTIF_ADD, silent))

    assert loops == []


def test_persistent_alert_from_quiet_hours_sounds_once_they_end(dummy_app):
    device, notification, loops, played = _persistent_alert_device(
        dummy_app, use_do_not_disturb=True, **_quiet_window_around_now()
    )

    device.process_event(HAUIEvent(NotifEvent.NOTIF_ADD, notification))
    (repeat,) = loops
    repeat({})
    # The loop runs through quiet hours, silently.
    assert played == []

    device.config["use_do_not_disturb"] = False  # quiet hours are over
    repeat({})

    assert played == ["alert"]


def test_persistent_alert_loop_goes_silent_when_quiet_hours_begin(dummy_app):
    device, notification, loops, played = _persistent_alert_device(
        dummy_app, use_do_not_disturb=False, **_quiet_window_around_now()
    )
    device.process_event(HAUIEvent(NotifEvent.NOTIF_ADD, notification))
    (repeat,) = loops
    assert played == ["alert"]

    device.config["use_do_not_disturb"] = True  # quiet hours begin
    repeat({})

    assert played == ["alert"]


def test_notification_wakes_the_display_outside_quiet_hours(dummy_app):
    esphome = MagicMock()
    dummy_app.controller["esphome"] = MagicMock(esphome=esphome)
    device = _device(dummy_app)

    device.wake_for_notification()

    esphome.publish.assert_called_once_with(ESPAction.RESET_LAST_INTERACTION, "0")


def test_notification_leaves_the_display_dark_in_quiet_hours(dummy_app):
    esphome = MagicMock()
    dummy_app.controller["esphome"] = MagicMock(esphome=esphome)
    device = _device(dummy_app, use_do_not_disturb=True, **_quiet_window_around_now())

    device.wake_for_notification()

    esphome.publish.assert_not_called()


# --- queue lifecycle, viewing and dismissal ----------------------------------


class _LocaleDevStub(_DevStub):
    def get_locale(self):
        return "en_US"


class LoopbackApp(DummyApp):
    """Routes events back into the controller and keeps timer callbacks, like NSPanelHAUI."""

    def __init__(self):
        super().__init__()
        self.device = _LocaleDevStub(self)
        self.timers = {}
        self.navigation = MagicMock()
        self.controller["navigation"] = self.navigation

    def callback_event(self, event):
        super().callback_event(event)
        self.controller["notification"].process_event(event)

    def run_in(self, cb, delay, **kwargs):
        handle = super().run_in(cb, delay)
        self.timers[handle] = cb
        return handle

    def cancel_timer(self, handle):
        super().cancel_timer(handle)
        self.timers.pop(handle, None)

    def run_every(self, cb, start, interval, **kwargs):
        handle = super().run_every(cb, start, interval)
        self.timers[handle] = cb
        return handle


@pytest.fixture
def loop_ctrl():
    app = LoopbackApp()
    ctrl = HAUINotificationController(app, {})
    app.controller["notification"] = ctrl
    return app, ctrl


def _opened(app):
    """(panel_key, kwargs) of the last open_panel call."""
    args, kwargs = app.navigation.open_panel.call_args
    return args[0], kwargs


def test_indicator_stops_blinking_when_last_notification_dismissed(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open")

    ctrl.remove_notification(ctrl._notifications[0])

    assert ctrl.blinker.new_notifications is False


def test_opening_notifications_marks_them_read(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open")

    ctrl.open_notifications()

    assert ctrl.blinker.new_notifications is False


def test_open_notifications_does_nothing_when_queue_is_empty(loop_ctrl):
    app, ctrl = loop_ctrl

    ctrl.open_notifications()

    app.navigation.open_panel.assert_not_called()


def test_single_notification_popup_shows_its_icon_color(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Smoke", "Kitchen", icon="mdi:fire", icon_color="#4aa5ee")

    ctrl.open_notifications()

    key, kwargs = _opened(app)
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert kwargs["icon_color"] == "#4aa5ee"


def test_single_notification_popup_passes_text_size(loop_ctrl):
    """Per-notification text size (issue #48) reaches the popup panel."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open", text_size=2)

    ctrl.open_notifications()

    key, kwargs = _opened(app)
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert kwargs["text_size"] == 2


def test_esphome_payload_carries_text_size(loop_ctrl):
    """The ESPHome JSON payload may set text_size per notification."""
    app, ctrl = loop_ctrl
    ctrl.process_event(
        HAUIEvent(
            ESPResponse.SEND_NOTIFICATION,
            value='{"title": "Door", "message": "open", "text_size": "3"}',
        )
    )

    (notif,) = ctrl.get_notifications()
    assert notif.text_size == "3"


def test_esphome_payload_without_text_size_defaults_to_auto(loop_ctrl):
    """Old firmware payloads omit text_size and stay on the default."""
    app, ctrl = loop_ctrl
    ctrl.process_event(
        HAUIEvent(
            ESPResponse.SEND_NOTIFICATION,
            value='{"title": "Door", "message": "open"}',
        )
    )

    (notif,) = ctrl.get_notifications()
    assert notif.text_size == "auto"


def test_dismiss_button_removes_notification(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open")
    ctrl.open_notifications()
    _, kwargs = _opened(app)

    kwargs["button_callback_fnc"](False, True)

    assert ctrl.get_notifications() == []


def test_several_notifications_open_the_list(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("A", "1")
    ctrl.add_notification("B", "2")

    ctrl.open_notifications()

    key, kwargs = _opened(app)
    assert key == PopupPanelKey.POPUP_SELECT
    assert [i["name"] for i in kwargs["items"]] == ["A: 1", "B: 2"]


def test_list_selection_opens_the_tapped_notification(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("A", "1")
    ctrl.add_notification("B", "2")
    ctrl.add_notification("C", "3")
    ctrl.open_notifications()
    _, list_kwargs = _opened(app)
    b_value = list_kwargs["items"][1]["value"]

    list_kwargs["selection_callback_fnc"](b_value)

    _, kwargs = _opened(app)
    assert kwargs["title"] == "B"


def test_list_items_drop_a_dismissed_notification(loop_ctrl):
    """Closing the popup re-renders the list from its stored kwargs, so they must stay current."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("A", "1")
    ctrl.add_notification("B", "2")
    ctrl.open_notifications()
    _, list_kwargs = _opened(app)
    list_kwargs["selection_callback_fnc"](list_kwargs["items"][0]["value"])
    _, popup_kwargs = _opened(app)

    popup_kwargs["button_callback_fnc"](False, True)

    assert [i["name"] for i in list_kwargs["items"]] == ["B: 2"]


def test_repeated_notification_alerts_again(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open")
    app.callback_event_calls.clear()

    ctrl.add_notification("Door", "open")

    assert len(ctrl.get_notifications()) == 1
    assert NotifEvent.NOTIF_ADD in [e.name for e in app.callback_event_calls]


@pytest.mark.parametrize(
    ("page_cls", "component"),
    [
        (ClockPage, ClockPage.COMPONENTS.t_main_icon),
        (ClockTwoPage, ClockTwoPage.COMPONENTS.t_notif),
        (WeatherPage, WeatherPage.COMPONENTS.t_main_icon),
    ],
)
def test_tapping_page_indicator_opens_notifications_through_controller(page_cls, component):
    page = page_cls.__new__(page_cls)
    notification = MagicMock()
    navigation = MagicMock()
    page.app = MagicMock(controller={"notification": notification, "navigation": navigation})

    page.callback_function_component(component.name, "")

    notification.open_notifications.assert_called_once_with()
    navigation.open_panel.assert_not_called()


# --- queue player: no-yank and auto-advance ----------------------------------


class _PanelStub:
    """Minimal panel stand-in for the notification-view checks.

    Typed like the real system panel the key opens: ``popup_notify`` has the
    type ``notify`` and ``popup_select`` the type ``select``.
    """

    def __init__(self, key: str, **config: Any):
        self._type = POPUP_PANEL_MAPPING.get(key, key)
        self._config = {"key": key, **config}

    def get_type(self) -> str:
        return self._type

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)


class _TrackingNav:
    """Navigation fake: records opens and reports a configurable current panel."""

    def __init__(self) -> None:
        self.opens: list[tuple[str, dict]] = []
        self.current: _PanelStub | None = None
        self.page = MagicMock()
        self.idle_panel_active = False

    def open_panel(self, panel_id: str, **kwargs: Any) -> None:
        self.opens.append((panel_id, kwargs))
        self.current = _PanelStub(str(panel_id), **kwargs)

    def get_current_panel(self) -> _PanelStub | None:
        return self.current

    def close_panel(self) -> None:
        self.current = None


def _queue_player(app: LoopbackApp) -> tuple[LoopbackApp, HAUINotificationController, _TrackingNav]:
    """App + controller + tracking navigation for the queue-player scenarios."""
    nav = _TrackingNav()
    app.navigation = nav
    app.controller["navigation"] = nav
    ctrl = HAUINotificationController(app, {})
    app.controller["notification"] = ctrl
    return app, ctrl, nav


def _advance_timers(app: LoopbackApp) -> list:
    """The deferred 'show next notification' callbacks currently armed."""
    return [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_advance_queue"]


def test_queued_popup_has_no_auto_close(loop_ctrl):
    """Notifications no longer auto-dismiss: popups carry no close_timeout."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open", force_show=True)

    _, kwargs = _opened(app)
    assert "close_timeout" not in kwargs


def test_force_show_does_not_rip_an_open_popup_away(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)

    ctrl.add_notification("First", "1", force_show=True)
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY

    ctrl.add_notification("Second", "2", force_show=True)

    # The first popup stays up; the second waits in the queue.
    assert len(nav.opens) == 1
    assert [n.title for n in ctrl.get_notifications()] == ["First", "Second"]


def test_force_show_dismissed_popup_advances_to_next_queued(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True)
    ctrl.add_notification("Second", "2", force_show=True)
    first = nav.opens[0][1]

    first["button_callback_fnc"](False, True)  # Dismiss
    first["close_callback_fnc"]()  # popup closes (navigation)
    nav.current = None  # ...back on a normal panel
    advance = _advance_timers(app)
    assert advance, "dismissing a popup with more queued must arm the advance"
    advance[0]({})

    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Second"
    assert [n.title for n in ctrl.get_notifications()] == ["Second"]


def test_closing_popup_without_dismissing_does_not_advance(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True)
    ctrl.add_notification("Second", "2", force_show=True)
    first = nav.opens[0][1]

    first["close_callback_fnc"]()  # user navigated away, notification stayed

    assert _advance_timers(app) == []
    assert len(nav.opens) == 1
    assert [n.title for n in ctrl.get_notifications()] == ["First", "Second"]


def test_advance_respects_an_open_notification_list(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True)
    ctrl.add_notification("Second", "2", force_show=True)
    first = nav.opens[0][1]
    # User opened the list (bell) while the popup was up; the close callback
    # fires when the popup page gives way to the list.
    nav.current = _PanelStub(
        PopupPanelKey.POPUP_SELECT,
        selection_callback_fnc=ctrl._notification_selection_callback,
    )
    first["button_callback_fnc"](False, True)
    first["close_callback_fnc"]()
    advance = _advance_timers(app)
    assert advance
    advance[0]({})

    # No popup forced over the list the user is looking at.
    assert len([o for o in nav.opens if o[0] == PopupPanelKey.POPUP_NOTIFY]) == 1


def test_new_notification_appears_in_open_list_without_page_switch(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1")
    ctrl.add_notification("Second", "2")
    ctrl.open_notifications()  # two queued -> list
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_SELECT
    before = len(nav.opens)

    ctrl.add_notification("Third", "3", force_show=True)

    # No page switch, but the shared list items gained the new entry.
    assert len(nav.opens) == before
    assert [i["name"] for i in nav.opens[-1][1]["items"]] == ["First: 1", "Second: 2", "Third: 3"]


def test_open_popup_is_not_a_notification_view_without_marker(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    # POPUP_NOTIFY used for a non-queued popup (update notice, unavailable
    # entity, ...) must not count as a notification view.
    nav.current = _PanelStub(PopupPanelKey.POPUP_NOTIFY, title="An update is available")

    ctrl.add_notification("First", "1", force_show=True)

    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["notif_id"] != ""


def test_persistent_notification_re_opens_popup_periodically(loop_ctrl):
    """A persistent notification's popup is re-opened by its periodic timer."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)

    ctrl.add_notification("Smoke", "Kitchen", persistent=True)

    # A persistent notification arms a repeating "show it again" timer and
    # opens its popup at once.
    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks, "a persistent notification must arm a periodic re-alert timer"
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY

    # The user navigated away: the next tick brings the popup back.
    nav.current = None
    nav.opens.clear()
    ticks[0]({})
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Smoke"

    # A second tick must not steal the popup the user is already reading.
    opens_before = len(nav.opens)
    ticks[0]({})
    assert len(nav.opens) == opens_before

    # Dismissing the notification stops the re-alert loop.
    ctrl.remove_notification(ctrl.get_notifications()[0])
    assert not [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]


def test_persistent_alert_re_opens_over_the_idle_page(loop_ctrl):
    """Any persistent alert may interrupt the idle/screensaver page."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    nav.idle_panel_active = True

    ctrl.add_notification("Laundry", "done", persistent=True)
    nav.current = None
    nav.opens.clear()

    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks
    ticks[0]({})
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Laundry"


def test_persistent_alert_shows_when_not_idle(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    nav.idle_panel_active = False

    ctrl.add_notification("Laundry", "done", persistent=True)
    nav.current = None
    nav.opens.clear()

    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks
    ticks[0]({})
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Laundry"


# --- optional auto-dismiss timeout -------------------------------------------


def _expire_timers(app):
    """The auto-dismiss callbacks currently armed."""
    return [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_expire"]


def test_without_a_timeout_no_auto_dismiss_timer_is_armed(loop_ctrl):
    """Notifications stay queued until dismissed unless a timeout is given."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open", force_show=True)

    assert _expire_timers(app) == []


def test_timeout_removes_the_notification_and_fires_the_removed_event(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open", timeout=5)
    before = len(app.fire_event_calls)

    (expire,) = _expire_timers(app)
    expire({})

    assert ctrl.get_notifications() == []
    assert ctrl.blinker.new_notifications is False
    removed = [
        data
        for event_type, data in app.fire_event_calls[before:]
        if event_type == "nspanel_haui.notification"
    ]
    assert removed and removed[0]["state"] == "removed"


def test_timed_popup_expires_closes_and_the_queue_advances(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True, timeout=5)
    ctrl.add_notification("Second", "2", force_show=True)
    first = nav.opens[0][1]

    (expire,) = _expire_timers(app)
    expire({})

    assert [n.title for n in ctrl.get_notifications()] == ["Second"]
    assert nav.current is None  # the timed-out popup was closed
    first["close_callback_fnc"]()  # the page stop calls it in the real flow
    advance = _advance_timers(app)
    assert advance, "expired popup must arm the queue advance"
    advance[0]({})
    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Second"


def test_queued_timeout_does_not_disturb_an_open_popup(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True)
    ctrl.add_notification("Second", "2", timeout=3)

    (expire,) = _expire_timers(app)
    expire({})

    assert [n.title for n in ctrl.get_notifications()] == ["First"]
    assert len(nav.opens) == 1  # the open popup stays on screen


def test_removing_a_timed_notification_cancels_its_timer(loop_ctrl):
    app, ctrl = loop_ctrl
    notification = ctrl.add_notification("Door", "open", timeout=5)
    assert _expire_timers(app)

    ctrl.remove_notification(notification)

    assert _expire_timers(app) == []


def test_clear_cancels_all_timeout_timers(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("One", "1", timeout=5)
    ctrl.add_notification("Two", "2", timeout=5)

    ctrl.clear_notifications()

    assert _expire_timers(app) == []


def test_a_timeout_may_expire_a_persistent_notification(loop_ctrl):
    """An explicit timeout overrides the persistent never-dismiss behavior."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("Smoke", "Kitchen", persistent=True, timeout=5)

    (expire,) = _expire_timers(app)
    expire({})

    assert ctrl.get_notifications() == []
    assert ctrl.has_persistent_notifications() is False


# --- display wake and notification ids ----------------------------------------


def test_force_show_wakes_the_display(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)

    ctrl.add_notification("Door", "open", force_show=True)

    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert app.device.wakes == 1


def test_queued_notification_does_not_wake_the_display(loop_ctrl):
    app, ctrl = loop_ctrl
    _queue_player(app)

    ctrl.add_notification("Door", "open")

    assert app.device.wakes == 0


def test_force_show_waiting_behind_an_open_popup_does_not_wake(loop_ctrl):
    app, ctrl = loop_ctrl
    _queue_player(app)
    ctrl.add_notification("First", "1", force_show=True)

    ctrl.add_notification("Second", "2", force_show=True)

    assert app.device.wakes == 1


def test_persistent_re_alert_wakes_the_display(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("Smoke", "Kitchen", persistent=True)
    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]

    ticks[0]({})

    assert nav.opens[-1][0] == PopupPanelKey.POPUP_NOTIFY
    assert app.device.wakes == 1


def test_notification_ids_stay_unique_when_the_queue_turns_over(dummy_app):
    """A freed notification's id is never handed on (CPython reuses id() at once)."""
    controller = HAUINotificationController(dummy_app, {})
    ids = []
    for i in range(5):
        notification = controller.add_notification("Door", str(i))
        ids.append(notification.notif_id)
        controller.remove_notification(notification)
        del notification
        dummy_app.callback_event_calls.clear()
        dummy_app.fire_event_calls.clear()

    assert len(set(ids)) == 5


def test_event_list_and_popup_share_the_notification_id(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1")
    second = ctrl.add_notification("Second", "2")

    ctrl.open_notifications()
    assert nav.opens[-1][1]["items"][1]["value"] == second.notif_id
    ctrl._on_notification_selected(second.notif_id)

    assert nav.opens[-1][1]["notif_id"] == second.notif_id
    added = [d for t, d in app.fire_event_calls if d["state"] == "added"]
    assert added[-1]["id"] == second.notif_id

import copy
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.controller.notification import HAUINotificationController, Notification
from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.device_config import DEVICE_CONFIG
from nspanel_haui.haui.mapping.const import ESPResponse, NotifEvent, SysPanelKey
from nspanel_haui.haui.page.clock import ClockPage
from nspanel_haui.haui.page.clocktwo import ClockTwoPage
from nspanel_haui.haui.page.weather import WeatherPage
from nspanel_haui.haui.utils import notification_blinker


class DummyEntity:
    def __init__(self):
        self.calls = []

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class _DevStub:
    """Stub for self.app.device required by HAUIBase.debug_log()."""

    def get(self, key: str, default=0):
        return default

    def get_name(self):
        return "testdevice"


class DummyApp:
    def __init__(self):
        self.controller = {}
        self.device = _DevStub()
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
    controller = HAUINotificationController(dummy_app, {})

    notif = controller.add_notification(
        "Door", "Front door open", "mdi:door", persistent=True, notif_type="critical"
    )

    assert (notif.title, notif.message, notif.icon) == (
        "Door",
        "Front door open",
        "mdi:door",
    )
    assert notif.persistent is True
    assert notif.notif_type == "critical"
    assert notif.force_show is False


def test_notification_controller_send_esphome(dummy_app, dummy_esphome):
    """Ensure send_notification fires notif_add callback_event with correct data."""
    controller = HAUINotificationController(dummy_app, {})

    title = "Alert"
    message = "This is a test"
    icon = "bell"
    controller.send_notification(title, message, icon)

    assert len(dummy_app.callback_event_calls) == 1
    event = dummy_app.callback_event_calls[0]
    assert event.name == "notif_add"
    expected_value = (title, message, icon, False, "info", False, "auto")
    assert event.value == expected_value


def test_device_play_sound_on_notification_event(dummy_app):
    """Test that a notification event triggers a sound when enabled in config."""
    device = _device(dummy_app, sound_on_notification=True)

    # Monkey‑patch play_sound to record calls
    device._played = None

    def mock_play(name):
        device._played = name

    device.play_sound = mock_play

    event = HAUIEvent(
        NotifEvent.NOTIF_ADD, Notification("Title", "Msg", "Icon", False, "info", False)
    )
    device.process_event(event)

    assert device._played == "notification"


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


def test_critical_notification_plays_alert_sound(dummy_app):
    device = _device(dummy_app)
    played = []
    device.play_sound = played.append

    device.process_event(
        HAUIEvent(
            NotifEvent.NOTIF_ADD, Notification("Smoke", "Kitchen", "", False, "critical", False)
        )
    )

    assert played == ["alert"]


def test_persistent_critical_notification_repeats_alert_sound(dummy_app):
    notification = Notification("Smoke", "Kitchen", "", True, "critical", False)
    notif_ctrl = MagicMock()
    notif_ctrl.get_notifications.return_value = [notification]
    notif_ctrl.has_persistent_notifications.return_value = True
    dummy_app.controller["notification"] = notif_ctrl
    loops = []
    dummy_app.run_every = lambda cb, start, interval: loops.append((cb, interval)) or "loop"
    device = _device(dummy_app, persistent_sound_interval=7)
    played = []
    device.play_sound = played.append

    device.process_event(HAUIEvent(NotifEvent.NOTIF_ADD, notification))
    ((repeat, interval),) = loops
    repeat({})

    assert played == ["alert", "alert"]
    assert interval == 7


# --- queue lifecycle, viewing and dismissal ----------------------------------


class _LocaleDevStub(_DevStub):
    def get_locale(self):
        return "en_US"


class LoopbackApp(DummyApp):
    """Routes events back into the controller and keeps timer callbacks, like NSPanelHAUI."""

    def __init__(self):
        super().__init__()
        self.device = _LocaleDevStub()
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
def loop_ctrl(monkeypatch):
    class _Timer:
        def __init__(self, interval, fn):
            self.daemon = False

        def start(self):
            pass

        def cancel(self):
            pass

    monkeypatch.setattr(notification_blinker.threading, "Timer", _Timer)
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


def test_single_notification_popup_shows_its_type(loop_ctrl):
    app, ctrl = loop_ctrl
    ctrl.add_notification("Smoke", "Kitchen", notif_type="critical")

    ctrl.open_notifications()

    key, kwargs = _opened(app)
    assert key == SysPanelKey.POPUP_NOTIFY
    assert kwargs["notif_type"] == "critical"


def test_single_notification_popup_passes_text_size(loop_ctrl):
    """Per-notification text size (issue #48) reaches the popup panel."""
    app, ctrl = loop_ctrl
    ctrl.add_notification("Door", "open", text_size=2)

    ctrl.open_notifications()

    key, kwargs = _opened(app)
    assert key == SysPanelKey.POPUP_NOTIFY
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
    assert key == SysPanelKey.POPUP_SELECT
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
    """Minimal panel stand-in for the notification-view checks."""

    def __init__(self, panel_type: str, **config: Any):
        self._type = panel_type
        self._config = config

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
    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY

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
    first["close_callback_fnc"]()              # popup closes (navigation)
    nav.current = None                         # ...back on a normal panel
    advance = _advance_timers(app)
    assert advance, "dismissing a popup with more queued must arm the advance"
    advance[0]({})

    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
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
        SysPanelKey.POPUP_SELECT,
        selection_callback_fnc=ctrl._notification_selection_callback,
    )
    first["button_callback_fnc"](False, True)
    first["close_callback_fnc"]()
    advance = _advance_timers(app)
    assert advance
    advance[0]({})

    # No popup forced over the list the user is looking at.
    assert len([o for o in nav.opens if o[0] == SysPanelKey.POPUP_NOTIFY]) == 1


def test_new_notification_appears_in_open_list_without_page_switch(loop_ctrl):
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    ctrl.add_notification("First", "1")
    ctrl.add_notification("Second", "2")
    ctrl.open_notifications()  # two queued -> list
    assert nav.opens[-1][0] == SysPanelKey.POPUP_SELECT
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
    nav.current = _PanelStub(SysPanelKey.POPUP_NOTIFY, title="An update is available")

    ctrl.add_notification("First", "1", force_show=True)

    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["notif_id"] != ""


def test_persistent_notification_re_opens_popup_periodically(loop_ctrl):
    """A persistent notification's popup is re-opened by its periodic timer."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)

    ctrl.add_notification("Smoke", "Kitchen", persistent=True)

    # A persistent notification arms a repeating "show it again" timer.
    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks, "a persistent notification must arm a periodic re-alert timer"

    # The timer fires while no notification view is open: the popup opens.
    ticks[0]({})
    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Smoke"

    # A second tick must not steal the popup the user is already reading.
    opens_before = len(nav.opens)
    ticks[0]({})
    assert len(nav.opens) == opens_before

    # Dismissing the notification stops the re-alert loop.
    ctrl.remove_notification(ctrl.get_notifications()[0])
    assert not [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]

def test_non_critical_persistent_alert_does_not_hijack_idle_page(loop_ctrl):
    """A non-critical persistent alert waits for the user to leave the idle page."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    nav.idle_panel_active = True

    ctrl.add_notification("Laundry", "done", persistent=True)

    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks
    ticks[0]({})
    # Still queued, but not forced over the screensaver.
    assert nav.opens == []
    assert [n.title for n in ctrl.get_notifications()] == ["Laundry"]

    # Once the user is back on a real panel, the next tick shows it.
    nav.idle_panel_active = False
    ticks[0]({})
    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Laundry"


def test_critical_persistent_alert_forces_over_idle_page(loop_ctrl):
    """A critical persistent alert may interrupt the idle page."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    nav.idle_panel_active = True

    ctrl.add_notification("Smoke", "Kitchen", persistent=True, notif_type="critical")

    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks
    ticks[0]({})
    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Smoke"


def test_non_critical_persistent_alert_shows_when_not_idle(loop_ctrl):
    """The idle-page guard only applies while the idle page is shown."""
    app, ctrl = loop_ctrl
    _, _, nav = _queue_player(app)
    nav.idle_panel_active = False

    ctrl.add_notification("Laundry", "done", persistent=True)

    ticks = [cb for cb in app.timers.values() if getattr(cb, "__name__", "") == "_re_alert_tick"]
    assert ticks
    ticks[0]({})
    assert nav.opens[-1][0] == SysPanelKey.POPUP_NOTIFY
    assert nav.opens[-1][1]["title"] == "Laundry"

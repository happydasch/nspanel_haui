"""Slider-drag vs. swipe-navigation disambiguation.

Regression target: dragging a slider (cover position, light brightness /
color temp, settings brightness, media volume) on the panel must update the
value, not be swallowed by gesture navigation.

The touch poller turns a slider drag into a ``swipe_*`` gesture.  Slider
components are marked as "drag" controls so their release defers the value
read briefly (flushed on TOUCH_END or a fallback timer, whichever first)
and the spurious swipe gesture is suppressed (no panel navigation).
"""

import time

from nspanel_haui.haui.abstract.component import Component
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.abstract.haui_page import HAUIPage, _PendingReadRequest
from nspanel_haui.haui.abstract.mixins.component_mixin import ComponentMixin
from nspanel_haui.haui.device import HAUIDevice
from nspanel_haui.haui.mapping.const import ESPEvent, ESPResponse, SysPanelKey

# --- marking sliders as drag components -----------------------------------


class FakeComponentHost(ComponentMixin):
    def __init__(self):
        self._callbacks = []
        self._drag_components = set()


def test_drag_callback_marks_drag_component():
    host = FakeComponentHost()
    slider = Component(11, "hVertPos")
    button = Component(8, "bUp")

    host.add_component_callback(button, lambda *a: None)
    host.add_component_callback(slider, lambda *a: None, drag=True)

    assert slider.id in host._drag_components
    assert button.id not in host._drag_components
    # both callbacks are still registered for dispatch
    assert len(host._callbacks) == 2


def test_mark_drag_component_direct():
    """Sliders exposed as function components are marked directly."""
    host = FakeComponentHost()
    volume = Component(18, "hVolume")

    host.mark_drag_component(volume)

    assert volume.id in host._drag_components


# --- device gesture suppression -------------------------------------------


class DummyNavigation:
    def __init__(self, page):
        self.page = page
        self.next_calls = 0
        self.prev_calls = 0
        self.opened = []

    def open_next_panel(self):
        self.next_calls += 1

    def open_prev_panel(self):
        self.prev_calls += 1

    def open_panel(self, panel_id, **kwargs):
        self.opened.append((panel_id, kwargs))

    # device timer resets touch these on interaction; no-op for the test
    def _start_idle_timer(self):
        pass

    def _start_nav_home_timer(self):
        pass


class DummyPage:
    def __init__(self, suppressed):
        self.panel = object()
        self._suppressed = suppressed

    def is_gesture_suppressed(self):
        return self._suppressed


class DummyApp:
    def __init__(self, page):
        self.controller = {"navigation": DummyNavigation(page)}
        self.device = type("MockDevice", (), {"get": lambda s, k, d=0: d})()

    def log(self, *a, **k):
        pass


def _device_with_page(suppressed):
    app = DummyApp(DummyPage(suppressed))
    device = HAUIDevice(app, {"name": "nspanel_haui"})
    return device, app.controller["navigation"]


def test_swipe_navigates_when_not_suppressed():
    device, nav = _device_with_page(suppressed=False)

    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_left"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_right"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_up"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_down"))

    assert nav.next_calls == 1
    assert nav.prev_calls == 1
    assert nav.opened == [
        (SysPanelKey.SYS_ABOUT, {}),
        (SysPanelKey.SYS_SETTINGS, {}),
    ]


def test_swipe_ignored_during_slider_drag():
    device, nav = _device_with_page(suppressed=True)

    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_left"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_right"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_up"))
    device.process_event(HAUIEvent(ESPEvent.GESTURE, "swipe_down"))

    assert nav.next_calls == 0
    assert nav.prev_calls == 0
    assert nav.opened == []


# --- deferring the slider value read to TOUCH_END -------------------------


class FakePageApp:
    def __init__(self):
        self.timers = []
        self.cancelled = []
        self.controller = {}
        self.device = type("MockDevice", (), {"get": lambda s, k, d=0: d})()
        self.sent_esphome = []
        self.log_calls: list[tuple] = []

    def log(self, msg, **kwargs):
        self.log_calls.append((msg, kwargs))

    def run_in(self, cb, delay, **kwargs):
        self.timers.append((cb, delay))
        return f"handle-{len(self.timers)}"

    def cancel_timer(self, handle):
        self.cancelled.append(handle)

    def send_esphome(self, *args, **kwargs):
        self.sent_esphome.append((args, kwargs))


def _bare_page(page_id=1):
    """A HAUIPage with just the attributes the event paths touch."""
    page = HAUIPage.__new__(HAUIPage)
    page.app = FakePageApp()
    page.page_id = page_id
    page._callbacks = []
    page._callback_map = {}
    page._fnc_id_by_component = {}
    page._drag_components = set()
    page._pending_drag_callback = None
    page._drag_flush_timer = None
    page._suppress_gesture = False
    page._suppress_gesture_timer = None
    page._queued_callback = None
    page._buffer_timer = None
    page._fnc_items = {}
    page._read_callbacks = {}
    page._pending_read_request = None
    page._in_read_callback = False
    page.send_esphome = lambda *a, **kw: page.app.sent_esphome.append((a, kw))
    return page


def test_slider_value_read_deferred_to_touch_end():
    """Releasing a slider defers the value read; the read fires on
    TOUCH_END (or the fallback timer) once the display has settled."""
    page = _bare_page()
    slider = Component(13, "hBrightness")
    calls = []

    def handler(v):
        calls.append(("handler", v))

    page.add_component_callback(slider, lambda *a: None, drag=True)
    page.add_read_callback(slider, handler)

    # slider release (Nextion component event: page,component,release)
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,13,0"))

    # callback NOT fired yet, but a read is pending, a fallback flush is
    # scheduled and gestures are suppressed
    assert calls == []
    assert page._pending_drag_callback is not None
    assert page._drag_flush_timer is not None
    assert page.is_gesture_suppressed() is True

    # touch fully ends -> deferred value read triggered via read request
    page.process_event(HAUIEvent(ESPEvent.TOUCH_END, "10,20,10,200"))

    # read request sent — handler not invoked yet (awaits read_response)
    assert len(page.app.sent_esphome) == 1
    assert page._pending_drag_callback is None
    assert page._drag_flush_timer is None

    # simulate read_response response — handler should fire now
    res_event = HAUIEvent(
        ESPResponse.READ_RESPONSE,
        '{"name":"hBrightness","type":"number","value":"75"}',
    )
    page._process_read_response(res_event)

    assert len(calls) == 1
    assert calls[0] == ("handler", 75)


def test_slider_read_flushes_via_fallback_timer():
    """TOUCH_END comes from a 500 ms touch poll and can be missed entirely
    for short drags — the fallback timer must flush the read anyway."""
    page = _bare_page()
    slider = Component(11, "hVertPos")
    calls = []
    page.add_read_callback(slider, lambda v: calls.append(("handler", v)))
    page.add_component_callback(slider, lambda *a: None, drag=True)

    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,11,0"))
    assert calls == []
    cb, delay = page.app.timers[-1]
    assert delay == HAUIPage.DRAG_FLUSH_DELAY

    # no TOUCH_END arrives; the fallback timer fires instead
    cb()
    assert len(page.app.sent_esphome) == 1

    # a late TOUCH_END must not dispatch a second read request
    page.process_event(HAUIEvent(ESPEvent.TOUCH_END, "10,20,10,200"))
    assert len(page.app.sent_esphome) == 1


def test_non_drag_release_not_deferred():
    """A normal button release is buffered (not handled via the drag path)."""
    page = _bare_page()
    button = Component(8, "bUp")
    calls = []
    page.add_component_callback(button, lambda *a: calls.append(a))

    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,8,0"))

    # not a drag control -> no pending drag read, buffered instead
    assert page._pending_drag_callback is None
    assert page._queued_callback is not None


# --- press events must not fall through to release handling ----------------


def test_press_does_not_queue_release_callback():
    """A press on an ``on_release`` component must not queue (and later
    fire) the release callback — that double-fired callbacks on holds."""
    page = _bare_page()
    button = Component(15, "bPower")
    calls = []
    page.on_release(button, lambda e, c: calls.append(c))

    # press (button_state=1): nothing queued, nothing dispatched
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,15,1"))
    assert page._queued_callback is None
    assert page._buffer_timer is None
    assert calls == []

    # release (button_state=0): buffered for gesture disambiguation
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,15,0"))
    assert page._queued_callback is not None


def test_slider_press_arms_suppression_without_pending_read():
    """A press on a drag control suppresses gestures (long drags must not
    navigate) but must not schedule the value read yet."""
    page = _bare_page()
    slider = Component(13, "hBrightness")
    page.on_release(slider, lambda e, c: None, drag=True)

    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, "1,13,1"))

    assert page.is_gesture_suppressed() is True
    assert page._pending_drag_callback is None
    assert page._drag_flush_timer is None


def test_touch_start_clears_pending_read():
    """TOUCH_START only clears an expired ``_pending_read_request`` — an
    active (non-expired) request is preserved so a fresh read_response that
    arrives after TOUCH_START is not wrongly dropped."""
    page = _bare_page()
    slider = Component(13, "hBrightness")
    calls = []

    def handler(v):
        calls.append(("handler", v))

    page.bind_slider(slider, handler)

    # No pending request → TOUCH_START is a no-op
    page.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert page._pending_read_request is None

    # Stale request (expiry far in the past)
    page._pending_read_request = _PendingReadRequest(
        component_name="stale_prev",
        expiry=0.0,
    )

    # TOUCH_START clears stale entry
    page.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert page._pending_read_request is None

    # Active request (not expired)
    page._pending_read_request = _PendingReadRequest(
        component_name="hBrightness",
        expiry=time.monotonic() + 1000,
    )

    # TOUCH_START preserves active entry
    page.process_event(HAUIEvent(ESPEvent.TOUCH_START, ""))
    assert page._pending_read_request is not None

    # Stale read_response for unknown component — dropped (no handler)
    page._process_read_response(
        HAUIEvent(ESPResponse.READ_RESPONSE, '{"name":"stale_prev","type":"number","value":0}')
    )
    assert calls == []

    # Fresh read_response for active component — dispatched
    page._process_read_response(
        HAUIEvent(ESPResponse.READ_RESPONSE, '{"name":"hBrightness","type":"number","value":75}')
    )
    assert calls == [("handler", 75)]

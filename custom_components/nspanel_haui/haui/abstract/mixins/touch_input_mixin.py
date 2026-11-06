"""Touch input handling for HAUIPage.

Routes the display's touch events to the page: release and press callbacks,
slider drags, the tap-or-swipe buffer, the long press back and display reads
(``REQ_VAL`` / ``REQ_TXT``).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from ...mapping.const import ESPEvent, ESPRequest, ESPResponse
from ..component import Component

if TYPE_CHECKING:
    from ....nspanel_haui import NSPanelHAUI
    from ..haui_event import HAUIEvent
    from ..haui_panel import HAUIPanel


@dataclass
class _PendingReadRequest:
    """A value/text read request awaiting its ``read_response`` event.

    Only one read can be in-flight at a time because the ESP32 has a single
    ``req_val_component``/``req_txt_component`` global.  Expires so a lost
    response doesn't wedge future reads.
    """

    component_name: str
    expiry: float


class TouchInputMixin:
    """Mixin that routes touch events to the page's component callbacks.

    Depends on :class:`~haui.abstract.haui_base.HAUIBase` for ``app``,
    ``log`` and ``send_esphome``, and on :class:`~haui.abstract.haui_page.HAUIPage`
    for ``page_id`` and ``panel``.  The host calls ``_init_touch_input()`` from
    its constructor and routes events through ``_process_touch_event()``.
    """

    # How long a release waits for a GESTURE before its callback fires: a swipe
    # that ends on a widget also releases it, and must navigate, not press it.
    RELEASE_BUFFER_DELAY: ClassVar[float] = 0.1

    # How long after a slider release the deferred callback fires if no
    # TOUCH_END arrives first.  TOUCH_END comes from a 500 ms touch poll
    # (plus one async sensor cycle of lag), so short drags can miss it
    # entirely — this timer guarantees the dispatch always happens, bounded.
    DRAG_FLUSH_DELAY: ClassVar[float] = 0.25

    # Swipe-gesture suppression window after a slider release.  Must outlast
    # the touch poller's worst-case delay (~1 s) because the spurious swipe
    # gesture produced by the drag is only published once the poller detects
    # the touch end.
    DRAG_SUPPRESS_DURATION: ClassVar[float] = 1.5

    # Long press to go back (panel option ``long_press_back``, for pages
    # without header buttons). Touch start/end come from the firmware's
    # 200 ms touch poll, which quantizes the duration: 0.8 s catches a
    # one-second hold. A tap is too short for the poll to report reliably,
    # so a long press is the gesture the poll can detect.
    LONG_PRESS_SECONDS: ClassVar[float] = 0.8
    # Most a long press may move (display pixels) and still count.
    LONG_PRESS_SLOP: ClassVar[int] = 30

    # How long a read request stays "pending" before a lost read_response no longer
    # counts as "in flight" (see request_component_value).  A read_response that
    # arrives after the timeout is dropped so a stale response can't overwrite
    # a newer read.  Set to 6 seconds to accommodate Nextion serial read latency
    # (~3-4 s for a full round-trip: ESPHome service → Nextion proxy read →
    # sensor update → HA event).
    READ_PENDING_TIMEOUT: ClassVar[float] = 6.0

    if TYPE_CHECKING:
        # Provided by HAUIBase / HAUIPage at runtime via MRO.
        app: NSPanelHAUI
        page_id: int
        panel: HAUIPanel | None

        def log(self, msg: str, **kwargs: Any) -> None: ...
        def send_esphome(self, name: str, value: Any = "", force: bool = False) -> None: ...

    def _init_touch_input(self) -> None:
        """Sets the touch input state; call from the host's constructor."""
        # press callbacks (button_state != 0), registered via add_component_callback
        self._callbacks: list[tuple[Component, Callable]] = []
        # release callbacks (button_state == 0): comp_id -> (component, callback)
        self._callback_map: dict[int, tuple[Component, Callable]] = {}
        # release buffered for tap-or-swipe disambiguation: (comp_id, event)
        self._queued_callback: tuple[int, HAUIEvent] | None = None
        self._buffer_timer: str | None = None
        # drag controls (sliders): the swipe gesture the drag motion produces
        # is suppressed (so dragging updates the value instead of navigating),
        # and the value read is deferred to TOUCH_END because the Nextion only
        # finalizes the slider's ``.val`` once the touch fully ends — reading
        # it on the component-release event returns a stale 0.
        self._drag_components: set[int] = set()
        self._suppress_gesture: bool = False
        self._suppress_gesture_timer: str | None = None
        self._pending_drag_callback: tuple[int, HAUIEvent] | None = None
        self._drag_flush_timer: str | None = None
        # start of the current touch, for long press to go back
        self._touch_started_at: float | None = None
        # the single in-flight display read (see _PendingReadRequest)
        self._pending_read_request: _PendingReadRequest | None = None
        # read_response handlers by component name
        self._read_callbacks: dict[str, Callable[[Any], None]] = {}

    def _clear_component_callbacks(self) -> None:
        """Drops the press, release, drag and read registrations of the current panel.

        The in-flight read goes too: its response belongs to the previous panel
        and must not reach the next one's handler for the same component.
        """
        self._callback_map.clear()
        self._callbacks.clear()
        self._drag_components.clear()
        self._read_callbacks.clear()
        self._pending_read_request = None

    def _reset_touch_input(self) -> None:
        """Cancels every pending touch timer and release."""
        self._drop_buffered_release()
        self._cancel_suppress_gesture_timer()
        self._suppress_gesture = False
        self._cancel_drag_flush_timer()
        self._pending_drag_callback = None

    # registration

    def on_release(
        self,
        component: Component | dict[Component, Callable],
        callback: Callable | None = None,
        /,
        *,
        drag: bool = False,
    ) -> None:
        """Register a callback for component release events (button_state == 0).

        This is the preferred way to register callbacks for button/touch
        release events.  The callback receives ``(event, component)`` — the
        ``button_state`` parameter is omitted because it is always 0.

        For rare press-event handling, use ``add_component_callback()`` instead.

        Two forms:

        **Single component:**
        ``self.on_release(self.COMPONENTS.btn_up, self._on_up)``

        **Multiple components (dict):**
        ``self.on_release({self.COMPONENTS.btn_up: self._on_up, ...})``

        Args:
            component: A single Component, or a dict mapping Component to
                callback.
            callback: Callback for the component (required if component is a
                single Component).  Signature: ``handler(event, component)``.
            drag: If True, treat the component as a drag control (slider).

        Raises:
            TypeError: A single component was given without a callback.
        """
        if isinstance(component, dict):
            callbacks = component
        elif callback is None:
            raise TypeError(f"on_release({component.name}) needs a callback")
        else:
            callbacks = {component: callback}
        for comp, cb in callbacks.items():
            self._callback_map[comp.id] = (comp, cb)
            if drag:
                self.mark_drag_component(comp)

    def add_component_callback(self, component: Component, callback: Callable) -> None:
        """Adds a callback for the given component (press events).

        **Prefer** ``on_release()`` for release-only callbacks.  This method
        is intended for rare press-event handling where the
        ``button_state != 0`` is needed.

        ``on_release()`` callbacks receive ``(event, component)`` without
        ``button_state`` (always 0).  This method preserves the old
        ``callback(event, component, button_state)`` signature.

        Args:
            component (Component): Component
            callback (function): Callback
        """
        self._callbacks.append((component, callback))

    def mark_drag_component(self, component: Component) -> None:
        """Marks a component as a drag control (slider).

        Marked components suppress the swipe gesture the drag produces and
        defer the release callback to TOUCH_END.  Use this directly when the
        callback is registered elsewhere (e.g. a slider exposed as a function
        component); ``bind_slider`` does it for plain sliders.

        Args:
            component (Component): Component
        """
        self._drag_components.add(component.id)

    def bind_slider(self, component: Component, handler: Callable[[Any], None]) -> None:
        """Wire up a slider component end-to-end.

        Registers the component as a drag control whose release triggers a
        read request (REQ_VAL), and routes the ``read_response`` event to
        ``handler``.  This replaces the per-page request/response boilerplate.

        Args:
            component: The slider component.
            handler: Called with the read value once the request completes.
                ``value`` is an ``int`` for number reads and a ``str`` for
                text reads.  Signature: ``handler(value)``.
        """
        self.on_release(component, self._callback_slider_release, drag=True)
        self.add_read_callback(component, handler)

    def add_read_callback(self, component: Component | str, handler: Callable[[Any], None]) -> None:
        """Route ``read_response`` events for ``component`` to ``handler``.

        Use this directly when the read request is sent from elsewhere
        (e.g. a function-component callback); use ``bind_slider()`` when the
        component is a plain slider registered via ``on_release``.

        Args:
            component: The component, or the name of a Nextion component or
                variable without a ``COMPONENTS`` entry (e.g. ``"va0"``).
            handler: Called with the read value.  ``value`` is an ``int`` for
                number reads and a ``str`` for text reads.
                Signature: ``handler(value)``.
        """
        self._read_callbacks[_component_name(component)] = handler

    # display reads (REQ_VAL / REQ_TXT)

    def request_component_value(self, component: Component | str) -> None:
        """Request a component's numeric value from the display (REQ_VAL).

        Uses the shared single-slot in-flight guard; see
        ``_request_component_read`` for details.

        Args:
            component: The component, or the name of a Nextion component or
                variable (e.g. ``"hBrightness"``).
        """
        self._request_component_read(component, ESPRequest.REQ_VAL, "value read request")

    def request_component_text(self, component: Component | str) -> None:
        """Request a component's text value from the display (REQ_TXT).

        Uses the shared single-slot in-flight guard; see
        ``_request_component_read`` for details.

        Args:
            component: The component, or the name of a Nextion component or
                variable (e.g. ``"tTitle"``).
        """
        self._request_component_read(component, ESPRequest.REQ_TXT, "text read request")

    def _request_component_read(
        self,
        component: Component | str,
        request_type: ESPRequest,
        log_label: str,
    ) -> None:
        """Send a read request and track it as the single in-flight read.

        Guarded per component: while a request is in flight, further requests
        for the same component are dropped so the ESP32's single request
        global isn't overwritten mid-read (which would attach the wrong
        component name to the read_response).  The guard expires after
        ``READ_PENDING_TIMEOUT`` so a lost response can't wedge the control.

        Args:
            component: The component (or its string name) to read.
            request_type: The ESP request type (``REQ_VAL`` or ``REQ_TXT``).
            log_label: Human-readable label used in diagnostic log messages.
        """
        name = _component_name(component)
        now = time.monotonic()
        if self._pending_read_request is not None and now < self._pending_read_request.expiry:
            self.log(f"{log_label} for {name}: skipped (request pending)")
            return
        self._pending_read_request = _PendingReadRequest(
            component_name=name,
            expiry=now + self.READ_PENDING_TIMEOUT,
        )
        self.log(f"{log_label} for {name}: sending request")
        self.send_esphome(request_type, name, force=True)

    def _callback_slider_release(self, event: HAUIEvent, component: Component) -> None:
        """Release handler installed by ``bind_slider()`` — reads the value."""
        self.request_component_value(component)

    def _process_read_response(self, event: HAUIEvent) -> None:
        """Dispatch a ``read_response`` event to the registered callback.

        Drops the response if ``_pending_read_request`` is ``None`` (the
        panel changed, or a touch dropped it after it expired) or expired
        (response arrived too late).
        """
        data = event.as_json()
        name = data.get("name", "")
        read_type = data.get("type", "number")
        handler = self._read_callbacks.get(name)
        if handler is None:
            return
        if self._pending_read_request is None:
            self.log(f"read_response for {name}: stale response dropped (no pending request)")
            return
        now = time.monotonic()
        if now >= self._pending_read_request.expiry:
            expired = self._pending_read_request
            self._pending_read_request = None
            self.log(
                f"read_response for {name}: stale response dropped "
                f"(expired after {self.READ_PENDING_TIMEOUT:.0f}s — "
                f"requested for {expired.component_name!r})"
            )
            return
        self._pending_read_request = None
        if read_type == "text":
            value = data.get("value", "")
        else:
            try:
                value = int(float(data.get("value", 0)))
            except TypeError, ValueError:
                self.log(f"Invalid read_response value for {name}: {data.get('value')!r}")
                return
        self.log(f"read_response for {name}: type={read_type} value={value!r} — dispatching")
        handler(value)

    # gesture suppression (slider drag vs. swipe navigation)

    def suppress_gesture(self, duration: float = 0.4) -> None:
        """Suppress swipe gestures for ``duration`` seconds.

        Called when a drag control (slider) is released.  The touch poller
        emits the swipe gesture up to ~200 ms after the release, so the
        suppression window must outlast that delay.  Auto-clears via timer.

        Args:
            duration: How long to suppress gestures, in seconds.
        """
        self._cancel_suppress_gesture_timer()
        self._suppress_gesture = True
        self._suppress_gesture_timer = self.app.run_in(self._clear_suppress_gesture, duration)

    def is_gesture_suppressed(self) -> bool:
        """Whether swipe gestures are currently suppressed (slider drag)."""
        return self._suppress_gesture

    def _cancel_suppress_gesture_timer(self) -> None:
        """Cancels the gesture-suppression timer, if active."""
        if self._suppress_gesture_timer is not None:
            self.app.cancel_timer(self._suppress_gesture_timer)
            self._suppress_gesture_timer = None

    def _clear_suppress_gesture(self, _cb_args: dict | None = None) -> None:
        """Clears the gesture-suppression flag when the window expires."""
        self._suppress_gesture = False
        self._suppress_gesture_timer = None

    # events

    def _process_touch_event(self, event: HAUIEvent) -> None:
        """Routes a component, gesture, touch or read-response event.

        Other events are ignored.

        Args:
            event (HAUIEvent): Event
        """
        if event.name == ESPEvent.COMPONENT:
            self.process_component_event(event)
        elif event.name == ESPEvent.GESTURE:
            # the buffered release was the end of a swipe
            self._drop_buffered_release()
        # new touch interaction — invalidate stale (expired) read request
        # entries from previous interactions.  Active entries (just sent)
        # are preserved so a fresh read_response that arrives after TOUCH_START
        # (from the touch poll cycle) is not wrongly dropped.
        elif event.name == ESPEvent.TOUCH_START:
            now = time.monotonic()
            if self._pending_read_request is not None and now >= self._pending_read_request.expiry:
                self._pending_read_request = None
            # A touch on a widget that sends its id reports touch_start twice
            # (Nextion event and touch poll); the first one starts the touch.
            if self._touch_started_at is None:
                self._touch_started_at = now
        elif event.name == ESPEvent.TOUCH_END:
            self._flush_pending_drag_callback()
            self._check_long_press_back(event)
        elif event.name == ESPResponse.READ_RESPONSE:
            self._process_read_response(event)

    def process_component_event(self, event: HAUIEvent) -> None:
        """Processes component events from component callback.

        Args:
            event (HAUIEvent): Event, "page_id,comp_id,button_state"
        """
        component_info = [int(x) for x in event.as_str().split(",")]
        if len(component_info) != 3:
            return
        page_id, comp_id, button_state = component_info
        if page_id != self.page_id:
            return

        # Press events (touch_event != 0): dispatch immediately via the press
        # callback list, then STOP.  A press must never fall through to the
        # release handling below — that would queue the release callback while
        # the finger is still down and double-fire it (e.g. a held power button
        # toggling twice).
        #
        # For drag controls (sliders) the press is skipped entirely because
        # touch_event is 1 for press, not the slider value — the actual
        # value is read asynchronously via a read request on release.
        if button_state != 0:
            # a press on a drag control starts a slider interaction —
            # suppress swipe gestures right away so a long drag can't
            # navigate away mid-interaction
            if comp_id in self._drag_components:
                self.log(
                    f"Drag-ctrl press (comp {comp_id}) — early return (button_state={button_state})"
                )
                self.suppress_gesture(self.DRAG_SUPPRESS_DURATION)
                return
            for component, callback in self._callbacks:
                if comp_id == component.id:
                    callback(event, component, button_state)
                    break
            return

        # Drag controls (sliders): suppress the swipe gesture the drag
        # produces and defer the value read briefly.  The read fires on
        # TOUCH_END or after DRAG_FLUSH_DELAY, whichever comes first —
        # TOUCH_END alone is unreliable (500 ms touch poll, short drags can
        # miss it entirely) and waiting up to ~1 s lets entity-state updates
        # overwrite the slider value before it is read.
        if comp_id in self._drag_components:
            self.log(f"Drag-ctrl release (comp {comp_id}) — queued deferred value read")
            self.suppress_gesture(self.DRAG_SUPPRESS_DURATION)
            self._pending_drag_callback = (comp_id, event)
            self._cancel_drag_flush_timer()
            self._drag_flush_timer = self.app.run_in(
                self._drag_flush_timeout, self.DRAG_FLUSH_DELAY
            )
            return

        # Release events (touch_event == 0): buffer until it is clear the
        # touch was a tap, not the end of a swipe.
        if comp_id in self._callback_map:
            self._drop_buffered_release()
            self._queued_callback = (comp_id, event)
            self._buffer_timer = self.app.run_in(
                self._flush_buffer_callback, self.RELEASE_BUFFER_DELAY
            )

    def _dispatch_release(self, comp_id: int, event: HAUIEvent) -> None:
        """Calls the release callback registered for ``comp_id``, if any."""
        entry = self._callback_map.get(comp_id)
        if entry is not None:
            component, callback = entry
            callback(event, component)

    def _drop_buffered_release(self) -> None:
        """Drops the buffered release and cancels its timer."""
        if self._buffer_timer is not None:
            self.app.cancel_timer(self._buffer_timer)
            self._buffer_timer = None
        self._queued_callback = None

    def _flush_buffer_callback(self, _cb_args: dict | None = None) -> None:
        """Flushes the buffered release callback once the buffer window expires.

        Called by the ``run_in`` timer when no GESTURE arrived within
        ``RELEASE_BUFFER_DELAY``.
        """
        if self._queued_callback is None:
            return
        comp_id, event = self._queued_callback
        self._queued_callback = None
        self._buffer_timer = None
        self._dispatch_release(comp_id, event)

    def _flush_pending_drag_callback(self) -> None:
        """Dispatch a deferred slider-release callback.

        Fires on TOUCH_END or on the ``DRAG_FLUSH_DELAY`` fallback timer,
        whichever comes first (TOUCH_END is produced by a 500 ms touch poll
        and can arrive ~1 s late or not at all for short drags).  Re-arms
        gesture suppression long enough to outlast the late swipe gesture the
        touch poller publishes after the drag.

        For drag controls, the callback stored via ``bind_slider()`` fires
        ``_callback_slider_release()`` which reads the actual slider value
        from the display via a read request.
        """
        self._cancel_drag_flush_timer()
        if self._pending_drag_callback is None:
            return
        comp_id, event = self._pending_drag_callback
        self._pending_drag_callback = None
        self.suppress_gesture(self.DRAG_SUPPRESS_DURATION)
        self._dispatch_release(comp_id, event)

    def _cancel_drag_flush_timer(self) -> None:
        """Cancels the drag-flush fallback timer, if active."""
        if self._drag_flush_timer is not None:
            self.app.cancel_timer(self._drag_flush_timer)
            self._drag_flush_timer = None

    def _drag_flush_timeout(self, _cb_args: dict | None = None) -> None:
        """Fallback flush when no TOUCH_END arrived after a slider release."""
        self._drag_flush_timer = None
        self._flush_pending_drag_callback()

    def _check_long_press_back(self, event: HAUIEvent) -> None:
        """Go back after a long press, when the panel enables ``long_press_back``.

        ``event`` is TOUCH_END with "x1,y1,x2,y2": the touch's start and end.
        """
        started, self._touch_started_at = self._touch_started_at, None
        if started is None or self.panel is None or not self.panel.get("long_press_back", False):
            return
        if time.monotonic() - started < self.LONG_PRESS_SECONDS:
            return
        try:
            x1, y1, x2, y2 = (int(v) for v in event.as_str().split(","))
        except ValueError:
            self.log(f"Long press: unexpected touch_end value {event.as_str()!r}", level="WARNING")
            return
        if abs(x2 - x1) > self.LONG_PRESS_SLOP or abs(y2 - y1) > self.LONG_PRESS_SLOP:
            return
        self.log("Long press: going back")
        self.app.controller["navigation"].go_back()


def _component_name(component: Component | str) -> str:
    """The Nextion name of ``component``, given as a Component or a name."""
    return component.name if isinstance(component, Component) else component

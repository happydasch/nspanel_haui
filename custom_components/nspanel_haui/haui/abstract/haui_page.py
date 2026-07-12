"""Represents a page on the Nextion display."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPEvent, ESPRequest, ESPResponse, NotifEvent, SysPanelKey
from ..mapping.page import PAGE_MAPPING
from .mixins.button_state_mixin import ButtonStateMixin
from .mixins.component_mixin import ComponentMixin
from .mixins.function_btn_mixin import FunctionButtonMixin


@dataclass
class _PendingReadRequest:
    """A value/text read request awaiting its ``read_response`` event.

    Only one read can be in-flight at a time because the ESP32 has a single
    ``req_val_component``/``req_txt_component`` global.  Expires so a lost
    response doesn't wedge future reads.
    """

    component_name: str
    expiry: float


class HAUIPage(FunctionButtonMixin, ButtonStateMixin, ComponentMixin, HAUIBase):
    """Represents a page on the nextion display.

    Every page on the display needs a page defined here to
    be able to interact with the components.

    - Process events on page
    - Render panel on page
    - Main logic for panels
    """

    COMPONENTS: ClassVar[ComponentRegistry] = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
    )

    # Pages that use pre-rendered picture backgrounds (clock, clocktwo, weather)
    # should set this to ``True`` so the base class skips the ``fill`` background
    # command (picture-background pages handle their own background).
    PICTURE_BACKGROUND: ClassVar[bool] = False

    # Pages with non-standard color palettes (about, clock, clocktwo, weather)
    # should set this to ``False`` so user-defined color overrides are bypassed
    # and the page's built-in palette is used instead.
    USE_SYSTEM_COLORS: ClassVar[bool] = True

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

    # How long a read request stays "pending" before a lost read_response no longer
    # counts as "in flight" (see request_component_value).  A read_response that
    # arrives after the timeout is dropped so a stale response can't overwrite
    # a newer read.  Set to 6 seconds to accommodate Nextion serial read latency
    # (~3-4 s for a full round-trip: ESPHome service → Nextion proxy read →
    # sensor update → HA event).
    READ_PENDING_TIMEOUT: ClassVar[float] = 6.0

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        super().__init__(app, config)
        self.page_id = int(self.get("page_id"))
        self.page_id_recv: int | None = None  # set when a page event is received
        # current panel
        self.panel: HAUIPanel | None = None
        # function items, components
        self._fnc_items: dict = {}
        # physical buttons, components
        self._btn_state_left: Component | None = None
        self._btn_state_right: Component | None = None
        # component callbacks: list for press events (button_state != 0)
        self._callbacks: list[tuple[Component, Callable]] = []
        # release callback map: comp_id -> (callback, is_drag)
        # O(1) lookup keyed by component.id for release events (button_state == 0).
        self._callback_map: dict[int, tuple[Component, Callable, bool]] = {}
        # function button inverse lookup: comp_id -> fnc_id
        self._fnc_id_by_component: dict[int, str] = {}
        # item handles
        self._handles: list[str] = []
        # listener metadata for debugging
        self._listener_meta: dict[str, dict] = {}
        # buffered release callback for swipe-disambiguation
        self._queued_callback: tuple[int, int, HAUIEvent] | None = None
        self._buffer_timer: str | None = None
        # drag controls (sliders): the swipe gesture the drag motion produces
        # is suppressed (so dragging updates the value instead of navigating),
        # and the value read is deferred to TOUCH_END because the Nextion only
        # finalizes the slider's ``.val`` once the touch fully ends — reading
        # it on the component-release event returns a stale 0.
        self._drag_components: set[int] = set()
        self._suppress_gesture: bool = False
        self._suppress_gesture_timer: str | None = None
        self._pending_drag_callback: tuple[int, int, HAUIEvent] | None = None
        self._drag_flush_timer: str | None = None
        # read-request plumbing (REQ_VAL / REQ_TXT for slider/value reads).
        # Tracks a single pending read request: only one can be in-flight
        # at a time because the ESP32 has a single ``req_val_component`` /
        # ``req_txt_component`` global pair.  Expires so a lost read_response
        # doesn't block future reads.
        self._pending_read_request: _PendingReadRequest | None = None
        # component callbacks for read_response dispatch.
        self._read_callbacks: dict[str, tuple[Component, Callable[[Any], None]]] = {}
        # Guard: True only while a slider handler is invoked from the
        # read_response response path (_process_read_response).  Handlers
        # check this flag to reject button_state values (0 or 1) that
        # reach them via a direct code path (e.g. an old add_component_callback
        # that leaks through the drag-component early return).
        self._in_read_callback: bool = False
        # subclass init hook
        self.prepare()

    def prepare(self) -> None:
        """Initialize page instance attributes.

        Override this instead of ``__init__`` to set default attribute
        values.  Called automatically after the base class constructor
        runs.  No need to call ``super().prepare()`` — the base
        implementation is a no-op.
        """

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
        """
        if isinstance(component, dict):
            for comp, cb in component.items():
                self._callback_map[comp.id] = (comp, cb, drag)
                if drag:
                    self.mark_drag_component(comp)
        else:
            if callback is None:
                return
            self._callback_map[component.id] = (component, callback, drag)
            if drag:
                self.mark_drag_component(component)

    # slider / value-request plumbing

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

    def add_read_callback(self, component: Component, handler: Callable[[Any], None]) -> None:
        """Route ``read_response`` events for ``component`` to ``handler``.

        Use this directly when the read request is sent from elsewhere
        (e.g. a function-component callback); use ``bind_slider()`` when the
        component is a plain slider registered via ``on_release``.

        Args:
            component: The component whose read responses to route.
            handler: Called with the read value.  ``value`` is an ``int`` for
                number reads and a ``str`` for text reads.
                Signature: ``handler(value)``.
        """
        self._read_callbacks[component.name] = (component, handler)

    def add_read_callback_by_name(self, name: str, handler: Callable[[Any], None]) -> None:
        """Route ``read_response`` events for a named component to ``handler``.

        Convenience wrapper around :meth:`add_read_callback` for wiring
        read responses without a :class:`Component` object.  Useful for
        reading display-side variables that don't have a Component
        declaration in the page's ``COMPONENTS`` registry.

        Args:
            name: The Nextion component or variable name whose read
                responses to route (e.g. ``"tTitle"``, ``"va0"``).
            handler: Called with the read value.  ``value`` is an ``int`` for
                number reads and a ``str`` for text reads.
                Signature: ``handler(value)``.
        """
        self._read_callbacks[name] = (Component(0, name), handler)

    def _extract_component_name(self, component: Component | str) -> str:
        """Return the string name from a Component or raw string."""
        if isinstance(component, Component):
            return component.name
        return component

    def _request_component_read(
        self,
        component: Component | str,
        request_type: ESPRequest,
        log_label: str,
        source_type: str = "component",
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
            source_type: ``"component"`` (default) — sends a plain string name.
                Set to ``"global"`` when reading a global Nextion variable that
                needs a dict ``{name, source_type}`` service value.
        """
        name = self._extract_component_name(component)
        now = time.monotonic()
        if self._pending_read_request is not None and now < self._pending_read_request.expiry:
            self.log(f"{log_label} for {name}: skipped (request pending)")
            return
        self._pending_read_request = _PendingReadRequest(
            component_name=name,
            expiry=now + self.READ_PENDING_TIMEOUT,
        )
        self.log(f"{log_label} for {name}: sending request")
        if source_type != "component":
            value: str | dict[str, str] = {"name": name, "source_type": source_type}
        else:
            value = name
        self.send_esphome(request_type, value, force=True)

    def request_component_value(self, component: Component) -> None:
        """Request a component's numeric value from the display (REQ_VAL).

        Uses the shared single-slot in-flight guard; see
        ``_request_component_read`` for details.

        Args:
            component: The component to read.
        """
        self._request_component_read(component, ESPRequest.REQ_VAL, "value read request")

    def request_component_value_by_name(self, name: str) -> None:
        """Request a numeric value from the display by component name.

        Convenience wrapper around :meth:`request_component_value` for
        reading display-side values without a :class:`Component` object.

        Args:
            name: The Nextion component or variable name to read
                (e.g. ``"hBrightness"``).
        """
        self._request_component_read(name, ESPRequest.REQ_VAL, "value read request")

    def request_component_text(self, component: Component) -> None:
        """Request a component's text value from the display (REQ_TXT).

        Uses the shared single-slot in-flight guard; see
        ``_request_component_read`` for details.

        Args:
            component: The component or variable name to read.
        """
        self._request_component_read(component, ESPRequest.REQ_TXT, "text read request")

    def request_component_text_by_name(self, name: str) -> None:
        """Request a text value from the display by component name.

        Convenience wrapper around :meth:`request_component_text` for
        reading display-side text without a :class:`Component` object.

        Args:
            name: The Nextion component or variable name to read
                (e.g. ``"tTitle"``).
        """
        self._request_component_read(name, ESPRequest.REQ_TXT, "text read request")

    def _callback_slider_release(self, event: HAUIEvent, component: Component) -> None:
        """Release handler installed by ``bind_slider()`` — reads the value."""
        self.request_component_value(component)

    def _process_read_response(self, event: HAUIEvent) -> None:
        """Dispatch a ``read_response`` event to the registered callback.

        Drops the response if ``_pending_read_request`` is ``None`` (cleared
        by a newer touch interaction) or expired (response arrived too late).
        """
        data = event.as_json()
        name = data.get("name", "")
        read_type = data.get("type", "number")
        entry = self._read_callbacks.get(name)
        if entry is None:
            return
        if self._pending_read_request is None:
            self.log(
                f"read_response for {name}: stale response dropped "
                f"(no pending request — TOUCH_START cleared it)"
            )
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
            except (TypeError, ValueError):
                self.log(f"Invalid read_response value for {name}: {data.get('value')!r}")
                return
        _comp, handler = entry
        self.log(f"read_response for {name}: type={read_type} value={value!r} — dispatching")
        self._in_read_callback = True
        try:
            handler(value)
        finally:
            self._in_read_callback = False

    # part

    def start_part(self) -> None:
        """Starts the part.

        This is called when the part is started.
        """
        # notify about page start
        self.start_page()

    def stop_part(self) -> None:
        """Stops of part.

        This is called when the part is stopped.
        """
        self._cancel_buffer_timer()
        self._queued_callback = None
        self._cancel_suppress_gesture_timer()
        self._suppress_gesture = False
        self._cancel_drag_flush_timer()
        self._pending_drag_callback = None
        self._read_callbacks.clear()
        self._pending_read_request = None
        self._in_read_callback = False
        self.set_panel(None)
        # notify about page stop
        self.stop_page()
        # clean up item handles
        for handle in self._handles.copy():
            self.remove_item_listener(handle)

    # page

    def start_page(self) -> None:
        """Starts the page.

        Put callback registration in here and code that should be run
        only once on start.

        When changing components, prefer using start_panel.
        """

    def stop_page(self) -> None:
        """Stops the page.

        Put callback deregistration in here and other code that should
        be run when stopping a part.
        """

    # panel functionality

    def refresh_panel(self) -> None:
        """Refreshes the current panel.

        This gives the possibility to update the panel.
        """
        if self.panel is None:
            return
        self.debug_log(
            f"Refreshing panel {self.panel.id}",
            min_level=2,
        )
        with self.rec_cmd:
            self.render_panel(self.panel)

    def set_panel(self, panel: HAUIPanel | None) -> None:
        """Sets a panel for the page.

        This is used to set a panel for current page.
        The panel is set to the page and the panel is then being rendered.

        Args:
            panel (HAUIPanel): The panel to set.
        """
        # prepare panel
        if self.panel is not None:
            self.stop_panel(self.panel)
        self.panel = panel
        if panel is None:
            self.log(f"Page {PAGE_MAPPING.get(self.page_id)} | closed")
            return
        panel_key = panel.get("key", "")
        panel_type = panel.get_type()
        self.log(f"Page {PAGE_MAPPING.get(self.page_id)} | Panel: {panel_key} ({panel_type})")

        # Batch ALL commands from start_panel, config_panel, and render_panel
        # into a single send_commands call so the ESP32 receives them as one
        # ESPHome service call.  Multiple rapid-fire service calls can overflow
        # the Nextion's serial buffer before the display finishes processing.
        # rec_cmd is re-entrant, so inner rec_cmd blocks in config_panel and
        # render_panel are absorbed into this outer batch.
        rendered = False
        self._fnc_items = {}
        with self.rec_cmd:
            self.start_panel(panel)

            # 1. call config for panel
            self.config_panel(panel)
            # 2. call before render for panel
            if self.before_render_panel(panel):
                self.debug_log(
                    f"Rendering panel {panel.id}",
                    min_level=2,
                )
                # Render function components (init vis/color/text) and the
                # panel's display content in one batch so the dedup logic
                # collapses redundant writes — e.g. ``vis x,0`` from an
                # ``update_function_component`` followed by ``vis x,1``
                # from ``render_panel`` becomes a single ``vis x,1``.
                self._render_function_components()
                self.render_panel(panel)
                rendered = True
            # 3. full page refresh LAST: redraws static TFT components erased
            # by the leading cls in config_panel, after all component writes.
            # Sending ref 0 right after cls keeps the display busy with a full
            # redraw while the rest of the batch streams in, which fills the
            # Nextion RX buffer on large batches (0x24 overflow -> re-render
            # loop).
            if not self.PICTURE_BACKGROUND:
                self.send_cmd("ref 0")
        # 4. call after render for panel
        self.after_render_panel(panel, rendered)

    def _render_function_components(self) -> None:
        """Send the current state of all registered function components.

        All components are rendered (including hidden ones) so that same-page
        panel transitions correctly hide components that were visible in the
        previous panel. Batch dedup collapses hide-then-show sequences to show.
        """
        for fnc_id in self._fnc_items:
            self.update_function_component(fnc_id)

    def config_panel(self, panel: HAUIPanel) -> None:
        """Configures the currently set panel.

        Args:
            panel (HAUIPanel): Current panel
        """
        with self.rec_cmd:
            # Apply background color for solid-color pages.
            # Picture-background pages (clock, weather, clocktwo) handle their
            # own background via pre-compiled picture assets in the TFT.
            if not self.PICTURE_BACKGROUND:
                # cls erases static TFT components; the matching "ref 0" that
                # redraws them is sent at the END of the set_panel batch so the
                # full-page refresh never runs while commands are streaming in.
                self.send_cmd(f"cls {self.get_color('background')}")
                # apply header colors to the header background (if the page has one)
                try:
                    header_comp = self.COMPONENTS.header
                except AttributeError:
                    pass
                else:
                    self.set_component_back_color(header_comp, self.get_color("header_background"))

                # apply header colors to the title component (if the page has one)
                try:
                    title_comp = self.COMPONENTS.title
                except AttributeError:
                    pass
                else:
                    self.set_component_text_color(title_comp, self.get_color("header_text"))
                    self.set_component_back_color(title_comp, self.get_color("header_background"))

            # physical button state
            if self._btn_state_left is not None:
                self.add_component_callback(
                    self._btn_state_left, self.callback_button_state_buttons
                )
                self.set_component_value(
                    self._btn_state_left, self.app.device.get_left_button_state()
                )
            if self._btn_state_right is not None:
                self.add_component_callback(
                    self._btn_state_right, self.callback_button_state_buttons
                )
                self.set_component_value(
                    self._btn_state_right, self.app.device.get_right_button_state()
                )

            # special case, single nav panel
            # swap secondary buttons with primary buttons, since nav is not used
            nav_panels = self.app.device_config.get_panels(True)
            if len(nav_panels) <= 1:
                self._swap_slots_if_single_nav(self.FNC_BTN_L_PRI, self.FNC_BTN_L_SEC)
                self._swap_slots_if_single_nav(self.FNC_BTN_R_PRI, self.FNC_BTN_R_SEC)

            # register function items (rendering deferred to render batch)
            self._fnc_id_by_component.clear()
            for fnc_id, fnc_item in self._fnc_items.items():
                self.add_component_callback(
                    fnc_item["fnc_component"], self.callback_function_components
                )
                self._fnc_id_by_component[fnc_item["fnc_component"].id] = fnc_id

    def create_panel(self, panel: HAUIPanel) -> None:
        """Called when a new panel is created.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """

    def start_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is started.

        Sets ``_use_system_colors`` from the page's ``USE_SYSTEM_COLORS``
        ClassVar so ``get_color()`` knows whether to respect user overrides.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """
        self._use_system_colors = type(self).USE_SYSTEM_COLORS

    def stop_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is stopped.

        Clears all item state listeners, then calls ``_stop_panel()``
        so subclasses can do their own cleanup without calling super.

        Args:
            panel (HAUIPanel): Current panel
        """
        for handle in list(self._handles):
            self.app.cancel_listen_state(handle)
        self._handles.clear()
        self._listener_meta.clear()
        self._callback_map.clear()
        self._callbacks.clear()
        self._drag_components.clear()
        self._stop_panel(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        """Subclass hook for panel cleanup.

        Override this instead of ``stop_panel``.  No need to call super.
        """

    def _save_auto_state(self) -> dict:
        """Save and disable auto-dimming/page/sleep for popup overlays.

        Returns the saved states dict, which must be passed to the passed to
        ``_restore_auto_state()`` on cleanup.
        """
        name = self.app.device.get_name()
        states: dict = {}
        for key, suffix in (
            ("auto_dimming", "use_auto_dimming"),
            ("auto_page", "use_auto_page"),
            ("auto_sleeping", "use_auto_sleeping"),
        ):
            item = self.app.get_item(f"switch.{name}_{suffix}")
            states[key] = item.get_state()
            item.turn_off()
        return states

    def _restore_auto_state(self, states: dict) -> None:
        """Restore previously saved auto-dimming/page/sleep states.

        Args:
            states: The dict returned by ``_save_auto_state()``.
        """
        name = self.app.device.get_name()
        for key, suffix in (
            ("auto_dimming", "use_auto_dimming"),
            ("auto_page", "use_auto_page"),
            ("auto_sleeping", "use_auto_sleeping"),
        ):
            if states.get(key):
                item = self.app.get_item(f"switch.{name}_{suffix}")
                item.turn_on()

    # gesture-buffer helpers

    def _cancel_buffer_timer(self) -> None:
        """Cancels the gesture-disambiguation buffer timer, if active."""
        if self._buffer_timer is not None:
            self.app.cancel_timer(self._buffer_timer)
            self._buffer_timer = None

    def _flush_buffer_callback(self, _cb_args: dict | None = None) -> None:
        """Flushes the buffered release callback once the buffer window expires.

        Called by ``run_in`` timer callback when no GESTURE arrived before
        the 100 ms disambiguation window.  Dispatches the callback to
        the registered component handler.
        """
        if self._queued_callback is None:
            return
        comp_id, button_state, event = self._queued_callback
        self._queued_callback = None
        self._buffer_timer = None
        entry = self._callback_map.get(comp_id)
        if entry is not None:
            _comp, callback, _is_drag = entry
            callback(event, _comp)
        else:
            for component, callback in self._callbacks:
                if comp_id == component.id:
                    callback(event, component, button_state)
                    break

    # gesture-suppression helpers (slider drag vs. swipe navigation)

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

    def _cancel_suppress_gesture_timer(self) -> None:
        """Cancels the gesture-suppression timer, if active."""
        if self._suppress_gesture_timer is not None:
            self.app.cancel_timer(self._suppress_gesture_timer)
            self._suppress_gesture_timer = None

    def _clear_suppress_gesture(self, _cb_args: dict | None = None) -> None:
        """Clears the gesture-suppression flag when the window expires."""
        self._suppress_gesture = False
        self._suppress_gesture_timer = None

    def is_gesture_suppressed(self) -> bool:
        """Whether swipe gestures are currently suppressed (slider drag)."""
        return self._suppress_gesture

    def _flush_pending_drag_callback(self) -> None:
        """Dispatch a deferred slider-release callback.

        Fires on TOUCH_END or on the ``DRAG_FLUSH_DELAY`` fallback timer,
        whichever comes first (TOUCH_END is produced by a 500 ms touch poll
        and can arrive ~1 s late or not at all for short drags).  Re-arms
        gesture suppression long enough to outlast the late swipe gesture the
        touch poller publishes after the drag.

        For drag controls, the callback stored via ``bind_slider()`` fires
        ``_callback_slider_release()`` which reads the actual slider value
        from the display via a read request.  For legacy
        ``add_component_callback`` entries the same read path is used — the
        ``button_state`` from the COMPONENT event is always 0 (release) and
        never the slider value.
        """
        self._cancel_drag_flush_timer()
        if self._pending_drag_callback is None:
            return
        comp_id, button_state, event = self._pending_drag_callback
        self._pending_drag_callback = None
        self.suppress_gesture(self.DRAG_SUPPRESS_DURATION)
        entry = self._callback_map.get(comp_id)
        if entry is not None:
            _comp, callback, _is_drag = entry
            callback(event, _comp)
        else:
            for component, _ in self._callbacks:
                if comp_id == component.id:
                    self.request_component_value(component)
                    break

    def _cancel_drag_flush_timer(self) -> None:
        """Cancels the drag-flush fallback timer, if active."""
        if self._drag_flush_timer is not None:
            self.app.cancel_timer(self._drag_flush_timer)
            self._drag_flush_timer = None

    def _drag_flush_timeout(self, _cb_args: dict | None = None) -> None:
        """Fallback flush when no TOUCH_END arrived after a slider release."""
        self._drag_flush_timer = None
        self._flush_pending_drag_callback()

    def before_render_panel(self, panel: HAUIPanel) -> bool:
        """Called before the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel

        Returns:
            bool, if False then panel will not be rendered
        """
        return True

    def render_panel(self, panel: HAUIPanel) -> None:
        """Called when the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """

    def after_render_panel(self, panel: HAUIPanel, rendered: bool) -> None:
        """Called after the panel is rendered.

        This gives the possibility to execute some checks after showing panel.

        Args:
            panel (HAUIPanel): Current panel
            rendered (bool): Was the panel rendered
        """

    # item

    def _build_items_from_panel(self, panel: HAUIPanel, *keys: str) -> list[HAUIItem]:
        """Build HAUIItem list from a panel's item config keys.

        Reads each config key in order.  For each key, if the value is a
        list every entry is added as a separate item; if it's a single
        value (dict or string) it is wrapped as a single item.

        Args:
            panel: The panel whose item config to read.
            *keys: Config key(s) to read item entries from.

        Returns:
            List of HAUIItem objects.
        """
        items: list[HAUIItem] = []
        for key in keys:
            val = panel.get(key, None)
            if isinstance(val, list):
                for entry in val:
                    items.append(HAUIItem(self.app, entry))
            elif val is not None:
                items.append(HAUIItem(self.app, val))
        return items

    def execute_item(self, item: HAUIItem) -> None:
        """Executes the given item.

        Args:
            item (HAUIItem): item
        """
        item_type = item.get_item_type()
        item_state = item.get_item_state()
        navigation = self.app.controller["navigation"]
        available = item_state != "unavailable"

        # item is not available
        if not available:
            msg = self.translate("The item {} is currently unavailable.")
            msg = msg.format(item.get_name())
            msg += "\r\n\r\n"
            msg += self.translate("Entity:")
            msg += "\r\n"
            msg += item.get_item_id()
            # open notification
            navigation.open_panel(
                SysPanelKey.POPUP_NOTIFY,
                title=self.translate("Entity unavailable"),
                btn_right=self.translate("Close"),
                icon=item.get_icon(),
                notification=msg,
            )

        # execute popup
        elif item_type in ["light", "media_player", "vacuum", "cover", "climate"]:
            popup_name = item.get("popup_key", None)
            if popup_name is None:
                popup_name = f"popup_{item_type}"
            kwargs = item.get_config()
            kwargs["item_id"] = item.get_item_id()
            # open popup
            navigation.open_panel(popup_name, **kwargs)
        # execute default
        else:
            self.log(f"Executing item {item.get_name()} - {item_type}")
            item.execute()

    def turn_on_item(self, item: HAUIItem) -> None:
        """Turns on the given item.

        Args:
            item (HAUIItem): item
        """
        self.log(f"Switching item on: {item.get_name()} ({item.get_item_id()})")
        item_type = item.get_item_type()
        if item_type == "media_player":
            item.call_item_service("media_play")
        else:
            item.call_item_service("turn_on")

    def turn_off_item(self, item: HAUIItem) -> None:
        """Turns off the given item.

        Args:
            item (HAUIItem): item
        """
        self.log(f"Switching item off: {item.get_name()} ({item.get_item_id()})")
        item_type = item.get_item_type()
        if item_type == "media_player":
            item.call_item_service("media_stop")
        else:
            item.call_item_service("turn_off")

    def add_item_listener(
        self, item_id: str, callback: Callable, attribute: str | None = None
    ) -> str:
        """Adds a item state listener.

        Args:
            item_id (str): Item ID
            callback (function): Callback
            attribute (str): Attribute

        Returns:
            handle (str): Handle
        """
        handle = self.app.listen_state(callback, item_id, attribute=attribute)
        self.debug_log(
            f"Adding listener for {item_id},"
            f" attribute={attribute},"
            f" callback={callback.__name__},"
            f" handle={handle}",
            min_level=2,
        )
        self._handles.append(handle)
        self._listener_meta[handle] = {
            "item_id": item_id,
            "attribute": attribute,
            "callback_name": getattr(callback, "__name__", str(callback)),
        }
        return handle

    def remove_item_listener(self, handle: str) -> None:
        """Removes a item state listener.

        Args:
            handle (str): Handle
        """
        if handle in self._handles:
            self.app.cancel_listen_state(handle)
            self.debug_log(
                f"Removing listener,"
                f" handle={handle},"
                f" item={self._listener_meta.get(handle, {}).get('item_id', '?')}",
                min_level=2,
            )
            if handle in self._handles:
                self._handles.remove(handle)
            self._listener_meta.pop(handle, None)

    # processing

    def process_event(self, event: HAUIEvent) -> None:
        """Processes app events.

        Args:
            event (HAUIEvent): Event
        """
        self.debug_log(
            f"Page process_event: {event.name} value={str(event.value)[:100]}",
            min_level=2,
        )
        # component event
        if event.name == ESPEvent.COMPONENT:
            self.process_component_event(event)
        # gesture — cancel any buffered component callback (it was a swipe)
        elif event.name == ESPEvent.GESTURE:
            self._cancel_buffer_timer()
            self._queued_callback = None
        # new touch interaction — invalidate stale (expired) read request
        # entries from previous interactions.  Active entries (just sent)
        # are preserved so a fresh read_response that arrives after TOUCH_START
        # (from the touch poll cycle) is not wrongly dropped.
        elif event.name == ESPEvent.TOUCH_START:
            now = time.monotonic()
            if self._pending_read_request is not None and now >= self._pending_read_request.expiry:
                self._pending_read_request = None
        # touch end — flush any deferred slider-release callback
        elif event.name == ESPEvent.TOUCH_END:
            self._flush_pending_drag_callback()
        # read response — route to registered slider / text handler
        elif event.name == ESPResponse.READ_RESPONSE:
            self._process_read_response(event)
        # notification indicator — the badge lives on the left-secondary button
        # when its fnc_name is NAV_NOTIF (set by _auto_assign_fncs).
        if self.FNC_BTN_L_SEC in self._fnc_items:
            left_sec = self._fnc_items[self.FNC_BTN_L_SEC]
            if left_sec["fnc_name"] == self.FNC_TYPE_NAV_NOTIF and event.name in [
                NotifEvent.NOTIF_ADD,
                NotifEvent.NOTIF_REMOVE,
                NotifEvent.NOTIF_CLEAR,
            ]:
                if event.name == NotifEvent.NOTIF_ADD:
                    color = self.get_color("header_accent")
                else:
                    color = self.get_color("component_text")
                notification = self.app.controller["notification"]
                visible = False
                if notification.has_notifications():
                    visible = True
                self.update_function_component(self.FNC_BTN_L_SEC, color=color, visible=visible)

    def set_slider_color(self, slider: Component, show_toggle: bool = True) -> None:
        """Set the slider handle color to ``component_active_dark``.

        Sliders on NSPanel displays use ``.pco`` for the handle/foreground
        color.  Call this once per render cycle after showing the slider
        so the handle appears in the configured dark-accent shade.

        Args:
            slider: The slider ``Component`` to colour.
            show_toggle: Whether to show the toggle switch.
        """
        if show_toggle:
            self.set_component_text_color(slider, self.get_color("component_active_dark"))
        else:
            self.set_component_text_color(slider, self.get_color("component_pressed"))

    def process_component_event(self, event: HAUIEvent) -> None:
        """Processes component events from component callback.

        Args:
            event (str): Event
        """
        component_info = [int(x) for x in event.as_str().split(",")]
        if len(component_info) != 3:
            return
        if component_info[0] != self.page_id:
            return

        comp_id = component_info[1]
        button_state = component_info[2]

        # Press events (touch_event != 0): dispatch immediately via legacy
        # list, then STOP.  A press must never fall through to the release
        # handling below — that would queue the release callback while the
        # finger is still down and double-fire it (e.g. a held power button
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
            self._pending_drag_callback = (comp_id, button_state, event)
            self._cancel_drag_flush_timer()
            self._drag_flush_timer = self.app.run_in(
                self._drag_flush_timeout, self.DRAG_FLUSH_DELAY
            )
            return

        # Release events (touch_event == 0): use O(1) lookup from _callback_map.
        entry = self._callback_map.get(comp_id)
        if entry is not None:
            _comp, callback, _is_drag = entry
            self._cancel_buffer_timer()
            self._queued_callback = (comp_id, button_state, event)
            self._buffer_timer = self.app.run_in(self._flush_buffer_callback, 0.1)
        else:
            # Fallback to legacy _callbacks list for components registered
            # via add_component_callback (e.g. function buttons in config_panel).
            for component, _cb in self._callbacks:
                if comp_id == component.id:
                    self._cancel_buffer_timer()
                    self._queued_callback = (comp_id, button_state, event)
                    self._buffer_timer = self.app.run_in(self._flush_buffer_callback, 0.1)
                    break

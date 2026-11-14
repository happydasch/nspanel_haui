"""Tests for the HAUIPage read-request API (REQ_VAL / REQ_TXT).

Covers reads by component name, pending-request guards, expiry,
and the ``_process_read_response`` dispatch and stale-response logic.
"""

import time
import types

import pytest

from custom_components.nspanel_haui.haui.abstract.component import Component
from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.abstract.haui_page import HAUIPage
from custom_components.nspanel_haui.haui.abstract.mixins.touch_input_mixin import (
    _PendingReadRequest,
)
from custom_components.nspanel_haui.haui.mapping.color import Theme
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent, ESPRequest, ESPResponse

# --- helpers ---------------------------------------------------------------


class FakePageApp:
    """Minimal app for HAUIPage tests — tracks ESPHome sends, timers, and logs."""

    def __init__(self):
        self.timers = []
        self.cancelled = []
        self.controller = {}
        self.theme = Theme()
        self.device = type("MockDevice", (), {"get": lambda s, k, d=0: d})()
        self.sent_esphome: list[tuple] = []
        self.log_calls: list[tuple] = []

    def log(self, msg, **kwargs):
        self.log_calls.append((msg, kwargs))

    def run_in(self, cb, delay, **kwargs):
        self.timers.append((cb, delay))
        return f"handle-{len(self.timers)}"

    def cancel_timer(self, handle):
        self.cancelled.append(handle)


def _bare_page(page_id=1):
    """A real HAUIPage on a fake app that records what it sends to the panel."""
    page = HAUIPage(FakePageApp(), {"page_id": page_id})
    page.send_esphome = lambda *a, **kw: page.app.sent_esphome.append((a, kw))
    return page


# --- reads by component name ------------------------------------------------


@pytest.mark.parametrize(
    ("method", "request_type"),
    [
        ("request_component_value", ESPRequest.REQ_VAL),
        ("request_component_text", ESPRequest.REQ_TXT),
    ],
)
@pytest.mark.parametrize("component", ["hSlider", Component(7, "hSlider")])
def test_a_read_request_names_the_component(method, request_type, component):
    """A read is requested by widget name, given as a name or as a ``Component``."""
    page = _bare_page()

    getattr(page, method)(component)

    ((args, _kwargs),) = page.app.sent_esphome
    assert args[:2] == (request_type, "hSlider")


def test_add_read_callback_and_request_text_by_name_together():
    """End-to-end: register by name, request by name, simulate response."""
    page = _bare_page()
    calls = []

    page.add_read_callback("va0", lambda v: calls.append(v))
    page.request_component_text("va0")

    assert len(page.app.sent_esphome) == 1
    args, _ = page.app.sent_esphome[0]
    assert args[0] == ESPRequest.REQ_TXT
    assert args[1] == "va0"

    # Simulate the read_response
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"va0","type":"text","value":"status text"}',
        )
    )
    assert calls == ["status text"]


def test_add_item_listener_logs_item_change_at_debug_and_forwards_args():
    """The listener wrapper logs entity changes at DEBUG and preserves the
    ``(entity_id, attribute, old, new, kwargs)`` callback contract."""
    page = _bare_page()
    page._handles = []
    page._listener_meta = {}
    registered = {}

    def listen_state(cb, entity_id, attribute=None, **kwargs):
        registered[entity_id] = (cb, attribute)
        return f"handle-{entity_id}"

    page.app.listen_state = listen_state

    received = []
    page.add_item_listener("sensor.temp", lambda *a: received.append(a), attribute="state")

    # Registration itself logs at DEBUG with the original callback name.
    add_logs = [
        kw for m, kw in page.app.log_calls if m.startswith("Adding listener for sensor.temp")
    ]
    assert add_logs and add_logs[0]["level"] == "DEBUG"

    cb, attr = registered["sensor.temp"]
    assert attr == "state"
    cb("sensor.temp", "state", "21", "22", {})

    assert received == [("sensor.temp", "state", "21", "22", {})]
    change_logs = [m for m, _kw in page.app.log_calls if m.startswith("Item change: sensor.temp")]
    assert change_logs[-1] == "Item change: sensor.temp state: '21' -> '22'"
    assert page._handles == ["handle-sensor.temp"]
    assert page._listener_meta["handle-sensor.temp"]["callback_name"] == "<lambda>"


# --- pending-request guards ------------------------------------------------


def test_request_component_read_skipped_when_pending_not_expired():
    """A second read is silently skipped while the first is in-flight
    (within READ_PENDING_TIMEOUT)."""
    page = _bare_page()
    page.request_component_value("hBrightness")
    # Second request while first is still pending
    page.request_component_value("hBrightness")

    assert len(page.app.sent_esphome) == 1  # second was skipped
    assert page._pending_read_request is not None


def test_request_component_read_allows_after_pending_expiry():
    """After the pending request expires, a new read proceeds."""
    page = _bare_page()
    # Create an expired pending request
    page._pending_read_request = _PendingReadRequest(
        component_name="hBrightness",
        expiry=time.monotonic() - 1.0,  # already expired
    )
    page.request_component_value("hBrightness")

    assert len(page.app.sent_esphome) == 1
    # New pending request has a fresh expiry
    assert page._pending_read_request is not None
    assert page._pending_read_request.component_name == "hBrightness"
    assert page._pending_read_request.expiry > time.monotonic()


# --- _process_read_response edge cases --------------------------------------


def test_panel_change_drops_the_previous_panels_read():
    """A read requested on one panel never reaches the next panel's handler
    for the same slider, and the next panel can read right away."""
    page = _bare_page()
    page._handles = []
    page._listener_meta = {}
    slider = Component(13, "hBrightness")
    old_values: list = []
    new_values: list = []
    page.bind_slider(slider, old_values.append)
    page.request_component_value(slider)

    page.stop_panel(None)
    page.bind_slider(slider, new_values.append)
    page._process_read_response(
        HAUIEvent(ESPResponse.READ_RESPONSE, '{"name":"hBrightness","type":"number","value":"42"}')
    )

    assert old_values == []
    assert new_values == []
    page.request_component_value(slider)
    assert len(page.app.sent_esphome) == 2


def test_panel_change_drops_the_previous_panels_buffered_tap():
    """A tap still waiting out the tap-or-swipe window never reaches the
    next panel's button with the same id."""
    page = _bare_page()
    page._handles = []
    page._listener_meta = {}
    button = Component(7, "bConfirm")
    old_taps: list = []
    new_taps: list = []
    page.on_release(button, lambda event, component: old_taps.append(component))
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{button.id},0"))

    page.stop_panel(None)
    page.on_release(button, lambda event, component: new_taps.append(component))
    for callback, _delay in page.app.timers:
        callback({})

    assert old_taps == []
    assert new_taps == []


def test_panel_change_drops_the_previous_panels_slider_release():
    """A slider release waiting for its value read never reads the next
    panel's slider with the same id."""
    page = _bare_page()
    page._handles = []
    page._listener_meta = {}
    slider = Component(13, "hBrightness")
    page.bind_slider(slider, lambda value: None)
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{slider.id},0"))

    page.stop_panel(None)
    page.bind_slider(slider, lambda value: None)
    page._drag_flush_timeout()

    assert page.app.sent_esphome == []


def test_process_read_response_drops_when_pending_is_none():
    """When ``_pending_read_request`` is None, the read_response is dropped
    (stale — cleared by a new touch)."""
    page = _bare_page()
    calls = []

    page.add_read_callback("hBrightness", lambda v: calls.append(v))
    # No pending request set
    page._pending_read_request = None

    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"hBrightness","type":"number","value":"42"}',
        )
    )
    assert calls == []


def test_process_read_response_drops_when_expired():
    """When the pending request has expired, the read_response is dropped."""
    page = _bare_page()
    calls = []

    page.add_read_callback("hBrightness", lambda v: calls.append(v))
    page._pending_read_request = _PendingReadRequest(
        component_name="hBrightness",
        expiry=time.monotonic() - 10.0,  # expired
    )
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"hBrightness","type":"number","value":"42"}',
        )
    )
    assert calls == []
    assert page._pending_read_request is None  # cleared after expired drop


def test_process_read_response_clears_pending_on_success():
    """After a successful dispatch, ``_pending_read_request`` is set to None."""
    page = _bare_page()
    calls = []

    page.add_read_callback("hBrightness", lambda v: calls.append(v))
    page._pending_read_request = _PendingReadRequest(
        component_name="hBrightness",
        expiry=time.monotonic() + 10.0,
    )
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"hBrightness","type":"number","value":"42"}',
        )
    )
    assert calls == [42]
    assert page._pending_read_request is None


def test_process_read_response_ignores_unknown_component():
    """A read_response for a component with no registered callback is silently
    ignored."""
    page = _bare_page()
    page._pending_read_request = _PendingReadRequest(
        component_name="unknown",
        expiry=time.monotonic() + 10.0,
    )
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"unknown","type":"number","value":"99"}',
        )
    )
    # No crash, pending request is NOT cleared (handler not found, so
    # _process_read_response returns before clearing)
    assert page._pending_read_request is not None


def test_process_read_response_handles_invalid_number_value():
    """A read_response with an unparseable number value is dropped with a log."""
    page = _bare_page()
    calls = []

    page.add_read_callback("hBrightness", lambda v: calls.append(v))
    page._pending_read_request = _PendingReadRequest(
        component_name="hBrightness",
        expiry=time.monotonic() + 10.0,
    )
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"hBrightness","type":"number","value":"not_a_number"}',
        )
    )
    assert calls == []
    # pending is cleared even for invalid values (the method returns after logging)
    assert page._pending_read_request is None


# --- set_component_text newline encoding -------------------------------------


def test_set_component_text_encodes_newlines():
    """.txt values carry the escaped line-break sequence, never raw CR/LF bytes."""
    page = _bare_page()
    cmds: list[str] = []
    page.send_cmd = cmds.append
    comp = Component(9, "tText")

    # Plain single-line text is sent unchanged.
    page.set_component_text(comp, "plain")
    assert cmds == ['tText.txt="plain"']

    # A logical newline (how fit_text joins page lines) becomes the
    # Nextion line-break escape, never a raw LF inside the command.
    cmds.clear()
    page.set_component_text(comp, "line1" + chr(10) + "line2")
    r = chr(92)
    assert cmds == ['tText.txt="line1' + r + 'rline2"']

    # CRLF (translated popup bodies) collapses to the same single line break.
    cmds.clear()
    page.set_component_text(comp, "line1" + chr(13) + chr(10) + "line2")
    assert cmds == ['tText.txt="line1' + r + 'rline2"']

    # Already-escaped text (callers writing Nextion escape sequences directly)
    # must survive untouched.
    cmds.clear()
    page.set_component_text(comp, "one" + r + "rtwo")
    assert cmds == ['tText.txt="one' + r + 'rtwo"']


def test_set_component_text_escapes_quotes_and_backslashes():
    """A quote or backslash in the text must not end the Nextion literal early."""
    page = _bare_page()
    cmds: list[str] = []
    page.send_cmd = cmds.append
    comp = Component(9, "tText")
    r = chr(92)

    page.set_component_text(comp, 'He said "hi"')
    assert cmds == ['tText.txt="He said ' + r + '"hi' + r + '""']

    # A trailing backslash would otherwise escape the closing quote.
    cmds.clear()
    page.set_component_text(comp, "C:" + r)
    assert cmds == ['tText.txt="C:' + r + r + '"']

    # A backslash-quote in the text stays both characters.
    cmds.clear()
    page.set_component_text(comp, "a" + r + '"b')
    assert cmds == ['tText.txt="a' + r + r + r + '"b"']


def test_popup_item_keeps_the_opening_items_overrides():
    """A popup opened from an item shows that item's name (and other overrides)."""
    from custom_components.nspanel_haui.haui.abstract.haui_page import HAUIPage

    class _Panel:
        def __init__(self, config):
            self.config = config

        def get(self, key, default=None):
            return self.config.get(key, default)

    page = HAUIPage.__new__(HAUIPage)
    page.app = types.SimpleNamespace(theme=Theme(), log=lambda *a, **k: None)
    page.panel = None
    panel = _Panel(
        {"item_id": "light.bed", "item": "light.bed", "name": "Bedside", "icon": "mdi:lamp"}
    )

    item = page._resolve_panel_item(panel)

    assert item.get_item_id() == "light.bed"
    assert (item.get("name"), item.get("icon")) == ("Bedside", "mdi:lamp")


def test_function_button_release_fires_via_registry_path():
    """Function buttons dispatch on release through the callback registry.

    ``config_panel`` registers function items via ``on_release`` (with an
    adapter for the 3-arg callback contract); presses must be inert, and the
    release must fire exactly once through ``_callback_map``.
    """
    page = _bare_page()

    # Mirror the config_panel registration: adapt (event, component) -> 3-arg callback
    comp = Component(7, "bConfirm")
    calls: list[tuple] = []

    def callback_function_components(event, component, button_state):
        calls.append((event, component, button_state))

    page.on_release(
        comp,
        lambda event, component: callback_function_components(event, component, 0),
    )

    # press must be inert for function buttons
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{comp.id},1"))
    assert calls == []

    # release is buffered (gesture disambiguation), then flushed once
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{comp.id},0"))
    assert calls == []
    page._flush_buffer_callback()
    assert len(calls) == 1
    assert calls[0][1] == comp
    assert calls[0][2] == 0


def test_function_button_press_without_registry_entry_is_inert():
    """A press on an unregistered component does not crash or queue a release."""
    page = _bare_page()
    comp = Component(8, "bGhost")

    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{comp.id},1"))
    page.process_component_event(HAUIEvent(ESPEvent.COMPONENT, f"1,{comp.id},0"))

    assert page._queued_callback is None
    assert page._buffer_timer is None

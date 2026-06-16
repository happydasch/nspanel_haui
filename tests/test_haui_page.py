"""Tests for the HAUIPage read-request API (REQ_VAL / REQ_TXT).

Covers the string-based convenience wrappers, pending-request guards, expiry,
and the ``_process_read_response`` dispatch and stale-response logic.
"""

import time

from nspanel_haui.haui.abstract.component import Component
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.abstract.haui_page import HAUIPage, _PendingReadRequest
from nspanel_haui.haui.mapping.const import ESPRequest, ESPResponse

# --- helpers ---------------------------------------------------------------


class FakePageApp:
    """Minimal app for HAUIPage tests — tracks ESPHome sends, timers, and logs."""

    def __init__(self):
        self.timers = []
        self.cancelled = []
        self.controller = {}
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
    """Create a bare HAUIPage with just the attributes the read paths touch."""
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


# --- string-based convenience API -------------------------------------------


def test_request_component_value_by_name_sends_req_val_with_source_type():
    """``request_component_value_by_name`` sends REQ_VAL with the plain
    component name string (backward-compatible default)."""
    page = _bare_page()
    page.request_component_value_by_name("hBrightness")

    assert len(page.app.sent_esphome) == 1
    args, _kwargs = page.app.sent_esphome[0]
    assert args[0] == ESPRequest.REQ_VAL
    # Default source_type="component" → plain string for backward compat
    assert args[1] == "hBrightness"


def test_request_component_text_by_name_sends_req_txt_with_source_type():
    """``request_component_text_by_name`` sends REQ_TXT with the plain
    component name string (backward-compatible default)."""
    page = _bare_page()
    page.request_component_text_by_name("tTitle")

    assert len(page.app.sent_esphome) == 1
    args, _kwargs = page.app.sent_esphome[0]
    assert args[0] == ESPRequest.REQ_TXT
    assert args[1] == "tTitle"


def test_add_read_callback_by_name_dispatches_read_response():
    """``add_read_callback_by_name`` registers a callback keyed by string name
    and ``_process_read_response`` dispatches to it."""
    page = _bare_page()
    calls = []

    def handler(value):
        calls.append(("handler", value))

    page.add_read_callback_by_name("tTitle", handler)
    page._pending_read_request = _PendingReadRequest(
        component_name="tTitle",
        expiry=time.monotonic() + 10.0,
    )
    page._process_read_response(
        HAUIEvent(
            ESPResponse.READ_RESPONSE,
            '{"name":"tTitle","type":"text","value":"Hello World"}',
        )
    )
    assert len(calls) == 1
    assert calls[0] == ("handler", "Hello World")


def test_add_read_callback_by_name_and_request_text_by_name_together():
    """End-to-end: register by name, request by name, simulate response."""
    page = _bare_page()
    calls = []

    page.add_read_callback_by_name("va0", lambda v: calls.append(v))
    page.request_component_text_by_name("va0")

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


# --- pending-request guards ------------------------------------------------


def test_request_component_read_skipped_when_pending_not_expired():
    """A second read is silently skipped while the first is in-flight
    (within READ_PENDING_TIMEOUT)."""
    page = _bare_page()
    page.request_component_value_by_name("hBrightness")
    # Second request while first is still pending
    page.request_component_value_by_name("hBrightness")

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
    page.request_component_value_by_name("hBrightness")

    assert len(page.app.sent_esphome) == 1
    # New pending request has a fresh expiry
    assert page._pending_read_request is not None
    assert page._pending_read_request.component_name == "hBrightness"
    assert page._pending_read_request.expiry > time.monotonic()


# --- _process_read_response edge cases --------------------------------------


def test_process_read_response_drops_when_pending_is_none():
    """When ``_pending_read_request`` is None, the read_response is dropped
    (stale — cleared by a new touch)."""
    page = _bare_page()
    calls = []

    page.add_read_callback_by_name("hBrightness", lambda v: calls.append(v))
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

    page.add_read_callback_by_name("hBrightness", lambda v: calls.append(v))
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

    page.add_read_callback_by_name("hBrightness", lambda v: calls.append(v))
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

    page.add_read_callback_by_name("hBrightness", lambda v: calls.append(v))
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


def test_request_component_value_sends_req_val():
    """``request_component_value`` with a Component sends REQ_VAL with
    the plain component name (backward-compatible default)."""
    page = _bare_page()
    comp = Component(7, "hSlider")
    page.request_component_value(comp)

    assert len(page.app.sent_esphome) == 1
    args, _ = page.app.sent_esphome[0]
    assert args[0] == ESPRequest.REQ_VAL
    assert args[1] == "hSlider"


def test_request_component_text_sends_req_txt():
    """``request_component_text`` with a Component sends REQ_TXT with
    the plain component name (backward-compatible default)."""
    page = _bare_page()
    comp = Component(9, "tLabel")
    page.request_component_text(comp)

    assert len(page.app.sent_esphome) == 1
    args, _ = page.app.sent_esphome[0]
    assert args[0] == ESPRequest.REQ_TXT
    assert args[1] == "tLabel"


def test_extract_component_name_handles_component_and_string():
    """``_extract_component_name`` returns ``.name`` for Component objects
    and the string directly for plain strings."""
    page = _bare_page()
    assert page._extract_component_name(Component(42, "mycomp")) == "mycomp"
    assert page._extract_component_name("plain_string") == "plain_string"

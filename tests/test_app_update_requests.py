"""An update request the editor or the update entity waits for always ends.

The update controller answers a request after its network stage, on the app's
worker. Once the app stops, the worker runs nothing more, so a request still
waiting then would wait forever.
"""

from __future__ import annotations

import asyncio
import threading
import types

import pytest

from custom_components.nspanel_haui.hub.adapter import HAAdapter
from custom_components.nspanel_haui.hub.app import NSPanelHAUI


def _stoppable_app(loop: asyncio.AbstractEventLoop) -> NSPanelHAUI:
    """An app whose update controller takes a request and has not answered it yet."""
    app = NSPanelHAUI.__new__(NSPanelHAUI)
    app._loop = loop
    app._update_requests = set()
    app._tick_timers = {}
    app._tick_subscribers = {}
    app._preview_state_subscribers = set()
    app._preview_output_subscribers = set()
    app._preview_state_lock = threading.Lock()
    app.device = None
    app.controller = {
        "update": types.SimpleNamespace(start_async_list_tft_releases=lambda on_complete: None)
    }

    async def run_inline(fn, *args):
        return fn(*args)

    app.async_run_on_worker = run_inline
    return app


def test_an_update_request_still_waiting_when_the_app_stops_ends_with_an_error(monkeypatch):
    monkeypatch.setattr(HAAdapter, "stop", lambda self: None)
    loop = asyncio.new_event_loop()
    try:
        app = _stoppable_app(loop)

        async def scenario() -> None:
            request = asyncio.ensure_future(app.async_list_tft_releases())
            await asyncio.sleep(0)  # the request now waits for its answer
            app.stop()
            with pytest.raises(RuntimeError, match="stopped"):
                await asyncio.wait_for(request, 1)

        loop.run_until_complete(scenario())
    finally:
        loop.close()

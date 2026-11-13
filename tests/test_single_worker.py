"""App code runs on the app's worker thread, never on a thread of its own.

Debounced page updates used to fire on a ``threading.Timer`` and then on Home
Assistant's executor, and every entity service call started a thread, so page
state was changed from a second thread while the worker drew the next panel.
"""

import threading
from types import SimpleNamespace

from custom_components.nspanel_haui.haui.abstract.haui_base import HAUIBase
from custom_components.nspanel_haui.haui.abstract.haui_entity import HAUIEntity
from custom_components.nspanel_haui.haui.utils.debounce import Debouncer


class _TimerApp:
    """The app's timer API: callbacks run when the test fires them."""

    def __init__(self) -> None:
        self.timers: dict[str, tuple] = {}
        self.cancelled: list[str] = []
        self._count = 0

    def run_in(self, cb, delay, **kwargs):
        self._count += 1
        handle = f"timer{self._count}"
        self.timers[handle] = (cb, delay)
        return handle

    def cancel_timer(self, handle):
        self.cancelled.append(handle)
        self.timers.pop(handle, None)

    def fire_all(self) -> None:
        for handle, (cb, _delay) in list(self.timers.items()):
            del self.timers[handle]
            cb({})


def test_a_debounced_call_runs_once_from_the_apps_timer():
    app = _TimerApp()
    calls = []
    debouncer = Debouncer(app, delay=0.3)

    debouncer.call("item_state", lambda: calls.append("first"))
    debouncer.call("item_state", lambda: calls.append("second"))

    assert app.cancelled == ["timer1"]
    assert [delay for _cb, delay in app.timers.values()] == [0.3]
    app.fire_all()
    assert calls == ["second"]


def test_cancelling_all_drops_every_pending_call():
    app = _TimerApp()
    calls = []
    debouncer = Debouncer(app)
    debouncer.call("a", lambda: calls.append("a"))
    debouncer.call("b", lambda: calls.append("b"))

    debouncer.clear_all()

    assert app.timers == {}
    assert calls == []


def test_page_debouncing_never_uses_home_assistants_executor():
    executor_jobs = []
    app = _TimerApp()
    app.hass = SimpleNamespace(
        loop=SimpleNamespace(call_soon_threadsafe=lambda *args: executor_jobs.append(args)),
        async_add_executor_job=lambda *args: executor_jobs.append(args),
    )
    calls = []

    HAUIBase(app).debouncer.call("item_state", lambda: calls.append("flush"))
    app.fire_all()

    assert calls == ["flush"]
    assert executor_jobs == []


class _Proxy:
    def __init__(self, calls):
        self._calls = calls

    def call_service(self, service, **kwargs):
        self._calls.append((threading.get_ident(), service, kwargs))


class _EntityApp:
    def __init__(self):
        self.calls = []

    def item_exists(self, entity_id):
        return True

    def get_item(self, entity_id):
        return _Proxy(self.calls)


def test_entity_services_are_called_in_order_on_the_calling_thread():
    app = _EntityApp()
    light = HAUIEntity(app, "light.desk")

    light.call_entity_service("turn_on", brightness=30)
    light.call_entity_service("turn_on", brightness=40)

    caller = threading.get_ident()
    assert app.calls == [
        (caller, "turn_on", {"brightness": 30}),
        (caller, "turn_on", {"brightness": 40}),
    ]

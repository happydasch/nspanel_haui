"""The home stream: a device's home panel, running for the dashboard cards that show it.

A dashboard card in Home panel mode (``web/card.py``) is a viewer of its
device's home stream. The stream runs the home panel on the device's virtual
app the way a panel card render does (``virtual_panel._PanelRender``), apart
from the sandbox previews, but it does not stop once the page drew: the
page's state listeners and timers redraw it as entities and the clock change,
and each output goes to every viewer. It reads Home Assistant's real states
only (``virtual_panel._StreamApp``).

The first viewer starts it and the last one stops it. A late viewer gets the
page drawn from what the stream sent so far, the last write per target, as a
live viewer gets a shown page (``HAUIESPHomeController.page_commands``). A
save restarts it on the new config; a stopping host ends it, and its viewers
are told.

``attach`` and ``detach`` are called from the event loop; everything else,
the viewers included, belongs to the app's worker.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ...haui.controller.esphome import command_target
from ...haui.device_config import is_portrait_model

_LOGGER = logging.getLogger(__name__)

# Sink for messages to the browser; must be safe to call from any thread.
Sink = Callable[[dict[str, Any]], None]


class HomeStream:
    """The home panel of one device's virtual app, shown to dashboard cards."""

    def __init__(self, app: Any, render: Callable[[dict[str, Any]], Any]) -> None:
        """Args:
        app: the device's ``VirtualNSPanelHAUI``.
        render: builds the isolated, streaming render of a panel config
            (``_PanelRender(..., stream=True)``), on the worker.
        """
        self._app = app
        self._new_render = render
        self._viewers: dict[str, Sink] = {}
        self._render: Any | None = None
        self._before: list[str] = []
        # Target -> its last command, in the order of those last writes.
        self._commands: dict[str, str] = {}
        # Why the home panel does not run while viewers wait for it.
        self._error: str | None = None
        self._ended = False

    @property
    def viewer_count(self) -> int:
        return len(self._viewers)

    # event loop

    def attach(self, viewer_id: str, sink: Sink) -> None:
        """Show the home panel to a viewer; the first one starts it."""
        self._app.dispatch(self._attach, viewer_id, sink)

    def detach(self, viewer_id: str) -> None:
        """Remove a viewer; the last one stops the page."""
        self._app.dispatch(self._detach, viewer_id)

    # worker

    def restart(self) -> None:
        """Run the home panel again on a saved config and draw it for every viewer.

        The home panel, its theme or the orientation may have changed.
        """
        if self._ended or not self._viewers:
            return
        self._stop()
        self._start()
        for sink in list(self._viewers.values()):
            self._show(sink)

    def end(self) -> None:
        """Stop for good (the host stops) and tell every viewer."""
        self._ended = True
        self._stop()
        viewers, self._viewers = self._viewers, {}
        for sink in viewers.values():
            sink({"type": "ended"})

    def _attach(self, viewer_id: str, sink: Sink) -> None:
        if self._ended:
            sink({"type": "ended"})
            return
        if self._render is None:
            self._start()
        # Kept without a page too: a save that adds a panel restarts it.
        self._viewers[viewer_id] = sink
        self._show(sink)

    def _detach(self, viewer_id: str) -> None:
        self._viewers.pop(viewer_id, None)
        if not self._viewers:
            self._stop()

    def _start(self) -> None:
        """Run the device's home panel, or note why it cannot run."""
        panel = self._app.controller["navigation"].home_panel
        if panel is None:
            self._error = "no_home_panel"
            return
        try:
            render = self._new_render(panel.get_default_config())
            render.start()
        except Exception:
            _LOGGER.exception("Home panel stream of '%s' failed to start", self._app.name)
            self._error = "start_failed"
            return
        self._error = None
        self._render = render
        self._before = list(render.before)
        self._commands = {}
        self._record(render.commands)
        render.stream_to(self._on_commands)

    def _stop(self) -> None:
        render, self._render = self._render, None
        self._before = []
        self._commands = {}
        if render is not None:
            render.stream_to(None)
            render.stop()

    def _record(self, commands: list[str]) -> None:
        for command in commands:
            target = command_target(command)
            self._commands.pop(target, None)
            self._commands[target] = command

    def _on_commands(self, commands: list[str]) -> None:
        self._record(commands)
        message = {"type": "commands", "commands": commands}
        for sink in list(self._viewers.values()):
            sink(message)

    def _show(self, sink: Sink) -> None:
        """Draw the running page for one viewer, or tell it why there is none."""
        render = self._render
        if render is None:
            sink({"type": "error", "message": self._error})
            return
        portrait = is_portrait_model(self._app.device.get("display_model"))
        sink({"type": "started", "portrait": portrait})
        sink({"type": "commands", "commands": self._before})
        sink({"type": "page", "page": render.page_id})
        sink({"type": "commands", "commands": list(self._commands.values())})

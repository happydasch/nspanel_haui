from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...hub.adapter import ESPHomeProxy
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ALL_CMD, ALL_RECV, ESP_NS_EVENT, ESPAction
from ..utils.draw_wire import (
    DRAW_FORMAT_PACKED,
    LEGACY_SLICE_RUNS,
    RUN_MS_CEILING,
    display_run,
    draw_format,
    pack_program,
    program_slices,
    run_packer,
)

#: Seconds a slice gets on top of its own drawing time before the hub sends the
#: next one without a report: a fence lost to a busy event loop must not wedge
#: the rest of the image.
DRAW_SLICE_GRACE: float = 2.0


class HAUIESPHomeController(HAUIBase):
    """ESPHome controller for device communication via ESPHome native API.

    Provides access to ESPHome native API functionality for device communication.
    """

    def __init__(
        self,
        app: NSPanelHAUI,
        config: dict[str, Any],
        esp_api: ESPHomeProxy,
        event_callback: Any,
    ) -> None:
        """Initialize ESPHome controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
            esp_api (ESPHomeProxy): ESPHome native API bridge
            event_callback (method): Callback for events
        """
        super().__init__(app, config)
        self.esphome = esp_api
        self.prev_cmd: tuple[str, str] | None = None
        # What the shown page was sent since it loaded: target -> last command.
        self._page_commands: dict[str, str] = {}
        self._event_callback = event_callback
        self._device_names: list[str] = []
        # Slices of a draw pass still to send, and the timer that sends the next
        # one if its fence never reports (see ``_start_draw``).
        self._draw_slices: list[list[str]] = []
        self._draw_timer: str | None = None
        #: The pass being drawn, so a slice the panel failed can be re-sent once.
        self._draw_runs: list[str] = []
        self._draw_retried = False
        self._draw_old_firmware_warned = False
        #: The packing the panel's firmware decodes, fixed per program: format 1
        #: takes the display instructions, 2 the base-36 runs (``draw_wire``).
        self._draw_pack: Callable[[str], str] = display_run

        # Build list of configured device names
        devices = self.config.get("devices", [])
        device_name = self.config.get("device_name", "")

        if not device_name and not devices:
            self.log(
                "Neither device_name nor devices configured in ESPHome config",
                level="ERROR",
            )
            raise ValueError("device_name is required when no devices list is configured")

        if devices:
            for device in devices:
                name = device.get("name", "")
                if name:
                    self._device_names.append(name)
        if not self._device_names and device_name:
            self._device_names = [device_name]

    # part

    def start_part(self) -> None:
        """Starts the part."""
        # Listen for the single static event type used by all device events
        self.esphome.listen_event(self.callback_event, ESP_NS_EVENT)
        self.log(f"Listening for ESPHome events (devices: {self._device_names})")

    def stop_part(self) -> None:
        """Stops the part.

        Cancels all ESPHome event bus listeners registered during start_part.
        """
        self._cancel_timer("_draw_timer")
        self._draw_slices.clear()
        self._draw_runs = []
        self.esphome.cancel_listen_events()

    # public

    def send_cmd(self, cmd: str, value: str | dict | list = "", force: bool = False) -> None:
        """Sends a command to the device(s) via ESPHome native API.

        Commands are broadcast to all discovered ESPHome devices.

        Args:
            cmd (str): Command name (with or without esphome. prefix).
            value: Value for command. Passed as-is (str/dict/list).
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        # Strip esphome. prefix for the JSON payload - ESPHomeProxy expects
        # unprefixed names (e.g., "send_command", not "esphome.send_command")
        bare_cmd = cmd.removeprefix("esphome.")

        if f"esphome.{bare_cmd}" not in ALL_CMD:
            self.log(f"Unknown command {cmd} received. content: {value}", level="WARNING")

        if value is None:
            value = ""

        if bare_cmd == ESPAction.DRAW_RUNS:
            self._start_draw(value)
            return

        # Dedup only single commands; batches are deduped in haui_base and
        # transport dedup would drop chunks.
        dedup_key = (bare_cmd, value if isinstance(value, str) else str(value))
        if (
            bare_cmd not in (ESPAction.SEND_COMMANDS, ESPAction.DRAW_RUNS)
            and not force
            and self.prev_cmd == dedup_key
        ):
            self.log(
                f"Dropping identical consecutive message: {bare_cmd}/{value}",
                level="WARNING",
            )
            return

        self.log(f"Publishing command: {bare_cmd}", level="DEBUG")
        published = self.esphome.publish(bare_cmd, value)
        if bare_cmd == ESPAction.GOTO_PAGE:
            # The display loads the page with its compiled widgets again.
            self._page_commands.clear()
        elif published and bare_cmd == ESPAction.SEND_COMMAND:
            self._record_page_command(str(value))
        elif published and bare_cmd == ESPAction.SEND_COMMANDS:
            for command in value if isinstance(value, list) else [value]:
                self._record_page_command(str(command))
        if published and bare_cmd in (
            ESPAction.SEND_COMMAND,
            ESPAction.SEND_COMMANDS,
            ESPAction.GOTO_PAGE,
        ):
            self.app.publish_preview_output(bare_cmd, value)
        # Only a command the device got may hold back the same one next time.
        if published:
            self.prev_cmd = dedup_key

    def publish_detached(self, cmd: str, value: str | dict | list = "") -> None:
        """Send a command without waiting for it and without touching the worker.

        Same command names as ``send_cmd`` (the ``esphome.`` prefix is
        stripped), but the command is executed fire-and-forget straight on the
        event loop: it neither waits for the device nor queues behind work on
        the app's worker thread. Only for high-frequency liveness traffic —
        the hub→device heartbeat — which must not be delayed by renders or
        update checks.

        Args:
            cmd (str): Command name (with or without esphome. prefix).
            value: Value for command.
        """
        if value is None:
            value = ""
        self.esphome.publish_detached(cmd.removeprefix("esphome."), value)

    def page_commands(self) -> list[str]:
        """The display commands the shown page was sent since it loaded.

        Only the last write to each target is kept (an attribute, a widget's
        ``vis`` or ``tsw``; any other command is its own target), in the order
        of those last writes. Replayed on the freshly loaded page, after the
        page's ``load_commands``, they end on the screen the panel shows: what
        the Live preview gives a viewer that attaches to a shown page.
        """
        return list(self._page_commands.values())

    def _record_page_command(self, command: str) -> None:
        target = command_target(command)
        self._page_commands.pop(target, None)
        self._page_commands[target] = command

    def _record_draw_program(self, runs: list[str]) -> None:
        """Replace the replayable image program with ``runs``.

        Each ``fill`` is its own target (it sets no attribute), so the previous
        program would otherwise stay in the replay and paint over — or under —
        the new one. One image program on the page is the whole point: a viewer
        that attaches late sees the same picture the panel shows.
        """
        for target in [t for t in self._page_commands if t.startswith("fill ")]:
            del self._page_commands[target]
        for run in runs:
            self._record_page_command(str(run))

    # image drawing

    def _draw_packer(self) -> Callable[[str], str]:
        """The packing this panel's firmware decodes (``draw_wire.draw_format``).

        Read from the handshake, not from the version: firmware 1 streams the
        display instructions, 2 the base-36 runs, and a panel that reports
        nothing predates the field and takes the instructions. Sending the wrong
        one paints nothing at all - the firmware refuses every run it cannot
        decode - so this is the one thing a draw must not guess.
        """
        return run_packer(self._draw_format())

    def _draw_format(self) -> int:
        """The ``draw_format`` the panel's firmware reported (1 when it says nothing)."""
        info = self.app.device.device_info or {}
        return draw_format(info.get("draw_format"))

    def _start_draw(self, value: str | dict | list) -> None:
        """Paint a pass of ``fill`` instructions, one slice at a time.

        A pass is far longer than one API message and far bigger than the
        panel's heap, so it is cut into slices (``draw_wire.program_slices``)
        that the firmware stages one after another: the panel reports a slice
        when its last run is on the wire and the next one follows
        (``on_draw_report``). The picture therefore appears in bands while RAM
        stays the size of a single slice.

        The whole pass - not the slice - is what the page replay keeps, so a
        viewer that attaches late still sees the finished image, and it is also
        what a failed pass is retried from (``on_draw_report``).
        """
        runs = [str(run) for run in (value if isinstance(value, list) else [value])]
        if not runs:
            return
        self._draw_runs = runs
        self._draw_retried = False
        self._record_draw_program(runs)
        self.app.publish_preview_output(ESPAction.DRAW_RUNS, runs)
        if self._draw_format() < DRAW_FORMAT_PACKED:
            self._warn_about_an_old_firmware()
        self._plan_draw_slices()

    def _warn_about_an_old_firmware(self) -> None:
        """Say once why a detailed image may lose runs on this panel.

        A firmware that reports ``draw_format`` 1 streams a pass at the pacer's
        fixed pace instead of waiting for the display to acknowledge each run,
        and a hairline ``fill`` (one per display pixel, which is what a detailed
        image is made of) takes the display longer than that pace. Its receive
        buffer then overflows and the instructions in flight are lost or
        truncated - the picture gets thin gaps and stray coloured strips, and the
        panel reports success anyway, because every run was handed to the queue.
        """
        if self._draw_old_firmware_warned:
            return
        self._draw_old_firmware_warned = True
        self.log(
            "draw_runs: this panel runs a firmware without the acknowledged draw "
            "(draw_format 1), which streams a pass faster than the display takes "
            "it; a detailed image can lose runs. Update the panel's firmware.",
            level="WARNING",
        )

    def _plan_draw_slices(self) -> None:
        """Cut the remembered pass into slices for this panel and start sending.

        A panel on a firmware without the acknowledged draw gets short slices: it
        streams a slice at the pacer's fixed pace, and the display has to have
        caught up before the next one lands, or its receive buffer overruns and
        runs are lost (``draw_wire.LEGACY_SLICE_RUNS``).
        """
        runs = self._draw_runs
        self._cancel_timer("_draw_timer")
        self._draw_pack = self._draw_packer()
        legacy = self._draw_format() < DRAW_FORMAT_PACKED
        slices = program_slices(
            runs,
            pack=self._draw_pack,
            max_runs=LEGACY_SLICE_RUNS if legacy else None,
        )
        self.log(
            f"draw_runs: {len(runs)} run(s), {len(slices)} slice(s), "
            f"{self._draw_pack(runs[0])!r} to start",
            level="DEBUG",
        )
        self._draw_slices = slices
        self._send_draw_slice()

    def _send_draw_slice(self) -> None:
        """Send the next slice, and arm the timer that covers a lost report."""
        while True:
            self._cancel_timer("_draw_timer")
            if not self._draw_slices:
                return
            runs = self._draw_slices.pop(0)
            program = pack_program(runs, pack=self._draw_pack)
            self.log(
                f"draw_runs: {len(runs)} run(s), {len(program)} characters, "
                f"{len(self._draw_slices)} slice(s) to go",
                level="DEBUG",
            )
            if not self.esphome.publish(ESPAction.DRAW_RUNS, program):
                self.log(
                    "draw_runs: the panel did not take a slice; the rest is dropped",
                    level="WARNING",
                )
                self._draw_slices.clear()
                return
            if not getattr(self.esphome, "simulated", False):
                expected = len(runs) * RUN_MS_CEILING / 1000
                self._draw_timer = self.app.run_in(
                    self._draw_slice_timeout, expected + DRAW_SLICE_GRACE
                )
                return
            # The simulator paints as it records, so there is no fence to wait
            # for: send every remaining slice straight away.

    def _draw_slice_timeout(self, **_kwargs: Any) -> None:
        """Send the next slice although the panel never reported the last one."""
        self._draw_timer = None
        if not self._draw_slices:
            return
        self.log(
            "draw_runs: no report for a slice within its drawing time; sending the next one",
            level="WARNING",
        )
        self._send_draw_slice()

    def on_draw_report(self, ok: bool) -> None:
        """esphome.res_draw - a slice is through: send the next one.

        Args:
            ok: Whether the panel took every run of the slice. A refused slice
                means the runs are missing from the picture it paints - a lost
                acknowledgment or an overrun display drops them - so the whole
                pass is re-sent once from its first run instead of leaving a
                picture with gaps in it. Only a second failure drops the rest.
        """
        self._cancel_timer("_draw_timer")
        if not ok:
            if self._draw_runs and not self._draw_retried:
                self._draw_retried = True
                self.log(
                    "draw_runs: the panel did not take every run; re-sending the image once",
                    level="WARNING",
                )
                self._plan_draw_slices()
                return
            self.log(
                "draw_runs: the panel refused a slice again; the rest of the image is dropped",
                level="WARNING",
            )
            self._draw_slices.clear()
            return
        self._send_draw_slice()

    def reset_prev_cmd(self) -> None:
        """Clear the previous-command cache so the next render is never suppressed.

        Call this when switching pages so the first render batch after a page
        transition always reaches the display, even if it happens to be
        identical to the last batch sent from the previous page.
        """
        self.prev_cmd = None

    def callback_event(self, event_name: str, data: dict[str, Any], kwargs: dict[str, Any]) -> None:
        """Callback for ESPHome events.

        The ESPHomeProxy passes pre-parsed data with 'name' and 'value' keys.

        Args:
            event_name (str): HA event type (e.g., "esphome.connected").
            data (dict): Event data with 'name' and 'value' keys.
            kwargs (dict): Additional arguments.
        """
        name = data.get("name", event_name)
        value = data.get("value", "")

        self.log(
            f"ESPHome event received - name: {name}, value: {str(value)[:100]}",
            level="DEBUG",
        )

        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received. content: {value}")

        event = HAUIEvent(name, value)
        self._event_callback(event)


def command_target(command: str) -> str:
    """What a display command sets: a later command with the same target replaces it."""
    eq = command.find("=")
    if eq > 0:
        return command[:eq]
    if command.startswith(("vis ", "tsw ")):
        comma = command.rfind(",")
        if comma > 0:
            return command[:comma]
    # Drawing, ref, click: each distinct command is one target.
    return command

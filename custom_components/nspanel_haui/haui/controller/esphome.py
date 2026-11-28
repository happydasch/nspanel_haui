from __future__ import annotations

from collections.abc import Callable
from itertools import islice
from typing import TYPE_CHECKING, Any, Final

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
from ..utils.image_program import Rect

#: Seconds a slice gets on top of its own drawing time before the hub sends the
#: next one without a report: a fence lost to a busy event loop must not wedge
#: the rest of the image.
DRAW_SLICE_GRACE: float = 2.0

#: Fills the page replay holds before its oldest ones are dropped. This is the
#: size of one detailed whole paint (``image_stream.MAX_FIRST_FRAME_RUNS``), not
#: of a stream: a page a camera draws on is shown for hours and never repaints its
#: rectangle whole (``camera_stream.start_page_stream``).
REPLAY_FILLS: Final = 12000


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
        # The fills among them, with the rectangle each paints, in the order they
        # were last written: what bounds the replay (``_trim_replay``).
        self._fills: dict[str, tuple[int, int, int, int]] = {}
        # The rectangle a completed whole pass has repainted since the fills were
        # last trimmed: what the replay still describes completely, if anything.
        self._replay_whole: tuple[int, int, int, int] | None = None
        self._event_callback = event_callback
        self._device_names: list[str] = []
        # Slices of a draw pass still to send, and the timer that sends the next
        # one if its fence never reports (see ``_start_draw``).
        self._draw_slices: list[list[str]] = []
        self._draw_timer: str | None = None
        #: The pass being drawn, so a slice the panel failed can be re-sent once.
        self._draw_runs: list[str] = []
        self._draw_in_flight: list[str] = []
        #: The rectangle the pass being drawn paints whole - its first fill, when
        #: it is a whole paint - so a completed pass can say which area the replay
        #: describes completely again (``picture_commands``).
        self._draw_whole: tuple[int, int, int, int] | None = None
        self._draw_external = False
        self._draw_done: Callable[[bool], None] | None = None
        self._draw_retried = False
        self._draw_old_firmware_warned = False
        #: Passes that may not be on the display: a slice the panel never took, a
        #: slice it refused twice, a pass another pass cut short. What arrived stays
        #: on the screen, so a camera stream that owns the rectangle has to paint it
        #: whole again instead of sending deltas against a picture the panel no
        #: longer shows (``draw_failures``).
        self._draw_failures = 0
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
        self.cancel_draw()
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
            # A page switch ends a draw in flight - the firmware stops its own
            # stream at the same point - and the display loads the page's
            # compiled widgets again.
            if published:
                self.cancel_draw()
                self._page_commands.clear()
                self._fills.clear()
                # The display loads the page's compiled widgets: nothing the
                # replay describes is on it any more.
                self._replay_whole = None
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

    def page_commands(self, *, exclude: Rect | None = None) -> list[str]:
        """The display commands the shown page was sent since it loaded.

        Only the last write to each target is kept (an attribute, a widget's
        ``vis`` or ``tsw``; any other command is its own target), in the order
        of those last writes. Replayed on the freshly loaded page, after the
        page's ``load_commands``, they end on the screen the panel shows: what
        the Live preview gives a viewer that attaches to a shown page.

        Args:
            exclude: Leave out the fills inside this rectangle - a page that
                paints its area from a picture the stream owns replays them
                through ``picture_commands`` instead.
        """
        if exclude is None:
            return list(self._page_commands.values())
        area = (exclude.x, exclude.y, exclude.w, exclude.h)
        return [
            command
            for command in self._page_commands.values()
            if (rect := _fill_rect(command)) is None or not _covers(area, rect)
        ]

    def picture_commands(self, x: int, y: int, w: int, h: int) -> list[str]:
        """Replay the confirmed fills contained in a panel's picture area.

        Empty when the replay can no longer describe that area whole: the oldest
        fills were dropped for room since a pass painted it, so what is left has
        holes in it. A viewer asks the stream that owns the area for a whole paint
        instead - a delta's worth of leftovers is not a picture.
        """
        area = (x, y, w, h)
        if self._replay_whole is None or not _covers(self._replay_whole, area):
            return []
        return [
            command
            for command in self._page_commands.values()
            if (rect := _fill_rect(command)) is not None and _covers(area, rect)
        ]

    def _record_page_command(self, command: str, *, own_draw: bool = False) -> None:
        """Record one display command for the page replay.

        Args:
            command: The display command the panel took.
            own_draw: This fill is part of a draw program this controller sent, so
                whoever owns its rectangle is not told about it. Every other fill
                is a program from elsewhere - a page's own script, a service image
                - and the stream that owns that area must paint it whole again
                instead of sending deltas against a picture the panel no longer
                shows (``app.paint_rect``).
        """
        rect = _fill_rect(command)
        # A different colour at exactly the same position overwrites the same
        # pixels. The latest write keeps its position relative to widget paints.
        target = f"fill {rect}" if rect is not None else command_target(command)
        self._page_commands.pop(target, None)
        self._page_commands[target] = command
        if rect is not None:
            self._fills.pop(target, None)
            self._fills[target] = rect
            self._trim_replay()
            if not own_draw:
                self.app.paint_rect(Rect(*rect))

    def _forget_page_command(self, target: str) -> None:
        """Drop a recorded command, and the fill that claims its pixels with it."""
        self._page_commands.pop(target, None)
        self._fills.pop(target, None)

    def _trim_replay(self) -> None:
        """Keep the replay the size of a picture, not of a whole stream.

        A camera streams for hours without ever painting its rectangle whole
        again (``refresh_every`` is 0 on a camera page: a full paint is a visible
        flash), so every distinct fill rectangle a moving scene produces would
        stay in the replay for the length of the stream - and a late viewer is
        sent all of it in one message. The oldest fills go first, which is what a
        picture needs least.
        """
        overflow = len(self._fills) - REPLAY_FILLS
        if overflow <= 0:
            return
        for target in list(islice(self._fills, overflow)):
            self._forget_page_command(target)
        # The fills that just went may have been part of what a pass painted
        # whole: what a viewer replays may now have holes, so it asks for a paint.
        self._replay_whole = None

    def _confirm_draw_slice(self) -> None:
        """Record and mirror exactly the decoded slice the panel confirmed."""
        runs, self._draw_in_flight = self._draw_in_flight, []
        if not runs:
            return
        if cover := _fill_rect(runs[0]):
            # Only the actual opaque first fill proves coverage. A bounding box
            # around sparse fills (or a partly sent image) can contain holes. A
            # pass repaints what its first fill covers whether or not it is a
            # whole one, so this applies to every pass, not only a full paint -
            # and it compares the stored rectangles, never the commands.
            for target, rect in list(self._fills.items()):
                if _covers(cover, rect):
                    self._forget_page_command(target)
        for run in runs:
            self._record_page_command(run, own_draw=True)
        self.app.publish_preview_output(ESPAction.DRAW_RUNS, runs, external=self._draw_external)

    def cancel_draw(self) -> None:
        """Stop the draw pass in flight: a page switch owns the display now.

        The slice already on the panel finishes painting (the firmware stops
        after the band it queued), and any report it still sends is ignored
        because no pass is remembered. Used when the hub sends a page switch and
        as the backstop for one the display reports; ``_handle_page_event``
        cancels before the page render starts.
        """
        self._finish_draw(False)

    def _finish_draw(self, ok: bool) -> None:
        self._cancel_timer("_draw_timer")
        self._draw_slices.clear()
        self._draw_runs = []
        self._draw_in_flight = []
        whole, self._draw_whole = self._draw_whole, None
        if ok and whole is not None:
            # The pass arrived whole: every pixel of its first fill has a colour
            # in the replay now, whatever it painted over went with it.
            self._replay_whole = whole
        done, self._draw_done = self._draw_done, None
        if done is not None:
            done(ok)

    def _fail_draw(self) -> None:
        self._draw_failures += 1
        self._finish_draw(False)

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

    def _start_draw(
        self,
        value: str | dict | list,
        *,
        full: bool = True,
        external: bool = False,
        on_done: Callable[[bool], None] | None = None,
    ) -> bool:
        """Paint a pass of ``fill`` instructions, one slice at a time.

        A pass is far longer than one API message and far bigger than the
        panel's heap, so it is cut into slices (``draw_wire.program_slices``)
        that the firmware stages one after another: the panel reports a slice
        when its last run is on the wire and the next one follows
        (``on_draw_report``). The picture therefore appears in bands while RAM
        stays the size of a single slice.

        The whole pass is kept for retries, but only confirmed slices enter
        the page replay or reach Live. The same path handles still images and
        camera deltas, including viewers that attach during a pass.

        Returns:
            Whether the pass was accepted for drawing. A pass the display cannot
            take - a TFT install owns it, which no caller may write into - is
            refused here rather than sliced and sent into the transfer.
        """
        if self._display_busy():
            self.log(
                f"Dropped {len(value) if isinstance(value, list) else 1} draw run(s) "
                "during a TFT install",
                level="DEBUG",
            )
            self._fail_draw()
            return False
        runs = [str(run) for run in (value if isinstance(value, list) else [value])]
        if not runs:
            return False
        if self.drawing:
            # A new pass replaces the one in flight: the firmware stops its own
            # stream, so the picture keeps whatever of the old pass arrived and
            # nothing of the rest. Whoever owned that rectangle must repaint it.
            self._fail_draw()
        self._draw_runs = runs
        self._draw_done = on_done
        self._draw_retried = False
        self._draw_whole = _fill_rect(runs[0]) if full else None
        self._draw_external = external
        if self._draw_format() < DRAW_FORMAT_PACKED:
            self._warn_about_an_old_firmware()
        self._plan_draw_slices()
        return True

    @property
    def drawing(self) -> bool:
        """Whether a program is still on its way to the display.

        True from the first slice to the report that ends the last one, which is
        what a stream checks before sending a frame: the firmware restarts its
        own program on a new call, so a frame sent into a busy draw would cut the
        previous one short instead of following it.
        """
        return bool(self._draw_slices or self._draw_runs)

    @property
    def draw_failures(self) -> int:
        """How many passes may have left the panel's picture incomplete.

        Counts every pass the display did not get whole: a slice the panel never
        took, a slice it refused twice, a pass another pass cut short. The runs
        that did arrive stay on the screen, so the panel now shows part of a
        picture nobody meant to paint there - a camera stream compares this
        counter and paints its rectangle whole again instead of sending deltas
        against a picture the panel no longer shows.
        """
        return self._draw_failures

    def draw_overlay(self, runs: list[str], *, rect: Rect | None = None) -> None:
        """Paint a service image, which also belongs on a matching sandbox panel.

        Args:
            runs: ``fill`` instructions, in the order they paint.
            rect: The rectangle the program paints, when it is one the caller
                knows. Whoever owns that area on the display - a camera stream -
                is told, so a picture it holds there is painted whole again
                instead of being left with a hole in it (``app.paint_rect``).
        """
        if self._display_busy():
            return
        if self._start_draw(runs, external=True) and rect is not None:
            self.app.paint_rect(rect)

    def draw_stream_frame(
        self,
        runs: list[str],
        *,
        full: bool = True,
        external: bool = False,
        on_done: Callable[[bool], None] | None = None,
    ) -> bool:
        """Draw a frame; commit the planner only after all of its slices drain.

        Returns:
            Whether the pass was accepted (see ``_start_draw``).
        """
        return self._start_draw(runs, full=full, external=external, on_done=on_done)

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
        """Send the next slice, and arm the timer that covers a lost report.

        Both transports answer a slice with a fence (``esphome.res_draw``): the
        panel reports when its last run is on the wire, and the virtual firmware
        does the same after the time the fills would take. There is no shortcut
        for the simulator, or the preview would never see a busy display or a
        refused slice - the two states the panel lives in.
        """
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
            self._fail_draw()
            return
        # The slice as display instructions, which is what this is: the program was
        # packed from ``runs``, so inside, the two forms are the same slice. It is
        # what a confirmed slice enters the replay as (``_confirm_draw_slice``).
        self._draw_in_flight = list(runs)
        expected = len(runs) * RUN_MS_CEILING / 1000
        self._draw_timer = self.app.run_in(self._draw_slice_timeout, expected + DRAW_SLICE_GRACE)

    def _draw_slice_timeout(self, _kwargs: dict[str, Any] | None = None) -> None:
        """Release a timed-out draw, or let a still image finish its other slices."""
        self._draw_timer = None
        if not self._draw_runs:
            return
        if self._draw_done is not None or not self._draw_slices:
            # A camera's next delta needs a confirmed baseline, not a guessed one.
            self.log("draw_runs: no report for a slice; the draw is dropped", level="WARNING")
            self._fail_draw()
            return
        self.log(
            "draw_runs: no report for a slice within its drawing time; sending the next one",
            level="WARNING",
        )
        self._send_draw_slice()

    def on_draw_report(self, ok: bool, *, runs: int | None = None) -> None:
        """esphome.res_draw - a slice is through: send the next one.

        Args:
            ok: Whether the panel took every run of the slice. A refused slice
                means the runs are missing from the picture it paints - a lost
                acknowledgment or an overrun display drops them - so the whole
                pass is re-sent once from its first run instead of leaving a
                picture with gaps in it. Only a second failure drops the rest.
            runs: How many runs the firmware sent, when the report provides it.
        """
        if not self._draw_runs and not self._draw_slices:
            # A report from a pass that was cancelled (a page switch) or already
            # finished on its last slice: there is nothing to advance.
            self.log(
                "draw_runs: a report arrived with no draw in flight; ignoring it",
                level="DEBUG",
            )
            return
        if ok and runs is not None and runs != len(self._draw_in_flight):
            self.log("draw_runs: report does not match the in-flight slice", level="WARNING")
            return
        self._cancel_timer("_draw_timer")
        last_slice = not self._draw_slices
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
            self._fail_draw()
            return
        self._confirm_draw_slice()
        if last_slice:
            self._finish_draw(True)
        else:
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


def _covers(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    x, y, w, h = outer
    left, top, width, height = inner
    return x <= left and y <= top and left + width <= x + w and top + height <= y + h


def _fill_rect(command: str) -> tuple[int, int, int, int] | None:
    """The ``x,y,w,h`` a ``fill`` command covers, or ``None`` for anything else.

    The replay holds display commands, so a fill is ``fill x,y,w,h,colour`` -
    width and height, not a second corner. Used to decide which recorded fills a
    new image already paints over, and which rectangle a page's own fill damaged.

    A fill off the display (a negative origin, no area) is ``None``: it is not a
    rectangle anything can reason about, and ``Rect`` would refuse it.
    """
    if not command.startswith("fill "):
        return None
    fields = command[len("fill ") :].split(",")
    if len(fields) != 5:
        return None
    try:
        x, y, w, h = (int(field) for field in fields[:4])
    except ValueError:
        return None
    if x < 0 or y < 0 or w < 1 or h < 1:
        return None
    return x, y, w, h

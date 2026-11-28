"""The wire format of a draw program, and how one is split into slices.

A run is one Nextion ``fill x,y,w,h,colour`` display instruction. Only the five
numbers matter to the device, so the program the panel receives drops the
``fill `` prefix and writes each number in base 36: ``3c,1s,8,8,1ekf`` instead of
``fill 120,64,8,8,65535``, a third less traffic for the same picture. The
firmware decodes a run back into the display instruction
(``esphome/nspanel_haui/image.yaml``), so everything above this module - page
replay, the previews, the golden tests - keeps speaking display commands.

That packing is a firmware capability (``draw_format`` in
``esphome/nspanel_haui/version.yaml``, read with ``draw_format()``): a firmware
older than 2 has no decoder and streams the display instructions themselves, so
it is sent ``display_run`` instead of ``pack_run`` and still paints the image.

A pass is also too long for one API message and too big for the panel's heap, so
it is sent as *slices*: ``program_slices`` cuts the ordered runs into programs the
firmware can stage one after another. The panel reports each slice when its last
run is on the wire, and the hub sends the next one; the picture therefore
appears in bands while RAM stays the size of one slice.

Pure and synchronous, no Home Assistant: the hub packs, the firmware unpacks.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Final

#: The ``draw_format`` a firmware reports when its ``draw_runs`` action decodes
#: base-36 runs (``esphome/nspanel_haui/version.yaml``). Firmware that reports 1
#: - or reports nothing, which is what a build without the decoder does - takes
#: the display instructions themselves.
DRAW_FORMAT_PACKED: Final = 2
#: Longest program (packed characters) one ``draw_runs`` call carries. The
#: firmware stages it as a second copy, so this is the panel's RAM budget, not
#: an API limit: a slice of 8 000 characters needs about 16 KB of heap.
DRAW_SLICE_CHARS: Final = 8000
#: Runs one slice may carry on a firmware that has no acknowledged draw
#: (``draw_format`` 1). Such a firmware streams a slice at the pacer's fixed pace
#: whatever the display needs, so a slice longer than the display's receive buffer
#: holds (about 40 instructions of 25 bytes) overruns it: the instructions in
#: flight are lost or truncated, which leaves thin gaps and stray coloured strips
#: in the picture. Cutting the slice short lets the fence - which the display only
#: answers after its last run - drain that backlog before the next slice arrives.
#: A firmware with the acknowledged draw needs none of this: it holds a window of
#: ``draw_window`` fills and paces itself, so its slices are the full 8 000.
LEGACY_SLICE_RUNS: Final = 64
#: Milliseconds the hub plans for one run: the firmware's pacer
#: (``command_spacing_ms``, ``esphome/nspanel_haui/base.yaml``), one command per
#: component phase. A draw switches the pacer off for its duration and keeps a
#: window of fills in flight instead (``image.yaml``), so the panel is usually
#: much faster than this - it is the pace the run budget is planned against, not
#: a measurement.
COMMAND_SPACING_MS: Final = 2
#: Milliseconds one run may take before the hub stops waiting for a slice's fence
#: and sends the next one anyway. The pacer paces nothing during a draw - the
#: pace is the display's own (``draw_window``) - and a slow panel legitimately
#: takes several times ``COMMAND_SPACING_MS`` per run. A slice cut short is not
#: harmless: the next one restarts the firmware's program, so this is pessimistic.
RUN_MS_CEILING: Final = 8.0
#: The display instruction a packed run expands to.
RUN_PREFIX: Final = "fill "
_RUN_FIELDS: Final = 5
_DIGITS: Final = "0123456789abcdefghijklmnopqrstuvwxyz"


class DrawWireError(ValueError):
    """A run could not be packed or unpacked."""


def base36(value: int) -> str:
    """``value`` in base 36, lowercase: 120 -> ``3c``, 65535 -> ``1ekf``.

    Raises:
        DrawWireError: When the value is negative.
    """
    if value < 0:
        raise DrawWireError(f"{value} has no base-36 form")
    digits: list[str] = []
    while True:
        value, remainder = divmod(value, 36)
        digits.append(_DIGITS[remainder])
        if not value:
            return "".join(reversed(digits))


def parse_base36(text: str) -> int:
    """The number ``text`` writes in base 36.

    Raises:
        DrawWireError: When ``text`` is empty or holds a digit outside base 36.
    """
    if not text:
        raise DrawWireError("an empty number")
    value = 0
    for char in text.lower():
        digit = _DIGITS.find(char)
        if digit < 0:
            raise DrawWireError(f"{text!r} is not a base-36 number")
        value = value * 36 + digit
    return value


def _fill_numbers(run: str) -> list[int]:
    """The five numbers of a display ``fill`` instruction.

    Raises:
        DrawWireError: When ``run`` is not a ``fill`` with five non-negative
            numbers - a program the device would drop should fail here, where
            the hub can say which run it was.
    """
    if not run.startswith(RUN_PREFIX):
        raise DrawWireError(f"{run!r} is not a {RUN_PREFIX.strip()} instruction")
    fields = run[len(RUN_PREFIX) :].split(",")
    if len(fields) != _RUN_FIELDS:
        raise DrawWireError(f"{run!r} does not hold {_RUN_FIELDS} numbers")
    try:
        numbers = [int(field) for field in fields]
    except ValueError as exc:
        raise DrawWireError(f"{run!r} holds a number that is not one: {exc}") from exc
    if any(number < 0 for number in numbers):
        raise DrawWireError(f"{run!r} holds a negative number")
    return numbers


def pack_run(run: str) -> str:
    """One display ``fill`` instruction as the ``x,y,w,h,colour`` the panel decodes.

    Raises:
        DrawWireError: When ``run`` is not a ``fill`` with five non-negative
            numbers.
    """
    return ",".join(base36(number) for number in _fill_numbers(run))


def display_run(run: str) -> str:
    """``run`` unchanged: the program format of a firmware older than 2.

    Those firmwares stream the display instructions themselves, so the only job
    left here is the validation ``pack_run`` does - a run the device would drop
    fails on the hub, where the source can be named.

    Raises:
        DrawWireError: When ``run`` is not a ``fill`` with five non-negative
            numbers.
    """
    _fill_numbers(run)
    return run


def unpack_run(packed: str) -> str:
    """The display instruction ``packed`` stands for; the inverse of ``pack_run``.

    Only the tests and the docs need this - the panel decodes in C++.

    Raises:
        DrawWireError: When ``packed`` is not five base-36 numbers.
    """
    fields = packed.split(",")
    if len(fields) != _RUN_FIELDS:
        raise DrawWireError(f"{packed!r} does not hold {_RUN_FIELDS} numbers")
    return RUN_PREFIX + ",".join(str(parse_base36(field)) for field in fields)


def pack_program(runs: Iterable[str], *, pack: Callable[[str], str] = pack_run) -> str:
    """``runs`` as one program string, ``;`` separated, each packed by ``pack``."""
    return ";".join(pack(run) for run in runs)


def program_slices(
    runs: Sequence[str],
    *,
    max_chars: int = DRAW_SLICE_CHARS,
    max_runs: int | None = None,
    pack: Callable[[str], str] = pack_run,
) -> list[list[str]]:
    """Cut ``runs`` into ordered programs within ``max_chars`` and ``max_runs``.

    A slice has to fit the firmware's own program limit and the panel's heap, so
    the length that matters is the packed one - ``pack`` is the firmware's format
    (``pack_run`` for 2, ``display_run`` for an older one). ``max_runs`` bounds it
    by count instead: on a firmware that streams a slice at a fixed pace, the
    count is what decides whether the display's receive buffer overflows
    (``LEGACY_SLICE_RUNS``).

    Order is preserved - the panel paints a slice as it arrives, so a slice is a
    band of the picture, not a random subset of it.

    Raises:
        DrawWireError: When a single run is longer than ``max_chars``, because a
            run cannot be split across two calls.
    """
    slices: list[list[str]] = []
    current: list[str] = []
    length = 0
    for run in runs:
        size = len(pack(run))
        if size > max_chars:
            raise DrawWireError(f"{run!r} does not fit a {max_chars}-character slice")
        full = length + 1 + size > max_chars
        if current and (full or (max_runs is not None and len(current) >= max_runs)):
            slices.append(current)
            current = []
            length = 0
        length += size + (1 if current else 0)
        current.append(run)
    if current:
        slices.append(current)
    return slices


def decode_program(program: str) -> list[str]:
    """The display instructions in ``program``, whichever format wrote them.

    For the previews, which replay what the panel paints: a run of either format
    decodes by its own shape - a packed run is five base-36 numbers and cannot
    start with ``fill `` - so a viewer never has to know which firmware answered.

    Raises:
        DrawWireError: When a run is neither a ``fill`` instruction nor five
            base-36 numbers.
    """
    return [
        run if run.startswith(RUN_PREFIX) else unpack_run(run) for run in program.split(";") if run
    ]


def draw_format(reported: object) -> int:
    """The draw program format a firmware reported; 1 when it says nothing.

    ``device_info["draw_format"]`` (``esphome/nspanel_haui/version.yaml``) is the
    firmware's own statement of what its ``draw_runs`` action decodes: ``1`` the
    display instructions themselves, ``DRAW_FORMAT_PACKED`` the base-36 runs.
    Reading it from the firmware is what keeps this honest - a version cannot: a
    build of an earlier commit reports the same version as one that has the
    packing, and the image would then not appear at all (every run is refused).

    Anything unreadable counts as 1: firmware that predates the field can only
    take display instructions, and whether it can draw at all is a separate
    question (``firmware_supports_draw_runs``).
    """
    if isinstance(reported, bool) or not isinstance(reported, (int, str)):
        return 1
    try:
        return int(str(reported).strip())
    except ValueError:
        return 1


def run_packer(program_format: int) -> Callable[[str], str]:
    """The packing ``program_format`` takes: base-36 runs, or the instructions."""
    return pack_run if program_format >= DRAW_FORMAT_PACKED else display_run

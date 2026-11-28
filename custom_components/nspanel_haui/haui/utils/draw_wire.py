"""The wire format of a draw program, and how one is split into slices.

A run is one Nextion ``fill x,y,w,h,colour`` display instruction. Only the five
numbers matter to the device, so the program the panel receives drops the
``fill `` prefix and writes each number in base 36: ``3c,1s,8,8,1ekf`` instead of
``fill 120,64,8,8,65535``, a third less traffic for the same picture. The
firmware decodes a run back into the display instruction
(``esphome/nspanel_haui/image.yaml``), so everything above this module - page
replay, the previews, the golden tests - keeps speaking display commands.

A pass is also too long for one API message and too big for the panel's heap, so
it is sent as *slices*: ``program_slices`` cuts the ordered runs into programs the
firmware can stage one after another. The panel reports each slice when its last
run is on the wire, and the hub sends the next one; the picture therefore
appears in bands while RAM stays the size of one slice.

Pure and synchronous, no Home Assistant: the hub packs, the firmware unpacks.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final

#: Longest program (packed characters) one ``draw_runs`` call carries. The
#: firmware stages it as a second copy, so this is the panel's RAM budget, not
#: an API limit: a slice of 8 000 characters needs about 16 KB of heap.
DRAW_SLICE_CHARS: Final = 8000
#: Milliseconds the panel takes per run (``command_spacing`` in
#: ``esphome/nspanel_haui/display.yaml``), so ``runs * COMMAND_SPACING_MS`` is the
#: latency of a program and the time a slice has to report back.
COMMAND_SPACING_MS: Final = 2
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


def pack_run(run: str) -> str:
    """One display ``fill`` instruction as the ``x,y,w,h,colour`` the panel decodes.

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
    return ",".join(base36(number) for number in numbers)


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


def pack_program(runs: Iterable[str]) -> str:
    """``runs`` as one program string, ``;`` separated."""
    return ";".join(pack_run(run) for run in runs)


def program_slices(runs: Sequence[str], *, max_chars: int = DRAW_SLICE_CHARS) -> list[list[str]]:
    """Cut ``runs`` into ordered programs no longer than ``max_chars`` packed.

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
        size = len(pack_run(run))
        if size > max_chars:
            raise DrawWireError(f"{run!r} does not fit a {max_chars}-character slice")
        if current and length + 1 + size > max_chars:
            slices.append(current)
            current = []
            length = 0
        length += size + (1 if current else 0)
        current.append(run)
    if current:
        slices.append(current)
    return slices

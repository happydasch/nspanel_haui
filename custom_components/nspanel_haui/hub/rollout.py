"""Hub-side update rollout: install the offered updates one device at a time.

A firmware or display upload blocks the panel's main loop until the transfer
ends, so the panel is offline for minutes. Fleet's *Install updates* therefore
installs one device, waits until that device's update finished, then moves on;
the first failure stops the rollout and the devices after it are not started.
Devices still queued can be cancelled; the one installing cannot be stopped.

The rollout runs on the event loop, one per config entry (``ROLLOUTS_KEY`` in
``hass.data``), and talks to each device's app only through its async update
methods. While it runs, every queued device holds its own automatic firmware
install (``HAUIUpdateController.set_rollout_hold``), so two panels never go
offline at once. It is in memory: a Home Assistant restart or an entry reload
drops it, and an install already transferring finishes on its own.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from ..const import DOMAIN
from ..haui.controller.update import FIRMWARE_INSTALL_TIMEOUT_SECONDS, INSTALL_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)

ROLLOUTS_KEY = f"{DOMAIN}_rollouts"
# How often the rollout reads the installing device's update state.
_POLL_SECONDS = 5.0
# After a firmware install the device checks its display file itself, a minute
# after it reconnects (``on_connect_delay``); the rollout gives it this long
# before it starts the display update itself.
_SETTLE_SECONDS = 120.0
# Slack on top of the update controller's own install timeouts.
_TIMEOUT_SLACK_SECONDS = 120.0

_BUSY_DISPLAY_STATES = ("checking", "installing")


class _InstallFailed(Exception):
    """The current device's update failed; the message says why."""


class UpdateRollout:
    """Install the offered updates of the given devices, one at a time."""

    def __init__(
        self,
        hass: Any,
        entry_id: str,
        *,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        poll_seconds: float | None = None,
        settle_seconds: float = _SETTLE_SECONDS,
    ) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._sleep = sleep
        self._clock = clock
        self._poll = _POLL_SECONDS if poll_seconds is None else poll_seconds
        self._settle = settle_seconds
        self._task: asyncio.Task | None = None
        # Set while async_start awaits the devices, so a second start is refused.
        self._starting = False
        self._id = 0
        self._state = "idle"
        self._started_at: str | None = None
        self._cancelled = False
        self._devices: list[dict[str, Any]] = []

    # public

    def snapshot(self) -> dict[str, Any]:
        """The rollout for the editor: its state and one entry per device."""
        return {
            "id": self._id,
            "state": self._state,
            "started_at": self._started_at,
            "devices": [
                {key: entry[key] for key in ("name", "kind", "state", "error")}
                for entry in self._devices
            ],
        }

    async def async_start(self, devices: list[str]) -> dict[str, Any]:
        """Start a rollout over ``devices``, in that order.

        Raises:
            ValueError: A rollout is running, or a device runs no app.
        """
        if self._state == "running" or self._starting:
            raise ValueError("An update rollout is already running")
        self._starting = True
        try:
            apps = self._apps()
            missing = [name for name in devices if name not in apps]
            if missing:
                raise ValueError(f"No running device {missing[0]!r}")
            entries = []
            for name in devices:
                snapshot = await apps[name].async_update_snapshot()
                kind = "firmware" if snapshot["firmware"]["available"] else "tft"
                entries.append(
                    {"name": name, "kind": kind, "state": "queued", "error": None, "held": False}
                )
            try:
                for entry in entries:
                    await apps[entry["name"]].async_set_rollout_hold(True)
                    entry["held"] = True
            except Exception:
                for entry in entries:
                    await self._release(entry)
                raise
            self._id += 1
            self._devices = entries
            self._cancelled = False
            self._state = "running"
            self._started_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
            self._task = self._hass.async_create_background_task(
                self._async_run(), f"{DOMAIN} update rollout {self._entry_id}"
            )
        finally:
            self._starting = False
        return self.snapshot()

    async def async_cancel(self, device: str | None = None) -> dict[str, Any]:
        """Cancel one queued device, or every queued device when ``device`` is None.

        The device installing goes on: its transfer cannot be stopped.
        """
        for entry in self._devices:
            if entry["state"] == "queued" and device in (None, entry["name"]):
                entry["state"] = "cancelled"
                await self._release(entry)
        if device is None and self._state == "running":
            self._cancelled = True
        return self.snapshot()

    async def async_stop(self) -> None:
        """Stop the rollout (entry unload) and release every device it holds."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        for entry in self._devices:
            await self._release(entry)

    # the run

    async def _async_run(self) -> None:
        stopped = False
        try:
            for entry in self._devices:
                if entry["state"] != "queued":
                    continue
                entry["state"] = "installing"
                try:
                    await self._install(entry)
                except _InstallFailed as exc:
                    entry["state"] = "failed"
                    entry["error"] = str(exc)
                    _LOGGER.warning("Update rollout stopped at %s: %s", entry["name"], exc)
                    stopped = True
                except Exception as exc:
                    # Any other error of the device's app stops the rollout the
                    # same way, instead of leaving it running with nothing to run it.
                    entry["state"] = "failed"
                    entry["error"] = str(exc) or type(exc).__name__
                    _LOGGER.exception("Update rollout stopped at %s", entry["name"])
                    stopped = True
                else:
                    entry["state"] = "done"
                finally:
                    await self._release(entry)
                if stopped:
                    break
        finally:
            for entry in self._devices:
                if entry["state"] in ("queued", "installing"):
                    entry["state"] = "not_started" if entry["state"] == "queued" else "failed"
                    await self._release(entry)
            self._state = "stopped" if stopped else "cancelled" if self._cancelled else "done"

    async def _install(self, entry: dict[str, Any]) -> None:
        app = self._apps().get(entry["name"])
        if app is None:
            raise _InstallFailed("The device is no longer running")
        snapshot = await app.async_update_snapshot()
        if snapshot["firmware"]["available"]:
            result = await app.async_install_firmware(None, None)
            if result.get("firmware_install_error"):
                raise _InstallFailed(result["firmware_install_error"])
            snapshot = await self._wait(
                app,
                lambda s: s["connected"] and not s["firmware"]["installing"],
                FIRMWARE_INSTALL_TIMEOUT_SECONDS + _TIMEOUT_SLACK_SECONDS,
                "The firmware install",
            )
            if snapshot["firmware"]["last_error"]:
                raise _InstallFailed(snapshot["firmware"]["last_error"])
            await self._display_after_firmware(app)
        elif snapshot["display"]["available"]:
            await self._install_display(app)

    async def _display_after_firmware(self, app: Any) -> None:
        """Finish the display file the new firmware needs.

        The device checks it itself a minute after it reconnects and may start
        the upload on its own; the rollout waits for that, and starts the
        upload itself only when the device has not after ``settle_seconds``.
        """
        deadline = self._clock() + self._settle
        # A device that never comes back after its firmware fails the rollout
        # here instead of holding it forever.
        give_up = deadline + INSTALL_TIMEOUT_SECONDS + _TIMEOUT_SLACK_SECONDS
        while True:
            snapshot = await app.async_update_snapshot()
            display = snapshot["display"]
            if display["state"] in _BUSY_DISPLAY_STATES:
                await self._wait_display(app)
                return
            if self._clock() >= give_up:
                raise _InstallFailed("The display update timed out: the device did not report back")
            settled = self._clock() >= deadline
            if display["available"]:
                if settled and snapshot["connected"]:
                    await self._install_display(app)
                    return
            elif display["installed_version"] or settled:
                return
            await self._sleep(self._poll)

    async def _install_display(self, app: Any) -> None:
        result = await app.async_install_tft(None, None)
        if result.get("state") == "error":
            raise _InstallFailed(result.get("last_error") or "The display update did not start")
        await self._wait_display(app)

    async def _wait_display(self, app: Any) -> None:
        snapshot = await self._wait(
            app,
            lambda s: s["connected"] and s["display"]["state"] not in _BUSY_DISPLAY_STATES,
            INSTALL_TIMEOUT_SECONDS + _TIMEOUT_SLACK_SECONDS,
            "The display update",
        )
        if snapshot["display"]["state"] == "error":
            raise _InstallFailed(snapshot["display"]["last_error"] or "The display update failed")

    async def _wait(
        self,
        app: Any,
        finished: Callable[[dict[str, Any]], bool],
        timeout: float,
        what: str,
    ) -> dict[str, Any]:
        """Poll the device's update state until ``finished`` holds."""
        deadline = self._clock() + timeout
        while True:
            await self._sleep(self._poll)
            snapshot = await app.async_update_snapshot()
            if finished(snapshot):
                return snapshot
            if self._clock() >= deadline:
                raise _InstallFailed(f"{what} timed out: the device did not report back")

    # helpers

    def _apps(self) -> dict[str, Any]:
        apps = self._hass.data.get(DOMAIN, {}).get(self._entry_id)
        return apps if isinstance(apps, dict) else {}

    async def _release(self, entry: dict[str, Any]) -> None:
        if not entry["held"]:
            return
        entry["held"] = False
        app = self._apps().get(entry["name"])
        if app is not None:
            await app.async_set_rollout_hold(False)


def async_get_rollout(hass: Any, entry_id: str) -> UpdateRollout:
    """The config entry's rollout, created on first use."""
    rollouts = hass.data.setdefault(ROLLOUTS_KEY, {})
    if entry_id not in rollouts:
        rollouts[entry_id] = UpdateRollout(hass, entry_id)
    return rollouts[entry_id]


def rollout_snapshot(hass: Any, entry_id: str) -> dict[str, Any]:
    """The entry's rollout for the status response; idle when there was none."""
    rollout = hass.data.get(ROLLOUTS_KEY, {}).get(entry_id)
    if rollout is None:
        return {"id": 0, "state": "idle", "started_at": None, "devices": []}
    return rollout.snapshot()


async def async_stop_rollout(hass: Any, entry_id: str) -> None:
    """Stop and forget the entry's rollout (entry unload)."""
    rollout = hass.data.get(ROLLOUTS_KEY, {}).pop(entry_id, None)
    if rollout is not None:
        await rollout.async_stop()

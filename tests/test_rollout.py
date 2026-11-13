"""The hub-side update rollout: one device at a time, stopping at the first failure."""

from __future__ import annotations

import asyncio
import copy

import pytest

from custom_components.nspanel_haui.hub import rollout as rollout_module
from custom_components.nspanel_haui.hub.rollout import (
    ROLLOUTS_KEY,
    UpdateRollout,
    async_get_rollout,
    async_stop_rollout,
)

ENTRY = "entry1"


def _snapshot(
    *,
    connected=True,
    firmware=False,
    firmware_installing=False,
    firmware_error=None,
    tft=False,
    tft_installed="0.5.0",
    tft_state="idle",
    tft_error=None,
):
    return {
        "device": "x",
        "connected": connected,
        "enabled": True,
        "display": {
            "installed_version": tft_installed,
            "available": tft,
            "state": tft_state,
            "last_error": tft_error,
        },
        "firmware": {
            "available": firmware,
            "installing": firmware_installing,
            "last_error": firmware_error,
        },
    }


class _Device:
    """A device app whose update state follows a script.

    ``before`` is what it reports until an install starts; each install swaps
    in the list of snapshots that install goes through, one per poll, the last
    one repeating.
    """

    def __init__(self, log, name, before, firmware_steps=None, tft_steps=None):
        self.log = log
        self.name = name
        self.steps = [before]
        self.firmware_steps = firmware_steps or []
        self.tft_steps = tft_steps or []

    async def async_update_snapshot(self):
        snapshot = self.steps[0]
        if len(self.steps) > 1:
            self.steps.pop(0)
        return copy.deepcopy(snapshot)

    async def async_install_firmware(self, version=None, url=None):
        self.log.append((self.name, "firmware"))
        self.steps = list(self.firmware_steps)
        return {"firmware_install_error": None}

    async def async_install_tft(self, version=None, url=None):
        self.log.append((self.name, "tft"))
        self.steps = list(self.tft_steps)
        return {"state": "installing", "last_error": None}

    async def async_set_rollout_hold(self, hold):
        self.log.append((self.name, "hold" if hold else "release"))


FIRMWARE_OK = [
    _snapshot(firmware=True, firmware_installing=True),
    _snapshot(connected=False, firmware_installing=True),
    _snapshot(),
]
FIRMWARE_FAILS = [
    _snapshot(firmware=True, firmware_installing=True),
    _snapshot(firmware=True, firmware_error="the panel did not reboot"),
]
TFT_OK = [
    _snapshot(tft=True, tft_state="installing"),
    _snapshot(connected=False, tft=True, tft_state="installing"),
    _snapshot(tft_state="done"),
]


class _Hass:
    def __init__(self, apps):
        self.data = {"nspanel_haui": {ENTRY: apps}}

    def async_create_background_task(self, coro, name):
        return asyncio.get_running_loop().create_task(coro)


class _Clock:
    """A clock the rollout's sleeps move forward, so timeouts pass instantly."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds
        await asyncio.sleep(0)


def _rollout(apps):
    clock = _Clock()
    hass = _Hass(apps)
    rollout = UpdateRollout(
        hass, ENTRY, sleep=clock.sleep, clock=clock, poll_seconds=5.0, settle_seconds=60.0
    )
    return rollout, hass


async def _run(rollout, devices):
    await rollout.async_start(devices)
    await rollout._task
    return rollout.snapshot()


def _states(snapshot):
    return {entry["name"]: entry["state"] for entry in snapshot["devices"]}


def test_devices_install_one_at_a_time_in_order():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen", "office"]))

    installs = [entry for entry in log if entry[1] in ("firmware", "tft")]
    assert installs == [("kitchen", "firmware"), ("office", "firmware")]
    assert snapshot["state"] == "done"
    assert _states(snapshot) == {"kitchen": "done", "office": "done"}


def test_firmware_then_tft_on_one_device():
    log = []
    after_firmware = [*FIRMWARE_OK[:-1], _snapshot(tft=True)]
    apps = {"kitchen": _Device(log, "kitchen", _snapshot(firmware=True), after_firmware, TFT_OK)}
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen"]))

    installs = [entry for entry in log if entry[1] in ("firmware", "tft")]
    assert installs == [("kitchen", "firmware"), ("kitchen", "tft")]
    assert _states(snapshot) == {"kitchen": "done"}


def test_tft_the_device_installs_itself_is_waited_for():
    """After the firmware the device's own check may start the TFT: do not start a second."""
    log = []
    after_firmware = [*FIRMWARE_OK[:-1], *TFT_OK]
    apps = {"kitchen": _Device(log, "kitchen", _snapshot(firmware=True), after_firmware)}
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen"]))

    assert [entry for entry in log if entry[1] == "tft"] == []
    assert _states(snapshot) == {"kitchen": "done"}


def test_tft_only_device_installs_its_tft():
    log = []
    apps = {"kitchen": _Device(log, "kitchen", _snapshot(tft=True), tft_steps=TFT_OK)}
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen"]))

    assert [entry for entry in log if entry[1] in ("firmware", "tft")] == [("kitchen", "tft")]
    assert snapshot["devices"][0]["kind"] == "tft"
    assert _states(snapshot) == {"kitchen": "done"}


def test_failure_stops_the_rollout_and_marks_the_rest_not_started():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_FAILS),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen", "office"]))

    assert snapshot["state"] == "stopped"
    assert _states(snapshot) == {"kitchen": "failed", "office": "not_started"}
    assert "did not reboot" in snapshot["devices"][0]["error"]
    assert ("office", "firmware") not in log


def test_offline_device_times_out_and_stops_the_rollout():
    log = []
    gone = [_snapshot(connected=False, firmware_installing=True)]
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), gone),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen", "office"]))

    assert snapshot["state"] == "stopped"
    assert _states(snapshot) == {"kitchen": "failed", "office": "not_started"}
    assert "timed out" in snapshot["devices"][0]["error"]


def test_cancel_one_queued_device():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    async def run():
        await rollout.async_start(["kitchen", "office"])
        await rollout.async_cancel("office")
        await rollout._task
        return rollout.snapshot()

    snapshot = asyncio.run(run())

    assert _states(snapshot) == {"kitchen": "done", "office": "cancelled"}
    assert ("office", "firmware") not in log
    assert snapshot["state"] == "done"


def test_cancel_all_lets_the_current_device_finish():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    async def run():
        await rollout.async_start(["kitchen", "office"])
        await asyncio.sleep(0)
        await rollout.async_cancel()
        await rollout._task
        return rollout.snapshot()

    snapshot = asyncio.run(run())

    assert snapshot["state"] == "cancelled"
    assert _states(snapshot) == {"kitchen": "done", "office": "cancelled"}


def test_holds_are_set_and_released():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_FAILS),
        "hall": _Device(log, "hall", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    asyncio.run(_run(rollout, ["kitchen", "office", "hall"]))

    for name in apps:
        holds = [entry[1] for entry in log if entry[0] == name and entry[1] in ("hold", "release")]
        assert holds == ["hold", "release"], name


def test_second_start_while_running_is_refused():
    log = []
    apps = {"kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK)}
    rollout, _ = _rollout(apps)

    async def run():
        await rollout.async_start(["kitchen"])
        with pytest.raises(ValueError):
            await rollout.async_start(["kitchen"])
        await rollout._task

    asyncio.run(run())


def test_unknown_device_is_refused():
    rollout, _ = _rollout({})

    with pytest.raises(ValueError):
        asyncio.run(rollout.async_start(["ghost"]))


def test_idle_snapshot():
    rollout, _ = _rollout({})

    assert rollout.snapshot() == {"id": 0, "state": "idle", "started_at": None, "devices": []}


def test_registry_creates_one_rollout_per_entry_and_stops_it():
    log = []
    apps = {"kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK)}
    hass = _Hass(apps)

    async def run():
        first = async_get_rollout(hass, ENTRY)
        assert async_get_rollout(hass, ENTRY) is first
        await async_stop_rollout(hass, ENTRY)
        assert ENTRY not in hass.data[ROLLOUTS_KEY]

    asyncio.run(run())


def test_unload_releases_the_holds_of_a_running_rollout(monkeypatch):
    log = []
    gone = [_snapshot(connected=False, firmware_installing=True)]
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), gone),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    hass = _Hass(apps)
    monkeypatch.setattr(rollout_module, "_POLL_SECONDS", 0.001)

    async def run():
        rollout = async_get_rollout(hass, ENTRY)
        await rollout.async_start(["kitchen", "office"])
        await asyncio.sleep(0.01)
        await async_stop_rollout(hass, ENTRY)

    asyncio.run(run())

    assert ("office", "release") in log
    assert ("kitchen", "release") in log


def test_device_that_drops_off_after_the_firmware_times_out():
    """The display step must not wait forever for a device that never comes back."""
    log = []
    gone_after_firmware = [
        *FIRMWARE_OK[:-1],
        _snapshot(tft=True, tft_installed=""),
        _snapshot(connected=False, tft=True, tft_installed=""),
    ]
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), gone_after_firmware),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen", "office"]))

    assert snapshot["state"] == "stopped"
    assert _states(snapshot) == {"kitchen": "failed", "office": "not_started"}
    assert "timed out" in snapshot["devices"][0]["error"]


class _Broken(_Device):
    """A device whose firmware install call raises instead of answering."""

    async def async_install_firmware(self, version=None, url=None):
        raise RuntimeError("worker gone")


def test_an_install_call_that_raises_fails_the_device_and_stops():
    log = []
    apps = {
        "kitchen": _Broken(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    snapshot = asyncio.run(_run(rollout, ["kitchen", "office"]))

    assert snapshot["state"] == "stopped"
    assert _states(snapshot) == {"kitchen": "failed", "office": "not_started"}
    assert "worker gone" in snapshot["devices"][0]["error"]
    assert ("office", "release") in log


class _HoldFails(_Device):
    async def async_set_rollout_hold(self, hold):
        if hold:
            raise RuntimeError("hold refused")
        await super().async_set_rollout_hold(hold)


def test_a_hold_that_fails_leaves_no_running_rollout():
    log = []
    apps = {
        "kitchen": _Device(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK),
        "office": _HoldFails(log, "office", _snapshot(firmware=True), FIRMWARE_OK),
    }
    rollout, _ = _rollout(apps)

    async def run():
        with pytest.raises(RuntimeError):
            await rollout.async_start(["kitchen", "office"])
        assert rollout.snapshot()["state"] != "running"
        assert ("kitchen", "release") in log
        apps["office"] = _Device(log, "office", _snapshot(firmware=True), FIRMWARE_OK)
        await rollout.async_start(["kitchen", "office"])
        await rollout._task
        return rollout.snapshot()

    assert asyncio.run(run())["state"] == "done"


class _Slow(_Device):
    """A device that answers on the next loop turn, as a real app's worker does."""

    async def async_update_snapshot(self):
        await asyncio.sleep(0)
        return await super().async_update_snapshot()


def test_two_starts_at_once_run_one_rollout():
    log = []
    apps = {"kitchen": _Slow(log, "kitchen", _snapshot(firmware=True), FIRMWARE_OK)}
    rollout, _ = _rollout(apps)

    async def run():
        results = await asyncio.gather(
            rollout.async_start(["kitchen"]),
            rollout.async_start(["kitchen"]),
            return_exceptions=True,
        )
        await rollout._task
        return results

    results = asyncio.run(run())

    assert sum(isinstance(result, ValueError) for result in results) == 1
    assert [entry for entry in log if entry[1] == "firmware"] == [("kitchen", "firmware")]

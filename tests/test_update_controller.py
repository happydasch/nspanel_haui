"""Tests for the GitHub release fetch in the update controller."""

import datetime
import hashlib

import pytest
import requests
from nspanel_haui.haui.controller import update
from nspanel_haui.haui.controller.update import HAUIUpdateController


@pytest.fixture(autouse=True)
def _reset_release_cache():
    """Reset the module-level release cache between tests."""
    update._release_cache = None
    yield
    update._release_cache = None


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _controller():
    ctrl = HAUIUpdateController.__new__(HAUIUpdateController)
    ctrl._req_fetch = False
    ctrl._release_infos = []
    ctrl.log = lambda *a, **kw: None
    return ctrl


def test_release_fetch_retries_after_a_failed_request(monkeypatch):
    responses = [
        requests.exceptions.ConnectTimeout("timed out"),
        _Response([{"tag_name": "v0.3.3"}]),
    ]

    def fake_get(url, timeout):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(update.requests, "get", fake_get)
    ctrl = _controller()

    with pytest.raises(RuntimeError):
        ctrl._update_release_infos()
    ctrl._update_release_infos()

    assert ctrl._release_infos == [{"tag_name": "v0.3.3"}]


def test_release_fetch_uses_the_shared_cache(monkeypatch):
    """Consecutive controllers share one GitHub request within the TTL."""
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _Response([{"tag_name": "v0.3.3"}])

    monkeypatch.setattr(update.requests, "get", fake_get)

    first = _controller()
    first._update_release_infos()
    second = _controller()
    second._update_release_infos()

    assert len(calls) == 1
    assert second._release_infos == [{"tag_name": "v0.3.3"}]


def test_release_fetch_bypasses_the_cache_when_forced(monkeypatch):
    """force=True refreshes even when a fresh cache entry exists."""
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _Response([{"tag_name": "v0.3.3"}])

    monkeypatch.setattr(update.requests, "get", fake_get)

    first = _controller()
    first._update_release_infos()
    second = _controller()
    second._update_release_infos(force=True)

    assert len(calls) == 2


def test_manual_check_clears_failure_state(monkeypatch):
    """A manual check resets error/install guards before evaluating."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.1",
    )
    ctrl._update_state = update.UPDATE_STATE_ERROR
    ctrl._last_install_at = datetime.datetime.now(tz=datetime.UTC)
    ctrl._last_install_confirmed = False

    ctrl.manual_check_for_update()

    assert ctrl._update_state == update.UPDATE_STATE_IDLE
    assert ctrl._last_install_at is None
    # The check's TFT evaluation then confirms the TFT the firmware needs.
    assert ctrl._last_install_confirmed is True


# --- automatic TFT update ----------------------------------------------------

import types  # noqa: E402

from nspanel_haui.haui.mapping.const import (  # noqa: E402
    DEFAULT_CONFIG,
    ESPAction,
    ESPResponse,
    SysPanelKey,
)


def _release(tag, with_tft=True, with_portrait=False):
    assets = [{"name": "nspanel_haui.tft", "browser_download_url": f"https://dl/{tag}.tft"}]
    if with_portrait:
        assets.append(
            {
                "name": "nspanel_haui_portrait.tft",
                "browser_download_url": f"https://dl/{tag}_portrait.tft",
            }
        )
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "",
        "assets": assets if with_tft else [],
    }


class _App:
    hass = None

    def log(self, msg: str, **kwargs) -> None:
        pass

    def __init__(self, device_info, connected=True, display_model="eu"):
        self.events: list = []
        self.device = types.SimpleNamespace(
            device_info=device_info,
            connected=connected,
            display_model=display_model,
            get_name=lambda: "kitchen",
            get=lambda key, default=None: 0,
            set_device_info=lambda info, append=True: self.device.__dict__.update(
                {"device_info": {**self.device.device_info, **info}}
            ),
        )
        self.published: list = []
        self.requests: list = []
        self.opened: list = []
        self.timers: dict = {}
        esphome = types.SimpleNamespace(
            publish=lambda action, value: self.published.append((action, value)) or True,
            send_cmd=lambda cmd, value="", force=False: self.requests.append(
                (cmd, value, force)
            ),
        )
        navigation = types.SimpleNamespace(
            open_panel=lambda key, **kw: self.opened.append((key, kw)), close_panel=lambda: None
        )
        self.controller = {
            "esphome": types.SimpleNamespace(
                esphome=esphome,
                send_cmd=lambda cmd, value="", force=False: self.requests.append(
                    (cmd, value, force)
                ),
            ),
            "navigation": navigation,
        }

    def fire_event(self, event_type, data=None):
        self.events.append((event_type, data))

    def run_in(self, callback, delay):
        handle = f"timer{len(self.timers)}"
        self.timers[handle] = (callback, delay)
        return handle

    def run_every(self, callback, start, interval):
        return self.run_in(callback, interval)

    def cancel_timer(self, handle):
        self.timers.pop(handle, None)


def _manifest(version, path=None):
    """A firmware manifest in the schema the release workflow writes."""
    return {
        "name": "NSPanel HAUI",
        "version": version,
        "variant": "universal",
        "builds": [
            {"ota": {"path": path or f"https://dl/fw/{version}/ota.bin", "md5": f"md5-{version}"}}
        ],
    }


def _updater(
    monkeypatch,
    device_info,
    releases=(),
    connected=True,
    display_model="eu",
    manifest=None,
    downloads=None,
    **config,
):
    """An updater whose GitHub API, firmware manifests and downloads are faked.

    ``manifest`` is served at the configured ``firmware_manifest_url`` — a
    version string or a raw manifest; without it that URL serves no manifest.
    ``fetches`` records the GitHub release list requests only.  The device
    reports the universal build variant by default (override with
    ``firmware_variant`` in ``device_info``; pass ``""`` for no variant).
    """
    merged_info = {"firmware_variant": "universal", **device_info}
    app = _App(merged_info, connected, display_model)
    config = {**DEFAULT_CONFIG["update"], **config}
    ctrl = HAUIUpdateController(app, config)
    ctrl.log = lambda *a, **kw: None
    ctrl.translate = lambda text: text
    ctrl.get_color = lambda key: 0
    fetches: list = []
    served = {"manifest": manifest, "release_manifests": {}}

    def fake_get(url, timeout, stream=False):
        if url == config["firmware_manifest_url"]:
            current = served["manifest"]
            if isinstance(current, Exception):
                raise current
            if isinstance(current, str):
                current = _manifest(current)
            return _Response(current or {})
        if url.endswith("/manifest.json"):  # a release's manifest, see _firmware_release
            tag = url.split("/")[-2]
            current = served["release_manifests"].get(tag, _manifest(tag, f"https://dl/{tag}/ota.bin"))
            if isinstance(current, Exception):
                raise current
            return _Response(current)
        if downloads and url in downloads:
            return _Download(downloads[url])
        fetches.append(url)
        return _Response(list(releases))

    monkeypatch.setattr(update.requests, "get", fake_get)
    app.served = served
    return ctrl, app, fetches


def _fire_timers(app):
    for callback, _delay in list(app.timers.values()):
        callback({})


def test_connect_schedules_the_tft_check_with_default_settings(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.4.0"})

    ctrl.on_connection_changed(True)

    delays = [delay for _cb, delay in app.timers.values()]
    assert delays == [DEFAULT_CONFIG["update"]["on_connect_delay"]]


def test_disconnect_cancels_the_pending_tft_check(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"})

    ctrl.on_connection_changed(True)
    ctrl.on_connection_changed(False)

    assert app.timers == {}


def test_outdated_tft_installs_the_version_the_firmware_needs(monkeypatch):
    releases = [_release("0.5.0"), _release("0.4.0"), _release("0.3.3")]
    ctrl, app, fetches = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, releases
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert fetches  # release list fetched before installing
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]


def test_outdated_tft_without_auto_install_asks_and_installs_on_confirm(monkeypatch):
    releases = [_release("0.5.0"), _release("0.4.0")]
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, releases, auto_install=False
    )

    ctrl.check_installed_version()

    assert app.published == []
    ((key, kwargs),) = app.opened
    assert key == SysPanelKey.POPUP_NOTIFY
    kwargs["button_callback_fnc"](False, True)
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]


def test_current_tft_needs_no_update(monkeypatch):
    ctrl, app, fetches = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.4.0"})

    ctrl.check_installed_version()

    assert (app.published, app.opened, fetches) == ([], [], [])


def test_missing_release_for_the_required_version_installs_nothing(monkeypatch):
    releases = [_release("0.5.0"), _release("0.4.0", with_tft=False)]
    versions = {"yaml_version": "0.4.0", "tft_version": "0.3.3"}
    ctrl, app, _ = _updater(monkeypatch, versions, releases)

    ctrl.check_installed_version()

    assert app.published == []


def test_no_check_while_disconnected(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        [_release("0.4.0")],
        connected=False,
    )

    ctrl.check_installed_version()

    assert (app.published, app.opened, fetches) == ([], [], [])


def test_new_release_check_only_notifies(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.4.0"}, [_release("0.5.0")]
    )

    ctrl.check_for_update()

    assert app.published == []
    ((key, kwargs),) = app.opened
    assert key == SysPanelKey.POPUP_NOTIFY
    assert "button_callback_fnc" not in kwargs


def test_tft_install_reports_state_transitions(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    result = ctrl.install_tft("0.4.0")

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]
    state = ctrl.get_update_state()
    assert state["state"] == "installing"
    assert state["version"] == "0.4.0"
    assert state["started_at"] is not None
    assert state["last_error"] is None
    # install_tft reports the state back so the editor can show the real outcome
    assert result == state


def test_tft_install_defaults_to_the_firmwares_yaml_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    result = ctrl.install_tft()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]
    assert ctrl.get_update_state()["version"] == "0.4.0"
    assert result["state"] == "installing"


def test_manual_tft_install_refreshes_stale_release_cache(monkeypatch):
    """The install action must see the TFT release matching freshly updated firmware."""
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": ""},
        [_release("0.4.2")],
    )
    update._release_cache = (update.time.monotonic(), [_release("0.4.1")])

    result = ctrl.install_tft()

    assert fetches == [HAUIUpdateController.RELEASES_URL]
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.2.tft")]
    assert result["state"] == "installing"


def test_auto_tft_install_refetches_a_cache_older_than_the_firmware(monkeypatch):
    """A firmware install skips the release fetch, so the cache can predate it.

    The TFT check after the firmware reboot must not fail with "no GitHub
    release" while the release exists.
    """
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        [_release("0.4.2"), _release("0.4.1")],
    )
    update._release_cache = (update.time.monotonic(), [_release("0.4.1")])

    ctrl.check_installed_version()

    assert fetches == [HAUIUpdateController.RELEASES_URL]
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.2.tft")]
    assert ctrl.get_update_state()["state"] == "installing"


def test_tft_install_without_release_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [])

    result = ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "No GitHub release" in (state["last_error"] or "")
    assert result == state


def test_tft_install_while_disconnected_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, connected=False
    )

    result = ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert state["last_error"] == "device disconnected"
    assert result == state


def test_tft_install_marks_done_when_the_display_reports_the_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    # The display reboots into the new TFT and reports the version with its
    # device state; the controller marks the install done.
    app.device.device_info = {**app.device.device_info, "tft_version": "0.4.0"}
    event = types.SimpleNamespace(
        name=ESPResponse.RES_DEVICE_STATE, as_json=lambda: app.device.device_info
    )
    ctrl.process_event(event)

    assert ctrl.get_update_state()["state"] == "done"


def test_tft_install_state_kept_while_disconnected_because_upload_reboots(monkeypatch):
    """A disconnect during an install is the upload's reboot, not a failure.

    The install confirmation happens after the device reconnects; resetting the
    state on disconnect would report a successful-sounding ``idle`` while the
    TFT was in fact still being installed (and later reinstalled after boot).
    """
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    ctrl.on_connection_changed(False)

    state = ctrl.get_update_state()
    assert state["state"] == "installing"
    assert state["last_error"] is None


# --- display model: which release asset ---------------------------------------


def test_portrait_model_installs_the_portrait_asset(monkeypatch):
    """A ``display_model: us`` device gets ``nspanel_haui_portrait.tft`` from the release."""
    releases = [_release("0.4.0", with_portrait=True)]
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        releases,
        display_model="us",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0_portrait.tft")]


def test_landscape_model_keeps_the_landscape_asset(monkeypatch):
    releases = [_release("0.4.0", with_portrait=True)]
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, releases
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]


def test_explicit_tft_filename_overrides_the_display_model(monkeypatch):
    ctrl, _, _ = _updater(monkeypatch, {}, display_model="us", tft_filename="custom.tft")
    assert ctrl._get_tft_filename() == "custom.tft"

    ctrl, _, _ = _updater(monkeypatch, {}, display_model="us")
    assert ctrl._get_tft_filename() == "nspanel_haui_portrait.tft"


def test_release_without_the_portrait_asset_names_the_missing_file(monkeypatch):
    """A release that only ships the landscape TFT must not install it on a portrait device."""
    releases = [_release("0.4.0")]
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        releases,
        display_model="us",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == update.UPDATE_STATE_ERROR
    assert "nspanel_haui_portrait.tft" in state["last_error"]


# --- TFT auto-update loop (#63): empty boot snapshots must not reinstall ------


def _fire_timer(app, delay):
    """Fire every pending timer with the given delay (in seconds).

    The fired handles are popped so a consumed timer cannot fire again (the
    fake ``run_in`` leaves handles in the dict; real HA removes them on fire).
    """
    for handle, (callback, d) in list(app.timers.items()):
        if d == delay:
            app.timers.pop(handle, None)
            callback({})


def _device_state(**state):
    return types.SimpleNamespace(name=ESPResponse.RES_DEVICE_STATE, as_json=lambda: state)


def test_empty_tft_version_triggers_a_state_refresh_not_an_install(monkeypatch):
    """The handshake reads tft_version before the display answers.

    The empty snapshot must not be compared as 0.0.0 (which reinstalled the
    TFT after every reboot) — the device is asked to re-read it instead.
    """
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": ""})

    ctrl.check_installed_version()

    assert app.requests == [("esphome.req_device_state", "", True)]
    assert app.published == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_refresh_response_with_the_matching_version_confirms_the_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    # The device republishes the state once the display reported the version.
    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version="0.4.0"))

    assert ctrl.get_update_state()["state"] == "done"
    assert ctrl._last_install_confirmed is True
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]


def test_refresh_timeout_with_empty_version_installs_nothing(monkeypatch):
    """A lost device-state answer is fail-safe: no install from an unknown version."""
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": ""})

    ctrl.check_installed_version()
    _fire_timer(app, update.DEVICE_STATE_REFRESH_SECONDS)  # the response never came

    assert app.published == []
    assert app.opened == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_successful_empty_refresh_installs_the_missing_tft_once(monkeypatch):
    """A first install still happens — but only after the refresh answered."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": ""}, [_release("0.4.0")]
    )

    ctrl.check_installed_version()
    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version=""))

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]


def test_unconfirmed_recent_install_is_not_auto_retried(monkeypatch):
    """An upload that never gets confirmed must not be fired again automatically."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    app.published.clear()
    ctrl.check_installed_version()

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "not confirmed" in state["last_error"]


def test_publish_failure_marks_the_install_as_failed(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )
    app.controller["esphome"].esphome.publish = lambda action, value: False

    result = ctrl.install_tft("0.4.0")

    assert result["state"] == "error"
    assert "could not send" in (result["last_error"] or "").lower()
    assert ctrl._last_install_at is None
    assert ctrl._last_install_confirmed is False


def test_invalid_yaml_version_is_an_error_not_a_0_0_0_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "not-a-version", "tft_version": "0.4.0"}
    )

    ctrl.check_installed_version()

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "invalid yaml_version" in state["last_error"]


def test_check_for_update_survives_a_github_failure(monkeypatch):
    def raise_timeout(url, timeout):
        raise requests.exceptions.ConnectTimeout("no route to host")

    monkeypatch.setattr(update.requests, "get", raise_timeout)
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.4.0"})

    ctrl.check_for_update()  # must not raise

    assert app.opened == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_reconnect_verification_times_out_into_an_error(monkeypatch):
    """The upload ends in a reboot: a bounded verification window owns the outcome."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    ctrl.on_connection_changed(False)  # the upload rebooted the device
    app.published.clear()
    app.requests.clear()
    # The post-reboot handshake knows nothing about the TFT yet.
    app.device.device_info = {"yaml_version": "0.4.0", "tft_version": ""}
    ctrl.on_connection_changed(True)  # the device reconnected
    app.requests.clear()

    empty = _device_state(yaml_version="0.4.0", tft_version="")
    for _ in range(2):
        ctrl.process_event(empty)
        _fire_timer(app, update.VERIFY_REFRESH_SECONDS)
        assert ctrl.get_update_state()["state"] == "installing"
    # ... refresh budget exhausted: the window reports the failed install
    _fire_timer(app, update.VERIFY_REFRESH_SECONDS)

    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "not confirmed" in state["last_error"]


def test_reconnect_verification_confirms_a_matching_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    ctrl.on_connection_changed(False)
    ctrl.on_connection_changed(True)

    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version="0.4.0"))

    state = ctrl.get_update_state()
    assert state["state"] == "done"
    assert ctrl._last_install_confirmed is True


# --- manual update check -----------------------------------------------------


def test_manual_check_reports_an_up_to_date_panel(monkeypatch):
    """The editor needs an answer even when nothing is newer."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, [_release("0.4.2")]
    )

    result = ctrl.manual_check_for_update()

    assert result["latest_release"] == "0.4.2"
    assert result["check_error"] is None
    assert result["state"] == "idle"
    assert app.published == []


def test_manual_check_installs_an_outdated_tft(monkeypatch):
    """Without it an outdated TFT installed only after the next reconnect."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.1"}, [_release("0.4.2")]
    )

    result = ctrl.manual_check_for_update()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.2.tft")]
    assert result["state"] == "installing"
    assert result["version"] == "0.4.2"


def test_manual_check_during_an_install_starts_no_second_upload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.1"}, [_release("0.4.2")]
    )
    ctrl.install_tft()
    app.published.clear()

    result = ctrl.manual_check_for_update()

    assert app.published == []
    assert result["state"] == "installing"


def test_manual_check_reports_a_github_failure(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})

    def failing_get(url, timeout):
        raise requests.exceptions.ConnectTimeout("timed out")

    monkeypatch.setattr(update.requests, "get", failing_get)

    result = ctrl.manual_check_for_update()

    assert "timed out" in result["check_error"]
    assert result["latest_release"] is None


def test_manual_check_while_disconnected_reports_it(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, connected=False
    )

    result = ctrl.manual_check_for_update()

    assert result["check_error"] == "device disconnected"
    assert fetches == []


# --- TFT install from a URL --------------------------------------------------

DEV_TFT_URL = "http://homeassistant.local:8123/local/nspanel/nspanel_haui.tft"


def test_url_install_sends_the_url_without_a_release_lookup(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, [_release("0.4.2")]
    )
    ctrl._update_version = "0.4.2"  # left over from an earlier release install

    state = ctrl.install_tft_url(DEV_TFT_URL)

    assert fetches == []
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, DEV_TFT_URL)]
    assert state["state"] == "installing"
    assert state["version"] is None


def test_url_install_while_disconnected_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, connected=False
    )

    state = ctrl.install_tft_url(DEV_TFT_URL)

    assert app.published == []
    assert state["state"] == "error"


def test_url_install_is_not_done_before_the_upload_reboot(monkeypatch):
    """A device-state answer before the reboot reports the old TFT."""
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})

    ctrl.install_tft_url(DEV_TFT_URL)
    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.2"))

    assert ctrl.get_update_state()["state"] == "installing"


def test_url_install_is_done_once_the_display_reports_after_the_reboot(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})

    ctrl.install_tft_url(DEV_TFT_URL)
    ctrl.on_connection_changed(False)  # the upload rebooted the device
    app.device.device_info = {"yaml_version": "0.4.2", "tft_version": ""}
    ctrl.on_connection_changed(True)
    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.2"))

    assert ctrl.get_update_state()["state"] == "done"


def _reboot_with(ctrl, app, **state):
    """The upload ends in a reboot; the display then reports ``state``."""
    ctrl.on_connection_changed(False)
    app.device.device_info = {**state, "tft_version": ""}
    ctrl.on_connection_changed(True)
    ctrl.process_event(_device_state(**state))


def test_older_release_install_is_kept_after_its_reboot(monkeypatch):
    """The automatic check must not replace a TFT the user installed by hand."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.2"), _release("0.4.1")],
    )

    ctrl.install_tft("0.4.1")
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.1.tft")]
    _reboot_with(ctrl, app, yaml_version="0.4.2", tft_version="0.4.1")
    assert ctrl.get_update_state()["state"] == "done"
    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.1.tft")]


def test_url_install_is_kept_after_its_reboot(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, [_release("0.4.2")]
    )

    ctrl.install_tft_url(DEV_TFT_URL)
    _reboot_with(ctrl, app, yaml_version="0.4.2", tft_version="0.4.0")
    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, DEV_TFT_URL)]


def test_a_new_firmware_version_replaces_a_kept_tft(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.3"), _release("0.4.2"), _release("0.4.1")],
    )
    ctrl.install_tft("0.4.1")
    _reboot_with(ctrl, app, yaml_version="0.4.2", tft_version="0.4.1")

    # The firmware updates to 0.4.3: the TFT has to follow it again.
    _reboot_with(ctrl, app, yaml_version="0.4.3", tft_version="0.4.1")
    ctrl.check_installed_version()

    assert app.published[-1] == (ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.3.tft")


def test_installing_the_required_release_ends_keeping_an_older_one(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.2"), _release("0.4.1")],
    )
    ctrl.install_tft("0.4.1")
    ctrl.install_tft()

    assert ctrl._manual_tft_firmware is None


def test_release_list_holds_only_releases_with_this_devices_tft(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.1"), _release("0.4.2"), _release("0.3.0", with_tft=False), _release("x")],
    )

    result = ctrl.list_tft_releases()

    assert result == {"releases": ["0.4.2", "0.4.1"], "required": "0.4.2", "error": None}


def test_release_list_reports_a_github_failure(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})

    def failing_get(url, timeout):
        raise requests.exceptions.ConnectTimeout("timed out")

    monkeypatch.setattr(update.requests, "get", failing_get)

    result = ctrl.list_tft_releases()

    assert result["releases"] == []
    assert "timed out" in result["error"]


# --- HAUI Display update entity events ---------------------------------------


def _display_events(app):
    return [data for event_type, data in app.events if event_type == update.DISPLAY_UPDATE_EVENT]


def test_device_state_publishes_the_display_versions(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": ""})

    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.1"))

    assert _display_events(app)[-1] == {
        "device": "kitchen",
        "connected": True,
        "installed_version": "0.4.1",
        "latest_version": "0.4.2",
        "state": "idle",
        "last_error": None,
    }


def test_unknown_tft_version_is_published_as_none(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": ""})

    ctrl.on_connection_changed(True)

    data = _display_events(app)[-1]
    assert data["installed_version"] is None
    assert data["latest_version"] == "0.4.2"


def test_install_state_changes_are_published(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.1"}, [_release("0.4.2")]
    )

    ctrl.install_tft()

    states = [data["state"] for data in _display_events(app)]
    assert states[-2:] == ["checking", "installing"]


# --- firmware manifest -------------------------------------------------------


def _firmware_events(app):
    return [data for event_type, data in app.events if event_type == update.FIRMWARE_UPDATE_EVENT]


def test_the_manifest_offers_a_newer_firmware(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.3",
        firmware_auto_update=False,
    )

    ctrl.check_for_update()

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is True
    assert state["firmware_update_version"] == "0.4.3"
    assert _firmware_events(app)[0] == {
        "device": "kitchen",
        "connected": True,
        "installed_version": "0.4.2",
        "latest_version": "0.4.3",
        "installing": False,
    }


@pytest.mark.parametrize("installed", ["0.4.3", "0.4.4-dev1"])
def test_the_manifest_offers_no_older_or_same_firmware(monkeypatch, installed):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": installed, "tft_version": installed},
        manifest="0.4.3",
        firmware_auto_update=False,
    )

    ctrl.check_for_update()

    assert ctrl.get_update_state()["firmware_update_available"] is False


def test_a_test_release_manifest_offers_the_next_test_build(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4-dev1", "tft_version": "0.4.3"},
        manifest="0.4.4-dev2",
        firmware_manifest_url="http://ha.local/local/nspanel/firmware-manifest.json",
        firmware_auto_update=False,
    )

    ctrl.check_for_update()

    assert ctrl.get_update_state()["firmware_update_available"] is True


def test_an_unreadable_manifest_drops_the_last_offer(monkeypatch):
    """After a URL change the old manifest would offer the wrong firmware."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.3",
        firmware_auto_update=False,
    )
    ctrl.check_for_update()
    app.served["manifest"] = requests.exceptions.ConnectTimeout("timed out")

    ctrl.check_for_update()

    assert ctrl.get_update_state()["firmware_update_available"] is False
    assert _firmware_events(app)[-1]["latest_version"] is None


def test_a_relative_image_path_resolves_against_the_manifest_url(monkeypatch):
    url = "http://ha.local/local/nspanel/firmware-manifest.json"
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest=_manifest("0.4.3", "nspanel_haui_ota.bin"),
        firmware_manifest_url=url,
    )

    ctrl.install_firmware()

    assert app.published[0][1]["url"] == "http://ha.local/local/nspanel/nspanel_haui_ota.bin"


def test_start_reads_the_manifest_and_a_changed_url_reads_it_again(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, manifest="0.4.3"
    )

    ctrl.start_part()
    ctrl.stop_part()
    ctrl.start_part()  # a config reload with the same URL
    assert len(_firmware_events(app)) == 1
    assert _firmware_events(app)[0]["latest_version"] == "0.4.3"

    ctrl.stop_part()
    ctrl.config = {**ctrl.config, "firmware_manifest_url": "http://ha.local/none.json"}
    ctrl.start_part()

    assert _firmware_events(app)[-1]["latest_version"] is None


def test_custom_device_is_never_offered_the_universal_manifest(monkeypatch):
    """A custom install.yaml build must not see the public universal image as an update."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": "custom"},
        manifest="0.4.4",
    )

    ctrl.check_for_update()

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is False
    assert state["firmware_update_version"] is None
    assert _firmware_events(app)[-1]["latest_version"] is None


def test_custom_device_manual_install_of_the_offered_manifest_is_refused(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": "custom"},
        manifest="0.4.4",
    )

    state = ctrl.install_firmware()

    assert app.published == []
    assert "custom" in state["firmware_install_error"]
    assert "universal" in state["firmware_install_error"]


def test_device_without_a_reported_variant_fails_closed(monkeypatch):
    """Pre-0.4.4 firmware reports no variant: never flash it the universal image."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": ""},
        manifest="0.4.4",
    )

    ctrl.check_for_update()

    assert ctrl.get_update_state()["firmware_update_available"] is False
    state = ctrl.install_firmware()
    assert app.published == []
    assert "does not report its build variant" in state["firmware_install_error"]


def test_a_manifest_without_a_variant_fails_closed(monkeypatch):
    manifest = {k: v for k, v in _manifest("0.4.4").items() if k != "variant"}
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3"},
        manifest=manifest,
    )

    ctrl.check_for_update()

    assert ctrl.get_update_state()["firmware_update_available"] is False
    state = ctrl.install_firmware()
    assert app.published == []
    assert "names no build variant" in state["firmware_install_error"]


def test_custom_device_release_install_refused_and_url_install_allowed(monkeypatch):
    """The editor picker release path fails closed; an explicit URL still installs."""
    url = "http://ha.local/firmware.ota.bin"
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": "custom"},
        [_firmware_release("v0.4.4")],
        downloads={url: OTA_IMAGE},
    )

    state = ctrl.install_firmware("v0.4.4")

    assert app.published == []
    assert "not interchangeable" in state["firmware_install_error"]

    state = ctrl.install_firmware(url=url)
    md5 = hashlib.md5(OTA_IMAGE, usedforsecurity=False).hexdigest()
    assert app.published == [(ESPAction.INSTALL_FIRMWARE_URL, {"url": url, "md5sum": md5})]
    assert state["firmware_install_error"] is None


def test_firmware_release_list_filters_by_variant(monkeypatch):
    """A custom panel's picker lists no universal releases (From URL stays available)."""
    release = _firmware_release("v0.4.4")
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": "custom"},
        [release],
    )

    assert ctrl.list_firmware_releases() == {"releases": [], "error": None}


def test_firmware_release_list_skips_unreadable_manifests(monkeypatch):
    """A release whose manifest cannot be read is dropped, not offered by guess."""
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")])
    app.served["release_manifests"]["v0.4.2"] = requests.exceptions.ConnectTimeout(
        "timed out"
    )

    assert ctrl.list_firmware_releases() == {"releases": [], "error": None}


def test_firmware_release_list_matches_a_custom_manifest_variant(monkeypatch):
    """A test release built for the custom variant is offered to a custom panel."""
    release = _firmware_release("v0.4.4")
    custom_manifest = {**_manifest("0.4.4", "https://dl/v0.4.4/custom.bin"), "variant": "custom"}
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3", "firmware_variant": "custom"},
        [release],
    )
    app.served["release_manifests"]["v0.4.4"] = custom_manifest

    assert ctrl.list_firmware_releases() == {"releases": ["v0.4.4"], "error": None}

    state = ctrl.install_firmware("v0.4.4")
    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/v0.4.4/custom.bin", "md5sum": "md5-0.4.4"},
        )
    ]
    assert state["firmware_install_error"] is None


# --- automatic firmware update -----------------------------------------------# --- automatic firmware update -----------------------------------------------


def test_check_for_update_installs_the_offered_firmware_first(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        [_release("0.4.3")],
        manifest="0.4.3",
        firmware_auto_update=True,
    )

    ctrl.check_for_update()

    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/fw/0.4.3/ota.bin", "md5sum": "md5-0.4.3"},
        )
    ]
    assert fetches == []  # the TFT follows after the reboot
    ((key, kwargs),) = app.opened
    assert key == SysPanelKey.POPUP_NOTIFY
    assert "Firmware update" in kwargs["title"]
    assert ctrl._firmware_installing is True
    assert ctrl._manual_firmware is False
    assert _firmware_events(app)[-1]["installing"] is True


def test_check_for_update_only_notifies_without_a_firmware_update(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.1",
    )

    ctrl.check_for_update()

    assert app.published == []
    ((key, kwargs),) = app.opened
    assert key == SysPanelKey.POPUP_NOTIFY
    assert "Update available" in kwargs["title"]


def test_on_connect_installs_firmware_before_checking_for_a_tft_upload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        [_release("0.4.2"), _release("0.4.3")],
        manifest="0.4.3",
        firmware_auto_update=True,
    )

    ctrl._timer_delay_callback({})

    ((action, _value),) = app.published
    assert action == ESPAction.INSTALL_FIRMWARE_URL
    assert ctrl._firmware_installing is True


def test_firmware_install_due_when_the_manifest_offers_an_update(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
        firmware_auto_update=True,
    )
    ctrl._refresh_firmware_manifest()

    assert ctrl._firmware_install_due() is True


def test_firmware_install_not_due_without_a_manifest(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"})
    ctrl._refresh_firmware_manifest()

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_by_default(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl._refresh_firmware_manifest()

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_when_disabled(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
        firmware_auto_update=False,
    )
    ctrl._refresh_firmware_manifest()

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_during_a_tft_upload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    ctrl._refresh_firmware_manifest()
    ctrl._set_update_state(update.UPDATE_STATE_INSTALLING, version="0.4.1")

    assert ctrl._firmware_install_due() is False


def test_firmware_install_respects_the_retry_cooldown(monkeypatch):
    """A failed attempt (the panel rebooted into its old firmware) waits an hour."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    ctrl._refresh_firmware_manifest()
    ctrl._firmware_install_at = datetime.datetime.now(tz=datetime.UTC)

    assert ctrl._firmware_install_due() is False


# --- manual firmware install -------------------------------------------------

OTA_IMAGE = bytes([update.ESP_IMAGE_MAGIC]) + b"app image"
FACTORY_IMAGE = b"\xff" * 16


def _firmware_release(tag):
    base = f"https://dl/{tag}"
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "",
        "assets": [
            {"name": "nspanel_haui.bin", "browser_download_url": f"{base}/factory.bin"},
            {"name": "nspanel_haui_ota.bin", "browser_download_url": f"{base}/ota.bin"},
            {"name": "firmware-manifest.json", "browser_download_url": f"{base}/manifest.json"},
        ],
    }


class _Download:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]


def _firmware_updater(monkeypatch, releases=(), **kwargs):
    """An updater for a panel on firmware 0.4.3."""
    device_info = {"yaml_version": "0.4.3", "tft_version": "0.4.3"}
    return _updater(monkeypatch, device_info, releases, **kwargs)


def test_manual_install_installs_the_offered_update_with_auto_update_off(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4", firmware_auto_update=False)

    state = ctrl.install_firmware()

    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/fw/0.4.4/ota.bin", "md5sum": "md5-0.4.4"},
        )
    ]
    assert state["firmware_installing"] is True
    assert state["firmware_update_version"] == "0.4.4"
    assert state["firmware_install_error"] is None


def test_manual_install_without_an_update_reports_it(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.3")

    state = ctrl.install_firmware()

    assert app.published == []
    assert state["firmware_install_error"] == "No firmware update is available"


def test_manual_install_with_an_unreadable_manifest_names_its_url(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch)

    state = ctrl.install_firmware()

    assert app.published == []
    assert DEFAULT_CONFIG["update"]["firmware_manifest_url"] in state["firmware_install_error"]


def test_installing_the_manifest_version_uses_the_manifest(monkeypatch):
    """A test release is no GitHub release; its version installs from the manifest."""
    ctrl, app, fetches = _firmware_updater(
        monkeypatch,
        manifest="0.4.4-dev1",
        firmware_manifest_url="http://ha.local/local/nspanel/firmware-manifest.json",
    )

    ctrl.install_firmware("0.4.4-dev1")

    assert app.published[0][1]["url"] == "https://dl/fw/0.4.4-dev1/ota.bin"
    assert fetches == []
    assert ctrl._manual_firmware is False


def test_firmware_release_list_holds_only_over_the_air_releases(monkeypatch):
    older = _release("0.4.1")  # factory image only: never offered over the air
    older["assets"].append({"name": "nspanel_haui.bin", "browser_download_url": "x"})
    ctrl, app, _ = _firmware_updater(
        monkeypatch, [_firmware_release("v0.4.2"), older, _firmware_release("v0.4.3")]
    )

    assert ctrl.list_firmware_releases() == {"releases": ["v0.4.3", "v0.4.2"], "error": None}


def test_firmware_release_install_flashes_the_release_manifest_image(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")

    state = ctrl.install_firmware("v0.4.2")

    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/v0.4.2/ota.bin", "md5sum": "md5-v0.4.2"},
        )
    ]
    assert state["firmware_installing"] is True
    assert state["firmware_install_error"] is None


def test_firmware_release_without_ota_image_is_refused(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, [_release("0.4.1")])

    state = ctrl.install_firmware("0.4.1")

    assert app.published == []
    assert "ships no over-the-air firmware" in state["firmware_install_error"]


def test_firmware_url_install_sends_the_md5_of_the_image(monkeypatch):
    url = "http://ha.local/firmware.ota.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: OTA_IMAGE})

    ctrl.install_firmware(url=url)

    md5 = hashlib.md5(OTA_IMAGE, usedforsecurity=False).hexdigest()
    assert app.published == [(ESPAction.INSTALL_FIRMWARE_URL, {"url": url, "md5sum": md5})]


@pytest.mark.parametrize(
    ("image", "error"),
    [
        pytest.param(FACTORY_IMAGE, "not the factory image", id="factory-image"),
        pytest.param(OTA_IMAGE + b"\0" * update.FIRMWARE_MAX_BYTES, "app partition", id="too-big"),
    ],
)
def test_firmware_url_install_refuses_an_unusable_image(monkeypatch, image, error):
    url = "http://ha.local/firmware.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: image})

    state = ctrl.install_firmware(url=url)

    assert app.published == []
    assert error in state["firmware_install_error"]


def test_firmware_without_the_install_action_reports_it(monkeypatch):
    """Firmware 0.4.2 has no install_firmware_url action: the hub cannot update it."""
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    app.controller["esphome"].esphome.publish = lambda action, value: False

    state = ctrl.install_firmware()

    assert "install_firmware_url action" in state["firmware_install_error"]
    assert state["firmware_installing"] is False


def test_hand_installed_firmware_pauses_the_automatic_update(monkeypatch):
    """Otherwise the next check reinstalls the latest release over it."""
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")
    ctrl.install_firmware("v0.4.2")
    ctrl.app.device.device_info["yaml_version"] = "0.4.2"
    ctrl.on_connection_changed(False)
    ctrl.on_connection_changed(True)  # rebooted into 0.4.2; the manifest offers 0.4.3
    ctrl._firmware_install_at = None  # past the retry cooldown

    ctrl.check_for_update()

    assert len(app.published) == 1
    assert ctrl._firmware_install_due() is False


def test_installing_the_offered_firmware_ends_the_pause(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")
    ctrl.install_firmware("v0.4.2")
    ctrl.app.device.device_info["yaml_version"] = "0.4.2"
    ctrl.on_connection_changed(False)
    ctrl.on_connection_changed(True)

    ctrl.install_firmware()

    assert app.published[-1][1]["url"] == "https://dl/fw/0.4.3/ota.bin"
    assert ctrl._manual_firmware is False


# --- firmware install outcome ------------------------------------------------


def _install_timer(app):
    return next(
        callback
        for callback, delay in app.timers.values()
        if delay == update.FIRMWARE_INSTALL_TIMEOUT_SECONDS
    )


def test_reconnect_with_the_new_version_finishes_the_install(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    ctrl.install_firmware()
    ctrl.on_connection_changed(False)

    ctrl.app.device.device_info["yaml_version"] = "0.4.4"
    ctrl.on_connection_changed(True)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert state["firmware_install_error"] is None
    assert ctrl._firmware_install_timer is None
    assert _firmware_events(app)[-1]["installed_version"] == "0.4.4"


def test_reconnect_with_the_old_version_reports_a_failed_install(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    ctrl.install_firmware()
    ctrl.on_connection_changed(False)

    ctrl.on_connection_changed(True)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert state["firmware_install_error"] == (
        "Firmware install of 0.4.4 failed: the panel still runs 0.4.3"
    )


def test_an_install_without_a_reboot_times_out(monkeypatch):
    """A failed download leaves the panel connected; the entity must not spin forever."""
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    ctrl.install_firmware()

    _install_timer(app)({})

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert "did not finish" in state["firmware_install_error"]
    assert _firmware_events(app)[-1]["installing"] is False


def test_firmware_reboot_defers_then_starts_the_required_tft_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.2"},
        [_release("0.4.3")],
    )
    ctrl._firmware_installing = True

    ctrl.check_installed_version()
    assert app.published == []

    ctrl.on_connection_changed(True)
    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.3.tft")]
    assert ctrl.get_update_state()["state"] == update.UPDATE_STATE_INSTALLING
    assert ctrl.get_update_state()["version"] == "0.4.3"


def test_tft_install_deferred_while_firmware_install_is_in_flight(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )
    ctrl._firmware_installing = True

    ctrl.check_installed_version()

    assert app.published == []
    assert app.opened == []


def test_reconnect_clears_the_firmware_install_flag(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"}, [_release("0.4.2")]
    )
    ctrl._firmware_installing = True

    ctrl.on_connection_changed(True)

    assert ctrl._firmware_installing is False

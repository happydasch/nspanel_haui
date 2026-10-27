"""Tests for the GitHub release fetch in the update controller."""

import pytest
import requests
from nspanel_haui.haui.controller import update
from nspanel_haui.haui.controller.update import HAUIUpdateController


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

    def __init__(self, device_info, connected=True, display_model="eu"):
        self.device = types.SimpleNamespace(
            device_info=device_info,
            connected=connected,
            display_model=display_model,
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

    def run_in(self, callback, delay):
        handle = f"timer{len(self.timers)}"
        self.timers[handle] = (callback, delay)
        return handle

    def run_every(self, callback, start, interval):
        return self.run_in(callback, interval)

    def cancel_timer(self, handle):
        self.timers.pop(handle, None)


def _updater(monkeypatch, device_info, releases=(), connected=True, display_model="eu", **config):
    app = _App(device_info, connected, display_model)
    ctrl = HAUIUpdateController(app, {**DEFAULT_CONFIG["update"], **config})
    ctrl.log = lambda *a, **kw: None
    ctrl.translate = lambda text: text
    ctrl.get_color = lambda key: 0
    fetches: list = []

    def fake_get(url, timeout):
        fetches.append(url)
        return _Response(list(releases))

    monkeypatch.setattr(update.requests, "get", fake_get)
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

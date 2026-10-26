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
        self.opened: list = []
        self.timers: dict = {}
        esphome = types.SimpleNamespace(
            publish=lambda action, value: self.published.append((action, value))
        )
        navigation = types.SimpleNamespace(
            open_panel=lambda key, **kw: self.opened.append((key, kw)), close_panel=lambda: None
        )
        self.controller = {
            "esphome": types.SimpleNamespace(esphome=esphome),
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

    ctrl.install_tft("0.4.0")

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]
    state = ctrl.get_update_state()
    assert state["state"] == "installing"
    assert state["version"] == "0.4.0"
    assert state["started_at"] is not None
    assert state["last_error"] is None


def test_tft_install_defaults_to_the_firmwares_yaml_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/0.4.0.tft")]
    assert ctrl.get_update_state()["version"] == "0.4.0"


def test_tft_install_without_release_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [])

    ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "No GitHub release" in (state["last_error"] or "")


def test_tft_install_while_disconnected_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, connected=False
    )

    ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert state["last_error"] == "device disconnected"


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


def test_tft_install_state_resets_on_disconnect(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.3.3"}, [_release("0.4.0")]
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    ctrl.on_connection_changed(False)

    state = ctrl.get_update_state()
    assert state["state"] == "idle"
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

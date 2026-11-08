"""Tests for the update controller (firmware manifest, TFT, version handling)."""

import datetime
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from custom_components.nspanel_haui.haui.controller import release_source, update
from custom_components.nspanel_haui.haui.controller.update import HAUIUpdateController


@pytest.fixture(autouse=True)
def _reset_release_cache():
    """Reset the shared release cache between tests."""
    release_source._release_cache = None
    yield
    release_source._release_cache = None


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


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

    monkeypatch.setattr(release_source.requests, "get", fake_get)

    with pytest.raises(requests.exceptions.ConnectTimeout):
        release_source.fetch_release_catalog()

    assert release_source.fetch_release_catalog().releases == [{"tag_name": "v0.3.3"}]


def test_release_fetch_uses_the_shared_cache(monkeypatch):
    """Consecutive controllers share one GitHub request within the TTL."""
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _Response([{"tag_name": "v0.3.3"}])

    monkeypatch.setattr(release_source.requests, "get", fake_get)

    release_source.fetch_release_catalog()
    second = release_source.fetch_release_catalog()

    assert len(calls) == 1
    assert second.releases == [{"tag_name": "v0.3.3"}]


def test_release_fetch_bypasses_the_cache_when_forced(monkeypatch):
    """force=True refreshes even when a fresh cache entry exists."""
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _Response([{"tag_name": "v0.3.3"}])

    monkeypatch.setattr(release_source.requests, "get", fake_get)

    release_source.fetch_release_catalog()
    release_source.fetch_release_catalog(force=True)

    assert len(calls) == 2


def test_a_failed_refresh_falls_back_to_the_cached_catalog(monkeypatch):
    """A stale catalog beats none; the warning says it is stale."""
    responses = [_Response([{"tag_name": "v0.3.3"}]), requests.exceptions.ConnectTimeout("t")]

    def fake_get(url, timeout):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(release_source.requests, "get", fake_get)

    release_source.fetch_release_catalog()
    catalog = release_source.fetch_release_catalog(force=True)

    assert catalog.releases == [{"tag_name": "v0.3.3"}]
    assert "using cached release info" in catalog.warning


def test_manual_check_preserves_failure_and_retry_state(monkeypatch):
    """A status refresh must not reset failures or start a TFT retry."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.3.9"},
        [_release("0.4.2")],
        manifest="0.4.1",
    )
    failed_at = datetime.datetime.now(tz=datetime.UTC)
    ctrl._update_state = update.UPDATE_STATE_ERROR
    ctrl._update_last_error = "previous TFT failure"
    ctrl._last_install_at = failed_at
    ctrl._last_install_confirmed = False

    _manual_check(ctrl)

    assert ctrl._update_state == update.UPDATE_STATE_ERROR
    assert ctrl._update_last_error == "previous TFT failure"
    assert ctrl._last_install_at == failed_at
    assert ctrl._last_install_confirmed is False
    assert app.published == []


# --- automatic TFT update ----------------------------------------------------

import types  # noqa: E402

from custom_components.nspanel_haui.haui.mapping.const import (  # noqa: E402
    DEFAULT_CONFIG,
    ESPAction,
    ESPResponse,
    PopupPanelKey,
)


def _release(tag, with_tft=True, prerelease=False):
    assets = [{"name": "nspanel_haui.tft", "browser_download_url": f"https://dl/{tag}.tft"}]
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "",
        "prerelease": prerelease,
        "assets": assets if with_tft else [],
    }


class _App:
    hass = None

    def log(self, msg: str, **kwargs) -> None:
        pass

    def __init__(self, device_info, connected=True, display_model="eu"):
        self.events: list = []
        self.run_off_worker = lambda func, *args, timeout=None: func(*args)
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
            send_cmd=lambda cmd, value="", force=False: self.requests.append((cmd, value, force)),
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

    def run_off_worker(self, fn, *args, timeout=60.0):
        """Mirror HAAdapter: blocking I/O runs off the worker (inline here)."""
        return fn(*args)

    def submit_off_worker(self, fn, *args, on_done=None):
        try:
            result = fn(*args)
        except BaseException as exc:
            if on_done is None:
                raise
            on_done(None, exc)
        else:
            if on_done is not None:
                on_done(result, None)


def _manifest(version, path=None, tft=True):
    """A firmware manifest in the schema the release workflow writes.

    ``tft=False`` omits the ``tft`` block (a local test release names none).
    """
    manifest = {
        "name": "NSPanel HAUI",
        "version": version,
        "variant": "universal",
        "builds": [
            {"ota": {"path": path or f"https://dl/fw/{version}/ota.bin", "md5": f"md5-{version}"}}
        ],
    }
    if tft:
        manifest["tft"] = {
            "version": version,
            "assets": {
                "eu": {
                    "path": f"https://dl/tft/{version}/nspanel_haui.tft",
                    "md5": f"tft-{version}",
                },
                "us": {
                    "path": f"https://dl/tft/{version}/nspanel_haui_portrait.tft",
                    "md5": f"tft-portrait-{version}",
                },
            },
        }
    return manifest


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
    merged_info = {
        "firmware_variant": "universal",
        "tft_required_version": device_info.get("yaml_version"),
        **device_info,
    }
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
            current = served["release_manifests"].get(
                tag, _manifest(tag, f"https://dl/{tag}/ota.bin")
            )
            if isinstance(current, Exception):
                raise current
            return _Response(current)
        if downloads and url in downloads:
            return _Download(downloads[url])
        fetches.append(url)
        return _Response(list(releases))

    monkeypatch.setattr(release_source.requests, "get", fake_get)
    app.served = served
    if manifest is not None and not isinstance(manifest, Exception):
        # ``start_part`` would have read the manifest on app start; the TFT
        # checks and the entity state depend on it being loaded.
        url = config["firmware_manifest_url"]
        ctrl._firmware_manifest = release_source.parse_firmware_manifest(
            release_source.fetch_json(url, 10), url, display_model
        )
    return ctrl, app, fetches


def _result(start, *args, **kwargs):
    """Run an async update entry point; the fake app completes it inline."""
    results: list = []
    start(*args, on_complete=results.append, **kwargs)
    assert len(results) == 1
    return results[0]


def _check(ctrl, **kwargs):
    """A scheduled update check, as the periodic timer starts it."""
    return _result(ctrl.start_async_check, **kwargs)


def _manual_check(ctrl):
    """The editor's update check (``NSPanelHAUI.async_check_for_update``)."""
    return _check(ctrl, force_refresh=True, allow_auto_install=False, include_notice=True)


def _install_firmware(ctrl, version=None, url=None):
    return _result(ctrl.start_async_firmware_install, version, url)


def _refresh_manifest(ctrl):
    """Load the manifests the way the startup check does."""
    _check(ctrl, allow_auto_install=False, include_notice=False, require_connected=False)


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
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    # The only GitHub call is the release notice check; the TFT comes from the
    # firmware manifest, not from a release lookup.
    assert fetches == [release_source.RELEASES_URL]
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_outdated_tft_without_auto_install_asks_and_installs_on_confirm(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
        auto_install=False,
    )

    ctrl.check_installed_version()

    assert app.published == []
    ((key, kwargs),) = app.opened
    assert key == PopupPanelKey.POPUP_NOTIFY
    kwargs["button_callback_fnc"](False, True)
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_current_tft_needs_no_update(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.4.0"},
        manifest="0.4.0",
    )

    ctrl.check_installed_version()

    assert (app.published, app.opened, fetches) == ([], [], [])


def test_tft_is_not_assumed_to_match_firmware_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5",
            "tft_version": "0.4.3",
        },
        manifest="0.4.5",
    )
    app.device.device_info.pop("tft_required_version")

    ctrl.check_installed_version()

    assert app.published == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_a_firmware_only_release_uses_its_declared_tft_version(monkeypatch):
    manifest = _manifest("0.4.5")
    manifest["tft"]["version"] = "0.4.4"
    manifest["tft"]["assets"]["eu"]["path"] = "https://dl/tft/0.4.4/nspanel_haui.tft"
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5",
            "tft_required_version": "0.4.4",
            "tft_version": "0.4.3",
        },
        manifest=manifest,
    )

    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.4/nspanel_haui.tft")]


def test_dev_firmware_installs_its_explicitly_required_newer_tft(monkeypatch):
    """Firmware and TFT dev serials can differ; the firmware requirement wins."""
    manifest = _manifest("0.4.5.dev29")
    manifest["tft"]["version"] = "0.4.5.dev30"
    manifest["tft"]["assets"]["eu"]["path"] = "https://dl/tft/0.4.5.dev30/nspanel_haui.tft"
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev29",
            "tft_required_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
        },
        manifest=manifest,
    )

    ctrl.check_installed_version()

    assert app.published == [
        (ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.5.dev30/nspanel_haui.tft")
    ]


def test_connect_check_installs_tft_version_newer_than_firmware_serial(monkeypatch):
    manifest = _manifest("0.4.5.dev29")
    manifest["tft"]["version"] = "0.4.5.dev30"
    manifest["tft"]["assets"]["eu"]["path"] = "https://dl/tft/0.4.5.dev30/nspanel_haui.tft"
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev29",
            "tft_required_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
        },
        manifest=manifest,
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [
        (ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.5.dev30/nspanel_haui.tft")
    ]


def test_connect_check_uses_installed_firmware_manifest_for_required_tft(monkeypatch):
    installed_manifest = _manifest("0.4.5.dev29")
    installed_manifest["tft"]["version"] = "0.4.5.dev30"
    installed_manifest["tft"]["assets"]["eu"]["path"] = (
        "https://dl/tft/0.4.5.dev30/nspanel_haui.tft"
    )
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev29",
            "tft_required_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
        },
        releases=[_firmware_release("0.4.5.dev29")],
        manifest="0.4.5.dev31",
    )
    app.served["release_manifests"]["0.4.5.dev29"] = installed_manifest

    ctrl.start_async_check(allow_auto_install=False, include_notice=False, check_tft=True)

    assert ctrl._tft_manifest["version"] == "0.4.5.dev29"
    assert ctrl.get_update_snapshot()["display"]["latest_version"] == "0.4.5.dev30"
    assert app.published == [
        (ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.5.dev30/nspanel_haui.tft")
    ]


def test_tft_picker_and_install_use_installed_firmware_manifest_fallback(monkeypatch):
    installed_manifest = _manifest("0.4.5.dev29")
    installed_manifest["tft"]["version"] = "0.4.5.dev30"
    installed_manifest["tft"]["assets"]["eu"]["path"] = (
        "https://dl/tft/0.4.5.dev30/nspanel_haui.tft"
    )
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev29",
            "tft_required_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
        },
        releases=[_firmware_release("0.4.5.dev29")],
        manifest="0.4.5.dev31",
    )
    app.served["release_manifests"]["0.4.5.dev29"] = installed_manifest

    picker_results = []
    ctrl.start_async_list_tft_releases(picker_results.append)
    install_results = []
    ctrl.start_async_tft_install(None, None, install_results.append)

    assert picker_results[0]["releases"] == ["0.4.5.dev30"]
    assert picker_results[0]["required"] == "0.4.5.dev30"
    assert install_results[0]["state"] == update.UPDATE_STATE_INSTALLING
    assert app.published == [
        (ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.5.dev30/nspanel_haui.tft")
    ]


def test_custom_build_finds_its_tft_in_the_universal_release_of_its_version(monkeypatch):
    """The TFT is the same for both build variants; only the firmware image differs."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
            "firmware_variant": "custom",
        },
        releases=[_firmware_release("0.4.5.dev30")],
        manifest=_manifest("0.4.4", tft=False),
    )
    app.served["release_manifests"]["0.4.5.dev30"] = _manifest("0.4.5.dev30")

    picker_results = []
    ctrl.start_async_list_tft_releases(picker_results.append)
    install_results = []
    ctrl.start_async_tft_install(None, None, install_results.append)

    assert picker_results[0] == {
        "releases": ["0.4.5.dev30"],
        "required": "0.4.5.dev30",
        "error": None,
    }
    assert install_results[0]["state"] == update.UPDATE_STATE_INSTALLING
    assert app.published == [
        (ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.5.dev30/nspanel_haui.tft")
    ]


def test_a_manifest_without_a_tft_block_installs_nothing(monkeypatch):
    """A local test release names no TFT: the check must not even try to install."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.5.dev3", "tft_version": "0.4.4"},
        manifest=_manifest("0.4.5.dev3", tft=False),
    )

    ctrl.check_installed_version()

    assert app.published == []
    assert app.opened == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_no_check_while_disconnected(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
        connected=False,
    )

    ctrl.check_installed_version()

    assert (app.published, app.opened, fetches) == ([], [], [])


def test_new_release_check_only_notifies(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.4.0"},
        [_release("0.5.0")],
        manifest="0.4.0",
    )

    _check(ctrl)

    assert app.published == []
    ((key, kwargs),) = app.opened
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert "button_callback_fnc" not in kwargs


def test_tft_install_reports_state_transitions(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    result = ctrl.install_tft("0.4.0")

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]
    state = ctrl.get_update_state()
    assert state["state"] == "installing"
    assert state["version"] == "0.4.0"
    assert state["started_at"] is not None
    assert state["last_error"] is None
    # install_tft reports the state back so the editor can show the real outcome
    assert result == state


def test_tft_install_defaults_to_the_firmwares_required_tft_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5",
            "tft_required_version": "0.4.0",
            "tft_version": "0.3.3",
        },
        manifest="0.4.0",
    )

    result = ctrl.install_tft()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]
    assert ctrl.get_update_state()["version"] == "0.4.0"
    assert result["state"] == "installing"


def test_a_tft_install_loads_the_manifest_when_it_was_never_read(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    ctrl._firmware_manifest = None  # e.g. the manifest read failed on start

    result = _result(ctrl.start_async_tft_install, None, None)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.2/nspanel_haui.tft")]
    assert result["state"] == "installing"


def test_install_tft_never_fetches_a_missing_manifest_on_the_worker(monkeypatch):
    """Only the async path fetches; a direct install reports the missing manifest."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    ctrl._firmware_manifest = None
    ctrl._firmware_manifest_error = "manifest read failed"

    def no_fetch(*_args, **_kwargs):
        raise AssertionError("install_tft fetched on the worker")

    monkeypatch.setattr(release_source.requests, "get", no_fetch)

    result = ctrl.install_tft()

    assert app.published == []
    assert result["state"] == update.UPDATE_STATE_ERROR
    assert result["last_error"] == "manifest read failed"


def test_a_newer_github_release_never_installs_its_tft_by_itself(monkeypatch):
    """A release notice never installs: the TFT follows the firmware manifest only."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.4.0"},
        [_release("0.5.0")],
        manifest="0.4.0",
    )

    ctrl.check_installed_version()

    assert app.published == []


def test_tft_install_without_a_manifest_tft_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest=_manifest("0.4.0", tft=False),
    )

    result = ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "ships no TFT" in (state["last_error"] or "")
    assert result == state


def test_tft_install_of_a_version_the_manifest_does_not_ship_is_refused(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.2",
    )

    result = ctrl.install_tft("0.4.1")

    assert app.published == []
    assert "not one for" in (result["last_error"] or "")


def test_tft_install_while_disconnected_moves_to_error(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        connected=False,
    )

    result = ctrl.install_tft("0.4.0")

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert state["last_error"] == "device disconnected"
    assert result == state


def test_tft_install_marks_done_when_the_display_reports_the_version(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
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
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    ctrl.on_connection_changed(False)

    state = ctrl.get_update_state()
    assert state["state"] == "installing"
    assert state["last_error"] is None


# --- display model: which manifest asset --------------------------------------


def test_portrait_model_installs_the_portrait_asset(monkeypatch):
    """A ``display_model: us`` device gets ``nspanel_haui_portrait.tft`` from the manifest."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
        display_model="us",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [
        (
            ESPAction.UPLOAD_TFT_URL,
            "https://dl/tft/0.4.0/nspanel_haui_portrait.tft",
        )
    ]


def test_landscape_model_keeps_the_landscape_asset(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_unknown_display_model_uses_the_landscape_asset(monkeypatch):
    """A model the manifest does not name falls back to the landscape asset."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
        display_model="",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_a_manifest_without_the_portrait_asset_offers_nothing_to_a_us_panel(monkeypatch):
    """A manifest that only ships the landscape TFT must not install it on portrait."""
    manifest = _manifest("0.4.0")
    del manifest["tft"]["assets"]["us"]
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest=manifest,
        display_model="us",
    )

    ctrl.on_connection_changed(True)
    _fire_timers(app)

    assert app.published == []
    assert ctrl.get_update_state()["state"] == update.UPDATE_STATE_IDLE
    # the entity offers nothing: the installed TFT is reported as latest
    assert _display_events(app)[-1]["latest_version"] == "0.3.3"


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
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.install_tft("0.4.0")
    assert ctrl.get_update_state()["state"] == "installing"

    # The device republishes the state once the display reported the version.
    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version="0.4.0"))

    assert ctrl.get_update_state()["state"] == "done"
    assert ctrl._last_install_confirmed is True
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_refresh_timeout_with_empty_version_installs_nothing(monkeypatch):
    """A lost device-state answer is fail-safe: no install from an unknown version."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": ""},
        manifest="0.4.0",
    )

    ctrl.check_installed_version()
    _fire_timer(app, update.DEVICE_STATE_REFRESH_SECONDS)  # the response never came

    assert app.published == []
    assert app.opened == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_successful_empty_refresh_installs_the_missing_tft_once(monkeypatch):
    """A first install still happens — but only after the refresh answered."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": ""},
        manifest="0.4.0",
    )

    ctrl.check_installed_version()
    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version=""))

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.0/nspanel_haui.tft")]


def test_unconfirmed_recent_install_is_not_auto_retried(monkeypatch):
    """An upload that never gets confirmed must not be fired again automatically."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
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
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )
    app.controller["esphome"].esphome.publish = lambda action, value: False

    result = ctrl.install_tft("0.4.0")

    assert result["state"] == "error"
    assert "could not send" in (result["last_error"] or "").lower()
    assert ctrl._last_install_at is None
    assert ctrl._last_install_confirmed is False


def test_invalid_required_tft_version_is_an_error_not_a_0_0_0_install(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "not-a-version", "tft_version": "0.4.0"})

    ctrl.check_installed_version()

    assert app.published == []
    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "invalid tft_required_version" in state["last_error"]


def test_check_for_update_survives_a_github_failure(monkeypatch):
    def raise_timeout(url, timeout):
        raise requests.exceptions.ConnectTimeout("no route to host")

    monkeypatch.setattr(release_source.requests, "get", raise_timeout)
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.0", "tft_version": "0.4.0"})

    _check(ctrl)  # must not raise

    assert app.opened == []
    assert ctrl.get_update_state()["state"] == "idle"


def test_reconnect_verification_times_out_into_an_error(monkeypatch):
    """The upload ends in a reboot: a bounded verification window owns the outcome."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.install_tft("0.4.0")
    ctrl.on_connection_changed(False)  # the upload rebooted the device
    app.published.clear()
    app.requests.clear()
    # The post-reboot handshake knows nothing about the TFT yet.
    app.device.device_info = {"yaml_version": "0.4.0", "tft_version": "", "uptime": 0}
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
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
    )

    ctrl.install_tft("0.4.0")
    ctrl.on_connection_changed(False)
    app.device.device_info["uptime"] = 0
    ctrl.on_connection_changed(True)

    ctrl.process_event(_device_state(yaml_version="0.4.0", tft_version="0.4.0"))

    state = ctrl.get_update_state()
    assert state["state"] == "done"
    assert ctrl._last_install_confirmed is True


# --- manual update check -----------------------------------------------------


def test_a_tft_manifest_mismatch_is_visible_and_does_not_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.2",
            "tft_required_version": "0.4.2",
            "tft_version": "0.4.0",
        },
        manifest="0.4.1",
    )

    ctrl.check_installed_version()

    state = ctrl.get_update_state()
    assert "TFT required by firmware: 0.4.2" in state["tft_update_reason"]
    assert "manifest provides: 0.4.1" in state["tft_update_reason"]
    assert state["state"] == update.UPDATE_STATE_IDLE
    assert app.published == []
    assert _display_events(app)[-1]["update_reason"] == state["tft_update_reason"]


def test_automatic_firmware_failure_is_published(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl._start_firmware_install("https://dl/fw.bin", "md5", "0.4.2", manual=False)

    ctrl._firmware_install_timer_callback({})

    state = ctrl.get_update_state()
    assert "did not reboot" in state["firmware_install_error"]
    event = _firmware_events(app)[-1]
    assert event["last_error"] == state["firmware_install_error"]


def test_async_check_submits_fetch_and_applies_result_only_in_completion(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.2",
    )
    jobs = []

    def capture(func, *args, on_done=None):
        jobs.append((func, args, on_done))

    app.submit_off_worker = capture
    completed = []
    ctrl.start_async_check(allow_auto_install=False, on_complete=completed.append)

    assert len(jobs) == 1
    assert completed == []
    assert ctrl._firmware_manifest["version"] == "0.4.2"

    fetch, args, callback = jobs.pop()
    fetched = fetch(*args)
    callback(fetched, None)

    assert completed[0]["firmware_update_available"] is True
    assert ctrl._firmware_manifest["version"] == "0.4.2"


def test_async_check_keeps_the_device_worker_available_during_slow_fetch(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    original_fetch = release_source.fetch_update_inputs
    fetch_started = threading.Event()
    release_fetch = threading.Event()
    applied = threading.Event()
    worker = ThreadPoolExecutor(max_workers=1)
    io = ThreadPoolExecutor(max_workers=1)

    def slow_fetch(*args):
        fetch_started.set()
        if not release_fetch.wait(5):
            raise TimeoutError("test fetch not released")
        return original_fetch(*args)

    def submit_off_worker(func, *args, on_done=None):
        future = io.submit(func, *args)

        def deliver(done):
            try:
                result = done.result()
            except BaseException as exc:
                worker.submit(on_done, None, exc)
            else:
                worker.submit(on_done, result, None)

        future.add_done_callback(deliver)

    monkeypatch.setattr(release_source, "fetch_update_inputs", slow_fetch)
    app.submit_off_worker = submit_off_worker
    try:
        started = worker.submit(
            lambda: ctrl.start_async_check(
                allow_auto_install=False,
                on_complete=lambda _result: applied.set(),
            )
        )
        started.result(timeout=1)
        assert fetch_started.wait(1)

        heartbeat = worker.submit(lambda: "worker still responsive")
        assert heartbeat.result(timeout=1) == "worker still responsive"

        release_fetch.set()
        assert applied.wait(2)
    finally:
        release_fetch.set()
        worker.shutdown(wait=True)
        io.shutdown(wait=True)


def test_async_firmware_install_keeps_the_worker_available_during_image_fetch(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    original_fetch = release_source.fetch_firmware_install_inputs
    fetch_started = threading.Event()
    release_fetch = threading.Event()
    completed = threading.Event()
    worker = ThreadPoolExecutor(max_workers=1)
    io = ThreadPoolExecutor(max_workers=1)

    def slow_fetch(*args):
        fetch_started.set()
        if not release_fetch.wait(5):
            raise TimeoutError("test fetch not released")
        return original_fetch(*args)

    def submit_off_worker(func, *args, on_done=None):
        future = io.submit(func, *args)

        def deliver(done):
            try:
                result = done.result()
            except BaseException as exc:
                worker.submit(on_done, None, exc)
            else:
                worker.submit(on_done, result, None)

        future.add_done_callback(deliver)

    monkeypatch.setattr(release_source, "fetch_firmware_install_inputs", slow_fetch)
    app.submit_off_worker = submit_off_worker
    try:
        started = worker.submit(
            lambda: ctrl.start_async_firmware_install(None, None, lambda _result: completed.set())
        )
        started.result(timeout=1)
        assert fetch_started.wait(1)

        heartbeat = worker.submit(lambda: "worker still responsive")
        assert heartbeat.result(timeout=1) == "worker still responsive"

        release_fetch.set()
        assert completed.wait(2)
        assert ctrl._firmware_installing is True
    finally:
        release_fetch.set()
        worker.shutdown(wait=True)
        io.shutdown(wait=True)


def test_update_check_does_not_invalidate_an_inflight_firmware_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.2",
    )
    jobs = []
    app.submit_off_worker = lambda func, *args, on_done=None: jobs.append((func, args, on_done))
    completed = []

    ctrl.start_async_firmware_install(None, None, completed.append)
    install_job = jobs.pop()
    install_result = install_job[0](*install_job[1])
    ctrl.start_async_check(allow_auto_install=False)
    check_job = jobs.pop()

    install_job[2](install_result, None)

    assert ctrl._firmware_installing is True
    assert completed[-1]["firmware_installing"] is True
    check_job[2](check_job[0](*check_job[1]), None)
    assert ctrl._firmware_installing is True


def test_async_tft_install_fetches_the_manifest_before_uploading(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_required_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    jobs = []
    app.submit_off_worker = lambda func, *args, on_done=None: jobs.append((func, args, on_done))
    completed = []

    ctrl.start_async_tft_install(None, None, completed.append)

    assert app.published == []
    fetch, args, callback = jobs.pop()
    callback(fetch(*args), None)

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.2/nspanel_haui.tft")]
    assert completed[-1]["state"] == update.UPDATE_STATE_INSTALLING


def test_async_check_ignores_stale_fetch_completion(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.2",
    )
    jobs = []
    app.submit_off_worker = lambda func, *args, on_done=None: jobs.append((func, args, on_done))

    ctrl.start_async_check(allow_auto_install=False)
    first = jobs.pop()
    old_inputs = first[0](*first[1])
    app.served["manifest"] = _manifest("0.4.4")
    ctrl.start_async_check(allow_auto_install=False)
    second = jobs.pop()
    new_inputs = second[0](*second[1])

    second[2](new_inputs, None)
    first[2](old_inputs, None)

    assert ctrl._firmware_manifest["version"] == "0.4.4"


def test_unload_invalidates_an_inflight_update_fetch(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    jobs = []
    app.submit_off_worker = lambda func, *args, on_done=None: jobs.append((func, args, on_done))
    ctrl.start_async_check(allow_auto_install=False)
    fetch, args, callback = jobs.pop()
    fetched = fetch(*args)
    ctrl.stop_part()

    callback(fetched, None)

    assert ctrl._firmware_manifest["version"] == "0.4.2"
    assert ctrl._firmware_installing is False


def test_manual_check_reports_an_up_to_date_panel(monkeypatch):
    """The editor needs an answer even when nothing is newer."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.2")],
        manifest="0.4.2",
    )

    result = _manual_check(ctrl)

    assert result["latest_release"] == "0.4.2"
    assert result["check_error"] is None
    assert result["state"] == "idle"
    assert app.published == []


def test_manual_check_does_not_install_an_outdated_tft(monkeypatch):
    """A manual status check reports offers but never starts an upload."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )

    result = _manual_check(ctrl)

    assert app.published == []
    assert result["state"] == "idle"
    assert result["tft_update_reason"] is None


def test_manual_check_does_not_auto_install_firmware(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        manifest="0.4.2",
        firmware_auto_update=True,
    )

    result = _manual_check(ctrl)

    assert result["firmware_update_available"] is True
    assert result["firmware_installing"] is False
    assert app.published == []


def test_periodic_check_while_disconnected_does_not_fetch_or_install(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        [_release("0.4.2")],
        connected=False,
        manifest="0.4.2",
        firmware_auto_update=True,
    )

    ctrl.callback_timer()

    assert fetches == []
    assert app.published == []
    assert ctrl._firmware_installing is False


def test_stop_part_cancels_install_tracking_on_unload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl.start_part()
    ctrl._update_state = update.UPDATE_STATE_INSTALLING
    ctrl._start_install_timeout_timer()
    ctrl._start_install_verify_timer()
    ctrl._start_firmware_install("https://dl/fw.bin", "md5", "0.4.2", manual=False)

    ctrl.stop_part()

    assert ctrl._firmware_installing is False
    assert ctrl._install_timeout_timer is None
    assert ctrl._install_verify_timer is None
    assert ctrl._firmware_install_timer is None
    assert app.timers == {}


def test_reload_options_preserves_tft_install_verification(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl.start_part()
    ctrl._update_state = update.UPDATE_STATE_INSTALLING
    ctrl._pending_state_check = True
    ctrl._start_install_timeout_timer()
    ctrl._start_install_verify_timer()
    install_timers = (ctrl._install_timeout_timer, ctrl._install_verify_timer)

    ctrl.reload_options({**ctrl.config, "update_interval": ctrl.config["update_interval"] + 60})

    assert ctrl._update_state == update.UPDATE_STATE_INSTALLING
    assert ctrl._pending_state_check is True
    assert (ctrl._install_timeout_timer, ctrl._install_verify_timer) == install_timers
    assert all(timer in app.timers for timer in install_timers)


def test_reload_options_preserves_firmware_install_timeout(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl._start_firmware_install("https://dl/fw.bin", "md5", "0.4.2", manual=False)
    install_timer = ctrl._firmware_install_timer

    ctrl.reload_options({**ctrl.config, "update_interval": ctrl.config["update_interval"] + 60})

    assert ctrl._firmware_installing is True
    assert ctrl._firmware_install_timer == install_timer
    assert install_timer in app.timers


def test_manual_check_during_an_install_starts_no_second_upload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    ctrl.install_tft()
    app.published.clear()

    result = _manual_check(ctrl)

    assert app.published == []
    assert result["state"] == "installing"


def test_manual_check_reports_a_github_failure(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})

    def failing_get(url, timeout):
        raise requests.exceptions.ConnectTimeout("timed out")

    monkeypatch.setattr(release_source.requests, "get", failing_get)

    result = _manual_check(ctrl)

    assert "timed out" in result["check_error"]
    assert result["latest_release"] is None


def test_manual_check_while_disconnected_reports_it(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"}, connected=False
    )

    result = _manual_check(ctrl)

    assert result["check_error"] == "device disconnected"
    assert fetches == []


# --- TFT install from a URL --------------------------------------------------

DEV_TFT_URL = "http://homeassistant.local:8123/local/nspanel/nspanel_haui.tft"


def test_url_install_sends_the_url_without_a_release_lookup(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.2",
    )
    ctrl._update_version = "0.4.2"  # left over from an earlier manifest install

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
    app.device.device_info = {"yaml_version": "0.4.2", "tft_version": "", "uptime": 0}
    ctrl.on_connection_changed(True)
    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.2"))

    assert ctrl.get_update_state()["state"] == "done"


def test_reboot_check_fails_closed_without_uptime(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})
    app.device.device_info.pop("uptime", None)

    assert ctrl._rebooted_since(datetime.datetime.now(tz=datetime.UTC)) is False
    assert ctrl._rebooted_since(None) is False
    app.device.device_info["uptime"] = "unknown"
    assert ctrl._rebooted_since(datetime.datetime.now(tz=datetime.UTC)) is False


def _reconnect_after_upload(ctrl, app, minutes, uptime):
    """The upload ran ``minutes``; the device then reconnects reporting ``uptime`` seconds."""
    ctrl._last_install_at -= datetime.timedelta(minutes=minutes)
    ctrl.on_connection_changed(False)
    app.device.device_info = {
        "yaml_version": "0.4.2",
        "tft_required_version": "0.4.2",
        "tft_version": "0.4.2",
        "uptime": uptime,
    }
    ctrl.on_connection_changed(True)


def test_a_reconnect_without_a_reboot_fails_the_url_install(monkeypatch):
    """A failed upload lets the device run on: it reconnects without rebooting."""
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})
    ctrl.install_tft_url(DEV_TFT_URL)

    _reconnect_after_upload(ctrl, app, minutes=13, uptime=6 * 60 * 60)
    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.2"))

    state = ctrl.get_update_state()
    assert state["state"] == "error"
    assert "did not reboot" in state["last_error"]
    assert app.published == [(ESPAction.UPLOAD_TFT_URL, DEV_TFT_URL)]


def test_a_reconnect_after_the_upload_reboot_verifies_the_url_install(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})
    ctrl.install_tft_url(DEV_TFT_URL)

    _reconnect_after_upload(ctrl, app, minutes=13, uptime=5)
    assert ctrl.get_update_state()["state"] == "installing"
    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.2"))

    assert ctrl.get_update_state()["state"] == "done"


def _reboot_with(ctrl, app, **state):
    """The upload ends in a reboot; the display then reports ``state``."""
    state.setdefault("tft_required_version", state.get("yaml_version"))
    ctrl.on_connection_changed(False)
    app.device.device_info = {**state, "tft_version": ""}
    ctrl.on_connection_changed(True)
    ctrl.process_event(_device_state(**state))


def test_url_install_is_kept_after_its_reboot(monkeypatch):
    """The automatic check must not replace a TFT the user installed from a URL."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.2",
    )

    ctrl.install_tft_url(DEV_TFT_URL)
    _reboot_with(ctrl, app, yaml_version="0.4.2", tft_version="0.4.0")
    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, DEV_TFT_URL)]


def test_a_new_firmware_version_replaces_a_kept_tft(monkeypatch):
    """A firmware update lifts the URL-hold: the new manifest's TFT installs."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.2",
    )
    ctrl.install_tft_url(DEV_TFT_URL)
    _reboot_with(ctrl, app, yaml_version="0.4.2", tft_version="0.4.0")

    # The release updates to 0.4.3: its manifest ships the TFT the firmware needs.
    app.served["manifest"] = "0.4.3"
    _refresh_manifest(ctrl)
    _reboot_with(ctrl, app, yaml_version="0.4.3", tft_version="0.4.0")
    ctrl.check_installed_version()

    assert app.published[-1] == (
        ESPAction.UPLOAD_TFT_URL,
        "https://dl/tft/0.4.3/nspanel_haui.tft",
    )


def test_installing_the_required_manifest_tft_ends_keeping_a_url_tft(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.2",
    )
    ctrl.install_tft_url(DEV_TFT_URL)
    assert ctrl._manual_tft_firmware == "0.4.2"
    ctrl.install_tft()
    assert ctrl._manual_tft_firmware is None


def test_tft_release_list_is_the_manifests_tft_only(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        [_release("0.4.1"), _release("0.4.2")],
        manifest="0.4.2",
    )

    result = _result(ctrl.start_async_list_tft_releases)

    assert result == {"releases": ["0.4.2"], "required": "0.4.2", "error": None}


def test_tft_picker_hides_channel_manifest_version_that_does_not_match_requirement(monkeypatch):
    ctrl, _, _ = _updater(
        monkeypatch,
        {
            "yaml_version": "0.4.5.dev29",
            "tft_required_version": "0.4.5.dev30",
            "tft_version": "0.4.5.dev29",
        },
        manifest={
            **_manifest("0.4.5.dev31"),
            "tft": {
                "version": "0.4.5.dev31",
                "assets": _manifest("0.4.5.dev31")["tft"]["assets"],
            },
        },
    )

    result = _result(ctrl.start_async_list_tft_releases)

    assert result["releases"] == []
    assert "TFT required by firmware: 0.4.5.dev30" in result["error"]


def test_tft_release_list_reports_a_manifest_failure(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.2", "tft_version": "0.4.2"})
    app.served["manifest"] = requests.exceptions.ConnectTimeout("timed out")

    result = _result(ctrl.start_async_list_tft_releases)

    assert result["releases"] == []
    assert "Could not read the firmware manifest" in result["error"]


# --- HAUI Display update entity events ---------------------------------------


def _display_events(app):
    return [data for event_type, data in app.events if event_type == update.DISPLAY_UPDATE_EVENT]


def test_update_events_and_status_share_the_controller_snapshot(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.0"},
        manifest="0.4.2",
    )

    snapshot = ctrl.get_update_snapshot()
    status = ctrl.get_update_state()
    ctrl.publish_display_update()
    ctrl.publish_firmware_update()

    assert status["firmware_update_version"] == snapshot["firmware"]["latest_version"]
    assert status["firmware_update_available"] == snapshot["firmware"]["available"]
    assert status["tft_update_available"] == snapshot["display"]["available"]
    assert _display_events(app)[-1]["installed_version"] == snapshot["display"]["installed_version"]
    assert _firmware_events(app)[-1]["latest_version"] == snapshot["firmware"]["latest_version"]


def test_update_state_reports_compatible_tft_offer_without_firmware_offer(monkeypatch):
    ctrl, _app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )

    state = ctrl.get_update_state()

    assert state["firmware_update_available"] is False
    assert state["tft_update_available"] is True


def test_update_state_withholds_tft_offer_when_manifest_misses_firmware_requirement(monkeypatch):
    ctrl, _app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.3",
    )

    state = ctrl.get_update_state()

    assert state["tft_update_available"] is False
    assert "TFT required by firmware" in state["tft_update_reason"]


def test_device_state_publishes_the_display_versions(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": ""},
        manifest="0.4.2",
    )

    ctrl.process_event(_device_state(yaml_version="0.4.2", tft_version="0.4.1"))

    assert _display_events(app)[-1] == {
        "device": "kitchen",
        "connected": True,
        "enabled": True,
        "installed_version": "0.4.1",
        "latest_version": "0.4.2",  # the manifest's TFT
        "state": "idle",
        "last_error": None,
        "update_reason": None,
    }


def test_unknown_tft_version_is_published_as_none(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": ""},
        manifest="0.4.2",
    )

    ctrl.on_connection_changed(True)

    data = _display_events(app)[-1]
    assert data["installed_version"] is None
    assert data["latest_version"] == "0.4.2"


def test_a_pinned_tft_release_does_not_offer_the_firmware_tag_as_a_display_update(
    monkeypatch,
):
    """Unchanged TFT binaries retain their embedded version in the release manifest."""
    manifest = _manifest("0.4.4")
    manifest["tft"]["version"] = "0.4.3"
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4", "tft_version": "0.4.3"},
        manifest=manifest,
    )

    ctrl.check_installed_version()
    ctrl.publish_display_update()

    data = _display_events(app)[-1]
    assert data["installed_version"] == "0.4.3"
    assert data["latest_version"] == "0.4.3"
    assert app.published == []
    assert app.opened == []


def test_a_manifest_without_a_tft_offers_no_display_update(monkeypatch):
    """A manifest without a TFT: the entity reports the installed TFT as latest."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.5.dev3", "tft_version": "0.4.4"},
        manifest=_manifest("0.4.5.dev3", tft=False),
    )

    ctrl.publish_display_update()

    data = _display_events(app)[-1]
    assert data["latest_version"] == "0.4.4"
    assert data["installed_version"] == "0.4.4"


def test_install_state_changes_are_published(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )

    ctrl.install_tft()

    states = [data["state"] for data in _display_events(app)]
    assert states[-2:] == ["checking", "installing"]


# --- firmware manifest -------------------------------------------------------


def test_master_disable_blocks_checks_installers_and_release_pickers(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.0"},
        releases=[_release("0.4.2")],
        manifest="0.4.2",
        enabled=False,
    )
    submissions = []
    app.submit_off_worker = lambda *args, **kwargs: submissions.append((args, kwargs))

    ctrl.start_part()
    ctrl.on_connection_changed(True)
    check = _manual_check(ctrl)
    firmware_install = _install_firmware(ctrl, url="https://example.test/firmware.bin")
    tft_install = ctrl.install_tft_url("https://example.test/display.tft")
    firmware_picker = []
    tft_picker = []
    ctrl.start_async_list_firmware_releases(firmware_picker.append)
    ctrl.start_async_list_tft_releases(tft_picker.append)
    ctrl.start_async_firmware_install(None, "https://example.test/firmware.bin", lambda _: None)
    ctrl.start_async_tft_install(None, "https://example.test/display.tft", lambda _: None)

    assert check["check_error"] == "Updates are disabled for this device"
    assert firmware_install["firmware_install_error"] == "Updates are disabled for this device"
    assert tft_install["last_error"] == "Updates are disabled for this device"
    assert firmware_picker == [{"releases": [], "error": "Updates are disabled for this device"}]
    assert tft_picker == [
        {
            "releases": [],
            "required": None,
            "error": "Updates are disabled for this device",
        }
    ]
    assert submissions == []
    assert fetches == []
    assert app.timers == {}
    assert app.published == []


def _firmware_events(app):
    return [data for event_type, data in app.events if event_type == update.FIRMWARE_UPDATE_EVENT]


def test_the_manifest_offers_a_newer_firmware(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.3",
        firmware_auto_update=False,
    )

    _check(ctrl)

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is True
    assert state["firmware_update_version"] == "0.4.3"
    assert _firmware_events(app)[0] == {
        "device": "kitchen",
        "connected": True,
        "enabled": True,
        "installed_version": "0.4.2",
        "latest_version": "0.4.3",
        "installing": False,
        "reason": None,
        "last_error": None,
    }


@pytest.mark.parametrize("installed", ["0.4.3", "0.4.4-dev1"])
def test_the_manifest_offers_no_older_or_same_firmware(monkeypatch, installed):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": installed, "tft_version": installed},
        manifest="0.4.3",
        firmware_auto_update=False,
    )

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is False


def test_a_test_release_manifest_offers_the_next_test_build(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4-dev1", "tft_version": "0.4.3"},
        manifest="0.4.4-dev2",
        firmware_manifest_url="http://ha.local/local/nspanel/firmware-manifest.json",
        firmware_auto_update=False,
    )

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is True


def test_an_unreadable_manifest_drops_the_last_offer(monkeypatch):
    """After a URL change the old manifest would offer the wrong firmware."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.2"},
        manifest="0.4.3",
        firmware_auto_update=False,
    )
    _check(ctrl)
    app.served["manifest"] = requests.exceptions.ConnectTimeout("timed out")

    _check(ctrl)

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

    _install_firmware(ctrl)

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

    _check(ctrl)

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

    state = _install_firmware(ctrl)

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

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is False
    state = _install_firmware(ctrl)
    assert app.published == []
    assert "does not report its build variant" in state["firmware_install_error"]


def test_a_manifest_without_a_variant_fails_closed(monkeypatch):
    manifest = {k: v for k, v in _manifest("0.4.4").items() if k != "variant"}
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.3"},
        manifest=manifest,
    )

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is False
    state = _install_firmware(ctrl)
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

    state = _install_firmware(ctrl, "v0.4.4")

    assert app.published == []
    assert "not interchangeable" in state["firmware_install_error"]

    state = _install_firmware(ctrl, url=url)
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

    assert _result(ctrl.start_async_list_firmware_releases) == {"releases": [], "error": None}


def test_firmware_release_list_skips_unreadable_manifests(monkeypatch):
    """A release whose manifest cannot be read is dropped, not offered by guess."""
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")])
    app.served["release_manifests"]["v0.4.2"] = requests.exceptions.ConnectTimeout("timed out")

    assert _result(ctrl.start_async_list_firmware_releases) == {"releases": [], "error": None}


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

    assert _result(ctrl.start_async_list_firmware_releases) == {
        "releases": ["v0.4.4"],
        "error": None,
    }

    state = _install_firmware(ctrl, "v0.4.4")
    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/v0.4.4/custom.bin", "md5sum": "md5-0.4.4"},
        )
    ]
    assert state["firmware_install_error"] is None


# --- automatic firmware update -----------------------------------------------


def test_check_for_update_installs_the_offered_firmware_first(monkeypatch):
    ctrl, app, fetches = _updater(
        monkeypatch,
        {"yaml_version": "0.4.2", "tft_version": "0.4.1"},
        [_release("0.4.3")],
        manifest="0.4.3",
        firmware_auto_update=True,
    )

    _check(ctrl)

    # The TFT follows after the reboot, and the release advisory stays away:
    # the only popup is the install notice.
    assert app.published == [
        (
            ESPAction.INSTALL_FIRMWARE_URL,
            {"url": "https://dl/fw/0.4.3/ota.bin", "md5sum": "md5-0.4.3"},
        )
    ]
    ((key, kwargs),) = app.opened
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert kwargs["title"] == "Update"
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

    _check(ctrl)
    _check(ctrl)

    assert app.published == []
    assert len(app.opened) == 1
    ((key, kwargs),) = app.opened
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert "configured firmware manifest" in kwargs["notification"]

    assert kwargs["title"] == "Update"


def test_the_update_notice_compares_the_firmware_not_the_tft(monkeypatch):
    """A display newer than the installed *firmware* must not hide a release.

    The GitHub release is a firmware release, so the notice compares it with
    the installed ``yaml_version`` — never the display ``tft_version``.
    """
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.5.0"},
        [_release("0.4.1")],
        manifest="0.4.0",
    )

    _check(ctrl)

    assert app.opened, "a newer firmware must be announced even when the TFT is newer"
    ((key, kwargs),) = app.opened
    assert key == PopupPanelKey.POPUP_NOTIFY
    assert kwargs["title"] == "Update"
    assert "Firmware release: 0.4.1" in kwargs["notification"]


def test_a_stale_tft_does_not_invent_a_firmware_update(monkeypatch):
    """A display older than the firmware must not surface a same-version release."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.5.0", "tft_version": "0.4.0"},
        [_release("0.5.0")],
        manifest="0.5.0",
    )

    _check(ctrl)

    assert app.opened == []


def test_stable_channel_ignores_github_prereleases_in_update_notifications(monkeypatch):
    stable = _release("0.4.4")
    prerelease = _release("0.4.5.dev1", prerelease=True)
    github_prerelease = _release("0.4.6", prerelease=True)
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4", "tft_version": "0.4.4"},
        [github_prerelease, prerelease, stable],
        manifest="0.4.4",
        firmware_update_channel="stable",
    )

    result = _check(ctrl)

    assert result["latest_release"] == "0.4.4"
    assert app.opened == []


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
    _refresh_manifest(ctrl)

    assert ctrl._firmware_install_due() is True


def test_firmware_install_not_due_without_a_manifest(monkeypatch):
    ctrl, app, _ = _updater(monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"})
    _refresh_manifest(ctrl)

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_by_default(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
    )
    _refresh_manifest(ctrl)

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_when_disabled(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.1", "tft_version": "0.4.1"},
        manifest="0.4.2",
        firmware_auto_update=False,
    )
    _refresh_manifest(ctrl)

    assert ctrl._firmware_install_due() is False


def test_firmware_install_not_due_during_a_tft_upload(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    _refresh_manifest(ctrl)
    ctrl._set_update_state(update.UPDATE_STATE_INSTALLING, version="0.4.1")

    assert ctrl._firmware_install_due() is False


def test_firmware_install_respects_the_retry_cooldown(monkeypatch):
    """A failed attempt (the panel rebooted into its old firmware) waits an hour."""
    ctrl, app, _ = _updater(
        monkeypatch, {"yaml_version": "0.4.1", "tft_version": "0.4.1"}, manifest="0.4.2"
    )
    _refresh_manifest(ctrl)
    ctrl._firmware_install_at = datetime.datetime.now(tz=datetime.UTC)

    assert ctrl._firmware_install_due() is False


# --- manual firmware install -------------------------------------------------

OTA_IMAGE = bytes([release_source.ESP_IMAGE_MAGIC]) + b"app image"
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

    state = _install_firmware(ctrl)

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

    state = _install_firmware(ctrl)

    assert app.published == []
    assert state["firmware_install_error"] == "No firmware update is available"


def test_manual_install_with_an_unreadable_manifest_names_its_url(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch)

    state = _install_firmware(ctrl)

    assert app.published == []
    assert DEFAULT_CONFIG["update"]["firmware_manifest_url"] in state["firmware_install_error"]


def test_installing_the_manifest_version_uses_the_manifest(monkeypatch):
    """A test release is no GitHub release; its version installs from the manifest."""
    ctrl, app, fetches = _firmware_updater(
        monkeypatch,
        manifest="0.4.4-dev1",
        firmware_manifest_url="http://ha.local/local/nspanel/firmware-manifest.json",
    )

    _install_firmware(ctrl, "0.4.4-dev1")

    assert app.published[0][1]["url"] == "https://dl/fw/0.4.4-dev1/ota.bin"
    assert fetches == []
    assert ctrl._manual_firmware is False


def test_firmware_release_list_holds_only_over_the_air_releases(monkeypatch):
    older = _release("0.4.1")  # factory image only: never offered over the air
    older["assets"].append({"name": "nspanel_haui.bin", "browser_download_url": "x"})
    ctrl, app, _ = _firmware_updater(
        monkeypatch, [_firmware_release("v0.4.2"), older, _firmware_release("v0.4.3")]
    )

    assert _result(ctrl.start_async_list_firmware_releases) == {
        "releases": ["v0.4.3", "v0.4.2"],
        "error": None,
    }


def test_firmware_release_install_flashes_the_release_manifest_image(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")

    state = _install_firmware(ctrl, "v0.4.2")

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

    state = _install_firmware(ctrl, "0.4.1")

    assert app.published == []
    assert "ships no over-the-air firmware" in state["firmware_install_error"]


def test_firmware_url_install_sends_the_md5_of_the_image(monkeypatch):
    url = "http://ha.local/firmware.ota.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: OTA_IMAGE})

    _install_firmware(ctrl, url=url)

    md5 = hashlib.md5(OTA_IMAGE, usedforsecurity=False).hexdigest()
    assert app.published == [(ESPAction.INSTALL_FIRMWARE_URL, {"url": url, "md5sum": md5})]


@pytest.mark.parametrize(
    ("image", "error"),
    [
        pytest.param(FACTORY_IMAGE, "not the factory image", id="factory-image"),
        pytest.param(
            OTA_IMAGE + b"\0" * release_source.FIRMWARE_MAX_BYTES,
            "app partition",
            id="too-big",
        ),
    ],
)
def test_firmware_url_install_refuses_an_unusable_image(monkeypatch, image, error):
    url = "http://ha.local/firmware.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: image})

    state = _install_firmware(ctrl, url=url)

    assert app.published == []
    assert error in state["firmware_install_error"]


def test_firmware_without_the_install_action_reports_it(monkeypatch):
    """Firmware 0.4.2 has no install_firmware_url action: the hub cannot update it."""
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    app.controller["esphome"].esphome.publish = lambda action, value: False

    state = _install_firmware(ctrl)

    assert "install_firmware_url action" in state["firmware_install_error"]
    assert state["firmware_installing"] is False


def test_hand_installed_firmware_pauses_the_automatic_update(monkeypatch):
    """Otherwise the next check reinstalls the latest release over it."""
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")
    _install_firmware(ctrl, "v0.4.2")
    ctrl.app.device.device_info["yaml_version"] = "0.4.2"
    ctrl.on_connection_changed(False)
    ctrl.on_connection_changed(True)  # rebooted into 0.4.2; the manifest offers 0.4.3
    ctrl._firmware_install_at = None  # past the retry cooldown

    _check(ctrl)

    assert len(app.published) == 1
    assert ctrl._firmware_install_due() is False


def test_installing_the_offered_firmware_ends_the_pause(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, [_firmware_release("v0.4.2")], manifest="0.4.3")
    _install_firmware(ctrl, "v0.4.2")
    ctrl.app.device.device_info["yaml_version"] = "0.4.2"
    ctrl.on_connection_changed(False)
    ctrl.on_connection_changed(True)

    _install_firmware(ctrl)

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
    _install_firmware(ctrl)
    ctrl.on_connection_changed(False)

    ctrl.app.device.device_info["yaml_version"] = "0.4.4"
    ctrl.app.device.device_info["uptime"] = 0
    ctrl.on_connection_changed(True)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert state["firmware_install_error"] is None
    assert ctrl._firmware_install_timer is None
    assert _firmware_events(app)[-1]["installed_version"] == "0.4.4"


def test_reconnect_with_the_old_version_reports_a_failed_install(monkeypatch):
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    _install_firmware(ctrl)
    ctrl.on_connection_changed(False)

    ctrl.app.device.device_info["uptime"] = 0
    ctrl.on_connection_changed(True)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert state["firmware_install_error"] == (
        "Firmware install of 0.4.4 failed: the panel still runs 0.4.3"
    )


def _reconnect_after_firmware_install(ctrl, minutes, uptime):
    """The install ran ``minutes``; the device then reconnects reporting ``uptime`` seconds."""
    ctrl._firmware_install_at -= datetime.timedelta(minutes=minutes)
    ctrl.on_connection_changed(False)
    ctrl.app.device.device_info["uptime"] = uptime
    ctrl.on_connection_changed(True)


def test_a_reconnect_without_a_reboot_fails_the_firmware_url_install(monkeypatch):
    """A failed download lets the device run on: it reconnects without rebooting."""
    url = "http://ha.local/firmware.ota.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: OTA_IMAGE})
    _install_firmware(ctrl, url=url)

    _reconnect_after_firmware_install(ctrl, minutes=3, uptime=6 * 60 * 60)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert "did not reboot" in state["firmware_install_error"]


def test_a_reconnect_after_the_reboot_finishes_the_firmware_url_install(monkeypatch):
    url = "http://ha.local/firmware.ota.bin"
    ctrl, app, _ = _firmware_updater(monkeypatch, downloads={url: OTA_IMAGE})
    _install_firmware(ctrl, url=url)

    _reconnect_after_firmware_install(ctrl, minutes=3, uptime=5)

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert state["firmware_install_error"] is None


def test_an_install_without_a_reboot_times_out(monkeypatch):
    """A failed download leaves the panel connected; the entity must not spin forever."""
    ctrl, app, _ = _firmware_updater(monkeypatch, manifest="0.4.4")
    _install_firmware(ctrl)

    _install_timer(app)({})

    state = ctrl.get_update_state()
    assert state["firmware_installing"] is False
    assert "did not finish" in state["firmware_install_error"]
    assert _firmware_events(app)[-1]["installing"] is False


def test_firmware_reboot_defers_then_starts_the_required_tft_install(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.3", "tft_version": "0.4.2"},
        manifest="0.4.3",
    )
    ctrl._firmware_installing = True

    ctrl.check_installed_version()
    assert app.published == []

    ctrl.on_connection_changed(True)
    ctrl.check_installed_version()

    assert app.published == [(ESPAction.UPLOAD_TFT_URL, "https://dl/tft/0.4.3/nspanel_haui.tft")]
    assert ctrl.get_update_state()["state"] == update.UPDATE_STATE_INSTALLING
    assert ctrl.get_update_state()["version"] == "0.4.3"


def test_tft_install_deferred_while_firmware_install_is_in_flight(monkeypatch):
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.0", "tft_version": "0.3.3"},
        manifest="0.4.0",
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


# --- version comparison matches Home Assistant (AwesomeVersion) --------------


def test_a_next_patch_dev_build_is_newer_than_the_stable_release(monkeypatch):
    """The plan's core rule: 0.4.5.devN > stable 0.4.4, so dev firmware updates."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4", "tft_version": "0.4.4"},
        manifest="0.4.5.dev3",
        firmware_auto_update=True,
    )

    _check(ctrl)

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is True
    assert state["firmware_update_version"] == "0.4.5.dev3"
    assert app.published[0][1]["url"] == "https://dl/fw/0.4.5.dev3/ota.bin"


def test_the_final_release_supersedes_its_dev_builds(monkeypatch):
    """0.4.5 is newer than 0.4.5.dev3: a panel on a dev build gets the release."""
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.5.dev3", "tft_version": "0.4.4"},
        manifest="0.4.5",
        firmware_auto_update=True,
    )

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is True
    assert app.published[0][1]["url"] == "https://dl/fw/0.4.5/ota.bin"


def test_a_local_segment_dev_build_is_never_offered_its_final_release(monkeypatch):
    """Why dev versions carry no ``+g<sha>``: AwesomeVersion sorts such a build
    above its final release, and the hub mirrors Home Assistant's comparison.
    """
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.5.dev3+gabcdef1", "tft_version": "0.4.4"},
        manifest="0.4.5",
        firmware_auto_update=True,
    )

    _check(ctrl)

    assert ctrl.get_update_state()["firmware_update_available"] is False
    assert app.published == []


def test_an_invalid_installed_version_is_withheld_not_offered(monkeypatch):
    """An old dev tag reports no parseable version: never offer an update.

    Home Assistant would fall back to "update available" for an unparseable
    installed version; the hub withholds the offer so the entity cannot loop.
    """
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "dev-3-f243f33", "tft_version": "0.4.4"},
        manifest="0.4.4",
    )

    _check(ctrl)

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is False
    assert state["firmware_update_version"] is None
    assert "invalid firmware version" in state["firmware_update_reason"]
    assert _firmware_events(app)[-1]["latest_version"] is None

    result = _install_firmware(ctrl)
    assert app.published == []
    assert "invalid firmware version" in result["firmware_install_error"]


def test_an_unparseable_manifest_version_is_withheld_too(monkeypatch):
    """An incomparable manifest ``version`` must not reach the HA update entity.

    Home Assistant falls back to "update available" when it cannot compare two
    versions, so an unparsable latest would offer the update on every check.
    """
    ctrl, app, _ = _updater(
        monkeypatch,
        {"yaml_version": "0.4.4", "tft_version": "0.4.4"},
        manifest=_manifest("0.4.4.dev-3-f243f33"),
    )

    _check(ctrl)

    state = ctrl.get_update_state()
    assert state["firmware_update_available"] is False
    # Withheld from the entity as well, not just from the internal availability
    # check, so the "HAUI Firmware" entity cannot show an incomparable update.
    assert state["firmware_update_version"] is None
    assert _firmware_events(app)[-1]["latest_version"] is None


# --- firmware update channel -------------------------------------------------


def _updater_with_channel(monkeypatch, channel, **kwargs):
    return _updater(
        monkeypatch,
        {"yaml_version": "0.4.4", "tft_version": "0.4.4"},
        firmware_update_channel=channel,
        **kwargs,
    )


def test_the_dev_channel_follows_the_newest_release_with_a_manifest(monkeypatch):
    dev = {**_firmware_release("0.4.5.dev3"), "prerelease": True}
    # Released, but its assets are still uploading.
    uploading = {"tag_name": "0.4.5.dev4", "name": "", "body": "", "prerelease": True}
    ctrl, app, _ = _updater_with_channel(
        monkeypatch, "dev", releases=[_firmware_release("v0.4.4"), dev, uploading]
    )

    ctrl.start_part()
    assert ctrl._firmware_manifest_url == "https://dl/0.4.5.dev3/manifest.json"
    assert _firmware_events(app)[-1]["latest_version"] == "0.4.5.dev3"


def test_a_failed_dev_release_lookup_clears_the_manifest(monkeypatch):
    ctrl, app, _ = _updater_with_channel(
        monkeypatch, "dev", releases=[_release("0.4.5.dev3", prerelease=True)]
    )

    ctrl.start_part()

    assert ctrl._firmware_manifest is None
    # Unresolved, so the next start looks the URL up again.
    assert ctrl._firmware_manifest_url is None
    assert (
        _result(ctrl.start_async_list_tft_releases)["error"]
        == "No GitHub release ships a firmware-manifest.json"
    )


def test_the_stable_channel_resolves_to_releases_latest(monkeypatch):
    ctrl, app, _ = _updater_with_channel(monkeypatch, "stable")

    _refresh_manifest(ctrl)

    assert ctrl._firmware_manifest_url == DEFAULT_CONFIG["update"]["firmware_manifest_url"]


def test_dev_channel_includes_prereleases_in_release_selection(monkeypatch):
    ctrl, _, _ = _updater_with_channel(monkeypatch, "dev")
    ctrl._release_infos = [
        _release("0.4.5.dev1", prerelease=True),
        _release("0.4.4"),
    ]

    assert ctrl._get_latest_release()["tag_name"] == "0.4.5.dev1"


def test_an_explicit_manifest_url_overrides_the_channel(monkeypatch):
    ctrl, app, _ = _updater_with_channel(
        monkeypatch, "dev", firmware_manifest_url="http://ha.local/local/firmware-manifest.json"
    )

    _refresh_manifest(ctrl)

    assert ctrl._firmware_manifest_url == "http://ha.local/local/firmware-manifest.json"


def test_a_channel_switch_refreshes_the_manifest_on_start(monkeypatch):
    """start_part compares the *resolved* URL, so switching channel re-reads it."""
    url = "http://ha.local/local/firmware-manifest.json"
    ctrl, app, _ = _updater_with_channel(
        monkeypatch, "dev", manifest="0.4.4.dev2", firmware_manifest_url=url
    )
    ctrl.start_part()
    assert _firmware_events(app)[-1]["latest_version"] == "0.4.4.dev2"

    ctrl.stop_part()
    # Drop the override: the stable channel now resolves to the GitHub URL,
    # which the fake does not serve — the old dev manifest must not linger.
    ctrl.config = {
        **ctrl.config,
        "firmware_update_channel": "stable",
        "firmware_manifest_url": DEFAULT_CONFIG["update"]["firmware_manifest_url"],
    }
    ctrl.start_part()

    assert ctrl._firmware_manifest is None
    assert _firmware_events(app)[-1]["latest_version"] is None

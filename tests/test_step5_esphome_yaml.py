"""Static checks for the ESPHome YAML (no ESPHome install needed)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "esphome" / "nspanel_haui"


def _read(name: str) -> str:
    return (ROOT / name).read_text()


def _load_tagged(path: Path) -> dict:
    """Parse ESPHome YAML, keeping custom tags (``!remove`` …) as ``"!<tag>"``."""
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    Loader.add_multi_constructor("!", lambda loader, suffix, node: f"!{suffix}")
    return yaml.load(path.read_text(), Loader=Loader)  # noqa: S506 - SafeLoader subclass


def test_hub_availability_reset_on_last_client_disconnect():
    api = _read("api.yaml")
    disconnected = api.split("on_client_disconnected:")[1].split("actions:")[0]
    assert "id(hub_availability) = global_api_server->is_connected();" in disconnected


def test_min_esphome_version_declared():
    assert "min_version: 2026.10.0" in _read("base.yaml")


def test_web_server_is_optional_and_off_by_default():
    """The web server costs flash/RAM; only the dev build enables it."""
    import re

    # base.yaml keeps only a commented example, so the shipped build omits it.
    assert not re.search(r"^web_server:", _read("base.yaml"), re.MULTILINE)
    # The local development build keeps the web UI for diagnostics.
    dev = (ROOT.parent / "nspanel_haui_dev.yaml").read_text()
    assert re.search(r"^web_server:", dev, re.MULTILINE)
    # The universal image bakes no web credentials because it has no web server.
    universal = (ROOT.parent / "nspanel_haui_universal.yaml").read_text()
    assert "web_username" not in universal


def test_unused_required_tft_version_removed():
    assert "required_tft_version" not in _read("version.yaml")


def test_http_request_buffers_fit_github_redirect_headers():
    """The firmware update entity needs room for GitHub's ~5.4 KB headers."""
    import re

    base = _read("base.yaml")
    assert re.search(r"^\s+buffer_size_rx:\s*8192\s*$", base, re.MULTILINE)
    assert re.search(r"^\s+buffer_size_tx:\s*2048\s*$", base, re.MULTILINE)


def test_command_spacing_is_enabled_to_prevent_nextion_rx_overflow():
    import re

    assert re.search(r"^\s+command_spacing:\s*2ms\s*$", _read("display.yaml"), re.MULTILINE)


def test_tft_upload_tx_buffer_fits_the_github_redirect():
    """GitHub redirects release TFTs to a ~870-character signed URL.

    The redirected request line overflows the 512-byte ESP-IDF default TX
    buffer, so every hub TFT install failed before the first byte.
    """
    import re

    match = re.search(
        r"^\s+tft_upload_http_buffer_size_tx:\s*(\d+)\s*$", _read("display.yaml"), re.MULTILINE
    )
    assert match and int(match.group(1)) >= 1024
    upload = (ROOT.parent / "nextion_patch" / "nextion" / "nextion_upload_esp32.cpp").read_text()
    assert ".buffer_size_tx = this->tft_upload_http_buffer_size_tx_" in upload


def test_tft_install_actions_live_in_the_integration():
    """Only the hub's transport action remains; installs go through nspanel_haui."""
    api = _read("api.yaml")
    assert "- action: upload_tft_url" in api
    assert "- action: upload_tft\n" not in api
    assert "id: tft_update" not in _read("button.yaml")


def test_buzzer_is_silenced_before_every_main_loop_stall():
    """rtttl turns a note off only from its loop(); the LEDC keeps sounding it.

    A blocked main loop (TFT upload, firmware OTA) or a reboot (a CPU-only
    reset leaves the LEDC running until the next boot's setup) left the note
    playing at that moment sounding continuously (#62).
    """
    import yaml

    base = yaml.safe_load(_read("base.yaml"))
    platforms = {ota["platform"]: ota for ota in base["ota"]}
    assert set(platforms) == {"esphome", "http_request"}
    for ota in platforms.values():
        assert {"script.execute": "suspend_activities"} in ota["on_begin"]
    assert {"script.execute": "suspend_activities"} in base["esphome"]["on_shutdown"]

    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    assert upload.index("script.execute: suspend_activities") < upload.index("upload_tft()")


def test_universal_image_keeps_its_wifi_across_firmware_updates():
    """ESPHome keys the captive-portal Wi-Fi to the config hash when the YAML
    defines a station network, so every firmware update forgot it and the panel
    fell back to its setup access point.  Without one it uses a fixed key; a
    boot migration (before WiFi's setup at priority 250) moves Wi-Fi saved by
    older builds there.
    """
    universal = _load_tagged(ROOT.parent / "nspanel_haui_universal.yaml")
    assert universal["wifi"]["ssid"] == "!remove"
    assert universal["wifi"]["password"] == "!remove"

    boot = universal["esphome"]["on_boot"]
    assert boot["priority"] > 250
    migrate = boot["then"][0]["lambda"]
    assert "88491487UL" in migrate
    assert "sizeof(saved)" in migrate
    assert "<nvs.h>" in universal["esphome"]["includes"]


def test_nextion_patch_is_never_older_than_the_package():
    """The package and the patch change together on dev.

    With the default 1-day cache a build combined a fresh display.yaml with an
    older patch: "[tft_upload_http_buffer_size_tx] is an invalid option".
    """
    package = (ROOT.parent / "nspanel_haui.yaml").read_text()
    block = package.split("external_components:")[1].split("packages:")[0]
    assert "path: esphome/nextion_patch" in block
    assert "refresh: 0s" in block


def test_firmware_can_be_flashed_from_a_url():
    """The hub installs other releases and custom builds through this action."""
    api = _read("api.yaml")
    block = api.split("- action: install_firmware_url")[1].split("- action:")[0]
    assert "md5sum: string" in block
    assert "ota.http_request.flash:" in block
    assert "md5: !lambda return md5sum;" in block
    assert "platform: http_request" in _read("base.yaml")

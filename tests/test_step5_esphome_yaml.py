"""Static checks for the ESPHome YAML (no ESPHome install needed)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "esphome" / "nspanel_haui"


def _read(name: str) -> str:
    return (ROOT / name).read_text()


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


def test_command_spacing_is_enabled_to_prevent_nextion_rx_overflow():
    import re

    assert re.search(r"^\s+command_spacing:\s*2ms\s*$", _read("display.yaml"), re.MULTILINE)

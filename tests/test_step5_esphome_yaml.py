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


def test_unused_required_tft_version_removed():
    assert "required_tft_version" not in _read("version.yaml")


def test_command_spacing_is_enabled_to_prevent_nextion_rx_overflow():
    import re

    assert re.search(r"^\s+command_spacing:\s*2ms\s*$", _read("display.yaml"), re.MULTILINE)

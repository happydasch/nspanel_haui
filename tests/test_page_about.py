from __future__ import annotations

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.page.about import AboutPage
from custom_components.nspanel_haui.haui.version import get_integration_version


class _Device:
    device_info = {"ip": "192.0.2.5", "yaml_version": "firmware-1", "tft_version": "display-2"}

    def get_name(self) -> str:
        return "Test panel"

    def get_locale(self) -> str:
        return "en_US"


class _Controller:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def send_cmd(self, command: str, value: str | list[str]) -> None:
        self.commands.extend(value if isinstance(value, list) else [value])


class _App:
    def __init__(self) -> None:
        self.device = _Device()
        self.controller = {"esphome": _Controller()}

    def log(self, msg: str, **kwargs) -> None:
        pass


def test_about_panel_labels_and_reports_integration_firmware_and_display_versions() -> None:
    app = _App()
    page = AboutPage(app, {"page_id": 2})
    page.render_panel(HAUIPanel(app, {}))

    commands = app.controller["esphome"].commands
    assert 'tHAUIVers.txt="Integration:"' in commands
    assert f'tHAUIVersVal.txt="{get_integration_version()}"' in commands
    assert 'tYamlVers.txt="Firmware:"' in commands
    assert 'tYamlVersVal.txt="firmware-1"' in commands
    assert 'tTftVersVal.txt="display-2"' in commands

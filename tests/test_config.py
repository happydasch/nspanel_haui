"""``HAUIConfig``: the validated config, its panels and the popup overrides."""

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_config import HAUIConfig


class DummyApp:
    def log(self, *args, **kwargs):
        pass


def test_get_panels_and_items():
    config = {
        "panels": [
            {
                "type": "grid",
                "key": "test_panel",
                "items": [{"item": "switch.test"}],
            }
        ],
    }
    app = DummyApp()
    ha_config = HAUIConfig(app, config)

    panels = ha_config.get_panels()
    sys_panels = ha_config.get("sys_panels", [])
    # 1 user panel + all auto-populated system panels
    assert len(panels) == 1 + len(sys_panels)
    # First panel should be the user panel
    assert panels[0].get("key") == "test_panel"


def _override(**panel):
    return HAUIConfig(DummyApp(), {"panels": [panel]}).get_panel(panel["key"])


def test_popup_override_keeps_system_defaults():
    """An edited popup keeps the system defaults it was not given."""
    sys_panels = [
        {"type": "popup_cover", "key": "popup_cover", "show_home_button": False},
    ]
    override = {"type": "cover", "key": "popup_cover", "title": "Blinds", "unlock_code": "12"}
    config = HAUIConfig(DummyApp(), {"panels": [override], "sys_panels": sys_panels})
    panel = config.get_panel("popup_cover")
    assert panel.get("show_home_button") is False
    assert panel.get("title") == "Blinds"
    assert panel.get("unlock_code") == "12"


@pytest.mark.parametrize(
    ("key", "panel_type"),
    [
        ("sys_system", "system"),
        ("sys_blank", "blank"),
        ("sys_settings", "system_settings"),
        ("sys_about", "system_about"),
    ],
)
def test_only_popups_can_be_overridden(key, panel_type):
    """System, Blank, Settings and About are fixed: a panel under their key is refused."""
    with pytest.raises(ValueError, match=key):
        _override(type=panel_type, key=key, title="T")


def test_system_override_stays_out_of_navigation():
    panel = _override(type="cover", key="popup_cover", show_in_navigation=True)
    assert panel.show_in_navigation() is False
    assert panel.get_type() == "cover"


def test_hub_driven_override_ignores_pin_and_auto_close():
    """A PIN on Unlock would re-open Unlock forever; auto-close would close queued
    notifications. The hub drives these panels, so both fields are dropped."""
    for key, panel_type in (
        ("popup_unlock", "popup_unlock"),
        ("popup_notify", "notify"),
        ("popup_select", "select"),
    ):
        panel = _override(type=panel_type, key=key, title="T", unlock_code="1", close_timeout=5)
        assert panel.get("unlock_code", "") == "", key
        assert panel.get("close_timeout", 0) == 0, key
        assert panel.get("title") == "T", key


def test_validation_keeps_unvalidated_device_keys():
    cfg = HAUIConfig(DummyApp(), {"device": {"name": "panel", "page_settle_delay": 0.3}})

    device = cfg.get("device")
    assert device["name"] == "panel"
    assert device["page_settle_delay"] == 0.3
    assert device["panels"] == [{"type": "clock"}]


def test_invalid_device_config_raises():
    with pytest.raises(ValueError):
        HAUIConfig(DummyApp(), {"device": {"timeout_display_off": "soon"}})

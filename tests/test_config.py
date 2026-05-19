from nspanel_haui.haui.abstract.haui_config import HAUIConfig


class DummyApp:
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

from nspanel_haui.haui.abstract.config import HAUIConfig


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
        "sys_panels": [],
    }
    app = DummyApp()
    ha_config = HAUIConfig(app, config)

    panels = ha_config.get_panels()
    assert len(panels) == 1
    assert panels[0].get("key") == "test_panel"

    item = ha_config.get_item("switch.test")
    assert item is not None
    assert item.get_item_type() == "switch"

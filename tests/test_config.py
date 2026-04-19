from apps.nspanel_haui.haui.abstract.config import HAUIConfig


class DummyApp:
    pass


def test_get_panels_and_entities():
    config = {
        "panels": [
            {
                "type": "grid",
                "key": "test_panel",
                "entities": [{"entity": "switch.test"}],
            }
        ],
        "sys_panels": [],
    }
    app = DummyApp()
    ha_config = HAUIConfig(app, config)

    panels = ha_config.get_panels()
    assert len(panels) == 1
    assert panels[0].get("key") == "test_panel"

    entity = ha_config.get_entity("switch.test")
    assert entity is not None
    assert entity.get_entity_type() == "switch"

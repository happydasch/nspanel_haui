"""Tests for the vacuum page: entity resolution, action button, listeners.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands, state listeners and service calls, so assertions are on what
reaches the display and Home Assistant.
"""

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.features import VacuumFeatures
from custom_components.nspanel_haui.haui.page.vacuum import VacuumPage
from custom_components.nspanel_haui.haui.utils.icon import get_icon

BASE_FEATURES = VacuumFeatures.START | VacuumFeatures.RETURN_HOME | VacuumFeatures.STATE


def _vacuum(state="docked", features=BASE_FEATURES):
    return Entity(state, {"friendly_name": "Robo", "supported_features": features})


def _show(vacuum, battery=None, **panel_cfg):
    entities = {"vacuum.robo": vacuum, "switch.mop": Entity("off", {"friendly_name": "Mop"})}
    if battery is not None:
        entities["sensor.battery"] = battery
    app = PageApp(entities)
    cfg = {"type": "vacuum", "item": {"item": "vacuum.robo"}}
    cfg.update(panel_cfg)
    panel = HAUIPanel(app, cfg)
    page = VacuumPage(app, {"page_id": 15})
    page.set_panel(panel)
    return app, page


def _press_action(page):
    page.callback_function_component(VacuumPage.COMPONENTS.btn_action.name, "action")


# item resolution


def test_no_selected_vacuum_hides_controls_and_keeps_secondary_items():
    app, page = _show(None, item=None, items=[{"item": "switch.mop"}])

    assert 'tStatus.txt=""' in app.cmds
    assert "vis bAction,0" in app.cmds
    assert "vis bHome,0" in app.cmds
    assert "vis bEntity1,1" in app.cmds
    page.callback_function_component(VacuumPage.COMPONENTS.btn_action.name, "action")


def test_unavailable_vacuum_displays_note_instead_of_controls():
    app, _page = _show(_vacuum(state="unavailable"))

    assert 'tStatus.txt="Unavailable"' in app.cmds
    assert "vis bAction,0" in app.cmds


def test_editor_panel_controls_configured_item_and_keeps_all_secondary_items():
    vacuum = _vacuum()
    app, page = _show(vacuum, items=[{"item": "switch.mop"}])

    _press_action(page)

    assert 'tTitle.txt="Robo"' in app.cmds
    assert vacuum.calls == [("start", {})]
    assert "vis bEntity1,1" in app.cmds


def test_popup_controls_item_passed_by_id():
    vacuum = _vacuum()
    app = PageApp({"vacuum.robo": vacuum})
    panel = HAUIPanel(app, {"type": "vacuum"})
    panel.apply_kwargs({"item": "vacuum.robo", "item_id": "vacuum.robo"})
    page = VacuumPage(app, {"page_id": 15})
    page.set_panel(panel)

    _press_action(page)

    assert vacuum.calls == [("start", {})]


# action button while cleaning


def test_cleaning_vacuum_with_pause_pauses():
    features = BASE_FEATURES | VacuumFeatures.PAUSE | VacuumFeatures.STOP
    vacuum = _vacuum(state="cleaning", features=features)
    _app, page = _show(vacuum)

    _press_action(page)

    assert vacuum.calls == [("pause", {})]


def test_cleaning_vacuum_without_pause_stops():
    vacuum = _vacuum(state="cleaning", features=BASE_FEATURES | VacuumFeatures.STOP)
    _app, page = _show(vacuum)

    _press_action(page)

    assert vacuum.calls == [("stop", {})]


# listeners


def test_page_listens_to_vacuum_state_only():
    vacuum = _vacuum()
    app, _page = _show(vacuum)

    assert [a for e, a in app.listeners if e == "vacuum.robo"] == [None]


# paused vacuum


def test_paused_vacuum_can_be_resumed():
    vacuum = _vacuum(state="paused", features=BASE_FEATURES | VacuumFeatures.PAUSE)
    app, page = _show(vacuum)

    _press_action(page)

    assert "tsw bAction,1" in app.cmds
    assert vacuum.calls == [("start", {})]


# battery


def _battery(level, icon=None):
    attributes = {"friendly_name": "Battery"}
    if icon:
        attributes["icon"] = icon
    return Entity(level, attributes)


def test_battery_sensor_level_picks_the_header_icon():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert "vis bFncRSec,1" in app.cmds
    assert f'bFncRSec.txt="{get_icon("mdi:battery-90")}"' in app.cmds


def test_battery_sensor_icon_attribute_wins_over_the_level():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87", icon="mdi:battery-charging"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert f'bFncRSec.txt="{get_icon("mdi:battery-charging")}"' in app.cmds


def test_battery_sensor_accepts_a_plain_entity_id():
    vacuum = _vacuum()
    app, _page = _show(vacuum, battery=_battery("42"), battery_sensor="sensor.battery")

    assert "vis bFncRSec,1" in app.cmds
    assert f'bFncRSec.txt="{get_icon("mdi:battery-40")}"' in app.cmds


def test_page_listens_to_the_battery_sensor():
    vacuum = _vacuum()
    app, _page = _show(
        vacuum,
        battery=_battery("87"),
        battery_sensor={"item": "sensor.battery"},
    )

    assert [a for e, a in app.listeners if e == "sensor.battery"] == [None]


def test_no_battery_icon_without_a_battery_sensor():
    vacuum = _vacuum()
    app, _page = _show(vacuum)

    assert "vis bFncRSec,1" not in app.cmds


def test_secondary_item_button_opens_the_items_popup_like_grid():
    app, page = _show(_vacuum(), items=[{"item": "switch.mop"}])
    executed = []
    page.execute_item = executed.append

    page.callback_function_component("bEntity1", "item")

    assert [item.get_item_id() for item in executed] == ["switch.mop"]


def _last_vis(cmds, name):
    return [cmd for cmd in cmds if cmd.startswith(f"vis {name},")][-1]


def test_vacuum_controls_come_back_when_the_vacuum_is_available_again():
    vacuum = _vacuum(state="docked")
    app, page = _show(vacuum)

    for state in ("unavailable", "docked"):
        vacuum.state = state
        page.callback_vacuum_entity("vacuum.robo", "state", None, state, {})

    for name in ("bAction", "bHome"):
        assert _last_vis(app.cmds, name) == f"vis {name},1"

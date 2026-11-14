"""Tests for the cover page: entity resolution and covers without a position.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands and service calls, so assertions are on what reaches the
display and Home Assistant.
"""

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.features import CoverFeatures
from custom_components.nspanel_haui.haui.page.cover import CoverPage

OPEN_CLOSE_STOP = CoverFeatures.OPEN | CoverFeatures.CLOSE | CoverFeatures.STOP


def _cover(state="open", **attrs):
    attributes = {"friendly_name": "Garage Door", "supported_features": OPEN_CLOSE_STOP}
    attributes.update(attrs)
    return Entity(state, attributes)


def _show(entity):
    app = PageApp({"cover.garage": entity})
    panel = HAUIPanel(app, {"type": "cover", "item": {"item": "cover.garage"}})
    page = CoverPage(app, {"page_id": 18})
    page.set_panel(panel)
    return app, page


def test_no_selected_item_hides_cover_controls_and_service_actions():
    entity = _cover()
    app = PageApp({"cover.garage": entity})
    panel = HAUIPanel(app, {"type": "cover"})
    page = CoverPage(app, {"page_id": 18})
    page.set_panel(panel)

    assert "vis bUp,0" in app.cmds
    assert "vis hVertPos,0" in app.cmds
    page.callback_cover_up(None, CoverPage.COMPONENTS.btn_up)
    page.process_cover_pos(50)

    assert entity.calls == []


def test_editor_panel_controls_configured_item():
    entity = _cover()
    app, page = _show(entity)

    page.callback_cover_down(None, CoverPage.COMPONENTS.btn_down)

    assert 'tTitle.txt="Garage Door"' in app.cmds
    assert entity.calls == [("close_cover", {})]


def test_popup_controls_item_passed_by_id():
    entity = _cover()
    app = PageApp({"cover.garage": entity})
    panel = HAUIPanel(app, {"type": "cover"})
    panel.apply_kwargs({"item": "cover.garage", "item_id": "cover.garage"})
    page = CoverPage(app, {"page_id": 18})
    page.set_panel(panel)

    page.callback_cover_up(None, CoverPage.COMPONENTS.btn_up)

    assert entity.calls == [("open_cover", {})]


def test_cover_without_position_shows_state_instead_of_zero_percent():
    app, _page = _show(_cover(state="open"))

    assert 'tInfo.txt="0%"' not in app.cmds
    assert 'tInfo.txt="Open"' in app.cmds


def test_open_cover_without_position_can_close_but_not_open():
    app, _page = _show(_cover(state="open"))

    assert "tsw bDown,1" in app.cmds
    assert "tsw bUp,0" in app.cmds


def test_closed_cover_without_position_can_open_but_not_close():
    app, _page = _show(_cover(state="closed"))

    assert "tsw bUp,1" in app.cmds
    assert "tsw bDown,0" in app.cmds


def test_unavailable_position_cover_leaves_slider_value_alone():
    features = OPEN_CLOSE_STOP | CoverFeatures.SET_POSITION
    app, _page = _show(_cover(state="unavailable", supported_features=features))

    assert not [cmd for cmd in app.cmds if cmd.startswith("hVertPos.val=")]


def test_cover_with_position_shows_percentage():
    features = OPEN_CLOSE_STOP | CoverFeatures.SET_POSITION
    app, _page = _show(_cover(state="open", supported_features=features, current_position=42))

    assert 'tInfo.txt="42%"' in app.cmds
    assert "hVertPos.val=42" in app.cmds
    assert "tsw bUp,1" in app.cmds
    assert "tsw bDown,1" in app.cmds


def _last_vis(cmds, name):
    return [cmd for cmd in cmds if cmd.startswith(f"vis {name},")][-1]


def test_cover_controls_come_back_when_the_cover_is_available_again():
    features = OPEN_CLOSE_STOP | CoverFeatures.SET_POSITION
    entity = _cover(state="open", current_position=100, supported_features=features)
    app, page = _show(entity)

    for state in ("unavailable", "open"):
        entity.state = state
        page.callback_cover_entity("cover.garage", "state", None, state, {})

    for name in ("bUp", "bStop", "bDown", "hVertPos"):
        assert _last_vis(app.cmds, name) == f"vis {name},1"

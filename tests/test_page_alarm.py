"""Tests for how the alarm page resolves its alarm entity.

The page runs its full ``set_panel`` lifecycle against a fake app that records
display commands and service calls, so assertions are on what reaches the
display and Home Assistant.
"""

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.color import ALARM_COLORS_LIGHT, Theme
from custom_components.nspanel_haui.haui.page.alarm import AlarmPage
from custom_components.nspanel_haui.haui.page.unlock import UnlockPage
from custom_components.nspanel_haui.haui.utils.color import parse_color_value

ENTITY_ID = "alarm_control_panel.home"
ARM_HOME_AND_AWAY = 1 | 2


def test_alarm_state_icon_uses_light_fixed_palette():
    app = PageApp({})
    app.theme = Theme("light")
    page = AlarmPage(app, {"page_id": 17})

    assert page._alarm_color("armed_home") == ALARM_COLORS_LIGHT["armed"]


def _alarm():
    return Entity("disarmed", {"friendly_name": "Home", "supported_features": ARM_HOME_AND_AWAY})


def _show(panel_cfg, kwargs=None):
    entity = _alarm()
    app = PageApp({ENTITY_ID: entity})
    panel = HAUIPanel(app, {"type": "alarm", **panel_cfg})
    if kwargs is not None:
        panel.apply_kwargs(kwargs)
    page = AlarmPage(app, {"page_id": 17})
    page.set_panel(panel)
    return app, page, entity


def test_no_selected_item_hides_keypad_and_disables_actions():
    app, page, entity = _show({})

    assert "vis bKey1,0" in app.cmds
    assert "vis b1Fnc,0" in app.cmds
    page.callback_keypad(None, AlarmPage.COMPONENTS.btn_key_1)
    page.callback_action(None, AlarmPage.COMPONENTS.b1_fnc)

    assert entity.calls == []


def test_editor_panel_controls_configured_item():
    app, page, entity = _show({"item": {"item": ENTITY_ID}})

    page.callback_action(None, AlarmPage.COMPONENTS.b1_fnc)

    assert 'tTitle.txt="Disarmed"' in app.cmds
    assert entity.calls == [("alarm_arm_home", {})]


def test_popup_controls_item_passed_by_id():
    # execute_item opens popup_alarm with the item config and its entity id
    app, page, entity = _show({}, kwargs={"item": ENTITY_ID, "item_id": ENTITY_ID})

    page.callback_action(None, AlarmPage.COMPONENTS.b2_fnc)

    assert entity.calls == [("alarm_arm_away", {})]


def test_dark_display_keeps_the_alarm_state_current():
    """The dark display is awake; see test_page_clock."""
    app, page, entity = _show({"item": {"item": ENTITY_ID}})
    app.device.device_info = {"display_state": "off"}
    app.cmds.clear()
    entity.state = "armed_away"

    page.callback_alarm_state(ENTITY_ID, "state", "disarmed", "armed_away", {})

    assert 'tTitle.txt="Armed away"' in app.cmds


ARM_HOME_AWAY_NIGHT = 1 | 2 | 4


def _show_with(panel_cfg, state="disarmed", features=ARM_HOME_AWAY_NIGHT):
    entity = Entity(state, {"friendly_name": "Home", "supported_features": features})
    app = PageApp({ENTITY_ID: entity})
    panel = HAUIPanel(app, {"type": "alarm", "item": {"item": ENTITY_ID}, **panel_cfg})
    page = AlarmPage(app, {"page_id": 17})
    page.set_panel(panel)
    return app, page, entity


def test_hidden_arm_modes_are_not_offered():
    app, page, entity = _show_with({"hidden_arm_modes": ["home"]})

    assert 'b1Fnc.txt="Away"' in app.cmds
    assert 'b2Fnc.txt="Night"' in app.cmds
    assert "vis b3Fnc,0" in app.cmds

    page.callback_action(None, AlarmPage.COMPONENTS.b1_fnc)
    assert entity.calls == [("alarm_arm_away", {})]


def test_action_icons_prefix_labels_that_fit():
    app, page, _entity = _show_with({"action_icons": True})

    night_icon = AlarmPage._ALARM_ICONS["armed_night"]
    assert f'b3Fnc.txt="{night_icon} Night"' in app.cmds


def test_action_icon_is_left_out_when_the_label_does_not_fit():
    app, page, _entity = _show_with({"action_icons": True}, state="armed_away")

    # "Disarm" + icon (3 bytes) + space = 10 bytes: fits
    disarm_icon = AlarmPage._ALARM_ICONS["disarmed"]
    assert f'b1Fnc.txt="{disarm_icon} Disarm"' in app.cmds

    page._show_action_button(AlarmPage.COMPONENTS.b2_fnc, "alarm_disarm", "Désarmer")
    assert 'b2Fnc.txt="Désarmer"' in app.cmds


_KEYPAD = [c.name for c in AlarmPage.COMPONENTS.values() if c.name.startswith("bKey")]


def test_keypad_takes_the_theme_colors_and_its_default_font():
    app, _page, _entity = _show_with({})
    theme = Theme()

    assert len(_KEYPAD) == 12
    for name in _KEYPAD:
        assert f"{name}.font=2" in app.cmds
        assert f"{name}.bco={theme.get('background')}" in app.cmds
        assert f"{name}.pco={theme.get('component_text')}" in app.cmds


def test_keypad_options_set_its_font_and_colors():
    app, _page, _entity = _show_with(
        {"keypad_font": 5, "keypad_bg_color": "#ff0000", "keypad_text_color": 12345}
    )

    for name in _KEYPAD:
        assert f"{name}.font=5" in app.cmds
        assert f"{name}.bco={parse_color_value('#ff0000')}" in app.cmds
        assert f"{name}.pco=12345" in app.cmds


def test_disarm_button_colors_apply_only_to_disarm():
    app, page, _entity = _show_with(
        {"disarm_button_color": 65535, "disarm_button_back_color": 3334}, state="armed_away"
    )

    assert "b1Fnc.pco=65535" in app.cmds
    assert "b1Fnc.bco=3334" in app.cmds


def test_arm_button_colors_keep_theme_when_unset():
    app, page, _entity = _show_with({"arm_button_color": "", "arm_button_back_color": None})
    themed_app, _page, _e = _show_with({})

    assert [c for c in app.cmds if c.startswith("b1Fnc.")] == [
        c for c in themed_app.cmds if c.startswith("b1Fnc.")
    ]


class _Navigation:
    page = None
    panel = None
    closed = 0

    def close_panel(self):
        self.closed += 1


def test_unlock_popup_keypad_enters_the_code_without_an_alarm_item():
    """The unlock popup has no alarm entity; its keypad must still take the code."""
    app = PageApp({})
    navigation = app.controller["navigation"] = _Navigation()
    locked = HAUIPanel(app, {"type": "grid", "key": "locked", "unlock_code": "12"})
    locked.set_state("locked", True)
    panel = HAUIPanel(app, {"type": "popup_unlock", "key": "popup_unlock"})
    panel.apply_kwargs({"unlock_panel": locked})
    page = UnlockPage(app, {"page_id": 17})
    page.set_panel(panel)

    page.callback_keypad(None, AlarmPage.COMPONENTS.btn_key_1)
    page.callback_keypad(None, AlarmPage.COMPONENTS.btn_key_2)
    page.callback_unlock(None, AlarmPage.COMPONENTS.b1_fnc)

    assert locked.get_state("locked") is False
    assert navigation.closed == 1


def test_the_unlock_popup_opens_without_the_code_of_the_last_unlock():
    app = PageApp({})
    app.controller["navigation"] = _Navigation()
    locked = HAUIPanel(app, {"type": "grid", "key": "locked", "unlock_code": "12"})
    panel = HAUIPanel(app, {"type": "popup_unlock", "key": "popup_unlock"})
    panel.apply_kwargs({"unlock_panel": locked})
    page = UnlockPage(app, {"page_id": 17})
    page.set_panel(panel)
    page.callback_keypad(None, AlarmPage.COMPONENTS.btn_key_1)
    page.callback_keypad(None, AlarmPage.COMPONENTS.btn_key_2)
    page.callback_unlock(None, AlarmPage.COMPONENTS.b1_fnc)

    locked.set_state("locked", True)
    page.set_panel(panel)
    page.callback_unlock(None, AlarmPage.COMPONENTS.b1_fnc)

    assert locked.get_state("locked") is True
    assert app.controller["navigation"].closed == 1

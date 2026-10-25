"""Row page rendering of slider and cover rows.

Pages are tested without HA: a bare ``RowPage`` records the Nextion commands
it sends, and items are minimal fakes exposing the HAUIItem accessors the
row page reads.
"""

import types

import pytest
from nspanel_haui.haui.abstract.haui_item import HAUIItem
from nspanel_haui.haui.features import CoverFeatures
from nspanel_haui.haui.page.row import RowPage

_COLORS = {"component_active": 1, "text_disabled": 2}


class _Item:
    def __init__(self, item_type, state, attrs=None):
        self.item_type = item_type
        self.state = state
        self.attrs = attrs or {}

    supports = HAUIItem.supports

    def get_item_type(self):
        return self.item_type

    def get_item_state(self):
        return self.state

    def get_item_attr(self, attr, default=None):
        return self.attrs.get(attr, default)

    def translate_item_state(self):
        return f"translated:{self.state}"

    def is_stale(self, max_age):
        return False


def _row_page():
    page = RowPage.__new__(RowPage)
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: _COLORS.get(key, 0)
    page.log = lambda *a, **kw: None
    # Sparse app for stale-data reads (threshold off → never stale).
    page.app = types.SimpleNamespace(
        device=types.SimpleNamespace(get=lambda key, default=0: default)
    )
    page._fnc_items = {}
    for name in [
        "r1_slider",
        "r1_slider_txt",
        "r1_btn_up",
        "r1_btn_stop",
        "r1_btn_down",
    ]:
        component = getattr(RowPage.COMPONENTS, name)
        page.set_function_component(component, component.name, name, row_index=0)
    return page


# --- slider rows ------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "step", "expected_max", "expected_val"),
    [
        # input_number reports float states even for integer steps
        ("21.0", 1, 15, 6),
        ("21", 1, 15, 6),
        ("21", 0.5, 150, 60),
        ("21.5", 0.5, 150, 65),
    ],
)
def test_slider_maps_state_to_scaled_value(state, step, expected_max, expected_val):
    page = _row_page()
    item = _Item("input_number", state, {"min": 15, "max": 30, "step": step})

    page.update_item_slider(item, 1)

    assert f"r1Slider.maxval={expected_max}" in page.cmds
    assert f"r1Slider.val={expected_val}" in page.cmds
    assert f'r1SliderTxt.txt="{state}"' in page.cmds


@pytest.mark.parametrize("state", ["unavailable", "unknown", None])
def test_slider_without_numeric_state_shows_state_text(state):
    page = _row_page()
    item = _Item("input_number", state, {"min": 15, "max": 30, "step": 1})

    page.update_item_slider(item, 1)

    assert "r1Slider.val=0" in page.cmds
    assert f'r1SliderTxt.txt="translated:{state}"' in page.cmds


# --- cover rows -------------------------------------------------------------

_ALL_COVER_FEATURES = CoverFeatures.OPEN | CoverFeatures.CLOSE | CoverFeatures.STOP


def _button_color(page, name):
    colors = [c for c in page.cmds if c.startswith(f"{name}.pco=")]
    return int(colors[-1].split("=")[1])


@pytest.mark.parametrize(
    ("state", "position", "stop_enabled"),
    [
        ("closed", 0, False),
        ("open", 100, False),
        ("opening", 40, True),
        ("closing", 40, True),
    ],
)
def test_cover_stop_enabled_only_while_moving(state, position, stop_enabled):
    page = _row_page()
    item = _Item(
        "cover",
        state,
        {"supported_features": _ALL_COVER_FEATURES, "current_position": position},
    )

    page.update_item_cover(item, 1)

    expected = _COLORS["component_active"] if stop_enabled else _COLORS["text_disabled"]
    assert _button_color(page, "r1BtnStop") == expected


def test_cover_with_missing_entity_renders_disabled_buttons():
    page = _row_page()
    item = _Item("cover", None)

    page.update_item_cover(item, 1)

    for name in ["r1BtnUp", "r1BtnStop", "r1BtnDown"]:
        assert _button_color(page, name) == _COLORS["text_disabled"]

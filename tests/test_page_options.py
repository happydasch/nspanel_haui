"""A page reads its options with the defaults its descriptor declares, and nowhere else.

The editor shows ``PageOption.default`` for an option the panel leaves out; a
second copy of that default in the page's code could disagree with it.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.panel import PANEL_MAPPING
from custom_components.nspanel_haui.haui.page.alarm import AlarmPage
from custom_components.nspanel_haui.haui.page.clock import ClockPage
from custom_components.nspanel_haui.haui.page.unlock import UnlockPage


def _panel(**config) -> HAUIPanel:
    return HAUIPanel(None, config)  # type: ignore[arg-type]


def _page(cls):
    return cls.__new__(cls)


def test_an_option_the_panel_leaves_out_takes_the_descriptors_default():
    page = _page(ClockPage)

    assert page.option(_panel(type="clock"), "show_weather") is True
    assert page.option(_panel(type="clock", show_weather=False), "show_weather") is False


def test_an_option_the_page_does_not_declare_is_refused():
    with pytest.raises(KeyError):
        _page(ClockPage).option(_panel(type="clock"), "not_an_option")


def test_a_page_reads_the_options_of_the_page_it_extends():
    """The unlock popup styles its keypad with the alarm page's keypad options."""
    alarm_default = next(o.default for o in AlarmPage.DESCRIPTOR.options if o.key == "keypad_font")

    assert _page(UnlockPage).option(_panel(type="popup_unlock"), "keypad_font") == alarm_default


def test_a_list_default_is_a_fresh_copy_for_every_read():
    page = _page(AlarmPage)
    panel = _panel(type="alarm")

    page.option(panel, "hidden_arm_modes").append("armed_home")

    assert page.option(panel, "hidden_arm_modes") == []


def _declared_options(cls) -> set[str]:
    keys: set[str] = set()
    for klass in cls.__mro__:
        descriptor = klass.__dict__.get("DESCRIPTOR")
        if descriptor is not None:
            keys |= {option.key for option in descriptor.options or []}
    return keys


def test_pages_read_their_declared_options_through_option():
    """``panel.get("<option>", <default>)`` would hold a second copy of the default."""
    declared_by_module: dict[str, set[str]] = {}
    for _page_name, cls in PANEL_MAPPING.values():
        path = sys.modules[cls.__module__].__file__
        declared_by_module.setdefault(path, set()).update(_declared_options(cls))

    copies = []
    for path, declared in declared_by_module.items():
        for node in ast.walk(ast.parse(Path(path).read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and ast.unparse(node.func.value) in ("panel", "self.panel")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in declared
            ):
                copies.append(f"{Path(path).name}:{node.lineno} {ast.unparse(node)}")

    assert copies == []

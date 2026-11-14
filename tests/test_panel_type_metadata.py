"""What the hub serves the editor about each panel type: its physical HMI page
(``page_id``), catalog category, components and options, for user panel types,
system panel entries and popup aliases."""

from __future__ import annotations

import pytest

from custom_components.nspanel_haui.haui.mapping.const import PopupPanelKey, SysPanelKey
from custom_components.nspanel_haui.haui.mapping.descriptor import (
    PANEL_CATEGORIES,
    page_category,
)
from custom_components.nspanel_haui.haui.mapping.panel import (
    PAGE_MAPPING,
    POPUP_PANEL_MAPPING,
    SYS_PANEL_MAPPING,
    get_system_panel_entries,
    get_user_panel_type_descriptors,
)
from custom_components.nspanel_haui.haui.page.blank import BlankPage


def _valid_page_id(pid) -> bool:
    return isinstance(pid, int) and pid in PAGE_MAPPING


def test_user_panel_type_descriptors_expose_a_physical_page():
    descriptors = get_user_panel_type_descriptors()
    assert descriptors
    for descriptor in descriptors:
        assert descriptor["type_key"]
        assert _valid_page_id(descriptor["page_id"]), (
            f"{descriptor['type_key']} has invalid page_id {descriptor['page_id']!r}"
        )
    # Cover the full set of user-visible types.
    keys = {d["type_key"] for d in descriptors}
    assert {"grid", "row", "light", "climate", "clock", "weather"} <= keys


def test_system_panel_entries_expose_a_physical_page_including_popups():
    entries = get_system_panel_entries()
    assert entries
    for entry in entries:
        assert _valid_page_id(entry["page_id"]), (
            f"{entry['key']} has invalid page_id {entry['page_id']!r}"
        )
    keys = {e["key"] for e in entries}
    # Popup aliases resolve to their physical pages.
    assert "popup_unlock" in keys
    assert "popup_notify" in keys


def test_popup_unlock_uses_the_alarm_physical_page():
    by_key = {e["key"]: e for e in get_system_panel_entries()}
    assert by_key["popup_unlock"]["page_id"] == 17  # alarm page (17)
    # The alarm panel itself is a user type on the same physical page.
    user = {d["type_key"]: d for d in get_user_panel_type_descriptors()}
    assert user["alarm"]["page_id"] == 17


def test_page_id_matches_the_hub_page_mapping():
    for descriptor in get_user_panel_type_descriptors():
        assert PAGE_MAPPING[descriptor["page_id"]]


def test_every_user_panel_type_has_a_catalog_category():
    """The editor's *Add panel* catalog lists the types under their category."""
    known = {c.key for c in PANEL_CATEGORIES}
    assert known == {"backgrounds", "entities", "grouping", "tools"}
    for descriptor in get_user_panel_type_descriptors():
        category = descriptor["category"]
        assert category["key"] in known, f"{descriptor['type_key']} has no catalog category"
        assert category["label"] == page_category(category["key"]).label
        assert category["icon"] == page_category(category["key"]).icon
    by_key = {d["type_key"]: d["category"]["key"] for d in get_user_panel_type_descriptors()}
    assert by_key["clock"] == by_key["clocktwo"] == by_key["weather"] == "backgrounds"
    assert by_key["grid"] == by_key["row"] == "grouping"
    assert by_key["light"] == by_key["climate"] == by_key["cover"] == "entities"
    assert by_key["alarm"] == by_key["qr"] == by_key["timer"] == "tools"


def test_user_panel_types_are_ordered_by_category():
    """The catalog groups whatever it is handed in order, so the hub sorts its list."""
    order = [c.key for c in PANEL_CATEGORIES]
    keys = [d["category"]["key"] for d in get_user_panel_type_descriptors()]
    assert keys == sorted(keys, key=order.index)


def test_an_unknown_panel_category_is_refused():
    """A type the catalog cannot group is a bug, not a fallback group."""
    with pytest.raises(ValueError, match="Unknown panel category"):
        page_category("nonsense")


def test_system_panel_entries_flag_hub_driven_panels():
    """The editor hides PIN and auto-close for the panels the hub drives."""
    driven = {e["key"] for e in get_system_panel_entries() if e["hub_driven"]}
    assert driven == {"popup_notify", "popup_select", "popup_unlock"}


def test_system_panels_and_popups_are_mapped_apart():
    """System, Blank, Settings and About are the fixed system panels; every
    ``popup_*`` key is a popup, the system popups (notify, select, unlock) too.
    The key enums list exactly the panels each mapping registers."""
    assert set(SYS_PANEL_MAPPING) == set(SysPanelKey)
    assert set(SysPanelKey) == {"sys_system", "sys_blank", "sys_settings", "sys_about"}
    assert set(POPUP_PANEL_MAPPING) == set(PopupPanelKey)
    assert all(key.startswith("popup_") for key in PopupPanelKey)
    assert POPUP_PANEL_MAPPING[PopupPanelKey.POPUP_NOTIFY] == "notify"


def test_only_popup_system_panels_are_editable():
    """The editor edits the popups only; System, Blank, Settings and About are fixed."""
    entries = get_system_panel_entries()
    editable = {e["key"] for e in entries if e["editable"]}
    fixed = {e["key"] for e in entries if not e["editable"]}
    assert editable == {e["key"] for e in entries if e["key"].startswith("popup_")}
    assert fixed == {"sys_system", "sys_blank", "sys_settings", "sys_about"}


# Clock, weather and clocktwo have no ``bFnc*`` widgets: the ids 3-6 belong to
# other widgets on those Nextion pages, and the component list is served to the editor.
@pytest.mark.parametrize("type_key", ["clock", "weather", "clocktwo"])
def test_headerless_page_components_have_no_header_buttons(type_key):
    (descriptor,) = [d for d in get_user_panel_type_descriptors() if d["type_key"] == type_key]
    components = descriptor["components"]

    assert descriptor["has_header"] is False
    assert [c["name"] for c in components if c["name"].startswith("bFnc")] == []
    ids = [c["id"] for c in components]
    assert len(ids) == len(set(ids))


def test_blank_page_declares_only_its_own_widget():
    assert [c.name for c in BlankPage.COMPONENTS.values()] == ["hBlank"]


@pytest.mark.parametrize(
    ("type_key", "options_key", "color_keys"),
    [
        (
            "alarm",
            "options",
            {
                "keypad_bg_color",
                "keypad_text_color",
                "arm_button_color",
                "arm_button_back_color",
                "disarm_button_color",
                "disarm_button_back_color",
            },
        ),
        ("clocktwo", "options", {"off_color", "letter_color", "special_color"}),
        (
            "grid",
            "item_options",
            {"text_color", "back_color", "color_pressed", "back_color_pressed", "power_color"},
        ),
    ],
)
def test_pages_with_colors_of_their_own_serve_them_as_color_options(
    type_key, options_key, color_keys
):
    (descriptor,) = [d for d in get_user_panel_type_descriptors("pl") if d["type_key"] == type_key]
    options = {option["key"]: option for option in descriptor[options_key]}

    assert color_keys <= options.keys()
    assert all(options[key]["kind"] == "color" for key in color_keys)

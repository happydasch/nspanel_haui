"""Panel-type descriptors expose the physical HMI page the editor's simulator
preview jumps to (page_id), for user panel types, system panel entries and
popup aliases."""

from __future__ import annotations

from nspanel_haui.haui.mapping.const import PopupPanelKey, SysPanelKey
from nspanel_haui.haui.mapping.panel import (
    PAGE_MAPPING,
    POPUP_PANEL_MAPPING,
    SYS_PANEL_MAPPING,
    get_system_panel_entries,
    get_user_panel_type_descriptors,
)


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

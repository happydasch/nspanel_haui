"""Panel-type descriptors expose the physical HMI page the editor's simulator
preview jumps to (page_id), for user panel types, system panel entries and
popup aliases."""

from __future__ import annotations

from nspanel_haui.haui.mapping.panel import (
    PAGE_MAPPING,
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

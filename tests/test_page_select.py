"""Select popup: what the selection callback receives when an entry is tapped."""

from custom_components.nspanel_haui.haui.page.select import SelectPage

_PAGE_ID = 5


class _Device:
    is_portrait = False

    def get(self, key, default=None):
        return {}.get(key, default)


class _DeviceConfig:
    def get_panels(self, show_in_navigation):
        return ["panel_a", "panel_b"]


class _Navigation:
    def __init__(self):
        self.closed = 0

    def close_panel(self):
        self.closed += 1


class _App:
    def __init__(self):
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.controller = {"navigation": _Navigation()}

    def log(self, msg, **kwargs):
        pass


class _Panel:
    id = "panel-id"

    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_type(self):
        return "select"

    def get_title(self, default=""):
        return default


def _select_page(**panel_config):
    page = SelectPage(_App(), {"page_id": _PAGE_ID})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: 0
    page._auto_assign_fncs = lambda panel: None
    selections = []
    page.set_panel(_Panel({"selection_callback_fnc": selections.append, **panel_config}))
    return page, selections


def test_tapping_selected_entry_reports_it_again():
    page, selections = _select_page(items=["low", "auto", "high"], selected="auto")

    page.callback_select(None, SelectPage.COMPONENTS.btn_sel_2)

    assert selections == ["auto"]
    assert page.app.controller["navigation"].closed == 1


def test_tapping_other_entry_reports_it():
    page, selections = _select_page(items=["low", "auto", "high"], selected="auto")

    page.callback_select(None, SelectPage.COMPONENTS.btn_sel_3)

    assert selections == ["high"]


def test_a_select_popup_does_not_inherit_the_previous_popups_options():
    """Media's group popup (multiple) and then its source popup (single) on one page."""
    page, _selections = _select_page(
        items=["Kitchen", "Office"], selected=["Kitchen"], multiple=True
    )
    page._current_page = 1

    page.set_panel(_Panel({"items": ["Radio 1", "Radio 2"], "selected": "Radio 1"}))

    assert page._multiple is False
    assert page._selected == "Radio 1"
    assert 'bSel1.txt="Radio 1"' in page.cmds


def test_long_selection_label_is_shortened_without_changing_selected_value():
    label = "Laundry cycle complete: remove the clothes now"
    page, selections = _select_page(items=[{"value": "notification-1", "name": label}])

    command = next(cmd for cmd in page.cmds if cmd.startswith("bSel1.txt="))
    assert command.endswith('.."')
    assert label not in command

    page.callback_select(None, SelectPage.COMPONENTS.btn_sel_1)

    assert selections == ["notification-1"]

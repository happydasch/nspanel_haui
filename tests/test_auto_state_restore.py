"""Tests that popups restore the auto dimming/page/sleep switches they found.

HA switch entities report ``"on"``/``"off"`` strings, so a popup that turns
the switches off on open must only turn back on the ones that were ``"on"``.
"""

import contextlib

from nspanel_haui.haui.abstract.haui_page import HAUIPage
from nspanel_haui.haui.page.qr import QRPage
from nspanel_haui.haui.page.settings import SettingsPage


class _Switch:
    def __init__(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def turn_on(self):
        self.state = "on"

    def turn_off(self):
        self.state = "off"


class _Number:
    def __init__(self, entity_id):
        self.entity_id = entity_id

    def get_state(self):
        return "50"

    def listen_state(self, cb):
        return f"listen-{self.entity_id}"


class _App:
    def __init__(self, items, name="panel", slug="panel"):
        self.items = items
        self.device = type("Device", (), {"get_name": lambda s: name, "get_slug": lambda s: slug})()

    def get_item(self, entity_id):
        return self.items[entity_id]

    def cancel_listen_state(self, handle):
        pass


def _switches(dimming, page, sleeping, slug="panel"):
    return {
        f"switch.{slug}_use_auto_dimming": _Switch(dimming),
        f"switch.{slug}_use_auto_page": _Switch(page),
        f"switch.{slug}_use_auto_display_off": _Switch(sleeping),
    }


def _states(items):
    return {k: v.state for k, v in items.items() if k.startswith("switch.")}


class _NoDisplay:
    """Replaces display-side helpers so start_panel runs without a device."""

    @property
    def rec_cmd(self):
        return contextlib.nullcontext()

    def on_release(self, *args, **kwargs):
        pass

    def bind_slider(self, *args, **kwargs):
        pass

    def set_function_buttons(self, *args, **kwargs):
        pass

    def set_function_component(self, *args, **kwargs):
        pass

    def set_component_text(self, *args, **kwargs):
        pass

    def get_color(self, key):
        return 0

    def _auto_assign_fncs(self, panel):
        pass

    def _apply_zoom_state(self):
        pass

    def _render_text(self, panel):
        pass

    def _build_items_from_panel(self, panel, key):
        return []


class _Panel:
    def get(self, key, default=None):
        return default

    def get_title(self):
        return ""


class _QRPage(_NoDisplay, QRPage):
    pass


class _SettingsPage(_NoDisplay, SettingsPage):
    pass


def test_popup_auto_state_restore_leaves_off_switches_off():
    items = _switches(dimming="off", page="on", sleeping="off")
    page = HAUIPage.__new__(HAUIPage)
    page.app = _App(items)

    saved = page._save_auto_state()
    page._restore_auto_state(saved)

    assert _states(items) == {
        "switch.panel_use_auto_dimming": "off",
        "switch.panel_use_auto_page": "on",
        "switch.panel_use_auto_display_off": "off",
    }


def test_qr_page_close_leaves_off_switches_off():
    items = _switches(dimming="off", page="off", sleeping="off")
    page = _QRPage.__new__(_QRPage)
    page.app = _App(items)

    page.start_panel(_Panel())
    page._stop_panel(_Panel())

    assert _states(items)["switch.panel_use_auto_dimming"] == "off"
    assert _states(items)["switch.panel_use_auto_page"] == "off"


def test_settings_page_close_leaves_auto_dimming_off():
    items = _switches(dimming="off", page="on", sleeping="on")
    items["number.panel_brightness_full"] = _Number("number.panel_brightness_full")
    items["number.panel_brightness_dimmed"] = _Number("number.panel_brightness_dimmed")
    page = _SettingsPage.__new__(_SettingsPage)
    page.app = _App(items)
    page._handle_brightness_full = None
    page._handle_brightness_dimmed = None

    page.start_panel(_Panel())
    page._stop_panel(_Panel())

    assert _states(items)["switch.panel_use_auto_dimming"] == "off"


def test_settings_page_close_restores_auto_dimming_that_was_on():
    items = _switches(dimming="on", page="on", sleeping="on")
    items["number.panel_brightness_full"] = _Number("number.panel_brightness_full")
    items["number.panel_brightness_dimmed"] = _Number("number.panel_brightness_dimmed")
    page = _SettingsPage.__new__(_SettingsPage)
    page.app = _App(items)
    page._handle_brightness_full = None
    page._handle_brightness_dimmed = None

    page.start_panel(_Panel())
    assert _states(items)["switch.panel_use_auto_dimming"] == "off"
    page._stop_panel(_Panel())

    assert _states(items)["switch.panel_use_auto_dimming"] == "on"


def test_popup_auto_state_uses_device_slug_not_raw_name():
    """A device named "NSPanel-Living" owns switch.nspanel_living_use_auto_*."""
    items = _switches(dimming="on", page="on", sleeping="off", slug="nspanel_living")
    page = HAUIPage.__new__(HAUIPage)
    page.app = _App(items, name="NSPanel-Living", slug="nspanel_living")

    saved = page._save_auto_state()
    assert _states(items) == {
        "switch.nspanel_living_use_auto_dimming": "off",
        "switch.nspanel_living_use_auto_page": "off",
        "switch.nspanel_living_use_auto_display_off": "off",
    }
    page._restore_auto_state(saved)

    assert _states(items) == {
        "switch.nspanel_living_use_auto_dimming": "on",
        "switch.nspanel_living_use_auto_page": "on",
        "switch.nspanel_living_use_auto_display_off": "off",
    }

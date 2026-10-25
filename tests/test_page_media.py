"""Media page: controls, group button and volume slider.

The page is constructed for real (so ``prepare()`` runs) and shown through
``set_panel()``; the display, HA entity and timers are fakes.  Assertions are
on the Nextion commands sent and the media_player services called.
"""

import pytest
from nspanel_haui.haui.abstract import haui_page as haui_page_module
from nspanel_haui.haui.abstract.haui_event import HAUIEvent
from nspanel_haui.haui.abstract.haui_item import HAUIItem
from nspanel_haui.haui.features import MediaPlayerFeatures as F
from nspanel_haui.haui.mapping.const import ESPEvent, ESPResponse
from nspanel_haui.haui.page import media as media_module
from nspanel_haui.haui.page.media import MediaPage

_COLORS = {"component_active": 1, "text_disabled": 2}
_PAGE_ID = 14
_ENTITY_ID = "media_player.kitchen"


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)


class _DeviceConfig:
    def get_panels(self, show_in_navigation):
        return ["panel_a", "panel_b"]


class _App:
    def __init__(self):
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.controller = {}

    def log(self, msg, **kwargs):
        pass

    def run_in(self, cb, delay, **kwargs):
        return "timer"

    def run_every(self, cb, start, interval, **kwargs):
        return "interval"

    def cancel_timer(self, handle):
        pass

    def listen_state(self, cb, entity_id, attribute=None, **kwargs):
        return "listener"

    def cancel_listen_state(self, handle):
        pass


class _MediaItem:
    def __init__(self, state, attrs):
        self.state = state
        self.attrs = attrs
        self.calls = []

    supports = HAUIItem.supports

    def has_item_id(self):
        return True

    def get_item_id(self):
        return _ENTITY_ID

    def get_item_state(self):
        return self.state

    def get_item_attr(self, attr, default=None):
        return self.attrs.get(attr, default)

    def get_icon(self):
        return "icon"

    def get_color(self):
        return 0

    def call_item_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class _Panel:
    id = "panel-id"

    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_type(self):
        return "media"

    def get_title(self, default=""):
        return default


def _media_page():
    page = MediaPage(_App(), {"page_id": _PAGE_ID})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.esphome = []
    page.send_esphome = lambda *args, **kwargs: page.esphome.append(args)
    page.get_color = lambda key: _COLORS.get(key, 0)
    page.translate = lambda text: text
    page._auto_assign_fncs = lambda panel: None
    return page


def _show(monkeypatch, item, **panel_config):
    monkeypatch.setattr(haui_page_module, "HAUIItem", lambda app, config: item)
    page = _media_page()
    page.set_panel(_Panel({"item_id": _ENTITY_ID, **panel_config}))
    return page


def _last_color(page, name):
    colors = [c for c in page.cmds if c.startswith(f"{name}.pco=")]
    return int(colors[-1].split("=")[1])


def test_new_page_renders_without_panel_state():
    page = _media_page()

    page.render_panel(_Panel({}))

    assert 'tTitle.txt=""' in page.cmds


def test_track_controls_enabled_without_queue_attributes(monkeypatch):
    """Players other than Sonos expose no queue_position/queue_size."""
    features = F.PLAY | F.PAUSE | F.PREVIOUS_TRACK | F.NEXT_TRACK | F.SHUFFLE_SET | F.REPEAT_SET
    item = _MediaItem(
        "playing", {"supported_features": features, "shuffle": False, "repeat": "off"}
    )

    page = _show(monkeypatch, item)

    for name in ["bPrev", "bNext", "bShuffle", "bRepeat"]:
        assert _last_color(page, name) == _COLORS["component_active"]
        assert f"tsw {name},0" not in page.cmds


@pytest.mark.parametrize(
    ("group_members", "group_items", "visible"),
    [
        (["media_player.kitchen", "media_player.office"], [], True),
        # HA reports None for a grouping-capable player that isn't grouped
        (None, ["media_player.office"], True),
        (None, [], False),
    ],
)
def test_group_button_follows_group_members(monkeypatch, group_members, group_items, visible):
    item = _MediaItem(
        "playing", {"supported_features": F.GROUPING, "group_members": group_members}
    )

    page = _show(monkeypatch, item, group_items=group_items)

    assert ("vis m2Btn,1" in page.cmds) is visible


def test_group_popup_lists_configured_players_when_ungrouped(monkeypatch):
    item = _MediaItem("playing", {"supported_features": F.GROUPING, "group_members": None})
    page = _show(monkeypatch, item, group_items=["media_player.office"])
    opened = []
    navigation = type("Nav", (), {"open_panel": lambda s, key, **kw: opened.append(kw)})()
    page.app.controller["navigation"] = navigation
    monkeypatch.setattr(
        media_module,
        "HAUIEntity",
        lambda app, entity_id: type("E", (), {"get_entity_attr": lambda s, a, d: d})(),
    )

    page.callback_select_group(None, MediaPage.COMPONENTS.m2_overlay)
    opened[0]["selection_callback_fnc"](["media_player.office"])

    assert [i["value"] for i in opened[0]["items"]] == ["media_player.office"]
    assert item.calls == [("join", {"group_members": ["media_player.office"]})]


def test_volume_slider_is_a_drag_control(monkeypatch):
    item = _MediaItem("playing", {"supported_features": F.VOLUME_SET, "volume_level": 0.2})
    page = _show(monkeypatch, item)
    volume = MediaPage.COMPONENTS.h_volume

    # releasing the slider must not navigate (swipe) and must not read yet:
    # the Nextion only finalizes the slider value once the touch ends
    page.process_event(HAUIEvent(ESPEvent.COMPONENT, f"{_PAGE_ID},{volume.id},0"))
    assert page.is_gesture_suppressed() is True
    assert page.esphome == []

    page.process_event(HAUIEvent(ESPEvent.TOUCH_END, "10,20,10,200"))
    assert len(page.esphome) == 1

    page.process_event(
        HAUIEvent(ESPResponse.READ_RESPONSE, '{"name":"hVolume","type":"number","value":"42"}')
    )
    assert item.calls == [("volume_set", {"volume_level": 0.42})]

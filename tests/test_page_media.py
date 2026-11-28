"""Media page: controls, group button and volume slider.

The page is constructed for real (so ``prepare()`` runs) and shown through
``set_panel()``; the display, HA entity and timers are fakes.  Assertions are
on the Nextion commands sent and the media_player services called.
"""

import json
from pathlib import Path

import pytest
from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract import haui_page as haui_page_module
from custom_components.nspanel_haui.haui.abstract.haui_event import HAUIEvent
from custom_components.nspanel_haui.haui.abstract.haui_item import HAUIItem
from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.features import MediaPlayerFeatures as F
from custom_components.nspanel_haui.haui.mapping.color import Theme
from custom_components.nspanel_haui.haui.mapping.const import ESPEvent, ESPResponse
from custom_components.nspanel_haui.haui.page import media as media_module
from custom_components.nspanel_haui.haui.page.media import ICON_RECT, MediaPage
from custom_components.nspanel_haui.haui.utils.image_program import Rect
from custom_components.nspanel_haui.haui.version import DRAW_RUNS_FIRMWARE_VERSION

_COLORS = {"component_active": 1, "text_disabled": 2}
_PAGE_ID = MediaPage.DESCRIPTOR.page_id
_ENTITY_ID = "media_player.kitchen"
LAYOUTS = Path(__file__).resolve().parent.parent / "custom_components/nspanel_haui/frontend/virtual"
#: The device info a panel reports once it is connected; a firmware without the
#: ``draw_runs`` action cannot paint a cover.
_DEVICE_INFO = {"yaml_version": DRAW_RUNS_FIRMWARE_VERSION}
_PICTURE = "/api/media_player_proxy/media_player.kitchen?token=abc"


class _Device:
    is_portrait = False
    device_info = {}

    def get(self, key, default=None):
        return {}.get(key, default)


class _DeviceConfig:
    def get_panels(self, show_in_navigation):
        return ["panel_a", "panel_b"]


class _App:
    def __init__(self):
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.theme = Theme("dark")
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

    def is_internal(self):
        return False

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
    monkeypatch.setattr(haui_page_module, "HAUIItem", lambda app, config, **kwargs: item)
    page = _media_page()
    panel = _Panel({"item_id": _ENTITY_ID, **panel_config})
    panel.theme = page.app.theme
    page.set_panel(panel)
    return page


def _last_color(page, name):
    colors = [c for c in page.cmds if c.startswith(f"{name}.pco=")]
    return int(colors[-1].split("=")[1])


def test_new_page_renders_without_panel_state():
    page = _media_page()

    page.render_panel(_Panel({}))

    assert 'tTitle.txt=""' in page.cmds
    assert 'tMTitle.txt=""' in page.cmds
    assert 'tMInterpret.txt=""' in page.cmds
    assert "vis bPower,0" in page.cmds
    assert "vis m1Btn,0" in page.cmds
    assert "vis m2Btn,0" in page.cmds
    assert "vis m3Btn,0" in page.cmds


def test_unknown_media_entity_shows_a_note_and_hides_power(monkeypatch):
    item = _MediaItem("unknown", {})
    page = _show(monkeypatch, item)

    assert 'tMTitle.txt="Unavailable"' in page.cmds
    assert "vis bPower,0" in page.cmds


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
    item = _MediaItem("playing", {"supported_features": F.GROUPING, "group_members": group_members})

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


def test_long_media_entity_label_is_shortened_to_fit_button():
    page = MediaPage.__new__(MediaPage)
    page.app = _App()
    page.show_component = lambda _component: None
    rendered = []
    page.set_component_text = lambda component, text: rendered.append((component, text))

    page.set_media_button(1, "icon", "Kitchen speaker with a very long name")

    assert rendered[-1][0] == MediaPage.COMPONENTS.m1_name
    assert rendered[-1][1].endswith("..")


def _last_vis(cmds, name):
    return [cmd for cmd in cmds if cmd.startswith(f"vis {name},")][-1]


def test_media_controls_come_back_when_the_player_is_available_again(monkeypatch):
    features = F.PLAY | F.PAUSE | F.PREVIOUS_TRACK | F.NEXT_TRACK | F.VOLUME_SET
    item = _MediaItem("playing", {"supported_features": features, "volume_level": 0.5})
    page = _show(monkeypatch, item)

    for state in ("unavailable", "playing"):
        item.state = state
        page.callback_media_entity(_ENTITY_ID, "state", None, state, {})

    for name in ("bPlay", "bPrev", "bNext", "hVolume"):
        assert _last_vis(page.cmds, name) == f"vis {name},1"


def test_a_light_theme_repaints_the_white_body_text():
    """The TFT compiles the media title white; a light page needs it dark.

    The page's Preinitialize theme code paints the page, header and button
    backgrounds only, so the hub sends the theme's body text colour with the
    panel's first render.
    """
    light = Theme("light")
    app = PageApp({_ENTITY_ID: Entity("playing", {"media_title": "Morning Coffee"})})
    app.theme = light
    page = MediaPage(app, {"page_id": _PAGE_ID})

    page.set_panel(HAUIPanel(app, {"type": "media", "item": _ENTITY_ID}))

    assert f"tMTitle.pco={light.get('component_text')}" in app.cmds
    assert f"m1Name.pco={light.get('component_text')}" in app.cmds
    assert f"m1Icon.pco={light.get('component_active')}" in app.cmds


# cover art


def _cover_app(picture=None, device_info=None):
    """A real page app whose player publishes ``picture`` as its cover art."""
    attributes = {"media_title": "Morning Coffee"}
    if picture is not None:
        attributes["entity_picture"] = picture
    app = PageApp({_ENTITY_ID: Entity("playing", attributes)})
    app.device.device_info = dict(_DEVICE_INFO if device_info is None else device_info)
    return app


def _show_cover(app):
    page = MediaPage(app, {"page_id": _PAGE_ID})
    page.set_panel(HAUIPanel(app, {"type": "media", "item": _ENTITY_ID}))
    return page


def _icon_commands(app):
    return [cmd for cmd in app.cmds if cmd.startswith("tIcon.")]


def test_the_icon_rectangle_is_the_one_both_hmis_compile():
    """A cover is drawn where the icon widget is, per display model."""
    app = PageApp({})
    page = MediaPage(app, {"page_id": _PAGE_ID})

    for orientation in ("landscape", "portrait"):
        app.device.is_portrait = orientation == "portrait"
        layout = json.loads((LAYOUTS / f"layout_{orientation}.json").read_text(encoding="utf-8"))
        media = next(p for p in layout["pages"].values() if p["name"] == "media")
        icon = next(c["attrs"] for c in media["components"] if c["name"] == "tIcon")

        assert page.icon_rect == Rect(icon["x"], icon["y"], icon["w"], icon["h"]), orientation
        assert ICON_RECT[orientation] == page.icon_rect


def test_a_player_with_cover_art_draws_it_in_the_icon_rectangle():
    app = _cover_app(_PICTURE)
    page = _show_cover(app)

    assert [request["url"] for request in app.cover_requests] == [_PICTURE]
    assert app.cover_requests[0]["rect"] == page.icon_rect

    app.cover(["fill 12,68,50,50,1"])

    assert app.cmds[-1] == "fill 12,68,50,50,1"


def test_a_player_without_cover_art_keeps_the_icon():
    app = _cover_app()
    _show_cover(app)

    assert app.cover_requests == []
    assert _icon_commands(app)


def test_firmware_without_a_draw_action_keeps_the_icon():
    """An old firmware would be sent a program it cannot paint."""
    app = _cover_app(_PICTURE, device_info={})
    page = _show_cover(app)

    assert app.cover_requests == []
    assert _icon_commands(app)
    assert page._cover_supported is False


def test_a_shown_cover_is_not_painted_over_by_the_icon():
    app = _cover_app(_PICTURE)
    page = _show_cover(app)
    app.cover(["fill 12,68,50,50,1"])
    app.cmds.clear()

    page.refresh_panel()

    assert _icon_commands(app) == []


def test_the_cover_comes_back_when_the_player_drops_it():
    app = _cover_app(_PICTURE)
    page = _show_cover(app)
    app.cover(["fill 12,68,50,50,1"])
    app.cmds.clear()

    app.entities[_ENTITY_ID].attributes.pop("entity_picture")
    page.callback_media_entity(_ENTITY_ID, "entity_picture", None, None, {})

    assert "fill" not in " ".join(app.cmds)
    assert _icon_commands(app)


def test_a_cover_for_the_previous_track_is_dropped():
    app = _cover_app(_PICTURE)
    page = _show_cover(app)
    answer_first = app.cover_requests[0]["on_done"]

    app.entities[_ENTITY_ID].attributes["entity_picture"] = "http://radio.example/other.png"
    page.callback_media_entity(_ENTITY_ID, "entity_picture", _PICTURE, "other", {})
    app.cmds.clear()
    answer_first(["fill 12,68,50,50,1"], None)

    assert [request["url"] for request in app.cover_requests][-1] == (
        "http://radio.example/other.png"
    )
    assert app.cmds == []


def test_a_cover_that_could_not_be_fetched_leaves_the_icon():
    app = _cover_app(_PICTURE)
    _show_cover(app)
    app.cmds.clear()

    app.cover(None, RuntimeError("404"))

    assert "fill" not in " ".join(app.cmds)
    assert _icon_commands(app)


def test_a_cover_that_arrives_after_the_page_is_left_is_dropped():
    app = _cover_app(_PICTURE)
    page = _show_cover(app)
    answer = app.cover_requests[0]["on_done"]

    page.set_panel(None)
    app.cmds.clear()
    answer(["fill 12,68,50,50,1"], None)

    assert app.cmds == []

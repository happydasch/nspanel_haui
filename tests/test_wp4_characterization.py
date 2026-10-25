"""Characterization of the display commands sent by the feature-gated pages.

Each scenario runs a page's full ``set_panel`` lifecycle against a fake app
and compares the exact commands, service calls and popup requests with
``wp4_golden.json``.  The golden file was recorded before the page
de-duplication refactor, so it guards that the refactor changes no output.

Regenerate deliberately with ``WP4_REGEN=1 pytest tests/test_wp4_characterization.py``.
"""

import json
import os
import types
from pathlib import Path

import pytest
from nspanel_haui.haui.abstract import haui_entity
from nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from nspanel_haui.haui.features import (
    ClimateFeatures,
    CoverFeatures,
    MediaPlayerFeatures,
    VacuumFeatures,
)
from nspanel_haui.haui.page.alarm import AlarmPage
from nspanel_haui.haui.page.climate import ClimatePage
from nspanel_haui.haui.page.cover import CoverPage
from nspanel_haui.haui.page.grid import GridPage
from nspanel_haui.haui.page.light import LightPage
from nspanel_haui.haui.page.media import MediaPage
from nspanel_haui.haui.page.row import RowPage
from nspanel_haui.haui.page.timer import TimerPage
from nspanel_haui.haui.page.unlock import UnlockPage
from nspanel_haui.haui.page.vacuum import VacuumPage

GOLDEN = Path(__file__).with_name("wp4_golden.json")
_RECORDED: dict[str, object] = {}


class _Entity:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes
        self.calls = []

    def get_state(self):
        return self.state

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


class _Controller:
    def __init__(self):
        self.cmds = []

    def send_cmd(self, command, value):
        self.cmds.extend(value if isinstance(value, list) else [value])

    def has_notifications(self):
        return False


class _Navigation:
    page = None
    panel = None

    def __init__(self):
        self.opened = []

    def open_panel(self, key, **kwargs):
        shown = {k: (v.__name__ if callable(v) else v) for k, v in kwargs.items()}
        self.opened.append([str(key), shown])


class _Device:
    def get(self, key, default=None):
        return {"debug_level": 0}.get(key, default)

    def get_locale(self):
        return "en_US"


class _DeviceConfig:
    def get_panels(self, nav_only):
        return ["home", "panel"]


class _App:
    def __init__(self, entities):
        self.entities = entities
        controller = _Controller()
        self.navigation = _Navigation()
        self.controller = {
            "esphome": controller,
            "notification": controller,
            "navigation": self.navigation,
        }
        self.device = _Device()
        self.device_config = _DeviceConfig()
        self.listeners = []
        self.removed = []

    @property
    def cmds(self):
        return self.controller["esphome"].cmds

    def log(self, msg, **kwargs):
        pass

    def item_exists(self, entity_id):
        return entity_id in self.entities

    def get_item(self, entity_id):
        return self.entities[entity_id]

    def listen_state(self, cb, entity_id, attribute=None, **kwargs):
        handle = f"{entity_id}:{attribute}"
        self.listeners.append(handle)
        return handle

    def cancel_listen_state(self, handle):
        self.removed.append(handle)

    def get_temperature_unit(self):
        return "°C"

    def run_in(self, cb, delay, **kwargs):
        return "timer"

    def run_every(self, cb, start, interval, **kwargs):
        return "interval"

    def cancel_timer(self, handle):
        pass


class _SyncThread:
    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def _sync_service_calls(monkeypatch):
    monkeypatch.setattr(haui_entity, "threading", types.SimpleNamespace(Thread=_SyncThread))


@pytest.fixture(scope="module", autouse=True)
def _golden():
    yield
    if os.environ.get("WP4_REGEN"):
        GOLDEN.write_text(json.dumps(_RECORDED, indent=1, sort_keys=True) + "\n")


def _check(name, value):
    value = json.loads(json.dumps(value))
    if os.environ.get("WP4_REGEN"):
        _RECORDED[name] = value
        return
    golden = json.loads(GOLDEN.read_text())
    assert value == golden[name]


def _show(page_cls, page_id, panel_cfg, entities):
    app = _App(entities)
    page = page_cls(app, {"page_id": page_id})
    page.set_panel(HAUIPanel(app, panel_cfg))
    return app, page


def _out(app, page, *entities):
    return {
        "cmds": list(app.cmds),
        "calls": [e.calls for e in entities],
        "opened": app.navigation.opened,
    }


# climate

_CLIMATE_ALL = (
    ClimateFeatures.TARGET_TEMPERATURE
    | ClimateFeatures.FAN_MODE
    | ClimateFeatures.PRESET_MODE
    | ClimateFeatures.SWING_MODE
)


def _climate(state, features, **attrs):
    attributes = {
        "friendly_name": "Living Room",
        "supported_features": features,
        "hvac_modes": ["off", "heat", "cool"],
        "current_temperature": 20.5,
        "temperature": 21.0,
        "min_temp": 7,
        "max_temp": 35,
        "fan_modes": ["auto", "low"],
        "fan_mode": "auto",
        "preset_modes": ["eco", "boost"],
        "preset_mode": "eco",
        "swing_modes": ["on", "off"],
        "swing_mode": "off",
    }
    attributes.update(attrs)
    return _Entity(state, attributes)


@pytest.mark.parametrize(
    ("name", "state", "features"),
    [
        ("climate_none", "heat", ClimateFeatures.TARGET_TEMPERATURE),
        ("climate_all", "cool", _CLIMATE_ALL),
        ("climate_off_fan_only", "off", ClimateFeatures.FAN_MODE),
        ("climate_swing_preset", "heat", ClimateFeatures.SWING_MODE | ClimateFeatures.PRESET_MODE),
    ],
)
def test_climate_render(name, state, features):
    entity = _climate(state, features)
    app, page = _show(
        ClimatePage,
        16,
        {"type": "climate", "item": {"item": "climate.c"}},
        {"climate.c": entity},
    )
    _check(name, _out(app, page, entity))


@pytest.mark.parametrize("fnc", ["fan_mode", "preset_mode", "swing_mode", "power_off", "other"])
@pytest.mark.parametrize("empty", [False, True])
def test_climate_callbacks(fnc, empty):
    attrs = {"fan_modes": [], "preset_modes": [], "swing_modes": []} if empty else {}
    entity = _climate("heat", _CLIMATE_ALL, **attrs)
    app, page = _show(
        ClimatePage,
        16,
        {"type": "climate", "item": {"item": "climate.c"}},
        {"climate.c": entity},
    )
    page.callback_function_component("x", fnc)
    for cb, arg in (
        (page.callback_fan_mode, "f"),
        (page.callback_preset_mode, "p"),
        (page.callback_swing_mode, "s"),
    ):
        cb(arg)
    _check(f"climate_cb_{fnc}_{empty}", _out(app, page, entity))


# cover

_COVER_ALL = (
    CoverFeatures.OPEN | CoverFeatures.CLOSE | CoverFeatures.STOP | CoverFeatures.SET_POSITION
)


@pytest.mark.parametrize(
    ("name", "state", "features", "position"),
    [
        ("cover_all_open", "open", _COVER_ALL, 100),
        ("cover_all_mid", "opening", _COVER_ALL, 50),
        ("cover_all_closed", "closed", _COVER_ALL, 0),
        ("cover_none", "open", 0, None),
        ("cover_open_only_closed", "closed", CoverFeatures.OPEN, None),
        ("cover_close_stop_open", "open", CoverFeatures.CLOSE | CoverFeatures.STOP, None),
    ],
)
def test_cover_render(name, state, features, position):
    attrs = {"friendly_name": "Door", "supported_features": features}
    if position is not None:
        attrs["current_position"] = position
    entity = _Entity(state, attrs)
    app, page = _show(
        CoverPage, 18, {"type": "cover", "item": {"item": "cover.d"}}, {"cover.d": entity}
    )
    _check(name, _out(app, page, entity))


# vacuum


@pytest.mark.parametrize(
    ("name", "state", "features"),
    [
        ("vac_docked_base", "docked", VacuumFeatures.START | VacuumFeatures.RETURN_HOME),
        (
            "vac_cleaning_pause",
            "cleaning",
            VacuumFeatures.START | VacuumFeatures.PAUSE | VacuumFeatures.STOP,
        ),
        ("vac_cleaning_stop", "cleaning", VacuumFeatures.STOP | VacuumFeatures.LOCATE),
        (
            "vac_paused_all",
            "paused",
            VacuumFeatures.START
            | VacuumFeatures.RETURN_HOME
            | VacuumFeatures.LOCATE
            | VacuumFeatures.FAN_SPEED
            | VacuumFeatures.BATTERY,
        ),
        ("vac_error_none", "error", 0),
    ],
)
def test_vacuum_render(name, state, features):
    entity = _Entity(
        state,
        {
            "friendly_name": "Robo",
            "supported_features": features,
            "fan_speed": "low",
            "fan_speed_list": ["low", "high"],
        },
    )
    mop = _Entity("off", {"friendly_name": "Mop"})
    app, page = _show(
        VacuumPage,
        15,
        {"type": "vacuum", "item": {"item": "vacuum.r"}, "items": [{"item": "switch.mop"}]},
        {"vacuum.r": entity, "switch.mop": mop},
    )
    for fnc in ("fan", "action", "locate", "return_home", "unknown"):
        page.callback_function_component("x", fnc)
    page.callback_fan_speed("high")
    _check(name, _out(app, page, entity))


# media


def _media(state, features, **attrs):
    attributes = {
        "friendly_name": "Kitchen",
        "supported_features": features,
        "volume_level": 0.4,
        "shuffle": True,
        "repeat": "one",
        "source_list": ["a", "b"],
    }
    attributes.update(attrs)
    return _Entity(state, attributes)


_M = MediaPlayerFeatures
_MEDIA_ALL = (
    _M.PAUSE
    | _M.PLAY
    | _M.VOLUME_SET
    | _M.PREVIOUS_TRACK
    | _M.NEXT_TRACK
    | _M.SHUFFLE_SET
    | _M.REPEAT_SET
    | _M.SELECT_SOURCE
    | _M.GROUPING
    | _M.TURN_ON
)


@pytest.mark.parametrize(
    ("name", "state", "features"),
    [
        ("media_all_playing", "playing", _MEDIA_ALL),
        ("media_all_paused", "paused", _MEDIA_ALL),
        ("media_none", "off", 0),
        ("media_play_vol", "playing", _M.PLAY | _M.VOLUME_SET),
        ("media_nav_only", "idle", _M.NEXT_TRACK | _M.SHUFFLE_SET),
    ],
)
def test_media_render(name, state, features):
    entity = _media(state, features, media_title="Song", media_artist="Band")
    app, page = _show(
        MediaPage,
        14,
        {
            "type": "media",
            "item": {"item": "media_player.k"},
            "group_items": [{"item": "media_player.g"}],
            "media_favorites": ["media_player.g"],
        },
        {"media_player.k": entity},
    )
    page.callback_function_component("x", "media_state")
    _check(name, _out(app, page, entity))


# row and grid


def _items():
    return {
        "cover.a": _Entity(
            "open",
            {
                "friendly_name": "Shutter",
                "supported_features": CoverFeatures.OPEN | CoverFeatures.STOP,
                "current_position": 100,
            },
        ),
        "cover.b": _Entity(
            "closed",
            {
                "friendly_name": "Door",
                "supported_features": _COVER_ALL,
                "current_position": 0,
                "device_class": "garage",
            },
        ),
        "light.c": _Entity("on", {"friendly_name": "Lamp"}),
        "switch.d": _Entity("off", {"friendly_name": "Plug"}),
        "input_number.e": _Entity(
            "21", {"friendly_name": "Num", "min": 15, "max": 30, "step": 1}
        ),
        "sensor.f": _Entity("5", {"friendly_name": "Sensor"}),
        "button.g": _Entity("unknown", {"friendly_name": "Btn"}),
    }


def _entries(keys):
    return [{"item": key} for key in keys]


def _next_page_id(page):
    return next(k for k, v in page._fnc_items.items() if v["fnc_name"] == "next_page")


@pytest.mark.parametrize("cls", [RowPage, GridPage])
def test_row_and_grid_paging(cls):
    entities = _items()
    keys = list(entities)
    app, page = _show(
        cls, 20, {"type": cls.DESCRIPTOR.type_key, "items": _entries(keys)}, entities
    )
    page_name = cls.DESCRIPTOR.type_key
    steps = []
    for _ in range(3):
        steps.append(len(app.cmds))
        page.callback_function_component(_next_page_id(page), "next_page")
        page.callback_item_state(keys[0], "state", None, None, {})
        page.callback_item_state("unknown.x", "state", None, None, {})
        page.debouncer.cancel(f"{page_name}_item_state")
        page._flush_item_updates()
    steps.append(len(app.cmds))
    page.stop_panel(page.panel)
    out = _out(app, page)
    out.update(
        steps=steps,
        listeners=sorted(app.listeners),
        removed=sorted(app.removed),
        pending=sorted(page._pending_item_updates),
        handles=len(page._active_handles),
        page_state=page.panel.get_state("current_page", 0) if page.panel else None,
    )
    _check(f"paging_{page_name}", out)


def test_row_cover_rows():
    entities = _items()
    app, page = _show(
        RowPage,
        20,
        {"type": "row", "items": _entries(["cover.a", "cover.b", "light.c", "switch.d"])},
        entities,
    )
    for fnc in ("overlay", "btn_text", "toggle", "btn_up", "btn_stop", "btn_down"):
        for i in range(5):
            ovl = getattr(RowPage.COMPONENTS, f"r{i + 1}_ovl")
            page.callback_function_component(ovl.name, fnc)
    out = _out(app, page, *entities.values())
    _check("row_cover_rows", out)


# timer


class _TimerPanel:
    id = "t"

    def __init__(self):
        self.state = {}

    def get(self, key, default=None):
        return default

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def get_type(self):
        return "timer"

    def get_title(self, default=""):
        return default


def test_timer_buttons():
    app = _App({})
    page = TimerPage(app, {"page_id": 12})
    page.cmds = []
    page.send_cmd = page.cmds.append
    page.get_color = lambda key: sum(map(ord, key))
    page.translate = lambda text: text
    page._auto_assign_fncs = lambda panel: None
    page.set_panel(_TimerPanel())
    seen = {}
    for step, (comp, fnc) in enumerate(
        [
            (None, None),
            ("bUp2", "bUp2"),
            ("bStart", "start_timer"),
            ("bStart", "pause_timer"),
            ("bStart", "resume_timer"),
            ("bStop", "stop_timer"),
            ("bStop", "stop_timer"),
        ]
    ):
        if comp:
            page.callback_function_component(comp, fnc)
        seen[step] = list(page.cmds)
    _check("timer_buttons", seen)


# alarm


@pytest.mark.parametrize(
    ("name", "state", "features"),
    [
        ("alarm_disarmed_two", "disarmed", 1 | 2),
        ("alarm_disarmed_none", "disarmed", 0),
        ("alarm_armed", "armed_home", 1 | 2 | 4),
    ],
)
def test_alarm_render(name, state, features):
    entity = _Entity(state, {"friendly_name": "Home", "supported_features": features})
    app, page = _show(
        AlarmPage,
        17,
        {"type": "alarm", "item": {"item": "alarm_control_panel.h"}},
        {"alarm_control_panel.h": entity},
    )
    for comp in page._action_buttons:
        page.callback_action(None, comp)
    _check(name, _out(app, page, entity))


# unlock


def test_unlock_update_components():
    page = UnlockPage.__new__(UnlockPage)
    page._title = "Unlock"
    page._unlock_code = "12"
    page.get_color = lambda key: sum(map(ord, key))
    page.set_component_text = lambda comp, text: recorded.append(["text", comp.name, text])
    page.update_function_component = lambda *a, **kw: recorded.append(
        [list(a), {k: kw[k] for k in sorted(kw)}]
    )
    recorded: list = []
    for value in ("", "1", "12"):
        page._input = value
        page.update_components()
    _check("unlock_update", recorded)


# light


def test_light_function_details_touch():
    page = LightPage.__new__(LightPage)
    page._current_light_function = None
    page.get_color = lambda key: 1
    sent: list = []
    page.send_cmd = sent.append
    page.set_component_text = lambda comp, text: None
    page.set_component_text_color = lambda comp, color: sent.append(f"{comp.name}.pco={color}")
    page.show_component = lambda comp: None
    page.set_light_function_details(1, "i", "n", "v", True, True)
    page.set_light_function_details(1, "i", "n", "v", False, True)
    _check("light_details_touch", sent)

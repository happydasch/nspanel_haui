"""Every panel card renders on the hub and replays cleanly in the browser.

The editor's panel cards are the hub's own render (``VirtualPanelHost.async_render``)
replayed in the browser's Nextion simulator. This renders a panel of every type,
and every system panel, with the sample world of the card gallery
(``scripts/preview_gallery/sample_world.py``), then replays each result with Node
(``tests/frontend/replay-renders.mjs``) in the device's layout: a page the
simulator cannot draw from the hub's output fails here.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from custom_components.nspanel_haui.haui.mapping.const import SysPanelKey
from custom_components.nspanel_haui.haui.mapping.panel import (
    get_system_panel_entries,
    get_user_panel_type_descriptors,
)
from custom_components.nspanel_haui.haui.utils.icon import get_icon
from scripts.preview_gallery import sample_world

ROOT = Path(__file__).resolve().parent.parent
REPLAY = ROOT / "tests" / "frontend" / "replay-renders.mjs"
# Theme colours unlike the HMI's own: a blue page, a darker blue header, a dark
# blue for control backgrounds (slider tracks, toggles off, progress bars) and a
# pressed blue.
THEMED_COLORS = {
    "background": 4479,
    "header_background": 4228,
    "component_background": 2114,
    "component_pressed": 6463,
}


@pytest.fixture
def hub_loop(monkeypatch):
    """An event loop thread with the HA helpers the hub imports at call time."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    sample_world.install_runtime_stubs(
        loop,
        monkeypatch.setitem,
        lambda target, name, value: monkeypatch.setattr(target, name, value, raising=False),
    )
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)


def _replay(tmp_path: Path, orientation: str, renders: dict, *flags: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node 22+ is required to replay the hub's renders (see AGENTS.md)")
    path = tmp_path / "renders.json"
    path.write_text(json.dumps(renders), encoding="utf-8")
    result = subprocess.run(
        [node, str(REPLAY), orientation, str(path), *flags],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.parametrize(
    ("display_model", "orientation"), [("eu", "landscape"), ("us", "portrait")]
)
def test_every_card_renders_on_the_hub_and_replays_in_the_browser(
    hub_loop, tmp_path, display_model, orientation
):
    renders = sample_world.render_every_card(hub_loop, display_model)

    assert len(renders) == len(get_user_panel_type_descriptors()) + len(get_system_panel_entries())
    # The blank page sends nothing after the page switch: its Preinitialize code
    # paints it in the theme sent ahead of it.
    assert renders[SysPanelKey.SYS_BLANK]["before"]
    empty = [name for name, render in renders.items() if not render["commands"]]
    assert empty == [SysPanelKey.SYS_BLANK]
    _replay(tmp_path, orientation, renders)


@pytest.mark.parametrize(
    ("display_model", "orientation"), [("eu", "landscape"), ("us", "portrait")]
)
def test_every_card_follows_the_selected_theme_colours(
    hub_loop, tmp_path, display_model, orientation
):
    """Compiled theme colours follow the shared palette from the page's first frame on.

    Page, header, pressed and control backgrounds take the selected theme's colours, and
    the page loads in them: no colour change is visible after the page switch.
    """
    from copy import deepcopy

    from custom_components.nspanel_haui.haui.mapping.color import BUILTIN_THEMES

    theme = deepcopy(BUILTIN_THEMES["dark"])
    theme["name"] = "Test"
    theme["colors"].update(THEMED_COLORS)
    renders = sample_world.render_every_card(
        hub_loop, display_model, {"theme_id": "test"}, {"test": theme}
    )

    assert f"thmBg={THEMED_COLORS['background']}" in renders[SysPanelKey.SYS_BLANK]["before"]
    _replay(tmp_path, orientation, renders, "--themed-colors")


def test_every_card_paints_its_body_text_in_the_selected_theme(hub_loop):
    """A light theme repaints the body text a compiled TFT leaves in the dark theme's.

    The media title, the vacuum status and the climate temperature are compiled
    white: on a light page they take the theme's body text colour, sent with the
    panel's first render (``haui/mapping/theme_foregrounds.py``).
    """
    from custom_components.nspanel_haui.haui.mapping.color import Theme

    colors = Theme("sky")
    renders = sample_world.render_every_card(hub_loop, "eu", {"theme_id": "sky"})

    media = renders["media"]["commands"]
    assert f"tMTitle.pco={colors.get('component_text')}" in media
    assert f"m1Name.pco={colors.get('component_text')}" in media
    assert f"m1Icon.pco={colors.get('component_active')}" in media
    assert f"tStatus.pco={colors.get('component_text')}" in renders["vacuum"]["commands"]
    assert f"tTemp.pco={colors.get('component_text')}" in renders["climate"]["commands"]


def test_unlock_card_shows_its_keypad_and_title(hub_loop):
    """The alarm page's load event hides the keypad, so the unlock popup shows it again."""
    commands = sample_world.render_every_card(hub_loop, "eu")["popup_unlock"]["commands"]

    keys = [f"bKey{n}" for n in range(10)] + ["bKeyClr", "bKeyDel"]
    assert [key for key in keys if f"vis {key},1" not in commands] == []
    # the system panel's title is "": the unlock popup falls back to its own
    assert 'tTitle.txt="Unlock"' in commands


def test_demo_qr_and_notify_cards_carry_sample_content(hub_loop):
    """The sample QR panel encodes its network and the notification shows its icon."""
    renders = sample_world.render_every_card(hub_loop, "eu")

    assert 'qrCode.txt="WIFI:S:Home Network;T:WPA;P:demo-password;;"' in renders["qr"]["commands"]
    notify = renders["popup_notify"]["commands"]
    assert f'tIcon.txt="{get_icon("mdi:bell")}"' in notify
    assert "tIcon.pco=62694" in notify
    assert "vis tIcon,1" in notify
    assert 'bBtnRight.txt="Confirm"' in notify
    assert "vis bBtnRight,1" in notify


def test_demo_clock_and_weather_cards_show_the_sample_forecast(hub_loop):
    """The clock shows the sample weather and the weather page its daily forecast."""
    renders = sample_world.render_every_card(hub_loop, "eu")

    clock = renders["clock"]["commands"]
    assert "vis tMainIcon,1" in clock
    assert any(cmd.startswith("tMainText.txt=") and cmd.endswith('18°C"') for cmd in clock)
    assert 'tSubText.txt="1013hPa"' in clock
    weather = renders["weather"]["commands"]
    assert "vis f1Icon,1" in weather
    assert 'f1Val.txt="24°C"' in weather
    assert 'f1SubVal.txt="13°C"' in weather


def test_demo_entity_panels_show_the_controls_their_sample_entity_supports(hub_loop):
    """The sample players advertise every feature, so their cards show every control."""
    renders = sample_world.render_every_card(hub_loop, "eu")

    media = renders["media"]["commands"]
    for widget in (
        "bPrev",
        "bNext",
        "bPlay",
        "bShuffle",
        "bRepeat",
        "bVolDown",
        "bVolUp",
        "hVolume",
        "jProgress",
        "m1Name",
        "m2Name",
        "m3Name",
    ):
        assert f"vis {widget},1" in media
    vacuum = renders["vacuum"]["commands"]
    for widget in ("bFan", "bAction", "bHome", "bLocate"):
        assert f"vis {widget},1" in vacuum


@pytest.mark.parametrize(
    ("display_model", "orientation"), [("eu", "landscape"), ("us", "portrait")]
)
def test_a_draw_program_replays_on_the_card(hub_loop, tmp_path, display_model, orientation):
    """A hub draw program (nspanel_haui.show_image) must replay in the simulator.

    The program is not part of a page render: the hub appends it to the commands
    of the page it was drawn over, which is exactly the shape a card viewer gets.
    """
    renders = sample_world.render_every_card(hub_loop, display_model)
    grid = renders["grid"]
    program = [
        "fill 20,20,40,40,63488",
        "fill 60,20,20,20,2016",
    ]

    renders["grid_after_show_image"] = {
        "page": grid["page"],
        "before": grid["before"],
        "commands": [*grid["commands"], *program],
    }

    _replay(tmp_path, orientation, renders)

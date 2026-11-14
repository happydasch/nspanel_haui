"""Grid page: state-keyed tile colours must be resolved and refreshed."""

from __future__ import annotations

from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.page.grid import GridPage
from custom_components.nspanel_haui.haui.utils.color import parse_color_value


def _last_color(app: PageApp, component: str) -> int | None:
    prefix = f"{component}.bco="
    for cmd in reversed(app.cmds):
        if cmd.startswith(prefix):
            return int(cmd[len(prefix) :])
    return None


def test_state_keyed_background_is_resolved_and_refreshed() -> None:
    light = Entity("off", {"friendly_name": "Lamp"})
    app = PageApp({"light.lamp": light})
    panel = HAUIPanel(
        app,
        {
            "type": "grid",
            "items": [
                {
                    "item": "light.lamp",
                    "back_color": {"on": "#ff0000", "off": "#00ff00"},
                }
            ],
        },
    )
    page = GridPage(app, {"page_id": 9})
    page.set_panel(panel)

    # Off -> green (not the black an unresolved dict would render).
    assert _last_color(app, "g1Btn") == parse_color_value("#00ff00")

    light.state = "on"
    page.callback_item_state("light.lamp", "state", None, None, {})
    page._flush_item_updates()

    assert _last_color(app, "g1Btn") == parse_color_value("#ff0000")


def test_long_entity_name_is_shortened_to_fit_tile():
    name = "Kitchen ceiling recessed light"
    app = PageApp({"light.lamp": Entity("off", {"friendly_name": name})})
    page = GridPage(app, {"page_id": 9})
    page.set_panel(HAUIPanel(app, {"type": "grid", "items": [{"item": "light.lamp"}]}))

    command = next(cmd for cmd in app.cmds if cmd.startswith("g1Name.txt="))
    assert command.endswith('.."')
    assert "Kitchen ceiling recessed light" not in command


def _draws(cmd: str, component: str) -> bool:
    return cmd.startswith(f"{component}.") or cmd in (f"ref {component}", f"vis {component},1")


def test_power_button_redrawn_after_icon_on_refresh() -> None:
    # The icon box overlaps the bottom of the power button on the display, so
    # every icon redraw has to be followed by a power button redraw.
    light = Entity("on", {"friendly_name": "Lamp", "brightness": 10})
    app = PageApp({"light.lamp": light})
    panel = HAUIPanel(
        app,
        {"type": "grid", "items": [{"item": "light.lamp", "show_power_button": True}]},
    )
    page = GridPage(app, {"page_id": 9})
    page.set_panel(panel)

    # Attribute-only update: nothing about the power button itself changes.
    app.cmds.clear()
    light.attributes["brightness"] = 200
    page.callback_item_state("light.lamp", "brightness", None, None, {})
    page._flush_item_updates()

    last_icon = max(i for i, cmd in enumerate(app.cmds) if _draws(cmd, "g1Icon"))
    assert any(_draws(cmd, "g1Power") for cmd in app.cmds[last_icon + 1 :])

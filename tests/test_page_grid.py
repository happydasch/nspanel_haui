"""Grid page: state-keyed tile colours must be resolved and refreshed."""

from __future__ import annotations

import pytest
from support.page_app import Entity, PageApp

from custom_components.nspanel_haui.haui.abstract.haui_item import HAUIItem
from custom_components.nspanel_haui.haui.abstract.haui_panel import HAUIPanel
from custom_components.nspanel_haui.haui.mapping.color import Theme, active_tile_color
from custom_components.nspanel_haui.haui.page.grid import GridPage
from custom_components.nspanel_haui.haui.utils.color import parse_color_value


def _last_color(app: PageApp, component: str, attr: str = "bco") -> int | None:
    prefix = f"{component}.{attr}="
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


def _draw_grid(theme_id: str, state: str, items: list[dict] | None = None) -> PageApp:
    app = PageApp({"light.lamp": Entity(state, {"friendly_name": "Lamp"})})
    app.theme = Theme(theme_id)
    page = GridPage(app, {"page_id": 9})
    page.set_panel(
        HAUIPanel(
            app,
            {"type": "grid", "items": items or [{"item": "light.lamp", "show_power_button": True}]},
        )
    )
    return app


def test_an_on_tile_takes_its_colours_from_the_selected_theme() -> None:
    # The tile lifted towards the dark theme's on colour used to be stored in the
    # panel, so on a light theme an on tile stayed dark under the light theme's
    # dark text. The hub mixes it into the theme's own page on every render.
    dark, light = Theme("dark"), Theme("light")
    dark_app = _draw_grid("dark", "on")
    light_app = _draw_grid("light", "on")

    assert _last_color(dark_app, "g1Btn") == active_tile_color(
        dark.get("background"), dark.get("entity_on")
    )
    assert _last_color(light_app, "g1Btn") == active_tile_color(
        light.get("background"), light.get("entity_on")
    )
    # The power button is the theme's own on colour, not the dark theme's yellow.
    assert _last_color(light_app, "g1Power", "pco") == light.get("entity_on")
    # An off tile stays flat on the page and keeps its power glyph dimmed.
    off_app = _draw_grid("light", "off")
    assert _last_color(off_app, "g1Btn") == light.get("background")
    assert _last_color(off_app, "g1Power", "pco") == light.get("component_pressed")


def test_item_colours_win_over_the_theme_tile() -> None:
    app = _draw_grid(
        "light",
        "on",
        [
            {
                "item": "light.lamp",
                "show_power_button": True,
                "back_color": {"on": "#ff0000"},
                "power_color": "#00ff00",
            }
        ],
    )

    assert _last_color(app, "g1Btn") == parse_color_value("#ff0000")
    assert _last_color(app, "g1Power", "pco") == parse_color_value("#00ff00")
    last_icon = max(i for i, cmd in enumerate(app.cmds) if _draws(cmd, "g1Icon"))
    assert any(_draws(cmd, "g1Power") for cmd in app.cmds[last_icon + 1 :])


@pytest.mark.parametrize(
    ("entity_id", "state", "method", "service"),
    [
        ("light.lamp", "off", "turn_on_item", "turn_on"),
        ("light.lamp", "on", "turn_off_item", "turn_off"),
        ("media_player.tv", "idle", "turn_on_item", "media_play"),
        ("media_player.tv", "playing", "turn_off_item", "media_stop"),
        ("lock.front", "unlocked", "turn_off_item", "lock"),
        ("lock.front", "locked", "turn_off_item", "unlock"),
        ("scene.morning", "2026-01-01T07:00:00+00:00", "turn_off_item", "turn_on"),
        ("climate.hall", "heat", "turn_on_item", "turn_on"),
    ],
)
def test_power_button_sends_a_service_the_domain_provides(
    entity_id: str, state: str, method: str, service: str
) -> None:
    """A tile's power button never sends turn_on/turn_off to a domain lacking them."""
    entity = Entity(state, {"friendly_name": "Item"})
    app = PageApp({entity_id: entity})
    page = GridPage(app, {"page_id": 9})

    getattr(page, method)(HAUIItem(app, {"item": entity_id}))

    assert [call[0] for call in entity.calls] == [service]

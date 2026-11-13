"""Starter templates: curated panels a new panel can start from.

The editor's *Add panel* catalog lists them under *Start from a template*. A
template is a panel config without a ``key``: choosing one opens the panel
editor with its type, title, options and items set. Entity slots the panel
needs are left empty (``{"item": ""}``), so the option rules
(``haui/option_rules.py``) mark each one until the user picks an entity. An
item-list entry may carry a ``domain`` hint: the catalog's preview fills the
slot with an example entity of that domain, and the editor drops the hint when
the template is chosen.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from ..utils.text import get_translation
from .descriptor import _


@dataclass(frozen=True)
class PanelTemplate:
    """One starter template: its catalog card and the panel it starts."""

    key: str
    label: str
    description: str
    icon: str
    panel: dict[str, Any]


def _slot(domain: str, icon: str, power: bool = False) -> dict[str, Any]:
    """An empty item-list slot for an entity of ``domain``."""
    slot: dict[str, Any] = {"item": "", "domain": domain, "icon": icon}
    if power:
        slot["show_power_button"] = True
    return slot


PANEL_TEMPLATES: tuple[PanelTemplate, ...] = (
    PanelTemplate(
        key="lights_grid",
        label=_("Lights grid"),
        description=_("Six lights with on/off buttons"),
        icon="mdi:lightbulb-group-outline",
        panel={
            "type": "grid",
            "title": _("Lights"),
            "items": [_slot("light", "mdi:lightbulb", power=True) for _index in range(6)],
        },
    ),
    PanelTemplate(
        key="room_overview",
        label=_("Room overview"),
        description=_("Light, blind, climate, media, fan and a scene in one grid"),
        icon="mdi:sofa-outline",
        panel={
            "type": "grid",
            "title": _("Living room"),
            "items": [
                _slot("light", "mdi:lightbulb", power=True),
                _slot("cover", "mdi:blinds-horizontal"),
                _slot("climate", "mdi:thermostat"),
                _slot("media_player", "mdi:television"),
                _slot("switch", "mdi:fan", power=True),
                _slot("scene", "mdi:movie-open"),
            ],
        },
    ),
    PanelTemplate(
        key="device_row",
        label=_("Device row"),
        description=_("Switches, a light and a blind as a list"),
        icon="mdi:format-list-bulleted",
        panel={
            "type": "row",
            "title": _("Devices"),
            "items": [
                _slot("switch", "mdi:power-socket-eu"),
                _slot("switch", "mdi:fan"),
                _slot("light", "mdi:lightbulb"),
                _slot("cover", "mdi:blinds-horizontal"),
            ],
        },
    ),
    PanelTemplate(
        key="thermostat",
        label=_("Thermostat"),
        description=_("Climate control with its modes"),
        icon="mdi:thermostat",
        panel={"type": "climate", "title": _("Thermostat"), "item": {"item": ""}},
    ),
    PanelTemplate(
        key="bedside_clock",
        label=_("Bedside clock"),
        description=_("A dark clock with the date and two sensors"),
        icon="mdi:bed-clock",
        panel={
            "type": "clock",
            "title": _("Clock"),
            "background": "dark",
            "show_time_date": True,
            "show_notifications": True,
            "items": [
                _slot("sensor", "mdi:thermometer"),
                _slot("sensor", "mdi:water-percent"),
            ],
        },
    ),
    PanelTemplate(
        key="weather_station",
        label=_("Weather station"),
        description=_("Daily forecast with two sensors"),
        icon="mdi:weather-partly-cloudy",
        panel={
            "type": "weather",
            "title": _("Weather"),
            "forecast_type": "daily",
            "show_time_date": True,
            "info_items": [
                _slot("sensor", "mdi:thermometer"),
                _slot("sensor", "mdi:water-percent"),
            ],
        },
    ),
    PanelTemplate(
        key="guest_wifi",
        label=_("Guest Wi-Fi"),
        description=_("A QR code guests scan to join your network"),
        icon="mdi:qrcode",
        panel={
            "type": "qr",
            "title": _("Guest Wi-Fi"),
            "essid": "",
            "password": "",
            "show_info": True,
        },
    ),
    PanelTemplate(
        key="alarm_keypad",
        label=_("Alarm keypad"),
        description=_("Arm and disarm your alarm with a code"),
        icon="mdi:shield-home-outline",
        panel={"type": "alarm", "title": _("Alarm"), "item": {"item": ""}, "action_icons": True},
    ),
)


def get_panel_templates(language: str = "en") -> list[dict[str, Any]]:
    """Return the starter templates for the editor, their texts translated.

    Args:
        language: The HAUI locale to translate label, description and title into.

    Returns:
        One ``{"key", "label", "description", "icon", "panel"}`` per template,
        in catalog order.
    """
    served = []
    for template in PANEL_TEMPLATES:
        panel = copy.deepcopy(template.panel)
        panel["title"] = get_translation(panel["title"], language)
        served.append(
            {
                "key": template.key,
                "label": get_translation(template.label, language),
                "description": get_translation(template.description, language),
                "icon": template.icon,
                "panel": panel,
            }
        )
    return served

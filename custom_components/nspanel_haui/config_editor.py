"""Business logic for options flow config mutations.

ConfigEditor wraps ListEditor instances for panels and devices,
managing the shared ``_ctx`` dict that the flow uses for state
transitions.
"""

from __future__ import annotations

import copy
from typing import Any

from .haui.mapping.const import DEFAULT_CONFIG
from .list_editor import ListEditor


class ConfigEditor:
    """Business logic for options flow config mutations.

    Wraps two ListEditor instances (panels, devices) and a shared
    context dict (_ctx) used by flow steps for state transitions.

    This class is pure data manipulation — it has no knowledge of
    Home Assistant steps, forms, or async flow mechanics.
    """

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._panel_editor = ListEditor()
        self._device_editor = ListEditor()
        self._ctx: dict[str, Any] = {
            "devices": self._device_editor.items,
            "panels": self._panel_editor.items,
            "device_idx": -1,
            "panel_idx": -1,
            "panel_device_idx": -1,
            "mode": None,
        }

    # ── Context access ────────────────────────────────────────────────────────

    @property
    def ctx(self) -> dict[str, Any]:
        return self._ctx

    @property
    def panels(self) -> list[dict]:
        return self._ctx["panels"]

    @property
    def devices(self) -> list[dict]:
        return self._ctx["devices"]

    @property
    def panel_idx(self) -> int:
        return self._ctx["panel_idx"]

    @panel_idx.setter
    def panel_idx(self, v: int) -> None:
        self._ctx["panel_idx"] = v

    @property
    def device_idx(self) -> int:
        return self._ctx["device_idx"]

    @device_idx.setter
    def device_idx(self, v: int) -> None:
        self._ctx["device_idx"] = v

    @property
    def panel_device_idx(self) -> int:
        return self._ctx["panel_device_idx"]

    @panel_device_idx.setter
    def panel_device_idx(self, v: int) -> None:
        self._ctx["panel_device_idx"] = v

    # ── Panel mutations (wrapping ListEditor) ─────────────────────────────────

    def add_panel(self, cfg: dict) -> int:
        return self._panel_editor.add(cfg)

    def edit_panel(self, idx: int, cfg: dict) -> None:
        self._panel_editor.edit(idx, cfg)

    def duplicate_panel(self, idx: int) -> int:
        return self._panel_editor.duplicate(idx)

    def move_panel(self, idx: int, direction: int) -> int:
        return self._panel_editor.move(idx, direction)

    def remove_panel(self, idx: int) -> bool:
        return self._panel_editor.remove(idx)

    # ── Device mutations (wrapping ListEditor) ────────────────────────────────

    def add_device(self, cfg: dict) -> int:
        return self._device_editor.add(cfg)

    def edit_device(self, idx: int, cfg: dict) -> None:
        self._device_editor.edit(idx, cfg)

    def duplicate_device(self, idx: int) -> int:
        return self._device_editor.duplicate(idx)

    def move_device(self, idx: int, direction: int) -> int:
        return self._device_editor.move(idx, direction)

    def remove_device(self, idx: int) -> bool:
        return self._device_editor.remove(idx)

    # ── Panel list management for per-device mode ─────────────────────────────

    def enter_panels_for_device(self, device_idx: int) -> None:
        """Switch the panel editor to show panels for a specific device."""
        self._ctx["panel_device_idx"] = device_idx
        dev_panels = copy.deepcopy(
            self._ctx["devices"][device_idx].get("panels", [{"type": "clock"}])
        )
        self._panel_editor = ListEditor(dev_panels)
        self._ctx["panels"] = self._panel_editor.items

    def commit_panels_to_device(self, device_idx: int) -> None:
        """Write the panel editor state back to the device and clear context."""
        self._ctx["devices"][device_idx]["panels"] = list(self._ctx["panels"])
        self._ctx["panel_device_idx"] = -1

    # ── Initialization from entry options ─────────────────────────────────────

    def init_panels_from_options(self, options: dict) -> None:
        """Initialize panel editor from entry options (used for shared panels)."""
        self._panel_editor = ListEditor(copy.deepcopy(
            options.get("panels", DEFAULT_CONFIG["panels"])
        ))
        self._ctx["panels"] = self._panel_editor.items

    def init_devices_from_options(self, options: dict) -> None:
        """Initialize device editor from entry options."""
        self._device_editor = ListEditor(copy.deepcopy(
            options.get("devices", [])
        ))
        self._ctx["devices"] = self._device_editor.items

    # ── Full config building ──────────────────────────────────────────────────

    def build_full_config(self) -> dict:
        """Build the full config dict from current flow state for validation.

        Mirrors ``_options_to_config_dict`` but uses the in-progress
        ``_ctx`` state so we can validate *before* the final ``async_create_entry``.
        """
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["device"]["name"] = self._config_entry.data.get("name", "")

        if "mqtt_topic_prefix" in self._config_entry.options:
            cfg["mqtt"]["topic_prefix"] = self._config_entry.options["mqtt_topic_prefix"]

        if self._ctx.get("devices"):
            cfg["devices"] = copy.deepcopy(self._ctx["devices"])
            all_panels = []
            for dev in cfg["devices"]:
                all_panels.extend(dev.get("panels", []))
            cfg["panels"] = all_panels
        elif self._ctx.get("panels"):
            cfg["panels"] = list(self._ctx["panels"])

        return cfg

    # ── Options snapshot for saving ───────────────────────────────────────────

    def to_options(self, existing_options: dict, *, mode: str = "ui") -> dict:
        """Build an options dict suitable for async_create_entry.

        Populates devices or panels from the current editor state and
        ensures config_mode is set.
        """
        new_options = dict(existing_options)
        new_options["config_mode"] = mode
        new_options.pop("config_yaml", None)
        return new_options

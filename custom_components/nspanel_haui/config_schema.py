"""Schema builders, transforms, and label helpers for the config flow UI."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectOptionDict

from .haui.mapping.const import PANEL_CONFIG

_LOGGER = logging.getLogger(__name__)


class ConfigSchema:
    """Static methods for building voluptuous schemas and transforming config data."""

    # ── Panel type discovery ──────────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=1)
    def user_panel_types() -> list[SelectOptionDict]:
        """Return selector options for user-visible (non-system, non-popup) panel types."""
        try:
            from .haui.mapping.panel import PANEL_MAPPING

            result: list[SelectOptionDict] = []
            for type_key, value in PANEL_MAPPING.items():
                if not isinstance(value, tuple) or len(value) != 2:
                    continue
                _, cls = value
                d = getattr(cls, "DESCRIPTOR", None)
                # type_key == d.type_key guards against popup aliases that reuse a
                # non-popup class — those aliases have a mismatched key (popup_light vs light)
                if d is not None and type_key == d.type_key and not d.is_system and not d.is_popup:
                    result.append(SelectOptionDict(value=type_key, label=d.label))
            return sorted(result, key=lambda x: x["label"])
        except Exception:
            _LOGGER.debug("Could not load panel types", exc_info=True)
            return [SelectOptionDict(value="clock", label="Clock")]

    # ── Label helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def panel_label(panel: dict) -> str:
        title = panel.get("title") or ""
        ptype = panel.get("type", "?")
        return f"{title} ({ptype})" if title else ptype

    @staticmethod
    def panel_list_options(panels: list[dict]) -> list[SelectOptionDict]:
        """One row per panel + Add/Save. Selecting a panel opens the action sub-menu."""
        opts: list[SelectOptionDict] = [SelectOptionDict(value="add", label="+ Add panel")]

        for i, p in enumerate(panels):
            opts.append(SelectOptionDict(value=str(i), label=ConfigSchema.panel_label(p)))

        opts.append(SelectOptionDict(value="done", label="Save & close"))
        return opts

    @staticmethod
    def panel_action_options(idx: int, panels: list[dict]) -> list[SelectOptionDict]:
        """Action sub-menu for a selected panel (edit, dup, move, remove)."""
        label = ConfigSchema.panel_label(panels[idx])
        return [
            SelectOptionDict(value=f"edit_{idx}", label=f"Edit: {label}"),
            SelectOptionDict(value=f"dup_{idx}", label=f"Duplicate: {label}"),
            SelectOptionDict(value=f"up_{idx}", label=f"Move up: {label}"),
            SelectOptionDict(value=f"down_{idx}", label=f"Move down: {label}"),
            SelectOptionDict(value=f"remove_{idx}", label=f"Remove: {label}"),
            SelectOptionDict(value="back", label="← Back"),
        ]

    @staticmethod
    def device_label(device: dict) -> str:
        name = device.get("name") or ""
        locale = device.get("locale", "")
        return f"{name} ({locale})" if locale else name

    @staticmethod
    def device_list_options(devices: list[dict]) -> list[SelectOptionDict]:
        """One row per device + Add/Discover/Save."""
        opts: list[SelectOptionDict] = [SelectOptionDict(value="add", label="+ Add device")]

        if devices:
            opts.append(SelectOptionDict(value="discover", label="Scan for new devices"))

        for i, d in enumerate(devices):
            opts.append(SelectOptionDict(value=str(i), label=ConfigSchema.device_label(d)))

        opts.append(SelectOptionDict(value="done", label="Save & close"))
        return opts

    @staticmethod
    def device_action_options(idx: int, devices: list[dict]) -> list[SelectOptionDict]:
        """Action sub-menu for a selected device (edit, dup, move, remove, panels)."""
        label = ConfigSchema.device_label(devices[idx])
        return [
            SelectOptionDict(value=f"panels_{idx}", label=f"Manage panels: {label}"),
            SelectOptionDict(value=f"edit_{idx}", label=f"Edit: {label}"),
            SelectOptionDict(value=f"dup_{idx}", label=f"Duplicate: {label}"),
            SelectOptionDict(value=f"up_{idx}", label=f"Move up: {label}"),
            SelectOptionDict(value=f"down_{idx}", label=f"Move down: {label}"),
            SelectOptionDict(value=f"remove_{idx}", label=f"Remove: {label}"),
            SelectOptionDict(value="back", label="← Back"),
        ]

    # ── Schema builders ───────────────────────────────────────────────────────

    @staticmethod
    def device_edit_schema(current: dict) -> vol.Schema:
        return vol.Schema({
            vol.Required("name", default=current.get("name", "")): str,
            vol.Optional("locale", default=current.get("locale", "en_US")): str,
            vol.Optional("button_left_entity"): selector.EntitySelector(),
            vol.Optional("button_right_entity"): selector.EntitySelector(),
            vol.Optional("show_home_button", default=current.get("show_home_button", False)): bool,
            vol.Optional("show_sleep_button", default=current.get("show_sleep_button", False)): bool,
            vol.Optional("show_notifications_button", default=current.get("show_notifications_button", True)): bool,
            vol.Optional("log_commands", default=current.get("log_commands", False)): bool,
            vol.Optional("home_on_wakeup", default=current.get("home_on_wakeup", False)): bool,
            vol.Optional("home_on_first_touch", default=current.get("home_on_first_touch", True)): bool,
            vol.Optional("home_only_when_on", default=current.get("home_only_when_on", False)): bool,
            vol.Optional("home_on_button_toggle", default=current.get("home_on_button_toggle", False)): bool,
            vol.Optional("return_to_home_after_seconds", default=current.get("return_to_home_after_seconds", 0)): vol.Coerce(int),
            vol.Optional("always_return_to_home", default=current.get("always_return_to_home", False)): bool,
            vol.Optional("sound_on_startup", default=current.get("sound_on_startup", True)): bool,
            vol.Optional("sound_on_notification", default=current.get("sound_on_notification", True)): bool,
        })

    @staticmethod
    def panel_edit_schema(current: dict, panel_types: list[SelectOptionDict]) -> vol.Schema:
        default_type = panel_types[0]["value"] if panel_types else "clock"
        return vol.Schema({
            vol.Required("type", default=current.get("type", default_type)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=panel_types,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("title", default=current.get("title", "")): str,
            vol.Optional("key", default=current.get("key", "")): str,
            vol.Optional("home_panel", default=current.get("home_panel", False)): bool,
            vol.Optional("sleep_panel", default=current.get("sleep_panel", False)): bool,
            vol.Optional("wakeup_panel", default=current.get("wakeup_panel", False)): bool,
            vol.Optional("entity"): selector.EntitySelector(),
            vol.Optional("entities"): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True)
            ),
        })

    @staticmethod
    @lru_cache(maxsize=64)
    def panel_type_options(panel_type: str) -> list:
        """Return the PageOption list declared on the page class for ``panel_type``."""
        try:
            from .haui.mapping.panel import PANEL_MAPPING

            entry = PANEL_MAPPING.get(panel_type)
            if not entry:
                return []
            _, cls = entry
            d = getattr(cls, "DESCRIPTOR", None)
            return list(d.options) if d and getattr(d, "options", None) else []
        except Exception:
            _LOGGER.debug("Could not load options for panel type %s", panel_type, exc_info=True)
            return []

    @staticmethod
    def panel_type_specific_schema(panel_type: str, current: dict | None = None) -> tuple[dict, dict]:
        """Build a schema dict and transform map from PageOptions declared on the panel's page class.

        Returns a (schema_dict, transforms_dict) tuple. The caller merges schema_dict
        into the full voluptuous schema; transforms_dict maps option keys to transform
        kinds (e.g. ``"list_str"``, ``"drop_empty"``) that should be applied to the
        validated user input via :func:`ConfigSchema.apply_transforms`.
        """
        current = current or {}
        schema: dict = {}
        transforms: dict = {}

        for opt in ConfigSchema.panel_type_options(panel_type):
            # Already covered by the common panel_edit form (entity/entities multi-select).
            # The per-panel "entity" override below uses domain filtering so it's still useful.
            cur = current.get(opt.key, opt.default)

            if opt.kind == "bool":
                default = bool(cur) if cur is not None else False
                schema[vol.Optional(opt.key, default=default)] = bool

            elif opt.kind == "int":
                default = int(cur) if cur is not None else 0
                schema[vol.Optional(opt.key, default=default)] = vol.Coerce(int)

            elif opt.kind == "float":
                default = float(cur) if cur is not None else 0.0
                schema[vol.Optional(opt.key, default=default)] = vol.Coerce(float)

            elif opt.kind == "str":
                default = str(cur) if cur is not None else ""
                schema[vol.Optional(opt.key, default=default)] = str
                transforms[opt.key] = "drop_empty"

            elif opt.kind == "color":
                # Stored as RGB565 int or "[r,g,b]" string. Use plain str input.
                default = str(cur) if cur is not None else ""
                schema[vol.Optional(opt.key, default=default)] = str
                transforms[opt.key] = "drop_empty"

            elif opt.kind == "entity":
                cfg = (
                    selector.EntitySelectorConfig(domain=opt.domain)
                    if opt.domain
                    else selector.EntitySelectorConfig()
                )
                if cur:
                    schema[vol.Optional(opt.key, default=cur)] = selector.EntitySelector(cfg)
                else:
                    schema[vol.Optional(opt.key)] = selector.EntitySelector(cfg)

            elif opt.kind == "select":
                choices = opt.choices or []
                default = cur if cur is not None else (choices[0][0] if choices else "")
                schema[vol.Optional(opt.key, default=default)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[SelectOptionDict(value=v, label=lbl) for v, lbl in choices],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                transforms[opt.key] = "drop_empty"

            elif opt.kind == "list_str":
                default_text = "\n".join(cur) if isinstance(cur, list) else (str(cur) if cur else "")
                schema[vol.Optional(opt.key, default=default_text)] = selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                )
                transforms[opt.key] = "list_str"

            else:
                # Unknown kind — fall through as plain string.
                schema[vol.Optional(opt.key, default=str(cur) if cur is not None else "")] = str

        return schema, transforms

    # ── Transforms ────────────────────────────────────────────────────────────

    @staticmethod
    def apply_transforms(user_input: dict, transforms: dict) -> dict:
        """Apply per-key transforms to convert form values into canonical config representation.

        Transforms are declared alongside the schema by :func:`ConfigSchema.panel_type_specific_schema`.
        Supported kinds:

        * ``"list_str"`` — split multiline text into ``list[str]``, stripping blanks
        * ``"drop_empty"`` — omit the key when the value is an empty string
        """
        cleaned: dict = {}

        for k, v in user_input.items():
            kind = transforms.get(k)

            if kind == "list_str":
                if isinstance(v, str):
                    cleaned[k] = [line.strip() for line in v.splitlines() if line.strip()]
                else:
                    cleaned[k] = v or []
            elif kind == "drop_empty" and v == "":
                continue
            else:
                cleaned[k] = v

        return cleaned

    # ── Panel config extraction ───────────────────────────────────────────────

    @staticmethod
    def extract_panel_config(user_input: dict, edit_idx: int, panels: list[dict]) -> dict:
        """Build a complete panel config dict from form input."""
        base = dict(PANEL_CONFIG)
        base.update({k: v for k, v in user_input.items() if v is not None})
        if not base.get("key"):
            ptype = base.get("type", "panel")
            idx = edit_idx if edit_idx >= 0 else len(panels)
            base["key"] = f"{ptype}_{idx}"
        if not base.get("entity"):
            base["entity"] = None
        if not base.get("entities"):
            base["entities"] = []
        return base

    # ── Composite schema builder ──────────────────────────────────────────────

    @staticmethod
    def build_panel_schema(current: dict, panel_types: list[SelectOptionDict], user_input: dict | None = None) -> vol.Schema:
        """Build the full panel edit schema by merging base + type-specific schemas."""
        base_schema = ConfigSchema.panel_edit_schema(current, panel_types).schema

        panel_type = None
        if user_input:
            panel_type = user_input.get("type")

        if not panel_type:
            panel_type = current.get("type")

        if not panel_type and panel_types:
            panel_type = panel_types[0]["value"]

        # If type changed since last submit, drop stale option values from current.
        type_current = current if current.get("type") == panel_type else {}
        type_schema, _transforms = ConfigSchema.panel_type_specific_schema(panel_type, type_current)

        return vol.Schema({**base_schema, **type_schema})

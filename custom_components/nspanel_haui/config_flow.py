"""Config flow for NSPanel HAUI."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
from enum import StrEnum
from functools import lru_cache
from typing import Any

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectOptionDict

from .haui.config_models import validate_config
from .haui.mapping.const import DEFAULT_CONFIG, DEVICE_CONFIG, PANEL_CONFIG
from .list_editor import ListEditor

DOMAIN = "nspanel_haui"
_LOGGER = logging.getLogger(__name__)


class Action(StrEnum):
    ADD = "add"
    DONE = "done"
    BACK = "back"
    DISCOVER = "discover"
    EDIT = "edit"
    DUP = "dup"
    MOVE_UP = "up"
    MOVE_DOWN = "down"
    REMOVE = "remove"
    PANELS = "panels"


MQTT_DISCOVERY_TIMEOUT = 10  # seconds


# ── Panel type helpers ──────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _user_panel_types() -> list[SelectOptionDict]:
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


def _panel_label(panel: dict) -> str:
    title = panel.get("title") or ""
    ptype = panel.get("type", "?")
    return f"{title} ({ptype})" if title else ptype


def _panel_list_options(panels: list[dict]) -> list[SelectOptionDict]:
    """One row per panel + Add/Save. Selecting a panel opens the action sub-menu."""
    opts: list[SelectOptionDict] = [SelectOptionDict(value=Action.ADD, label="+ Add panel")]

    for i, p in enumerate(panels):
        opts.append(SelectOptionDict(value=str(i), label=_panel_label(p)))

    opts.append(SelectOptionDict(value=Action.DONE, label="Save & close"))
    return opts


def _panel_action_options(idx: int, panels: list[dict]) -> list[SelectOptionDict]:
    """Action sub-menu for a selected panel (edit, dup, move, remove)."""
    label = _panel_label(panels[idx])
    return [
        SelectOptionDict(value=f"{Action.EDIT}_{idx}", label=f"Edit: {label}"),
        SelectOptionDict(value=f"{Action.DUP}_{idx}", label=f"Duplicate: {label}"),
        SelectOptionDict(value=f"{Action.MOVE_UP}_{idx}", label=f"Move up: {label}"),
        SelectOptionDict(value=f"{Action.MOVE_DOWN}_{idx}", label=f"Move down: {label}"),
        SelectOptionDict(value=f"{Action.REMOVE}_{idx}", label=f"Remove: {label}"),
        SelectOptionDict(value=Action.BACK, label="← Back"),
    ]


# ── Schema builders (add fields here to extend each step) ──────────────────

def _device_label(device: dict) -> str:
    name = device.get("name") or ""
    locale = device.get("locale", "")
    return f"{name} ({locale})" if locale else name


def _device_list_options(devices: list[dict]) -> list[SelectOptionDict]:
    """One row per device + Add/Discover/Save."""
    opts: list[SelectOptionDict] = [SelectOptionDict(value=Action.ADD, label="+ Add device")]

    if devices:
        opts.append(SelectOptionDict(value=Action.DISCOVER, label="Scan for new devices"))

    for i, d in enumerate(devices):
        opts.append(SelectOptionDict(value=str(i), label=_device_label(d)))

    opts.append(SelectOptionDict(value=Action.DONE, label="Save & close"))
    return opts


def _device_action_options(idx: int, devices: list[dict]) -> list[SelectOptionDict]:
    """Action sub-menu for a selected device (edit, dup, move, remove, panels)."""
    label = _device_label(devices[idx])
    return [
        SelectOptionDict(value=f"{Action.PANELS}_{idx}", label=f"Manage panels: {label}"),
        SelectOptionDict(value=f"{Action.EDIT}_{idx}", label=f"Edit: {label}"),
        SelectOptionDict(value=f"{Action.DUP}_{idx}", label=f"Duplicate: {label}"),
        SelectOptionDict(value=f"{Action.MOVE_UP}_{idx}", label=f"Move up: {label}"),
        SelectOptionDict(value=f"{Action.MOVE_DOWN}_{idx}", label=f"Move down: {label}"),
        SelectOptionDict(value=f"{Action.REMOVE}_{idx}", label=f"Remove: {label}"),
        SelectOptionDict(value=Action.BACK, label="← Back"),
    ]


def _device_edit_schema(current: dict) -> vol.Schema:
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



def _panel_edit_schema(current: dict, panel_types: list[SelectOptionDict]) -> vol.Schema:
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


@lru_cache(maxsize=64)
def _panel_type_options(panel_type: str) -> list:
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


def _panel_type_specific_schema(panel_type: str, current: dict | None = None) -> tuple[dict, dict]:
    """Build a schema dict and transform map from PageOptions declared on the panel's page class.

    Returns a (schema_dict, transforms_dict) tuple. The caller merges schema_dict
    into the full voluptuous schema; transforms_dict maps option keys to transform
    kinds (e.g. ``"list_str"``, ``"drop_empty"``) that should be applied to the
    validated user input via :func:`_apply_transforms`.
    """
    current = current or {}
    schema: dict = {}
    transforms: dict = {}

    for opt in _panel_type_options(panel_type):
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


def _apply_transforms(user_input: dict, transforms: dict) -> dict:
    """Apply per-key transforms to convert form values into canonical config representation.

    Transforms are declared alongside the schema by :func:`_panel_type_specific_schema`.
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


def _extract_panel_config(user_input: dict, edit_idx: int, panels: list[dict]) -> dict:
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



def _find_esphome_device(hass, device_name: str) -> str | None:
    """Try to match an NSPanel device name to an existing ESPHome device entry.

    Returns the ESPHome config entry ID if matched, or None.
    """
    # Primary path: esphome integration stores entries in hass.data
    try:
        esphome_data = hass.data.get("esphome", {})
        if esphome_data:
            for entry_id, entry_data in esphome_data.items():
                if not isinstance(entry_data, dict):
                    continue
                device_info = entry_data.get("device_info", {})
                if isinstance(device_info, dict):
                    if device_info.get("name") == device_name:
                        return entry_id
    except Exception:
        _LOGGER.debug("Error in _find_esphome_device primary lookup", exc_info=True)

    # Fallback: scan entity states for esphome platform entities.
    # Cannot determine entry_id here, so return None even on match.
    try:
        for state in hass.states.async_all():
            if state.attributes.get("platform") == "esphome":
                if device_name.lower() in state.entity_id.lower():
                    return None  # confirmed match, but no entry_id available
    except Exception:
        _LOGGER.debug("Error in _find_esphome_device fallback lookup", exc_info=True)

    return None

# ── Config Flow ─────────────────────────────────────────────────────────────


class NSPanelHAUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("scan_mqtt"):
                # ── Scan MQTT path: store context, run discovery, transition ──
                mqtt_available = await _mqtt_available(self.hass)
                if not mqtt_available:
                    errors["base"] = "mqtt_not_configured"
                else:
                    self._entry_name = user_input["name"].strip()
                    prefix = user_input.get("mqtt_topic_prefix", "nspanel_haui")
                    self._mqtt_topic_prefix = prefix
                    self._discovered_devices = await _run_mqtt_discovery(
                        self.hass, prefix=prefix, timeout=MQTT_DISCOVERY_TIMEOUT,
                    )
                    return await self.async_step_discovery()
            else:
                # ── Submit path (no scan): validate, create entry with empty devices ──
                name = user_input["name"].strip()
                if not name:
                    errors["name"] = "empty_name"
                else:
                    await self.async_set_unique_id(name)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=name,
                        data={"name": name},
                        options={
                            "mqtt_topic_prefix": user_input.get("mqtt_topic_prefix", "nspanel_haui"),
                            "devices": [],
                            "config_yaml": "",
                        },
                    )

        # Build schema (base fields only; device multi-select moved to discovery step)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Optional("mqtt_topic_prefix", default="nspanel_haui"): str,
                vol.Optional("scan_mqtt", default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_discovery(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Second step: select discovered devices with ESPHome matching info."""
        discovered: list[dict] = getattr(self, "_discovered_devices", [])
        entry_name: str = getattr(self, "_entry_name", "nspanel_haui")
        prefix: str = getattr(self, "_mqtt_topic_prefix", "nspanel_haui")

        if user_input is not None:
            selected: list[str] = user_input.get("selected_devices", [])

            # Validate entry name (deferred from user step scan path)
            await self.async_set_unique_id(entry_name)
            self._abort_if_unique_id_configured()

            # Build devices list with ESPHome matching
            discovered_map: dict[str, dict] = {d["name"]: d for d in discovered}
            devices_list: list[dict] = []
            for device_name in selected:
                dev = copy.deepcopy(DEVICE_CONFIG)
                dev["name"] = device_name
                match = discovered_map.get(device_name)
                if match and match.get("esphome_device_id"):
                    dev["esphome_device_id"] = match["esphome_device_id"]
                devices_list.append(dev)

            return self.async_create_entry(
                title=entry_name,
                data={"name": entry_name},
                options={
                    "mqtt_topic_prefix": prefix,
                    "devices": devices_list,
                    "config_yaml": "",
                },
            )

        # ── Show discovery form ──
        if not discovered:
            # No devices found — empty schema, user clicks Submit to continue
            return self.async_show_form(
                step_id="discovery",
                data_schema=vol.Schema({}),
                description_placeholders={"count": "0", "esphome_info": ""},
            )

        # Count ESPHome matches
        esphome_count = sum(1 for d in discovered if d.get("esphome_device_id"))
        esphome_info = (
            f"ESPHome matched: {esphome_count} device(s)" if esphome_count > 0 else ""
        )

        # Pre-select ESPHome-matched devices; fall back to selecting all
        preselected = [d["name"] for d in discovered if d.get("esphome_device_id")]
        if not preselected:
            preselected = [d["name"] for d in discovered]

        device_options = [
            SelectOptionDict(value=d["name"], label=d["name"]) for d in discovered
        ]
        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema({
                vol.Required(
                    "selected_devices", default=preselected
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }),
            description_placeholders={
                "count": str(len(discovered)),
                "esphome_info": esphome_info,
            },
        )

    @staticmethod
    async def async_migrate_entry(hass, config_entry):
        """Migrate config entry from v1 to v2, then v2 to v3."""
        if config_entry.version == 1:
            from .haui.mapping.const import DEFAULT_CONFIG as _DEFAULT

            new_data = dict(config_entry.data)
            new_options = dict(config_entry.options)

            # Move mqtt_topic_prefix from data to options
            mqtt_prefix = new_data.pop(
                "mqtt_topic_prefix",
                _DEFAULT["mqtt"]["topic_prefix"],
            )
            new_options["mqtt_topic_prefix"] = mqtt_prefix

            # Keep only "name" in data
            new_data = {"name": new_data.get("name", "nspanel_haui")}

            # Drop device/connection/update/navigation keys from options
            for key in ("device", "connection", "update", "navigation"):
                new_options.pop(key, None)

            # Preserve panels and config_yaml (stay in new_options as-is)

            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                options=new_options,
                version=2,
            )

        if config_entry.version == 2:
            new_options = dict(config_entry.options)
            if "devices" not in new_options:
                new_options["devices"] = []
            hass.config_entries.async_update_entry(
                config_entry, options=new_options, version=3
            )

        if config_entry.version == 3:
            new_options = dict(config_entry.options)
            shared_panels = new_options.pop("panels", None)
            if shared_panels is not None and "devices" in new_options:
                for dev in new_options["devices"]:
                    if "panels" not in dev or not dev["panels"]:
                        dev["panels"] = copy.deepcopy(shared_panels)
            hass.config_entries.async_update_entry(
                config_entry, options=new_options, version=4
            )

        return True

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NSPanelHAUIOptionsFlow:
        return NSPanelHAUIOptionsFlow(config_entry)


# ── Options Flow ─────────────────────────────────────────────────────────────


class NSPanelHAUIOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__(config_entry)
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

    def _build_full_config(self) -> dict:
        """Build the full config dict from current flow state for validation.

        Mirrors :func:`_options_to_config_dict` but uses the in-progress
        ``_ctx`` state so we can validate *before* the final ``async_create_entry``.
        """
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["device"]["name"] = self.config_entry.data.get("name", "")

        if "mqtt_topic_prefix" in self.config_entry.options:
            cfg["mqtt"]["topic_prefix"] = self.config_entry.options["mqtt_topic_prefix"]

        if self._ctx.get("devices"):
            cfg["devices"] = copy.deepcopy(self._ctx["devices"])
            all_panels = []
            for dev in cfg["devices"]:
                all_panels.extend(dev.get("panels", []))
            cfg["panels"] = all_panels
        elif self._ctx.get("panels"):
            cfg["panels"] = list(self._ctx["panels"])

        return cfg

    def _build_panel_schema(self, current: dict, panel_types, user_input=None):
        base_schema = _panel_edit_schema(current, panel_types).schema

        panel_type = None
        if user_input:
            panel_type = user_input.get("type")

        if not panel_type:
            panel_type = current.get("type")

        if not panel_type and panel_types:
            panel_type = panel_types[0]["value"]

        # If type changed since last submit, drop stale option values from current.
        type_current = current if current.get("type") == panel_type else {}
        type_schema, _transforms = _panel_type_specific_schema(panel_type, type_current)

        return vol.Schema({**base_schema, **type_schema})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["devices", "topic", "yaml_override"],
        )

    async def async_step_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            new_options = dict(self.config_entry.options)
            new_options["mqtt_topic_prefix"] = user_input["mqtt_topic_prefix"]
            new_options.pop("config_yaml", None)

            # Validate full config before saving
            try:
                validate_config(self._build_full_config())
            except Exception:
                return self.async_show_form(
                    step_id="topic",
                    data_schema=vol.Schema({
                        vol.Required(
                            "mqtt_topic_prefix",
                            default=user_input["mqtt_topic_prefix"],
                        ): str,
                    }),
                    errors={"base": "invalid_config"},
                )

            return self.async_create_entry(data=new_options)

        current_prefix = self.config_entry.options.get("mqtt_topic_prefix", "nspanel_haui")
        return self.async_show_form(
            step_id="topic",
            data_schema=vol.Schema({
                vol.Required("mqtt_topic_prefix", default=current_prefix): str,
            }),
        )

    async def async_step_panels(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if not ctx["panels"] and user_input is None:
            if ctx["panel_device_idx"] >= 0:
                dev = ctx["devices"][ctx["panel_device_idx"]]
                self._panel_editor = ListEditor(copy.deepcopy(dev.get("panels", [{"type": "clock"}])))
            else:
                self._panel_editor = ListEditor(copy.deepcopy(
                    self.config_entry.options.get("panels", DEFAULT_CONFIG["panels"])
                ))
            ctx["panels"] = self._panel_editor.items

        if user_input is not None:
            action = user_input["panel_action"]

            if action == Action.ADD:
                ctx["panel_idx"] = -1
                return await self.async_step_panel_edit()

            if action == Action.DONE:
                if ctx["panel_device_idx"] >= 0:
                    ctx["devices"][ctx["panel_device_idx"]]["panels"] = ctx["panels"]
                    ctx["panel_device_idx"] = -1

                    # Validate full config before saving
                    try:
                        validate_config(self._build_full_config())
                    except Exception:
                        return self.async_show_form(
                            step_id="panels",
                            data_schema=vol.Schema({
                                vol.Required("panel_action"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=_panel_list_options(ctx["panels"]),
                                        mode=selector.SelectSelectorMode.LIST,
                                    )
                                ),
                            }),
                            errors={"base": "invalid_config"},
                        )

                    new_options = dict(self.config_entry.options)
                    new_options["devices"] = ctx["devices"]
                    new_options.pop("config_yaml", None)
                    return self.async_create_entry(data=new_options)
                else:
                    # Validate full config before saving
                    try:
                        validate_config(self._build_full_config())
                    except Exception:
                        return self.async_show_form(
                            step_id="panels",
                            data_schema=vol.Schema({
                                vol.Required("panel_action"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=_panel_list_options(ctx["panels"]),
                                        mode=selector.SelectSelectorMode.LIST,
                                    )
                                ),
                            }),
                            errors={"base": "invalid_config"},
                        )

                    new_options = dict(self.config_entry.options)
                    new_options["panels"] = ctx["panels"]
                    new_options.pop("config_yaml", None)
                    return self.async_create_entry(data=new_options)

            # Action is an index string like "0", "1", "2" for panel selection
            ctx["panel_idx"] = int(action)
            return await self.async_step_panel_action()

        return self.async_show_form(
            step_id="panels",
            data_schema=vol.Schema({
                vol.Required("panel_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_panel_list_options(ctx["panels"]),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={"count": str(len(ctx["panels"]))},
        )

    async def async_step_panel_action(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if user_input is not None:
            action = user_input["panel_action"]

            if action == Action.BACK:
                return await self.async_step_panels()

            edit_prefix = Action.EDIT + "_"
            if action.startswith(edit_prefix):
                ctx["panel_idx"] = int(action[len(edit_prefix):])
                return await self.async_step_panel_edit()

            dup_prefix = Action.DUP + "_"
            if action.startswith(dup_prefix):
                idx = int(action[len(dup_prefix):])
                self._panel_editor.duplicate(idx)

            up_prefix = Action.MOVE_UP + "_"
            if action.startswith(up_prefix):
                i = int(action[len(up_prefix):])
                self._panel_editor.move(i, -1)

            down_prefix = Action.MOVE_DOWN + "_"
            if action.startswith(down_prefix):
                i = int(action[len(down_prefix):])
                self._panel_editor.move(i, 1)

            remove_prefix = Action.REMOVE + "_"
            if action.startswith(remove_prefix):
                idx = int(action[len(remove_prefix):])
                self._panel_editor.remove(idx)

            # After inline actions (dup, up, down, remove), return to panel list
            if action != Action.BACK:
                return await self.async_step_panels()

            return await self.async_step_panel_action()

        idx = ctx["panel_idx"]
        panel_label = _panel_label(ctx["panels"][idx])
        return self.async_show_form(
            step_id="panel_action",
            data_schema=vol.Schema({
                vol.Required("panel_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_panel_action_options(idx, ctx["panels"]),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={
                "index": str(idx),
                "label": panel_label,
            },
        )

    async def async_step_panel_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        panel_types = _user_panel_types()
        panel_idx = ctx["panel_idx"]
        editing = panel_idx >= 0

        current: dict = ctx["panels"][panel_idx] if editing else {}

        if user_input is not None:
            panel_type = user_input.get("type") or current.get("type", "")
            _type_schema, transforms = _panel_type_specific_schema(panel_type, {})
            normalized = _apply_transforms(user_input, transforms)
            panel_cfg = _extract_panel_config(normalized, panel_idx, ctx["panels"])

            # validate
            try:
                validate_config({"panels": [panel_cfg]})
            except Exception:
                return self.async_show_form(
                    step_id="panel_edit",
                    data_schema=self._build_panel_schema(current, panel_types, user_input),
                    errors={"base": "invalid_panel"},
                )

            if editing:
                self._panel_editor.edit(panel_idx, panel_cfg)
            else:
                self._panel_editor.add(panel_cfg)

            ctx["panel_idx"] = -1
            return await self.async_step_panels()

        return self.async_show_form(
            step_id="panel_edit",
            data_schema=self._build_panel_schema(current, panel_types),
            errors={},
        )

    # ── Device options sub-flow ──────────────────────────────────────────────

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if not ctx["devices"] and user_input is None:
            self._device_editor = ListEditor(copy.deepcopy(
                self.config_entry.options.get("devices", [])
            ))
            ctx["devices"] = self._device_editor.items

        if user_input is not None:
            action = user_input["device_action"]

            if action == Action.ADD:
                ctx["device_idx"] = -1
                return await self.async_step_device_edit()

            if action == Action.DISCOVER:
                return await self.async_step_device_discover()

            if action == Action.DONE:
                # Validate full config before saving
                try:
                    validate_config(self._build_full_config())
                except Exception:
                    return self.async_show_form(
                        step_id="devices",
                        data_schema=vol.Schema({
                            vol.Required("device_action"): selector.SelectSelector(
                                selector.SelectSelectorConfig(
                                    options=_device_list_options(ctx["devices"]),
                                    mode=selector.SelectSelectorMode.LIST,
                                )
                            ),
                        }),
                        errors={"base": "invalid_config"},
                    )

                new_options = dict(self.config_entry.options)
                new_options["devices"] = ctx["devices"]
                new_options.pop("config_yaml", None)
                return self.async_create_entry(data=new_options)

            # Action is an index string like "0", "1", "2" for device selection
            ctx["device_idx"] = int(action)
            return await self.async_step_device_action()

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({
                vol.Required("device_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_device_list_options(ctx["devices"]),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={"count": str(len(ctx["devices"]))},
        )

    async def async_step_device_action(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if user_input is not None:
            action = user_input["device_action"]

            if action == Action.BACK:
                return await self.async_step_devices()

            panels_prefix = Action.PANELS + "_"
            if action.startswith(panels_prefix):
                idx = int(action[len(panels_prefix):])
                ctx["panel_device_idx"] = idx
                self._panel_editor = ListEditor(copy.deepcopy(
                    ctx["devices"][idx].get("panels", [{"type": "clock"}])
                ))
                ctx["panels"] = self._panel_editor.items
                return await self.async_step_panels()

            edit_prefix = Action.EDIT + "_"
            if action.startswith(edit_prefix):
                ctx["device_idx"] = int(action[len(edit_prefix):])
                return await self.async_step_device_edit()

            dup_prefix = Action.DUP + "_"
            if action.startswith(dup_prefix):
                idx = int(action[len(dup_prefix):])
                self._device_editor.duplicate(idx)

            up_prefix = Action.MOVE_UP + "_"
            if action.startswith(up_prefix):
                i = int(action[len(up_prefix):])
                self._device_editor.move(i, -1)

            down_prefix = Action.MOVE_DOWN + "_"
            if action.startswith(down_prefix):
                i = int(action[len(down_prefix):])
                self._device_editor.move(i, 1)

            remove_prefix = Action.REMOVE + "_"
            if action.startswith(remove_prefix):
                idx = int(action[len(remove_prefix):])
                self._device_editor.remove(idx)

            # After inline actions, return to device list
            if action != Action.BACK:
                return await self.async_step_devices()

            return await self.async_step_device_action()

        idx = ctx["device_idx"]
        device_label = _device_label(ctx["devices"][idx])
        return self.async_show_form(
            step_id="device_action",
            data_schema=vol.Schema({
                vol.Required("device_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_device_action_options(idx, ctx["devices"]),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={
                "index": str(idx),
                "label": device_label,
            },
        )

    async def async_step_device_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        device_idx = ctx["device_idx"]
        editing = device_idx >= 0
        current: dict = ctx["devices"][device_idx] if editing else {}

        if user_input is not None:
            device_cfg = {}
            for field in DEVICE_CONFIG:
                if field in user_input:
                    device_cfg[field] = user_input[field]
                else:
                    device_cfg[field] = current.get(field, DEVICE_CONFIG[field])

            if editing:
                self._device_editor.edit(device_idx, device_cfg)
            else:
                self._device_editor.add(device_cfg)

            ctx["device_idx"] = -1
            return await self.async_step_devices()

        return self.async_show_form(
            step_id="device_edit",
            data_schema=_device_edit_schema(current),
            errors={},
        )

    async def async_step_device_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Discover new devices on MQTT and let the user add them."""
        ctx = self._ctx
        if user_input is not None:
            selected: list[str] = user_input.get("selected_devices", [])
            existing_names = {d.get("name") for d in ctx["devices"]}
            for device_name in selected:
                if device_name not in existing_names:
                    dev = copy.deepcopy(DEVICE_CONFIG)
                    dev["name"] = device_name
                    self._device_editor.add(dev)
            return await self.async_step_devices()

        # Run discovery
        mqtt_available = await _mqtt_available(self.hass)
        if not mqtt_available:
            return self.async_show_form(
                step_id="device_discover",
                data_schema=vol.Schema({}),
                errors={"base": "mqtt_not_configured"},
                description_placeholders={"count": "0"},
            )

        current_prefix = self.config_entry.options.get("mqtt_topic_prefix", "nspanel_haui")
        discovered = await _run_mqtt_discovery(
            self.hass, prefix=current_prefix, timeout=MQTT_DISCOVERY_TIMEOUT,
        )

        existing_names = {d.get("name") for d in ctx["devices"]}
        new_devices = [d for d in discovered if d["name"] not in existing_names]

        if not new_devices:
            # No new devices — return to device list with a note
            return await self.async_step_devices()

        device_options = [
            SelectOptionDict(value=d["name"], label=d["name"]) for d in new_devices
        ]
        return self.async_show_form(
            step_id="device_discover",
            data_schema=vol.Schema({
                vol.Required("selected_devices", default=[d["name"] for d in new_devices]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }),
            description_placeholders={"count": str(len(new_devices))},
        )

    async def async_step_yaml_override(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        current_yaml: str = self.config_entry.options.get("config_yaml", "")

        if user_input is not None:
            raw_yaml: str = user_input.get("config_yaml", "")
            try:
                parsed = yaml.safe_load(raw_yaml)
                if not isinstance(parsed, dict):
                    raise TypeError("must be mapping")
            except Exception:
                errors["config_yaml"] = "invalid_yaml"
            else:
                try:
                    validate_config(parsed)
                except Exception:
                    errors["config_yaml"] = "invalid_config"

            if not errors:
                new_options = dict(self.config_entry.options)
                new_options["config_yaml"] = raw_yaml
                return self.async_create_entry(data=new_options)

            current_yaml = raw_yaml

        return self.async_show_form(
            step_id="yaml_override",
            data_schema=vol.Schema({
                vol.Required("config_yaml", default=current_yaml): selector.selector({
                    "text": {"multiline": True}
                }),
            }),
            errors=errors,
        )


# ── MQTT helpers ─────────────────────────────────────────────────────────────


async def _mqtt_available(hass: Any) -> bool:
    try:
        from homeassistant.components import mqtt

        return mqtt.is_connected(hass)
    except Exception:
        return False


async def _run_mqtt_discovery(
    hass: Any,
    prefix: str = "nspanel_haui",
    timeout: int = MQTT_DISCOVERY_TIMEOUT,
) -> list[dict]:
    """Subscribe to all NSPanel recv topics; collect device names + ESPHome matches."""
    found: set[str] = set()

    try:
        from homeassistant.components import mqtt

        async def _on_message(msg: Any) -> None:
            try:
                data = json.loads(msg.payload)
                if data.get("name") == "connected":
                    parts = msg.topic.split("/")
                    if len(parts) == 3:
                        found.add(parts[1])
            except (json.JSONDecodeError, ValueError):
                pass

        unsub = await mqtt.async_subscribe(hass, f"{prefix}/+/recv", _on_message)
        await asyncio.sleep(timeout)
        unsub()
    except Exception as exc:
        _LOGGER.debug("MQTT discovery error: %s", exc)

    # Enrich with ESPHome device matches
    result: list[dict] = []
    for name in sorted(found):
        result.append({
            "name": name,
            "esphome_device_id": _find_esphome_device(hass, name),
        })
    return result

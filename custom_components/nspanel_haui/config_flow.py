"""Config flow for NSPanel HAUI."""

from __future__ import annotations

import copy
import logging
from enum import StrEnum
from typing import Any

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectOptionDict

from .haui.config_models import validate_config
from .haui.mapping.const import DEFAULT_CONFIG, DEVICE_CONFIG
from .config_editor import ConfigEditor
from .list_editor import ListEditor
from .mqtt_helpers import (
    MQTT_DISCOVERY_TIMEOUT,
    find_esphome_device as _find_esphome_device,
    mqtt_available as _mqtt_available,
    normalize_device_name as _normalize_device_name,
    run_mqtt_discovery as _run_mqtt_discovery,
)
from .config_schema import ConfigSchema

# Backward-compatible re-exports for tests that import from config_flow
_user_panel_types = ConfigSchema.user_panel_types
_panel_label = ConfigSchema.panel_label
_panel_list_options = ConfigSchema.panel_list_options
_panel_action_options = ConfigSchema.panel_action_options
_device_label = ConfigSchema.device_label
_device_list_options = ConfigSchema.device_list_options
_device_action_options = ConfigSchema.device_action_options
_device_edit_schema = ConfigSchema.device_edit_schema
_panel_edit_schema = ConfigSchema.panel_edit_schema
_panel_type_options = ConfigSchema.panel_type_options
_panel_type_specific_schema = ConfigSchema.panel_type_specific_schema
_apply_transforms = ConfigSchema.apply_transforms
_extract_panel_config = ConfigSchema.extract_panel_config

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




class NSPanelHAUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 5

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
                            "config_mode": "ui",
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
                    "config_mode": "ui",
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

        if config_entry.version == 4:
            new_options = dict(config_entry.options)
            if "config_mode" not in new_options:
                if new_options.get("config_yaml"):
                    new_options["config_mode"] = "yaml"
                else:
                    new_options["config_mode"] = "ui"
            hass.config_entries.async_update_entry(
                config_entry, options=new_options, version=5
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
        self._editor = ConfigEditor(config_entry)

    # Backward-compatible accessors for tests that manipulate internal state
    @property
    def _ctx(self) -> dict[str, Any]:
        return self._editor.ctx

    @property
    def _panel_editor(self) -> ListEditor:
        return self._editor._panel_editor

    @_panel_editor.setter
    def _panel_editor(self, value: ListEditor) -> None:
        self._editor._panel_editor = value

    @property
    def _device_editor(self) -> ListEditor:
        return self._editor._device_editor

    @_device_editor.setter
    def _device_editor(self, value: ListEditor) -> None:
        self._editor._device_editor = value

    def _build_full_config(self) -> dict:
        """Build the full config dict from current flow state for validation."""
        return self._editor.build_full_config()

    def _build_panel_schema(self, current: dict, panel_types, user_input=None):
        return ConfigSchema.build_panel_schema(current, panel_types, user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        options = dict(self.config_entry.options)
        current_mode = options.get("config_mode", "ui")

        if current_mode == "yaml":
            return self.async_show_menu(
                step_id="init",
                menu_options=["yaml_override", "switch_to_ui"],
                description_placeholders={"mode": "YAML"},
            )
        else:
            return self.async_show_menu(
                step_id="init",
                menu_options=["devices", "topic", "switch_to_yaml"],
            )

    async def async_step_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            new_options = dict(self.config_entry.options)
            new_options["mqtt_topic_prefix"] = user_input["mqtt_topic_prefix"]
            new_options.pop("config_yaml", None)
            new_options["config_mode"] = "ui"

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
                    new_options["config_mode"] = "ui"
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
                    new_options["config_mode"] = "ui"
                    new_options.pop("config_yaml", None)
                    return self.async_create_entry(data=new_options)

            # Action is an index string like "0", "1", "2" for panel selection
            if action.isdigit():
                idx = int(action)
                ctx["panel_idx"] = idx
                panel = ctx["panels"][idx]
                return self.async_show_menu(
                    step_id="panel_menu",
                    menu_options=[
                        "edit_panel",
                        "duplicate_panel",
                        "move_up",
                        "move_down",
                        "remove_panel",
                        "back",
                    ],
                    description_placeholders={"label": _panel_label(panel)},
                )

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

    async def async_step_panel_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if user_input is not None:
            action = user_input.get("menu_item", "")
            idx = ctx["panel_idx"]

            if action == "edit_panel":
                return await self.async_step_panel_edit()

            if action == "duplicate_panel":
                self._panel_editor.duplicate(idx)
            elif action == "move_up":
                self._panel_editor.move(idx, -1)
            elif action == "move_down":
                self._panel_editor.move(idx, 1)
            elif action == "remove_panel":
                self._panel_editor.remove(idx)
            elif action == "back":
                pass
            else:
                # Unknown action — reshow menu
                idx = ctx["panel_idx"]
                panel_label = _panel_label(ctx["panels"][idx])
                return self.async_show_menu(
                    step_id="panel_menu",
                    menu_options=[
                        "edit_panel",
                        "duplicate_panel",
                        "move_up",
                        "move_down",
                        "remove_panel",
                        "back",
                    ],
                    description_placeholders={"label": panel_label},
                )

            return await self.async_step_panels()

        idx = ctx["panel_idx"]
        panel_label = _panel_label(ctx["panels"][idx])
        return self.async_show_menu(
            step_id="panel_menu",
            menu_options=[
                "edit_panel",
                "duplicate_panel",
                "move_up",
                "move_down",
                "remove_panel",
                "back",
            ],
            description_placeholders={"label": panel_label},
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
                new_options["config_mode"] = "ui"
                new_options.pop("config_yaml", None)
                return self.async_create_entry(data=new_options)

            # Action is an index string like "0", "1", "2" for device selection
            if action.isdigit():
                idx = int(action)
                ctx["device_idx"] = idx
                device = ctx["devices"][idx]
                return self.async_show_menu(
                    step_id="device_menu",
                    menu_options=[
                        "manage_panels",
                        "edit_device",
                        "duplicate_device",
                        "move_up",
                        "move_down",
                        "remove_device",
                    ],
                    description_placeholders={"label": _device_label(device)},
                )

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

    async def async_step_device_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        ctx = self._ctx
        if user_input is not None:
            action = user_input.get("menu_item", "")
            idx = ctx["device_idx"]

            if action == "manage_panels":
                ctx["panel_device_idx"] = idx
                dev_panels = copy.deepcopy(
                    ctx["devices"][idx].get("panels", [{"type": "clock"}])
                )
                self._panel_editor = ListEditor(dev_panels)
                ctx["panels"] = self._panel_editor.items
                return await self.async_step_panels()

            if action == "edit_device":
                return await self.async_step_device_edit()

            if action == "duplicate_device":
                self._device_editor.duplicate(idx)
            elif action == "move_up":
                self._device_editor.move(idx, -1)
            elif action == "move_down":
                self._device_editor.move(idx, 1)
            elif action == "remove_device":
                self._device_editor.remove(idx)
            else:
                # back or unknown — return to device list
                pass

            return await self.async_step_devices()

        idx = ctx["device_idx"]
        device_label = _device_label(ctx["devices"][idx])
        return self.async_show_menu(
            step_id="device_menu",
            menu_options=[
                "manage_panels",
                "edit_device",
                "duplicate_device",
                "move_up",
                "move_down",
                "remove_device",
            ],
            description_placeholders={"label": device_label},
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
                new_options["config_mode"] = "yaml"
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

    async def async_step_switch_to_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Generate YAML from current structured config and switch mode."""
        options = dict(self.config_entry.options)

        if user_input is not None:
            confirm = user_input.get("confirm", False)
            if confirm:
                # Ensure context is populated from entry options for _build_full_config
                if not self._ctx.get("devices"):
                    self._device_editor = ListEditor(copy.deepcopy(
                        options.get("devices", [])
                    ))
                    self._ctx["devices"] = self._device_editor.items

                full_config = self._build_full_config()
                yaml_text = yaml.dump(full_config, default_flow_style=False, allow_unicode=True)

                new_options = dict(options)
                new_options["config_yaml"] = yaml_text
                new_options["config_mode"] = "yaml"
                return self.async_create_entry(data=new_options)
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="switch_to_yaml",
            data_schema=vol.Schema({
                vol.Required("confirm", default=True): bool,
            }),
            description_placeholders={
                "note": "Switching to YAML mode will generate YAML from your current UI config. "
                        "Future changes must be made in YAML. You can switch back at any time."
            },
        )

    async def async_step_switch_to_ui(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Parse YAML → structured config and switch mode."""
        options = dict(self.config_entry.options)
        current_yaml = options.get("config_yaml", "")

        if user_input is not None:
            confirm = user_input.get("confirm", False)
            if confirm:
                try:
                    parsed = yaml.safe_load(current_yaml)
                    if not isinstance(parsed, dict):
                        raise TypeError("must be mapping")
                except Exception:
                    return self.async_show_form(
                        step_id="switch_to_ui",
                        data_schema=vol.Schema({
                            vol.Required("confirm", default=True): bool,
                        }),
                        errors={"base": "invalid_yaml"},
                        description_placeholders={
                            "note": "Failed to parse YAML. Please fix it in yaml_override first."
                        },
                    )

                new_options = dict(options)
                new_options["config_mode"] = "ui"

                # Populate structured fields from parsed YAML
                if "devices" in parsed:
                    new_options["devices"] = parsed["devices"]
                elif "panels" in parsed:
                    new_options["panels"] = parsed["panels"]

                if "mqtt" in parsed and "topic_prefix" in parsed["mqtt"]:
                    new_options["mqtt_topic_prefix"] = parsed["mqtt"]["topic_prefix"]

                # Keep config_yaml so user can switch back
                return self.async_create_entry(data=new_options)
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="switch_to_ui",
            data_schema=vol.Schema({
                vol.Required("confirm", default=True): bool,
            }),
            description_placeholders={
                "note": "Switching to UI mode will import your YAML config. "
                        "The YAML will be preserved but no longer used. You can switch back at any time."
            },
        )


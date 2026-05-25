/**
 * NSPanel HAUI - Editor - device configuration.
 * Extracted from panel-editor.js; see that file for the class that delegates to these helpers.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.  The class methods are thin wrappers:
 *
 *   _loadDeviceConfig(name)   { return DeviceConfig.loadDeviceConfig(this, name); }
 *   _openDeviceConfig()       { return DeviceConfig.openDeviceConfig(this); }
 *   _closeDeviceConfig()      { return DeviceConfig.closeDeviceConfig(this); }
 *   _saveDeviceConfig()       { return DeviceConfig.saveDeviceConfig(this); }
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';

/* ── load ─────────────────────────────────────────────────────────────────── */

export function loadDeviceConfig(host, name) {
  const dev = host._panels.devices ? host._panels.devices[name] : undefined;
  const existing = (dev && dev.config) || {};
  host._deviceConfig = { ...DEVICE_CONFIG_DEFAULTS, ...existing };
}

/* ── open / close ─────────────────────────────────────────────────────────── */

export function openDeviceConfig(host) {
  host._editingDeviceConfig = true;
  host._deviceConfigForm = clone(host._deviceConfig || DEVICE_CONFIG_DEFAULTS);
}

export function closeDeviceConfig(host) {
  host._editingDeviceConfig = false;
  host._deviceConfigForm = null;
}

/* ── save ─────────────────────────────────────────────────────────────────── */

export async function saveDeviceConfig(host) {
  const form = host.renderRoot ? host.renderRoot.querySelector("#device-config-form") : null;
  if (!form || !host._deviceConfigForm) return;

  const cfg = clone(host._deviceConfigForm);

  // Read booleans from checkboxes
  const boolKeys = [
    "show_home_button", "show_sleep_button", "show_notifications_button",
    "home_on_wakeup", "home_on_first_touch", "home_only_when_on",
    "home_on_button_toggle", "always_return_to_home", "sound_on_startup",
    "sound_on_notification", "use_relay_left", "use_relay_right",
    "enabled",
  ];
  for (const k of boolKeys) {
    const el = form.querySelector(`#dc-${k}`); cfg[k] = el ? el.checked : false;
  }

  // Read text fields
  let dcEl;
  dcEl = form.querySelector("#dc-locale"); cfg.locale = dcEl ? dcEl.value : "en_US";
  dcEl = form.querySelector("#dc-button_left_entity"); cfg.button_left_entity = dcEl ? dcEl.value : null;
  dcEl = form.querySelector("#dc-button_right_entity"); cfg.button_right_entity = dcEl ? dcEl.value : null;
  dcEl = form.querySelector("#dc-home_panel"); cfg.home_panel = (dcEl && dcEl.value) || "";
  dcEl = form.querySelector("#dc-sleep_panel"); cfg.sleep_panel = (dcEl && dcEl.value) || "";
  dcEl = form.querySelector("#dc-wakeup_panel"); cfg.wakeup_panel = (dcEl && dcEl.value) || "";

  // Read number fields
  let numEl;
  numEl = form.querySelector("#dc-return_to_home_after_seconds"); const rth = parseInt(numEl ? numEl.value : "0", 10);
  cfg.return_to_home_after_seconds = rth;
  numEl = form.querySelector("#dc-debug_level"); const dbg = parseInt(numEl ? numEl.value : "0", 10);
  cfg.debug_level = isNaN(dbg) ? 0 : dbg;

  host._deviceConfig = cfg;
  host._editingDeviceConfig = false;
  host._deviceConfigForm = null;

  // savePanels clones host._deviceConfig into the POST payload, so
  // we don't need to manually update _panels.devices[].config.
  const panels = host._devicePanels();
  await host._savePanels(panels, "Device settings saved");
}

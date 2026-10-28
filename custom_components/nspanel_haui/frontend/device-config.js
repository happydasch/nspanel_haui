/**
 * NSPanel HAUI - device configuration.
 * Load/open/close helpers for the device configuration dialog state.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.  The class methods are thin wrappers:
 *
 *   _loadDeviceConfig(name)   { return DeviceConfig.loadDeviceConfig(this, name); }
 *   _openDeviceConfig()       { return DeviceConfig.openDeviceConfig(this); }
 *   _closeDeviceConfig()      { return DeviceConfig.closeDeviceConfig(this); }
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';

/* ── load ─────────────────────────────────────────────────────────────────── */

export function loadDeviceConfig(host, name) {
  const dev = host._panels.devices ? host._panels.devices[name] : undefined;
  const existing = (dev && dev.config) || {};
  host._deviceConfig = {
    ...DEVICE_CONFIG_DEFAULTS,
    ...existing,
    // The update block is nested; merge it over its defaults so a partial
    // stored block still shows the shipped defaults in the editor.
    update: { ...DEVICE_CONFIG_DEFAULTS.update, ...(existing.update || {}) },
  };
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

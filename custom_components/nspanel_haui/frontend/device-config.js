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
  host._deviceConfig = host.store.selectors.configFor(name);
}

/* ── open / close ─────────────────────────────────────────────────────────── */

export function openDeviceConfig(host) {
  host._editingDeviceConfig = true;
  host._deviceConfigForm = clone(host._deviceConfig || DEVICE_CONFIG_DEFAULTS);
  host.store.actions.pushOverlay({
    kind: 'device-settings',
    anchorKey: 'device-settings',
    subject: host._selectedDevice,
    draft: null,
  });
}

export function closeDeviceConfig(host) {
  host._editingDeviceConfig = false;
  host._deviceConfigForm = null;
  host.store.actions.closeOverlay('device-settings', 'device-settings');
}

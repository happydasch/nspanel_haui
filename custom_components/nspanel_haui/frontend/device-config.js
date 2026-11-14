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
import { clone } from './constants.js';

/* ── load ─────────────────────────────────────────────────────────────────── */

export function loadDeviceConfig(host, name) {
  host._deviceConfig = host.store.selectors.configFor(name);
}

/* ── open / close ─────────────────────────────────────────────────────────── */

export async function openDeviceConfig(host) {
  const name = host._selectedDevice;
  if (!name) return;
  if (!(await host.store.actions.loadDeviceConfig(name))) return;
  host._editingDeviceConfig = true;
  host._deviceConfigForm = clone(host.store.selectors.configFor(name));
  host.store.actions.pushOverlay({
    kind: 'device-settings',
    anchorKey: 'device-settings',
    subject: name,
    draft: null,
  });
}

export function closeDeviceConfig(host) {
  host._editingDeviceConfig = false;
  host._deviceConfigForm = null;
  host.store.actions.closeOverlay('device-settings', 'device-settings');
}

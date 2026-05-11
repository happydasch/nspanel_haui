/**
 * NSPanel HAUI - Editor - device management.
 *
 * Device dropdown and settings action.  Every function takes the Lit element
 * instance (`host`) as its first parameter.
 *
 * The device selector displays devices by their friendly name.
 * Internally the device key (ESPHome node name) is used as the stable
 * identifier - a lookup map bridges friendly name → device key.
 */
import { html } from './lit-import.js';
import * as Api from './api.js';
import * as DeviceConfig from './device-config.js';

/* ── device name map ──────────────────────────────────────────────────────── */

/**
 * Build a map of display name → device key.
 *
 * When two devices share the same friendly name the colliding entries are
 * disambiguated by appending the device key in parentheses so the user can
 * tell them apart.
 */
export function buildDeviceMap(host) {
  const devices = host._panels.devices || {};
  const nameToKey = {};
  const friendlyCounts = {};

  // First pass: count how many devices share each base name
  for (const key of Object.keys(devices)) {
    const cfg = devices[key]?.config || {};
    const baseName = cfg.friendly_name || key;
    friendlyCounts[baseName] = (friendlyCounts[baseName] || 0) + 1;
  }

  // Second pass: build unique display names
  for (const key of Object.keys(devices)) {
    const cfg = devices[key]?.config || {};
    const baseName = cfg.friendly_name || key;
    const displayName = friendlyCounts[baseName] > 1 && cfg.friendly_name
      ? `${baseName} (${key})`
      : baseName;
    nameToKey[displayName] = key;
  }

  return nameToKey;
}

/**
 * Return the display name (friendly name) for a given device key.
 */
export function getDeviceDisplayName(host, deviceKey) {
  const deviceMap = buildDeviceMap(host);
  return Object.entries(deviceMap).find(([, key]) => key === deviceKey)?.[0] || deviceKey;
}

/* ── device selection ─────────────────────────────────────────────────────── */

export function selectDevice(host, displayName) {
  const deviceMap = buildDeviceMap(host);
  const deviceKey = deviceMap[displayName];
  if (!deviceKey) return;
  host._selectedDevice = deviceKey;
  DeviceConfig.loadDeviceConfig(host, deviceKey);
  host.requestUpdate();
}

/* ── YAML import/export ──────────────────────────────────────────────────── */

export async function exportDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    await Api.exportDeviceYaml(host, deviceKey);
    host._showToast(`Exported "${deviceKey}" as YAML`, "success");
  } catch (e) {
    host._showToast(e.message || "Export failed", "error");
  }
}

export async function importDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    const msg = await Api.importDeviceYaml(host, deviceKey);
    if (msg) host._showToast(msg, "success");
  } catch (e) {
    host._showToast(e.message || "Import failed", "error");
  }
}

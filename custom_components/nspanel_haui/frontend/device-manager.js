/**
 * NSPanel HAUI - Editor - device management.
 *
 * Device map, selection, YAML import/export, and device manager button.
 * Every function takes the Lit element instance (`host`) as its first parameter.
 *
 * Device keys (ESPHome node names) are used as both the display name and
 * stable identifier — there is no separate friendly name.
 */
import { html } from './lit-import.js';
import * as Api from './api.js';
import * as DeviceConfig from './device-config.js';

/* ── device name map ──────────────────────────────────────────────────────── */

/**
 * Build a map of display name → device key.
 *
 * Since we use the device key itself as the display name, the map is a simple
 * identity mapping over device keys.
 */
export function buildDeviceMap(host) {
  const devices = host._panels.devices || {};
  const nameToKey = {};
  for (const key of Object.keys(devices)) {
    nameToKey[key] = key;
  }
  return nameToKey;
}

/**
 * Return the display name for a given device key — the key itself.
 */
export function getDeviceDisplayName(host, deviceKey) {
  return deviceKey;
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

/* ── device manager button ──────────────────────────────────────────────── */

/**
 * Render a device manager button that opens the device manager overlay
 * showing all configured devices with add/discover/remove capabilities.
 */
export function renderDeviceManagerButton(host) {
  return html`
    <ha-icon-button
      title="Device Manager"
      class="device-manager-btn"
      @click=${() => {
        host._openDeviceManager();
      }}
    >
      <ha-icon icon="mdi:devices"></ha-icon>
    </ha-icon-button>
  `;
}

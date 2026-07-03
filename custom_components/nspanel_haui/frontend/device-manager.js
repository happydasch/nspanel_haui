/**
 * NSPanel HAUI - device management.
 *
 * Device list, selection, YAML import/export, and device manager button.
 * Every function takes the Lit element instance (`host`) as its first parameter.
 *
 * Device keys (ESPHome node names) are used as both the display name and
 * stable identifier — there is no separate friendly name.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import * as Api from './api.js';
import * as DeviceConfig from './device-config.js';

/* ── device keys ──────────────────────────────────────────────────────────── */

/**
 * Return the list of device keys (sorted, stable).
 * Each key is the ESPHome node name and serves as both ID and display name.
 */
export function getDeviceKeys(host) {
  return Object.keys(host._panels.devices || {});
}

/* ── device selection ─────────────────────────────────────────────────────── */

export function selectDevice(host, name) {
  if (!name || !host._panels.devices?.[name]) return;
  host._selectedDevice = name;
  DeviceConfig.loadDeviceConfig(host, name);
  host.requestUpdate();
}

/* ── YAML import/export ──────────────────────────────────────────────────── */

export async function exportDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    await Api.exportDeviceYaml(host, deviceKey);
    host._showToast(t('Exported "{name}" as YAML').replace('{name}', deviceKey), "success");
  } catch (e) {
    host._showToast(e.message || t("Export failed"), "error");
  }
}

export async function importDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    const msg = await Api.importDeviceYaml(host, deviceKey);
    if (msg) host._showToast(msg, "success");
  } catch (e) {
    host._showToast(e.message || t("Import failed"), "error");
  }
}

/* ── device manager button ──────────────────────────────────────────────── */

/**
 * Render a device manager button icon.
 */
export function renderDeviceManagerButton(host) {
  return html`<ha-icon-button
    title=${t('Device Manager')}
    class="device-manager-btn"
    @click=${() => host._openDeviceManager()}
  ><ha-icon icon="mdi:devices"></ha-icon></ha-icon-button>`;
}

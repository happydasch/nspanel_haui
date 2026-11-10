/**
 * NSPanel HAUI - device management.
 *
 * Device list, selection, YAML import/export, and device manager button.
 * Every function takes the Lit element instance (`host`) as its first parameter.
 *
 * Device keys (ESPHome node names) are the stable identifiers; the editor shows
 * the device registry name (`friendly_name`, added by the panels endpoint).
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import * as DeviceConfig from './device-config.js';

/* ── device keys ──────────────────────────────────────────────────────────── */

/**
 * Return the device keys in store order (the order set in the Device Manager).
 */
export function getDeviceKeys(host) {
  return Object.keys(host._panels.devices || {});
}

/* ── device selection ─────────────────────────────────────────────────────── */

export function selectDevice(host, name) {
  if (!name || !host.store.getState().devices.byName[name]) return;
  host.store.actions.selectDevice(name);
  DeviceConfig.loadDeviceConfig(host, name);
  host.requestUpdate();
}

/* ── YAML import/export ──────────────────────────────────────────────────── */

export async function exportDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    const yamlText = await host.api.yaml.export(host.entryId, deviceKey);
    downloadBlob(yamlText, `${deviceKey}.yaml`, "application/x-yaml");
    host._showToast(t('Exported "{name}" as YAML').replace('{name}', deviceKey), "success");
  } catch (e) {
    host._showToast(e.message || t("Export failed"), "error");
  }
}

export async function importDeviceYaml(host) {
  const deviceKey = host._selectedDevice;
  if (!deviceKey) return;
  try {
    const file = await pickYamlFile();
    if (!file) return;
    const yamlText = await file.text();
    const result = await host.api.yaml.import(host.entryId, deviceKey, yamlText);
    await host.store.actions.loadPanels();
    host._showToast(t('Imported YAML for "{name}"').replace('{name}', result.device), "success");
  } catch (e) {
    host._showToast(e.message || t("Import failed"), "error");
  }
}

/* ── helpers ─────────────────────────────────────────────────────────────── */

/**
 * Create a downloadable file in the browser.
 */
function downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Open a file picker restricted to YAML files and return the selected File.
 * @returns {Promise<File|null>}
 */
function pickYamlFile() {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".yaml,.yml";
    input.onchange = () => {
      const file = input.files && input.files[0];
      resolve(file || null);
    };
    input.oncancel = () => resolve(null);
    input.click();
  });
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

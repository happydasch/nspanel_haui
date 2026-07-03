/**
 * NSPanel HAUI - Device manager event handlers.
 *
 * Extracted from haui-editor.js; each function takes the component instance
 * (`host`) as its first parameter.
 */
import { clone } from './constants.js';
import { t } from './localize.js';
import * as Api from './api.js';

export async function onDeviceManagerMoveDevice(host, e) {
  const { name, direction } = e.detail || {};
  if (!name || !direction) return;
  const devices = host._panels.devices || {};
  const deviceKeys = Object.keys(devices);
  const idx = deviceKeys.indexOf(name);
  if (idx < 0) return;
  const swapIdx = idx + direction;
  if (swapIdx < 0 || swapIdx >= deviceKeys.length) return;

  const newKeys = [...deviceKeys];
  [newKeys[idx], newKeys[swapIdx]] = [newKeys[swapIdx], newKeys[idx]];

  const newDevices = {};
  for (const key of newKeys) {
    newDevices[key] = devices[key];
  }
  host._panels = { ...host._panels, devices: newDevices };
  const label = direction < 0 ? "up" : "down";
  await host._savePanels(host._devicePanels(), t('Device "{name}" moved {direction}').replace('{name}', name).replace('{direction}', label));
}

export async function onDeviceManagerToggleDevice(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  const devices = host._panels.devices || {};
  const dev = devices[name];
  if (!dev) return;
  const config = dev.config || {};
  const newEnabled = !(config.enabled !== false);

  host._panels = {
    ...host._panels,
    devices: {
      ...devices,
      [name]: { ...dev, config: { ...config, enabled: newEnabled } },
    },
  };
  host.requestUpdate();

  try {
    const payload = clone(host._panels);
    if (!payload.devices[name].panels) payload.devices[name].panels = [];

    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/panels/${host.entryId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (resp.ok) {
      host._panels = payload;
      host._showToast(`"${name}" ${t(newEnabled ? "enabled" : "disabled")}`, "success");
    } else {
      const err = await resp.json().catch(() => ({}));
      host._panels = {
        ...host._panels,
        devices: {
          ...devices,
          [name]: dev,
        },
      };
      host._showToast(err.message || t("Save failed"), "error");
    }
  } catch (e) {
    host._panels = {
      ...host._panels,
      devices: {
        ...devices,
        [name]: dev,
      },
    };
    host._showToast(e.message || t("Network error"), "error");
  }
  host.requestUpdate();
}

export function onDeviceManagerSelect(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  host._selectDevice(name);
}

export function onDeviceManagerSettings(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  host._showDeviceManager = false;
  host._selectedDevice = name;
  host._loadDeviceConfig(name);
  host._openDeviceConfig();
  host.requestUpdate();
}

export async function onDeviceManagerRemove(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    await Api.removeDevice(host, name);
    await Api.loadPanels(host);
    host._showToast(t('Removed "{name}"').replace('{name}', name), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to remove device"), "error");
  }
  host.requestUpdate();
}

export async function onDeviceManagerAdd(host, e) {
  const device = e.detail?.device;
  if (!device) return;
  try {
    await Api.addDevice(host, device);
    await Api.loadPanels(host);
    host._showToast(t('Added "{name}"').replace('{name}', device.name), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to add device"), "error");
  }
  host.requestUpdate();
}

export async function onDeviceManagerImportYaml(host) {
  const { importDeviceYaml } = await import('./device-manager.js');
  host._showDeviceManager = false;
  importDeviceYaml(host);
  host.requestUpdate();
}

export async function onDeviceManagerExportYaml(host) {
  const { exportDeviceYaml } = await import('./device-manager.js');
  host._showDeviceManager = false;
  exportDeviceYaml(host);
  host.requestUpdate();
}

export async function onDeviceManagerUpdateDisplay(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    const result = await Api.updateDeviceDisplay(host, name);
    const count = result.devices_updated?.length || 0;
    if (name === "*") {
      host._showToast(t('Updated display for {count} device(s)').replace('{count}', count), "success");
    } else {
      host._showToast(t('Display updated for "{name}"').replace('{name}', name), "success");
    }
  } catch (err) {
    host._showToast(err.message || t("Failed to update display"), "error");
  }
}